"""Failure probes for readiness, declared continuation and scoped reuse."""
import copy
import unittest
import test_execution_gates as gates

m = gates.m


class GateEdges(unittest.TestCase):
    setUp = gates.ExecutionGates.setUp
    tearDown = gates.ExecutionGates.tearDown
    git = gates.ExecutionGates.git
    write = gates.ExecutionGates.write
    op = gates.ExecutionGates.op
    plan = gates.ExecutionGates.plan

    def test_recovered_prerequisite_does_not_restore_old_downstream_pass(self):
        self.plan(freeze_requires=['sum'])
        self.op('check',id='ready')
        self.op('check',id='sum')
        self.write('.git/broken','1')
        self.op('check',id='ready')
        (self.repo/'.git/broken').unlink()
        self.op('check',id='ready')
        with self.assertRaisesRegex(m.GateError,'prerequisite'):
            self.op('freeze')
        self.op('check',id='sum')
        self.op('freeze')
        self.op('seal')

    def test_revision_cannot_reset_budget_or_drop_continuation(self):
        self.plan()
        self.op('freeze')
        self.op('repair',reason='real repair')
        self.op('stop',status='blocked',reason='dependent unavailable')
        self.op('cleanup',note='disposable',dispositions={})
        self.op('finish',classification='executor_issue',finding='retained budget',source_ref='test')
        linked={**self.contract,'continues_run':self.run}
        child=self.sup.operate('start',linked)['id']
        for contract in [{**linked,'repair_budget':4},self.contract]:
            with self.assertRaises(m.GateError):
                self.sup.operate('revise',{'contract':contract,'reason':'reset attempt','source_ref':'test'},child,'controller')
        self.assertEqual(self.sup.load(child)['repairs'],1)
        self.assertNotIn('additional_authority',self.sup.load(child))
        with self.assertRaises(m.GateError):
            self.sup.operate('start',linked)

    def test_continuation_parent_integrity_and_active_owner(self):
        with self.assertRaises(m.GateError):
            self.sup.operate('start',{**self.contract,'continues_run':self.run})
        self.plan()
        self.op('stop',status='blocked',reason='fixture')
        self.op('cleanup',note='disposable',dispositions={})
        self.op('finish',classification='no_issue',finding='fixture',source_ref='test')
        state=self.sup.load(self.run)
        state['graph_digest']='unknown'
        self.sup.save(state,'corrupt_fixture',{})
        with self.assertRaisesRegex(m.GateError,'graph'):
            self.sup.operate('start',{**self.contract,'continues_run':self.run})


class ReuseGateEdges(unittest.TestCase):
    setUp = gates.ScopedReuse.setUp
    tearDown = gates.ScopedReuse.tearDown
    git = gates.ScopedReuse.git
    write = gates.ScopedReuse.write
    op = gates.ScopedReuse.op
    baseline = gates.ScopedReuse.baseline
    refreeze = gates.ScopedReuse.refreeze
    reuse = gates.ScopedReuse.reuse
    scoped = gates.ScopedReuse.scoped

    def test_reuse_environment_cannot_create_implicit_cycle(self):
        self.baseline()
        self.op('revise',reason='cycle probe',source_ref='test')
        with self.assertRaisesRegex(m.GateError,'cyclic'):
            self.op('plan',source_ref='test',checks=[{**self.env,'requires':['sum']},self.product])

    def test_frozen_head_only_change_rebinds_without_repair_or_new_epoch(self):
        self.scoped()
        self.op('freeze')
        before=self.sup.load(self.run)
        self.git('commit','--allow-empty','-qm','new HEAD identical content')
        try:
            self.op('check',id='environment')
            self.reuse()
        except m.GateError as error:
            self.fail('identity refresh and explicit reuse must not spend repair budget: '+str(error))
        with self.assertRaisesRegex(m.GateError,'candidate changed'):
            self.op('seal')
        self.op('freeze')
        with self.assertRaisesRegex(m.GateError,'independent review'):
            self.op('seal')
        self.op('review',reviewer='independent',disposition='accepted',finding='Fixture candidate unchanged',source_ref='test:review')
        self.op('seal')
        after=self.sup.load(self.run)
        self.assertEqual((after['repairs'],after['plan_epoch']),(before['repairs'],before['plan_epoch']))
        self.assertEqual((self.repo/'.git/executions').read_text(),'xx')

    def test_scoped_reuse_rejects_stale_self_review_and_keeps_review_full_scope(self):
        self.scoped()
        self.op('freeze')
        self.op('review',reviewer='independent',disposition='accepted',finding='actual scope',source_ref='review')
        original_review=copy.deepcopy(self.sup.load(self.run)['review'])
        self.write('unrelated.py','value=1\n')
        self.git('add','.')
        self.git('commit','-qm','unrelated code')
        self.op('repair',reason='outside scope change')
        self.op('check',id='environment')
        after=self.sup.reuse_dependencies(self.sup.load(self.run),self.policy['narrative_paths'],self.policy['dependency_paths'])
        impact={'before':self.original['reuse_evidence']['outside_dependencies'],'after':after['outside_dependencies'],
                'reviewer':'independent','source_ref':'actual review','finding':'Complete closure unaffected'}
        for bad in [{**impact,'after':'stale'},{**impact,'reviewer':'controller'}]:
            with self.assertRaises(m.GateError):
                self.reuse(impact_review=bad)
        self.reuse(impact_review=impact)
        self.op('freeze')
        with self.assertRaises(m.GateError):
            self.op('review-reuse',source_review_id=original_review['id'],source_ref='test')

    def test_scoped_paths_reject_symlink_alias_and_deleted_dependency(self):
        self.scoped()
        (self.repo/'alias').symlink_to(self.repo,target_is_directory=True)
        with self.assertRaises(m.GateError):
            self.sup.dependency_paths(['alias/product.py'])
        (self.repo/'product.py').unlink()
        with self.assertRaises(m.GateError):
            self.reuse()

    def test_exact_081_adoption_preserves_proof_without_new_gates(self):
        self.op('coordination',action='activate',source_ref='test:drained')
        self.op('coordination',action='tests',resources=[],source_ref='test:isolated')
        self.baseline()
        self.git('add','.')
        self.git('commit','-qm','clean')
        self.op('freeze')
        before=self.sup.load(self.run)
        before.update(version=m.REUSE_GRAPH['version'],graph_digest=m.digest(m.REUSE_GRAPH))
        before.pop('freeze_requires',None)
        self.sup.save(before,'081_fixture',{})
        self.op('adopt',source_ref='test:approved')
        after=self.sup.load(self.run)
        for key in ['receipts','review_history','plan_epoch']:
            self.assertEqual(after[key],before[key])
        self.assertNotIn('freeze_requires',after)
        self.assertEqual(after['version'],m.VERSION)


if __name__=='__main__':
    unittest.main(verbosity=2)
