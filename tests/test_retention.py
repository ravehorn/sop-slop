"""Retention tests use only synthetic files and isolated supervisor databases."""
import copy
import tempfile
from pathlib import Path
import unittest
import test_supervisor as fixture

mod = fixture.mod


class RetentionTests(unittest.TestCase):
    setUp = fixture.SupervisorTests.setUp
    tearDown = fixture.SupervisorTests.tearDown
    git = fixture.SupervisorTests.git
    write = fixture.SupervisorTests.write
    op = fixture.SupervisorTests.op
    plan = fixture.SupervisorTests.plan
    green = fixture.SupervisorTests.green

    def artifact(self, path, kind='scratch'):
        path.write_text('regenerable fixture')
        self.op('resource', id='scratch', path=str(path.resolve()), kind=kind, source_ref='test:owned')

    def decision(self):
        return {'dispositions': {'scratch': {'state': 'release',
            'reason': 'last consumer complete', 'authority_source': 'test:exact target approval',
            'inspection_source': 'test:stopped owner and no dependencies',
            'no_longer_needed': True, 'holds': []}}}

    def release(self):
        return {'dispositions': {'scratch': {'state': 'released',
            'reason': 'fixture removed', 'source_ref': 'test:unlink observed'}}, 'note': 'fixture cleanup'}

    def test_feature_is_available(self):
        self.assertTrue(hasattr(mod.Supervisor, 'retention_decision'), 'retention lifecycle missing')

    def test_release_needs_completed_delivery_and_explicit_authority(self):
        with tempfile.TemporaryDirectory() as root:
            self.artifact(Path(root) / 'scratch')
            with self.assertRaises(mod.GateError):
                self.op('retention', **self.decision())
            self.green()
            self.op('seal')
            bad = self.decision()
            del bad['dispositions']['scratch']['authority_source']
            with self.assertRaises(mod.GateError):
                self.op('retention', **bad)
            self.op('retention', **self.decision())
            with self.assertRaisesRegex(mod.GateError, 'still exists'):
                self.op('cleanup', **self.release())
            (Path(root) / 'scratch').unlink()
            self.op('cleanup', **self.release())
            self.op('finish', classification='no_issue', finding='safe release', source_ref='test')
            self.assertEqual(self.op('audit')['integrity'], 'pass')

    def test_absence_without_predecision_is_not_release_proof(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'scratch'
            self.artifact(path)
            self.green()
            self.op('seal')
            path.unlink()
            with self.assertRaises(mod.GateError):
                self.op('cleanup', **self.release())
            with self.assertRaises(mod.GateError):
                self.op('retention', **self.decision())

    def test_preservation_and_terminal_revisit_leave_authority_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'scratch'
            self.artifact(path)
            self.green()
            self.op('seal')
            self.op('cleanup', note='keep until consumer finishes', dispositions={
                'scratch': {'state': 'preserved', 'reason': 'consumer still needs it', 'revisit_when': 'consumer finishes'}})
            self.op('finish', classification='no_issue', finding='retained safely', source_ref='test')
            before = copy.deepcopy(self.sup.load(self.run))
            self.op('retention', **self.decision())
            path.unlink()
            self.op('retention-reconcile', **self.release())
            after = self.sup.load(self.run)
            for key in ('delivery', 'terminal', 'run_review', 'contract', 'repairs', 'candidate', 'receipts', 'cleanup'):
                self.assertEqual(before[key], after[key], key)
            self.assertEqual(after['resources'][0]['disposition']['state'], 'released')

    def test_stale_decision_and_peer_overlap_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'scratch'
            self.artifact(path)
            self.green()
            self.op('seal')
            self.op('retention', **self.decision())
            self.op('input', id='new', summary='question', source_ref='test')
            with self.assertRaises(mod.GateError):
                self.op('cleanup', **self.release())
            self.op('classify', id='new', classification='result_question', reason='no change')
            other = self.sup.operate('start', {**self.contract, 'actor': 'other'})['id']
            self.sup.operate('resource', {'id': 'shared', 'path': str(Path(root).resolve()), 'kind': 'scratch',
                'source_ref': 'test:peer'}, other, 'other')
            with self.assertRaisesRegex(mod.GateError, 'peer'):
                self.op('retention', **self.decision())

    def test_protected_paths_and_required_evidence_are_preserved(self):
        for kind in ('audit', 'approval', 'database', 'worktree'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as root:
                # Independent fixture for each classification.
                path = Path(root) / 'scratch'
                if not self.sup.load(self.run)['resources']:
                    self.artifact(path, kind)
                    self.green()
                    self.op('seal')
                state = self.sup.load(self.run)
                state['resources'][0].update(kind=kind, path=str(path))
                self.sup.save(state, 'test_fixture', {})
                with self.assertRaises(mod.GateError):
                    self.op('retention', **self.decision())

    def test_pending_execution_prevents_cleanup_and_keeps_writer(self):
        self.green()
        self.op('seal')
        state = self.sup.load(self.run)
        state['execution'] = {'controller_pid': 99999999}
        self.sup.save(state, 'test_fixture', {})
        with self.assertRaisesRegex(mod.GateError, 'execution'):
            self.op('cleanup', note='must not release writer', dispositions={})
        self.assertIsNotNone(self.sup.db.execute('SELECT * FROM writer').fetchone())

    def test_identity_change_symlink_and_hold_block_preaction(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'scratch'
            self.artifact(path)
            self.green()
            self.op('seal')
            bad = self.decision()
            bad['dispositions']['scratch']['holds'] = ['audit']
            with self.assertRaises(mod.GateError):
                self.op('retention', **bad)
            self.op('retention', **self.decision())
            self.op('retention-check')
            path.write_text('changed after approval')
            with self.assertRaisesRegex(mod.GateError, 'identity changed'):
                self.op('retention-check')
            path.unlink()
            path.symlink_to(Path(root) / 'missing')
            with self.assertRaises(mod.GateError):
                self.op('retention', **self.decision())

    def test_pending_work_preserves_resources(self):
        with tempfile.TemporaryDirectory() as root:
            self.artifact(Path(root) / 'scratch')
            self.green()
            self.op('seal')
            self.op('work', key='later', kind='dependency', title='Consumer', reason='needs evidence', source_ref='test')
            with self.assertRaisesRegex(mod.GateError, 'pending work'):
                self.op('retention', **self.decision())

    def test_redundant_evidence_requires_recovery_proof(self):
        with tempfile.TemporaryDirectory() as root:
            self.artifact(Path(root) / 'scratch', 'redundant_evidence')
            self.green()
            self.op('seal')
            with self.assertRaises(mod.GateError):
                self.op('retention', **self.decision())
            decision = self.decision()
            decision['dispositions']['scratch'].update(replacement_source='test:retained audit manifest',
                                                       restore_source='test:verified restoration')
            self.op('retention', **decision)
            self.assertIn('decision_digest', self.op('retention-check'))

    def test_repository_resource_is_never_disposable(self):
        self.artifact(self.repo / 'source')
        self.green()
        self.op('seal')
        with self.assertRaisesRegex(mod.GateError, 'protected resource path'):
            self.op('retention', **self.decision())

    def test_old_run_is_not_silently_adopted(self):
        state = self.sup.load(self.run)
        state.update(version='0.8.2', graph_digest=mod.digest(mod.READINESS_GRAPH))
        self.sup.save(state, 'legacy_fixture', {})
        before = self.sup.db.execute('SELECT state FROM runs WHERE id=?', (self.run,)).fetchone()[0]
        with self.assertRaisesRegex(mod.GateError, 'version differs'):
            self.op('retention', dispositions={})
        self.assertEqual(before, self.sup.db.execute('SELECT state FROM runs WHERE id=?', (self.run,)).fetchone()[0])

    def test_same_run_nested_evidence_blocks_parent_disposal(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root).resolve()
            child = parent / 'audit'
            child.write_text('required evidence')
            self.op('resource', id='scratch', path=str(parent), kind='scratch', source_ref='test')
            self.op('resource', id='audit', path=str(child), kind='audit', source_ref='test')
            self.green()
            self.op('seal')
            decision = self.decision()
            decision['dispositions']['audit'] = {'state': 'preserve', 'reason': 'audit', 'revisit_when': 'reviewed expiry'}
            with self.assertRaisesRegex(mod.GateError, 'same-run'):
                self.op('retention', **decision)

    def test_queued_claims_and_continuations_block_release(self):
        with tempfile.TemporaryDirectory() as root:
            self.artifact(Path(root) / 'scratch')
            self.green()
            self.op('seal')
            self.sup.db.execute('INSERT INTO claim_queue(key,run_id) VALUES(?,?)', ('delivery', self.run))
            with self.assertRaisesRegex(mod.GateError, 'claim requests'):
                self.op('retention', **self.decision())
            self.sup.db.execute('DELETE FROM claim_queue')
            other = self.sup.operate('start', {**self.contract, 'actor': 'other'})['id']
            state = self.sup.load(other)
            state['contract']['continues_run'] = self.run
            state['contract_digest'] = mod.digest(state['contract'])
            self.sup.save(state, 'synthetic_continuation_fixture', {})
            with self.assertRaisesRegex(mod.GateError, 'continuation'):
                self.op('retention', **self.decision())

    def test_terminal_revisit_keeps_peer_claims_and_authority(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'scratch'
            self.artifact(path)
            self.green()
            self.op('authorize', actions=['commit'], source_ref='test:authority')
            self.op('seal')
            self.op('cleanup', note='retained', dispositions={'scratch': {
                'state': 'preserved', 'reason': 'consumer', 'revisit_when': 'consumer finished'}})
            self.op('finish', classification='no_issue', finding='retained', source_ref='test')
            other = self.sup.operate('start', {**self.contract, 'actor': 'other'})['id']
            self.sup.db.execute('INSERT INTO claims VALUES(?,?,?,?)', ('delivery', other, 'peer-token', None))
            self.sup.db.execute('INSERT INTO claim_queue(key,run_id) VALUES(?,?)', ('test:shared', other))
            before = copy.deepcopy(self.sup.load(self.run))
            claims = [tuple(r) for r in self.sup.db.execute('SELECT * FROM claims')]
            queue = [tuple(r) for r in self.sup.db.execute('SELECT * FROM claim_queue')]
            self.op('retention', **self.decision())
            self.op('retention-check')
            path.unlink()
            self.op('retention-reconcile', **self.release())
            after = self.sup.load(self.run)
            for key in before:
                if key not in ('revision', 'updated_at', 'resources'):
                    self.assertEqual(before[key], after[key], key)
            self.assertEqual(claims, [tuple(r) for r in self.sup.db.execute('SELECT * FROM claims')])
            self.assertEqual(queue, [tuple(r) for r in self.sup.db.execute('SELECT * FROM claim_queue')])
