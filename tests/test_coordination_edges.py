"""Migration and stale-owner regressions; never touches a live project."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import test_supervisor as fixture

mod = fixture.mod


class CoordinationEdges(unittest.TestCase):
    setUp = fixture.SupervisorTests.setUp
    tearDown = fixture.SupervisorTests.tearDown
    git = fixture.SupervisorTests.git
    write = fixture.SupervisorTests.write
    op = fixture.SupervisorTests.op

    def activate(self):
        self.op('coordination', action='activate', source_ref='test:drained')

    def legacy_run(self):
        # Fixture represents the exactly allowlisted predecessor; archive remains untouched.
        state = self.sup.load(self.run)
        state.update(version='0.7.1', graph_digest=mod.digest(mod.LEGACY_GRAPH))
        self.sup.save(state, 'legacy_fixture', {})
        return state

    def test_adoption_preserves_receipts_and_rejects_dirty_or_wrong_version(self):
        self.activate()
        state = self.legacy_run()
        before = self.sup.db.execute('SELECT state FROM events WHERE run_id=? ORDER BY sequence', (self.run,)).fetchall()
        self.write('uncommitted', 'dirty')
        with self.assertRaisesRegex(mod.GateError, 'clean checkpoint'):
            self.op('adopt', source_ref='test:approved')
        self.git('add', 'uncommitted')
        self.git('commit', '-qm', 'checkpoint')
        self.op('adopt', source_ref='test:approved')
        after = self.sup.load(self.run)
        self.assertEqual(after['receipts'], state['receipts'])
        self.assertEqual(after['plan_epoch'], state['plan_epoch'])
        self.assertEqual([r[0] for r in before], [r[0] for r in self.sup.db.execute('SELECT state FROM events WHERE run_id=? ORDER BY sequence LIMIT ?', (self.run,len(before)))])
        with self.assertRaisesRegex(mod.GateError, 'version differs'):
            self.op('adopt', source_ref='test:retry-no-silent-conversion')

    def test_adoption_rejects_pending_execution_and_changed_assertions(self):
        self.activate()
        self.op('lock', source_ref='test', basis='approved')
        self.op('plan', source_ref='test', checks=[self.check])
        self.op('lease', action='acquire')
        self.op('coordination', action='tests', resources=[], source_ref='test:pure-function')
        self.op('check', id='sum', phase='red')
        self.op('freeze')
        state = self.legacy_run()
        state['execution'] = {'controller_pid':99999999}
        self.sup.save(state, 'pending_fixture', {})
        with self.assertRaisesRegex(mod.GateError, 'pending'):
            self.op('adopt', source_ref='test')
        state['execution'] = None
        self.sup.save(state, 'finished_fixture', {})
        self.write('test_product.py', 'assert True\n')
        self.git('add', 'test_product.py')
        self.git('commit', '-qm', 'changed assertions')
        with self.assertRaisesRegex(mod.GateError, 'candidate changed'):
            self.op('adopt', source_ref='test')

    def test_actual_old_package_cannot_write_after_activation(self):
        # Reconstruct the committed predecessor locally, not a fake controller.
        root = Path(__file__).resolve().parents[1]
        old_dir = self.repo / '.git' / 'old-package'
        (old_dir/'scripts').mkdir(parents=True)
        (old_dir/'references').mkdir()
        result = subprocess.run(['git','-C',str(root),'show','e2170e5:sop-slop/scripts/supervisor.py'], capture_output=True, check=True)
        (old_dir/'scripts/supervisor.py').write_bytes(result.stdout)
        (old_dir/'references/supervisor-graph.json').write_text(json.dumps(mod.LEGACY_GRAPH))
        self.activate()
        self.legacy_run()
        base = [sys.executable, str(old_dir/'scripts/supervisor.py')]
        flags = ['--repo',str(self.repo),'--run',self.run,'--actor','controller']
        for op, data, success in [('status',{},True), ('lease',{'action':'acquire'},False), ('input',{'id':'new','summary':'test','source_ref':'test'},False)]:
            result = subprocess.run(base+[op]+flags, input=json.dumps(data), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0 if success else 2, result.stderr)
        self.assertFalse(self.sup.db.execute('SELECT 1 FROM writer').fetchone())

    def test_migration_reservation_survives_cleanup_and_conflicts(self):
        self.activate()
        self.op('lease', action='acquire')
        data = dict(action='reserve-migration', id='20260928090000', path='supabase/migrations/20260928090000_one.sql', source_ref='test')
        self.op('coordination', **data)
        self.op('stop', status='blocked', reason='fixture stop')
        self.op('cleanup', note='retain allocation', dispositions={})
        self.assertTrue(self.sup.db.execute('SELECT 1 FROM migration_ids').fetchone())
        self.assertFalse(self.sup.db.execute('SELECT 1 FROM claims').fetchone())
        other = self.sup.operate('start', {**self.contract,'actor':'other'})['id']
        self.sup.operate('lease', {'action':'acquire'}, other, 'other')
        with self.assertRaisesRegex(mod.GateError, 'already reserved'):
            self.sup.operate('coordination', data, other, 'other')

    def test_pending_execution_keeps_claims_and_queue(self):
        self.activate()
        self.op('lease', action='acquire')
        status = self.op('lease', action='acquire', key='delivery')
        token = next(c['token'] for c in status['coordination']['claims'] if c['key']=='delivery')
        state = self.sup.load(self.run)
        state['execution'] = {'controller_pid':99999999}
        self.sup.save(state, 'pending_fixture', {})
        with self.assertRaisesRegex(mod.GateError, 'execution'):
            self.op('lease', action='release', key='delivery', token=token)
        self.assertEqual(self.sup.db.execute("SELECT token FROM claims WHERE key='delivery'").fetchone()[0], token)

    def test_four_processes_race_for_single_delivery_owner(self):
        self.activate()
        runs = []
        for i in range(4):
            path = self.repo / '.git' / ('race-' + str(i))
            self.git('worktree','add','-qb','race-'+str(i),str(path))
            sup = mod.Supervisor(path)
            actor = 'race-' + str(i)
            run = sup.operate('start', {**self.contract,'actor':actor})['id']
            sup.operate('lease', {'action':'acquire'}, run, actor)
            sup.close()
            runs.append((path,run,actor))
        processes = []
        try:
            for path,run,actor in runs:
                child = subprocess.Popen([sys.executable,str(fixture.SCRIPT),'lease','--repo',str(path),'--run',run,'--actor',actor], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                processes.append(child)
                child.stdin.write('{"action":"acquire","key":"delivery"}')
                child.stdin.close()
            for child in processes:
                child.wait(timeout=15)
                self.assertEqual(child.returncode,0,child.stderr.read())
            self.assertEqual(self.sup.db.execute("SELECT COUNT(*) FROM claims WHERE key='delivery'").fetchone()[0],1)
            self.assertEqual(self.sup.db.execute("SELECT COUNT(*) FROM claim_queue WHERE key='delivery'").fetchone()[0],3)
        finally:
            for child in processes:
                if child.poll() is None:
                    child.kill()
                    child.wait()
                child.stdout.close()
                child.stderr.close()

    def test_delivery_can_verify_shared_tests_without_reverse_lock_order(self):
        self.activate()
        self.op('lock', source_ref='test', basis='approved')
        self.op('plan', source_ref='test', checks=[self.check])
        self.op('lease', action='acquire')
        delivery = self.op('lease', action='acquire', key='delivery')
        delivery_token = next(c['token'] for c in delivery['coordination']['claims'] if c['key']=='delivery')
        shared = self.op('lease', action='acquire', key='test:unclassified')
        test_token = next(c['token'] for c in shared['coordination']['claims'] if c['key']=='test:unclassified')
        self.assertEqual(self.op('check', id='sum', phase='red')['result'], 'expected_failure')
        with self.assertRaisesRegex(mod.GateError, 'release test'):
            self.op('lease', action='release', key='delivery', token=delivery_token)
        self.op('lease', action='release', key='test:unclassified', token=test_token)
        self.op('lease', action='release', key='delivery', token=delivery_token)

    def test_read_only_run_can_use_test_resource_without_writer(self):
        self.activate()
        self.op('revise', reason='artifact review', source_ref='test', contract={**self.contract,'lane':'review-only','target':'review_complete'})
        self.op('lock', source_ref='test', basis='approved')
        self.op('plan', source_ref='test', checks=[{**self.check,'kind':'artifact','require_red':False,'argv':[sys.executable,'-c','print("review")']}])
        for key in ['worktree:' + str(self.sup.repo), 'delivery']:
            with self.assertRaisesRegex(mod.GateError,'review/decision'):
                self.op('lease', action='acquire', key=key)
        self.op('lease', action='acquire', key='test:unclassified')
        self.op('freeze')
        self.assertEqual(self.op('check', id='sum')['result'],'pass')

    def test_nonempty_valid_receipts_survive_preflight_and_adoption(self):
        self.activate()
        self.op('lock', source_ref='test', basis='approved')
        self.op('plan', source_ref='test', checks=[self.check])
        self.op('lease', action='acquire')
        self.op('coordination', action='tests', resources=[], source_ref='test:pure-function')
        self.op('check', id='sum', phase='red')
        state = self.legacy_run()
        preflight = self.op('adopt-check', source_ref='test')
        self.assertTrue(preflight['ready'])
        self.op('adopt', source_ref='test')
        self.assertEqual(self.sup.load(self.run)['receipts'],state['receipts'])
        self.assertGreater(len(state['receipts']),0)

    def test_stale_dormant_run_has_explicit_replan_recovery_after_fencing(self):
        self.activate()
        self.op('lock', source_ref='test', basis='approved')
        self.op('plan', source_ref='test', checks=[self.check])
        self.op('lease', action='acquire')
        self.op('freeze')
        self.legacy_run()
        self.write('product.py','def total(values): return sum(values)\n')
        self.git('add','product.py')
        self.git('commit','-qm','changed checkpoint')
        with self.assertRaisesRegex(mod.GateError,'candidate changed'):
            self.op('adopt-check', source_ref='test')
        self.assertEqual(self.op('adopt', source_ref='test:explicit-replan', replan=True)['phase'],'plan')

    def test_branch_alias_and_changed_branch_are_rejected(self):
        self.activate()
        self.op('lease',action='acquire')
        branch = self.git('symbolic-ref','--short','HEAD').decode().strip()
        path = self.repo / '.git' / 'alias'
        self.git('worktree','add','--force',str(path),branch)
        other = mod.Supervisor(path)
        self.addCleanup(other.close)
        run = other.operate('start',{**self.contract,'actor':'alias'})['id']
        with self.assertRaisesRegex(mod.GateError,'branch already owned'):
            other.operate('lease',{'action':'acquire'},run,'alias')
        self.git('switch','-qc','changed-branch')
        with self.assertRaisesRegex(mod.GateError,'claimed branch changed'):
            self.sup.has_writer(self.sup.load(self.run))


if __name__ == '__main__':
    unittest.main(verbosity=2)
