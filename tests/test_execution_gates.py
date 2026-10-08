"""Early execution gates and continuity; all repositories are disposable."""
import copy
import sys
import unittest
import test_supervisor as fixture
import test_evidence_reuse as reuse_fixture

m = fixture.mod


class ExecutionGates(unittest.TestCase):
    setUp = fixture.SupervisorTests.setUp
    tearDown = fixture.SupervisorTests.tearDown
    git = fixture.SupervisorTests.git
    write = fixture.SupervisorTests.write
    op = fixture.SupervisorTests.op

    def plan(self, **extra):
        self.write('preflight.py',"from pathlib import Path\nassert not Path('.git/broken').exists()\n")
        self.write('product.py','def total(values):\n    return sum(values)\n')
        self.preflight = {**self.check,'id':'ready','kind':'required','criteria':[],
                          'argv':[sys.executable,'preflight.py'],'test_files':['preflight.py'],'require_red':False}
        self.product = {**self.check,'require_red':False,'requires':['ready'], 'prerequisite_max_age_seconds':60}
        self.op('lock',source_ref='test',basis='approved')
        self.op('plan',source_ref='test',checks=[self.preflight,self.product],**extra)
        self.op('lease',action='acquire')

    def test_missing_assertion_rejects_plan_atomically(self):
        self.op('lock',source_ref='test',basis='approved')
        before=self.sup.load(self.run)
        for path in ['missing.py','/etc/hosts']:
            with self.subTest(path=path), self.assertRaisesRegex(m.GateError,'assertion'):
                self.op('plan',source_ref='test',checks=[{**self.check,'test_files':[path]}])
            self.assertEqual(self.sup.load(self.run),before)

    def test_prerequisites_prevent_spawn_on_missing_failed_stale_and_changed(self):
        self.plan()
        with self.assertRaisesRegex(m.GateError,'prerequisite'):
            self.op('check',id='sum')
        self.assertIsNone(self.sup.load(self.run)['execution'])
        self.write('.git/broken','1')
        self.assertEqual(self.op('check',id='ready')['result'],'fail')
        with self.assertRaises(m.GateError):
            self.op('check',id='sum')
        (self.repo/'.git/broken').unlink()
        self.op('check',id='ready')
        state=self.sup.load(self.run)
        state['receipts'][-1]['finished_at']-=61
        self.sup.save(state,'stale_fixture',{})
        with self.assertRaises(m.GateError):
            self.op('check',id='sum')
        self.op('check',id='ready')
        self.write('product.py','def total(values):\n    return 5\n')
        with self.assertRaises(m.GateError):
            self.op('check',id='sum')
        self.op('check',id='ready')
        passed=self.op('check',id='sum')
        self.assertEqual(passed['result'],'pass')
        self.assertEqual(len(passed['prerequisite_receipt_ids']),1)

    def test_freeze_readiness_then_later_prerequisite_failure_blocks_seal(self):
        self.plan(freeze_requires=['sum'])
        with self.assertRaisesRegex(m.GateError,'prerequisite'):
            self.op('freeze')
        self.op('check',id='ready')
        self.op('check',id='sum')
        self.op('freeze')
        self.op('seal')

    def test_later_failure_invalidates_downstream_and_transitive_proof(self):
        self.plan()
        self.op('revise',reason='chain',source_ref='test')
        middle={**self.preflight,'id':'middle','requires':['ready']}
        self.op('plan',source_ref='test',checks=[self.preflight,middle,{**self.product,'requires':['middle']}])
        for cid in ['ready','middle','sum']:
            self.op('check',id=cid)
        self.op('freeze')
        self.write('.git/broken','1')
        self.op('check',id='ready')
        with self.assertRaises(m.GateError):
            self.op('seal')

    def test_invalid_prerequisite_graphs_reject_atomically(self):
        self.plan()
        self.op('revise',reason='invalid graph probe',source_ref='test')
        for checks, extra in [
            ([self.preflight,{**self.product,'requires':['absent']}],{}),
            ([{**self.preflight,'requires':['sum']},self.product],{}),
            ([self.preflight,{**self.product,'requires':['sum']}],{}),
            ([self.preflight,self.product],{'freeze_requires':['absent']}),
            ([self.preflight,{**self.product,'prerequisite_max_age_seconds':0}],{}),
        ]:
            before=self.sup.load(self.run)
            with self.assertRaises(m.GateError):
                self.op('plan',source_ref='test',checks=checks,**extra)
            self.assertEqual(self.sup.load(self.run),before)

    def test_freshness_is_admission_check_not_post_execution_expiry(self):
        self.plan()
        self.op('check',id='ready')
        self.op('check',id='sum')
        state=self.sup.load(self.run)
        state['receipts'][0]['finished_at']-=61
        self.sup.save(state,'elapsed_fixture',{})
        self.op('freeze')
        self.op('seal')

    def test_continuation_preserves_budget_and_blocks_duplicate_resets(self):
        self.plan()
        for _ in range(3):
            self.op('freeze')
            self.op('repair',reason='same mission repair')
        self.op('stop',status='blocked',reason='budget exhausted')
        self.op('cleanup',note='disposable',dispositions={})
        self.op('finish',classification='executor_issue',finding='budget exhausted',source_ref='test')
        prior=copy.deepcopy(self.sup.load(self.run))
        with self.assertRaisesRegex(m.GateError,'continu'):
            self.sup.operate('start',self.contract)
        linked={**self.contract,'continues_run':self.run}
        child=self.sup.operate('start',linked)['id']
        self.assertEqual(self.sup.load(child)['repairs'],3)
        self.assertEqual(self.sup.load(self.run),prior)
        with self.assertRaises(m.GateError):
            self.sup.operate('start',linked)
        for op,data in [('lock',{'basis':'same mission','source_ref':'test'}),('plan',{'checks':[self.check],'source_ref':'test'}),('lease',{'action':'acquire'}),('freeze',{})]:
            self.sup.operate(op,data,child,'controller')
        with self.assertRaisesRegex(m.GateError,'budget'):
            self.sup.operate('repair',{'reason':'reset attempt'},child,'controller')


