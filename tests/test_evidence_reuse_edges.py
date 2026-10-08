"""Additional integrity and upgrade probes; no live services or repositories."""
import copy
import hashlib
import unittest
import test_evidence_reuse as fixture

m = fixture.m


class ReuseEdges(unittest.TestCase):
    setUp = fixture.EvidenceReuse.setUp
    tearDown = fixture.EvidenceReuse.tearDown
    git = fixture.EvidenceReuse.git
    write = fixture.EvidenceReuse.write
    op = fixture.EvidenceReuse.op
    baseline = fixture.EvidenceReuse.baseline
    refreeze = fixture.EvidenceReuse.refreeze
    reuse = fixture.EvidenceReuse.reuse

    def test_prior_graph_adoption_preserves_receipts_claims_and_review(self):
        self.op('coordination',action='activate',source_ref='test:drained')
        self.op('coordination',action='tests',resources=[],source_ref='test:isolated')
        self.baseline()
        self.git('add','.')
        self.git('commit','-qm','clean checkpoint')
        self.op('freeze')
        state = self.sup.load(self.run)
        state.update(version=m.PRIOR_GRAPH['version'],graph_digest=m.digest(m.PRIOR_GRAPH))
        self.sup.save(state,'prior_version_fixture',{})
        claims = list(self.sup.db.execute('SELECT * FROM claims'))
        self.assertTrue(self.op('adopt-check',source_ref='test:approved')['ready'])
        self.op('adopt',source_ref='test:approved')
        after = self.sup.load(self.run)
        for key in ('receipts','review_history','plan_epoch'):
            self.assertEqual(after[key],state[key])
        self.assertEqual(list(self.sup.db.execute('SELECT * FROM claims')),claims)
        self.assertEqual(after['version'],m.VERSION)

    def test_ignored_assertion_invalidation_includes_review(self):
        self.write('.git/info/exclude','test_product.py\n')
        self.git('rm','--cached','test_product.py')
        self.baseline()
        self.write('test_product.py','assert True\n')
        self.op('freeze')
        with self.assertRaisesRegex(m.GateError,'assertion'):
            self.op('review-reuse',source_review_id=self.review['id'],source_ref='test')

    def test_assertion_aliases_cannot_be_excluded(self):
        self.baseline()
        for name in ['./docs/receipt.md',str(self.repo/'docs/receipt.md')]:
            with self.subTest(name=name), self.assertRaisesRegex(m.GateError,'assertion'):
                self.sup.narrative_paths(['docs/receipt.md'],[name])

    def test_freshness_failure_and_original_contract_are_enforced(self):
        self.baseline()
        state = self.sup.load(self.run)
        original = copy.deepcopy(state)
        state['receipts'][0]['finished_at'] -= 61
        self.sup.save(state,'stale_fixture',{})
        with self.assertRaisesRegex(m.GateError,'environment'):
            self.reuse()
        self.sup.save(original,'restore_fixture',{})
        state = self.sup.load(self.run)
        state['receipts'][0]['result'] = 'fail'
        self.sup.save(state,'failed_environment_fixture',{})
        with self.assertRaisesRegex(m.GateError,'environment'):
            self.reuse()
        self.sup.save(original,'restore_fixture',{})
        state = self.sup.load(self.run)
        state['receipts'][1]['contract_digest'] = 'different'
        self.sup.save(state,'contract_fixture',{})
        with self.assertRaisesRegex(m.GateError,'contract'):
            self.reuse()

    def test_latest_rejected_review_cannot_be_bypassed(self):
        self.baseline()
        self.op('review',reviewer='independent',disposition='revision_required',finding='Real issue',source_ref='review:reject')
        self.op('freeze')
        with self.assertRaises(m.GateError):
            self.op('review-reuse',source_review_id=self.review['id'],source_ref='test')

    def test_environment_identity_hashes_full_output_not_just_tail(self):
        self.baseline()
        output='identity-a'+'x'*10000
        self.write('environment.py','print('+repr(output)+')\n')
        self.op('revise',reason='measure complete output',source_ref='test')
        self.op('plan',source_ref='test',checks=[self.env,self.product])
        self.op('freeze')
        receipt=self.op('check',id='environment')
        self.assertEqual(receipt['output_digest'],hashlib.sha256((output+'\n').encode()).hexdigest())
        self.assertEqual(len(receipt['output_tail']),4096)
        self.assertNotIn('identity-a',receipt['output_tail'])


if __name__=='__main__':
    unittest.main(verbosity=2)
