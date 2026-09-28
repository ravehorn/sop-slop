"""Disposable, real Git/SQLite/process probes for coordination protocol 1."""
import json
import subprocess
import sys
import time
import unittest
from test_supervisor import SupervisorTests, mod, SCRIPT


class CoordinationTests(unittest.TestCase):
    setUp = SupervisorTests.setUp
    tearDown = SupervisorTests.tearDown
    git = SupervisorTests.git
    write = SupervisorTests.write
    op = SupervisorTests.op

    def activate(self):
        try:
            return self.op('coordination', action='activate', source_ref='test:drained')
        except mod.GateError as e:
            self.fail('scoped coordination must activate: ' + str(e))

    def peer(self, name):
        path = self.repo / '.git' / ('peer-' + name)
        self.git('worktree', 'add', '-qb', name, str(path))
        sup = mod.Supervisor(path)
        self.addCleanup(sup.close)
        run = sup.operate('start', {**self.contract, 'actor':name})['id']
        return sup, run, name

    def call(self, peer, op, **data):
        return peer[0].operate(op, data, peer[1], peer[2])

    def token(self, status, key):
        return next(c['token'] for c in status['coordination']['claims'] if c['key'] == key)

    def test_distinct_worktrees_and_same_checkout_exclusion(self):
        self.activate()
        self.op('lease', action='acquire')
        peer = self.peer('peer')
        self.call(peer, 'lease', action='acquire')
        rival = self.sup.operate('start', {**self.contract, 'actor':'rival'})['id']
        with self.assertRaisesRegex(mod.GateError, 'owned'):
            self.sup.operate('lease', {'action':'acquire'}, rival, 'rival')
        self.assertEqual(len(self.op('status')['coordination']['claims']), 1)

    def test_fifo_delivery_cancellation_and_stale_token(self):
        self.activate()
        peers = [(self.sup, self.run, 'controller'), self.peer('b'), self.peer('c'), self.peer('d')]
        for p in peers:
            self.call(p, 'lease', action='acquire')
        owner = self.call(peers[0], 'lease', action='acquire', key='delivery')
        token = self.token(owner, 'delivery')
        for p in peers[1:]:
            self.assertEqual(self.call(p, 'lease', action='acquire', key='delivery')['coordination']['waiting'], ['delivery'])
        self.call(peers[1], 'lease', action='cancel', key='delivery')
        with self.assertRaisesRegex(mod.GateError, 'token'):
            self.call(peers[0], 'lease', action='release', key='delivery', token='stale')
        self.call(peers[0], 'lease', action='release', key='delivery', token=token)
        self.assertEqual(self.call(peers[3], 'lease', action='acquire', key='delivery')['coordination']['waiting'], ['delivery'])
        result = self.call(peers[2], 'lease', action='acquire', key='delivery')
        self.assertTrue(self.token(result, 'delivery'))

    def test_resources_are_exclusive_and_not_stolen_after_restart(self):
        self.activate()
        self.op('lease', action='acquire')
        self.op('lease', action='acquire', key='test:db-one')
        peer = self.peer('peer')
        self.call(peer, 'lease', action='acquire')
        self.assertEqual(self.call(peer, 'lease', action='acquire', key='test:db-one')['coordination']['waiting'], ['test:db-one'])
        self.sup.close()
        self.sup = mod.Supervisor(self.repo)
        self.assertTrue(self.token(self.op('status'), 'test:db-one'))
        with self.assertRaisesRegex(mod.GateError, 'one shared'):
            self.op('lease', action='acquire', key='delivery')

    def test_activation_drains_writer_and_all_pending_executions(self):
        self.op('lease', action='acquire')
        with self.assertRaisesRegex(mod.GateError, 'legacy writer'):
            self.op('coordination', action='activate', source_ref='test')
        self.op('lease', action='release')
        state = self.sup.load(self.run)
        state['execution'] = {'controller_pid': 99999999}
        self.sup.save(state, 'fixture_pending', {})
        with self.assertRaisesRegex(mod.GateError, 'execution'):
            self.op('coordination', action='activate', source_ref='test')

    def test_legacy_connection_fenced_but_reads_survive(self):
        import sqlite3
        old = sqlite3.connect(self.sup.home / 'runs.sqlite3')
        self.addCleanup(old.close)
        self.activate()
        self.assertEqual(old.execute('SELECT COUNT(*) FROM runs').fetchone()[0], 1)
        for sql in ("UPDATE runs SET state=state", "INSERT INTO writer VALUES(1,'legacy','actor')"):
            with self.assertRaises(sqlite3.DatabaseError):
                old.execute(sql)
            old.rollback()

    def test_mailbox_cursor_idempotency_and_checkpoint(self):
        self.activate()
        peer = self.peer('peer')
        self.op('checkpoint', thread_id='thread-one', summary='contract ready', contracts=['recipe'], dependencies=[])
        message = dict(key='ready-one', recipient=peer[1], kind='dependency_ready', body='Use committed contract at HEAD')
        first = self.op('signal', **message)
        self.assertEqual(first, self.op('signal', **message))
        inbox = self.call(peer, 'inbox', after=0)
        self.assertEqual(len(inbox['events']), 1)
        self.assertEqual(self.call(peer, 'inbox', after=inbox['cursor'])['events'], [])
        with self.assertRaisesRegex(mod.GateError, 'reused'):
            self.op('signal', **{**message, 'body':'different'})

    def test_parallel_checks_overlap_in_four_processes(self):
        self.activate()
        peers = [(self.sup, self.run, 'controller')] + [self.peer(n) for n in ['b','c','d']]
        children = []
        for p in peers:
            self.call(p, 'lock', source_ref='test', basis='approved')
            check = {**self.check, 'argv':[sys.executable, '-c', 'import time; time.sleep(1); print("isolated")'], 'require_red':False}
            self.call(p, 'plan', source_ref='test', checks=[check])
            self.call(p, 'lease', action='acquire')
            self.call(p, 'coordination', action='tests', resources=[], source_ref='test:process-only-no-shared-state')
            self.call(p, 'freeze')
            child = subprocess.Popen([sys.executable, str(SCRIPT), 'check', '--repo',str(p[0].repo),'--run',p[1],'--actor',p[2]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(child)
            child.stdin.write('{"id":"sum"}')
            child.stdin.close()
        receipts = []
        for child in children:
            child.wait(timeout=20)
            output, error = child.stdout.read(), child.stderr.read()
            child.stdout.close()
            child.stderr.close()
            self.assertEqual(child.returncode, 0, error)
            receipts.append(json.loads(output))
        self.assertLess(max(r['started_at'] for r in receipts), min(r['finished_at'] for r in receipts))
        self.assertTrue(all(r['result']=='pass' for r in receipts))

    def test_unclassified_checks_need_explicit_test_lock(self):
        self.activate()
        self.op('lock', source_ref='test', basis='approved')
        self.op('plan', source_ref='test', checks=[self.check])
        self.op('lease', action='acquire')
        with self.assertRaisesRegex(mod.GateError, 'test:unclassified'):
            self.op('check', id='sum', phase='red')
        self.op('lease', action='acquire', key='test:unclassified')
        self.assertEqual(self.op('check', id='sum', phase='red')['result'], 'expected_failure')


if __name__ == '__main__':
    unittest.main(verbosity=2)