class ScopedReuse(unittest.TestCase):
    setUp=fixture.SupervisorTests.setUp
    tearDown=fixture.SupervisorTests.tearDown
    git=fixture.SupervisorTests.git
    write=fixture.SupervisorTests.write
    op=fixture.SupervisorTests.op
    baseline=reuse_fixture.EvidenceReuse.baseline
    refreeze=reuse_fixture.EvidenceReuse.refreeze
    reuse=reuse_fixture.EvidenceReuse.reuse

    def scoped(self):
        self.baseline()
        self.op('revise',reason='reviewed scoped plan',source_ref='review')
        self.policy.update(dependency_paths=['product.py','test_product.py','environment.py','.gitignore'],dependency_coverage='Reviewed complete pure-Python inputs; no installed dependencies')
        self.op('plan',source_ref='review',checks=[self.env,self.product],freeze_requires=['sum'])
        self.git('add','.')
        self.git('commit','-qm','scope baseline')
        self.op('check',id='environment')
        self.original=self.op('check',id='sum')
        self.assertEqual(self.original['result'],'pass')

    def test_outside_change_requires_exact_independent_impact_and_no_product_rerun(self):
        self.scoped()
        self.write('unrelated.py','value=1\n')
        self.git('add','.')
        self.git('commit','-qm','independent change')
        self.op('check',id='environment')
        with self.assertRaisesRegex(m.GateError,'impact'):
            self.reuse()
        after=self.sup.reuse_dependencies(self.sup.load(self.run),self.policy['narrative_paths'],self.policy['dependency_paths'])
        review={'reviewer':'independent','source_ref':'review:actualdiff','finding':'No new callers, shared inputs or effect on registered behavior',
                'before':self.original['reuse_evidence']['outside_dependencies'],'after':after['outside_dependencies']}
        self.reuse(impact_review=review)
        self.op('freeze')
        self.assertEqual((self.repo/'.git/executions').read_text(),'xx')
        self.assertEqual(self.sup.load(self.run)['receipts'][-1]['impact_review'],review)

    def test_scoped_execution_needs_clean_original_and_exact_inputs(self):
        self.scoped()
        self.write('product.py','def total(values):\n    return 5\n')
        self.op('check',id='environment')
        with self.assertRaisesRegex(m.GateError,'committed'):
            self.op('check',id='sum')
        with self.assertRaisesRegex(m.GateError,'dependenc'):
            self.reuse()

    def test_scope_paths_cannot_escape_or_hide_assertions(self):
        self.baseline()
        for paths in [[],['../outside'],['docs/**'],['product.py','missing.py']]:
            self.op('revise',reason='invalid scope probe',source_ref='test')
            policy={**self.policy,'dependency_paths':paths,'dependency_coverage':'test'}
            with self.assertRaises(m.GateError):
                self.op('plan',source_ref='test',checks=[self.env,{**self.product,'reuse':policy}])


if __name__=='__main__':
    unittest.main(verbosity=2)
