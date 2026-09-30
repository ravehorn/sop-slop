"""Conservative equivalence probes; all files and executions are disposable."""
import copy
import json
from pathlib import Path
import sys
import unittest
import test_supervisor as fixture

m = fixture.mod


class EvidenceReuse(unittest.TestCase):
    setUp = fixture.SupervisorTests.setUp
    tearDown = fixture.SupervisorTests.tearDown
    git = fixture.SupervisorTests.git
    write = fixture.SupervisorTests.write
    op = fixture.SupervisorTests.op

    def baseline(self):
        (self.repo/'docs').mkdir()
        self.write('docs/receipt.md','Initial evidence narrative\n')
        self.write('.git/environment-value','fixture-alpha')
        self.write('environment.py',"from pathlib import Path\nprint(Path('.git/environment-value').read_text())\n")
        self.write('product.py','def total(values):\n    return sum(values)\n')
        self.write('test_product.py',"from pathlib import Path\nfrom product import total\nassert total([2,3])==5\nwith Path('.git/executions').open('a') as f: f.write('x')\n")
        self.policy = {'narrative_paths':['docs/receipt.md'], 'environment_check':'environment',
                       'revision_independent':True, 'max_environment_age_seconds':60,
                       'reviewer':'independent', 'source_ref':'review:scope',
                       'environment_coverage':'Disposable fixture identity; no external dependencies in this simulated pure Python product.'}
        self.product = {**self.check,'require_red':False,'reuse':self.policy}
        self.env = {**self.check,'id':'environment','kind':'environment','criteria':[],
                    'argv':[sys.executable,'environment.py'],'test_files':['environment.py'],'require_red':False}
        self.op('lock',source_ref='test',basis='approved')
        try:
            self.op('plan',source_ref='test',checks=[self.env,self.product])
        except m.GateError as e:
            self.fail('eligible evidence plan must be supported: '+str(e))
        self.op('lease',action='acquire')
        self.op('freeze')
        self.op('check',id='environment')
        self.original=self.op('check',id='sum')
        self.assertEqual(self.original['result'],'pass')
        self.original_copy=copy.deepcopy(self.original)
        self.op('review',reviewer='independent',disposition='accepted',finding='Code accepted; exact receipt narrative may be reviewed separately',source_ref='review:initial',reuse_narrative_paths=['docs/receipt.md'])
        self.review=copy.deepcopy(self.sup.load(self.run)['review'])

    def refreeze(self):
        self.op('freeze')
        self.op('check',id='environment')

    def approval(self, before):
        return {'reviewer':'independent','source_ref':'review:actual-delta','finding':'Only reporting changed, no behavior, criteria or executable input changed',
                'changes':{'docs/receipt.md':{'before':before['narratives']['docs/receipt.md'],
                                            'after':m.file_hash(self.repo/'docs/receipt.md')}}}

    def reuse(self, **extra):
        return self.op('reuse',id='sum',source_receipt_id=self.original['id'],**extra)

    def test_head_only_commit_reuses_without_another_product_execution(self):
        self.baseline()
        self.git('add','.')
        self.git('commit','-qm','same tested content')
        self.refreeze()
        reused=self.reuse()
        self.assertEqual(reused['provenance'],'explicit_evidence_reuse')
        self.assertEqual(reused['source_receipt_id'],self.original['id'])
        self.assertEqual(reused['executed_at'],self.original['finished_at'])
        self.assertEqual((self.repo/'.git/executions').read_text(),'x')
        self.assertEqual(self.sup.load(self.run)['receipts'][1],self.original_copy)
        self.assertIsNone(self.sup.load(self.run)['review'])
        self.op('review-reuse',source_review_id=self.review['id'],source_ref='review:unchanged-content')
        self.op('seal')

    def test_narrative_change_requires_exact_independent_delta_review(self):
        self.baseline()
        self.write('docs/receipt.md','Check result recorded\n')
        self.refreeze()
        with self.assertRaisesRegex(m.GateError,'narrative'):
            self.reuse()
        approval=self.approval(self.original['reuse_evidence'])
        self.reuse(narrative_review=approval)
        self.op('review-reuse',source_review_id=self.review['id'],source_ref='review:delta',narrative_review=self.approval(self.review['reuse_evidence']))
        self.op('seal')

    def test_unapproved_or_stale_narrative_review_rejected(self):
        self.baseline()
        self.write('docs/receipt.md','Changed\n')
        self.refreeze()
        approval=self.approval(self.original['reuse_evidence'])
        approval['changes']['docs/receipt.md']['after']='wrong'
        with self.assertRaisesRegex(m.GateError,'narrative'):
            self.reuse(narrative_review=approval)

    def test_code_fixture_config_lockfile_and_behavior_doc_changes_invalidate(self):
        self.baseline()
        for name in ['product.py','fixture.sql','config.json','package-lock.json','docs/behavior.md']:
            with self.subTest(name=name):
                prior=(self.repo/name).read_bytes() if (self.repo/name).exists() else None
                self.write(name,'changed dependency\n')
                self.refreeze()
                with self.assertRaisesRegex(m.GateError,'dependenc'):
                    self.reuse()
                if prior is None:
                    (self.repo/name).unlink()
                else:
                    (self.repo/name).write_bytes(prior)

    def test_assertion_change_and_executable_mode_invalidate(self):
        self.baseline()
        (self.repo/'product.py').chmod(0o755)
        self.refreeze()
        with self.assertRaisesRegex(m.GateError,'dependenc'):
            self.reuse()
        (self.repo/'product.py').chmod(0o644)
        self.write('test_product.py','assert True\n')
        self.refreeze()
        with self.assertRaises(m.GateError):
            self.reuse()

    def test_environment_change_or_stale_probe_rejected(self):
        self.baseline()
        self.git('add','.')
        self.git('commit','-qm','commit')
        self.op('freeze')
        with self.assertRaisesRegex(m.GateError,'environment'):
            self.reuse()
        self.write('.git/environment-value','fixture-beta')
        self.op('check',id='environment')
        with self.assertRaisesRegex(m.GateError,'environment'):
            self.reuse()

    def test_later_failure_is_not_hidden_and_reuse_chains_are_forbidden(self):
        self.baseline()
        self.write('.git/environment-value','')
        self.refreeze()
        with self.assertRaises(m.GateError):
            self.reuse()
        self.write('.git/environment-value','fixture-alpha')
        self.refreeze()
        reused=self.reuse()
        with self.assertRaisesRegex(m.GateError,'original'):
            self.op('reuse',id='sum',source_receipt_id=reused['id'])
        s=self.sup.load(self.run)
        failed={**self.original,'id':'fixture-failure','result':'fail'}
        s['receipts'].append(failed)
        self.sup.save(s,'fixture_later_failure',{})
        with self.assertRaisesRegex(m.GateError,'later'):
            self.reuse()

    def test_release_environment_and_revision_sensitive_checks_cannot_opt_in(self):
        self.baseline()
        for kind in ['release','production','environment']:
            with self.subTest(kind=kind):
                self.op('revise',reason='invalid policy probe',source_ref='test')
                with self.assertRaisesRegex(m.GateError,'reuse'):
                    self.op('plan',source_ref='test',checks=[self.env,{**self.product,'kind':kind}])
        with self.assertRaisesRegex(m.GateError,'revision'):
            self.op('plan',source_ref='test',checks=[self.env,{**self.product,'reuse':{**self.policy,'revision_independent':False}}])

    def test_policy_cannot_exclude_assertions_or_glob_docs(self):
        self.baseline()
        for paths in [['docs/**'],['test_product.py'],['AGENTS.md']]:
            self.op('revise',reason='invalid exclusion probe',source_ref='test')
            with self.assertRaises(m.GateError):
                self.op('plan',source_ref='test',checks=[self.env,{**self.product,'reuse':{**self.policy,'narrative_paths':paths}}])

    def test_plan_change_and_legacy_receipt_prevent_reuse(self):
        self.baseline()
        s=self.sup.load(self.run)
        s['receipts'][1].pop('reuse_evidence')
        self.sup.save(s,'legacy_fixture',{})
        with self.assertRaisesRegex(m.GateError,'snapshot'):
            self.reuse()
        self.op('revise',reason='new plan',source_ref='test')
        self.op('plan',source_ref='new plan',checks=[self.env,self.product])
        self.refreeze()
        with self.assertRaises(m.GateError):
            self.reuse()

    def test_planning_rules_preserve_risk_and_narrow_execution(self):
        guide=(Path(__file__).resolve().parents[1]/'sop-slop/references/evidence-reuse.md')
        self.assertTrue(guide.exists(),'evidence and planning guide required')
        text=guide.read_text()
        for phrase in ['assertion-level','two unrelated infrastructure failures','one working day','implemented','qualified','deployed','oracle','one integrated']:
            self.assertIn(phrase,text)


if __name__=='__main__':
    unittest.main(verbosity=2)
