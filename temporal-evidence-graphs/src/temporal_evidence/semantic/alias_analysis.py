"""Audit the separately scoped primitive-name replication without changing core scores."""
from collections import Counter,defaultdict
from temporal_evidence.io import read_json,write_json,digest_file
from temporal_evidence.semantic.structural_analysis import RUN,OUT,audit_program
from temporal_evidence.semantic.statistics import csv_rows,cluster_ratio

def analyze():
    root=RUN/'primitive_alias_replication';complete=read_json(root/'completion.json')
    cases=read_json(RUN/'cases.json');rows=[];depths=Counter();admitted=0
    for case in cases:
        name=case['case_id']+'.json';candidate=read_json(root/'candidates'/name)
        assert candidate['original_candidate_sha256']==digest_file(RUN/'core/candidates'/name)
        scores=audit_program(candidate['accepted'],case)
        assert all(r['grounded'] and r['sound_witnesses'] and all(r['sound_witnesses']) for r in scores)
        rs=read_json(root/'replay'/name);rows.extend(rs)
        representative=next(r for r in rs if r['method']=='M1' and r['condition']=='necessary')
        depths[str(representative['realized_depth'])]+=1;admitted+=candidate['adequate_answer']
    assert len(rows)==complete['cells']==4800 and admitted==complete['admissible_roots']
    index={(r['case_id'],r['method'],r['condition']):r for r in rows}
    parity=eligible=agreement=0
    for case in cases:
        for condition in ('necessary','route_loss','benign','irrelevant'):
            b1,b2,m1,b3=(index[(case['case_id'],m,condition)] for m in ('B1','B2','M1','B3'))
            assert b1['logical_hash']==b2['logical_hash'] and m1['logical_hash']==b3['logical_hash'];parity+=1
            if b2['xi'] is not None:
                eligible+=1;agreement+=b2['missed_changes']==len(set(b2['required_change_ids'])-set(b2['direct_scheduled_ids']))
    methods=[]
    for method in ('B0','B1','B2','M1','B3'):
        rs=[r for r in rows if r['method']==method]
        methods.append({'method':method,'required':sum(r['required_changes'] for r in rs),'missed':sum(r['missed_changes'] for r in rs),
            'collateral':sum(r['collateral'] for r in rs),'correction':cluster_ratio(rs,'corrected','required_changes'),
            'nonzero_exposure':sum(r['xi'] is not None and r['xi']>0 for r in rs),'eligible_exposure':sum(r['xi'] is not None for r in rs)})
    retention={regime:{'eligible':len(rs),'retained':sum(r['root_preserved'] for r in rs)} for regime in ('single','alternative')
        for rs in [[r for r in rows if r['method']=='M1' and r['condition']=='route_loss' and r['regime']==regime and r['root_count']]]}
    summary={'completion':complete,'methods':methods,'depth_counts':dict(depths),'parity_groups':parity,'eligible_prediction_groups':eligible,
        'prediction_agreement':agreement,'retention':retention,'scope':'Separate corrected replication; original core is unchanged.'}
    write_json(OUT/'primitive_alias_summary.json',summary)
    csv_rows(OUT/'primitive_alias_replay_metrics.csv',[{k:v for k,v in r.items() if not isinstance(v,(list,dict))} for r in rows])
    print(summary)

if __name__=='__main__':analyze()
