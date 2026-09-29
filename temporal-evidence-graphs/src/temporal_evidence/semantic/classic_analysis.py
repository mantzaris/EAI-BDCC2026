"""Equation annotations from saved inputs; independent of drawing coordinates.

The existing witness evaluator supplies S; the separate event/task oracle supplies
A. Reachability uses only the theorem's claim dependency projection. Neither
assessment flags nor the drawing's expanded provenance graph supply reference truth.
"""
from collections import Counter, defaultdict, deque
from copy import deepcopy

from temporal_evidence.schema import Record
from temporal_evidence.semantic.ontology import NODE_RULES, node_origin, edge_origin, validate_export
from temporal_evidence.semantic.projection import records, latest, core
from temporal_evidence.semantic.structural_analysis import audit_program
from temporal_evidence.structure.program import runtime_support
from temporal_evidence.structure.oracle import reference


def reverse_reachable(edges, inputs):
    reverse=defaultdict(set)
    for e in edges:reverse[e['target']].add(e['source'])
    found=set(inputs);agenda=deque(sorted(inputs))
    while agenda:
        for rid in sorted(reverse[agenda.popleft()]-found):
            found.add(rid);agenda.append(rid)
    return found


def predicate_rows(case, events, time):
    """Expose operands of the existing oracle as auditable per-test queries."""
    visible={e['record_id']:e for e in events if e['ingested_at_seconds']<=time}
    current=latest(visible);out={}
    for token,test in sorted(case['tests'].items()):
        r=current.get(test['logical_id'])
        checks={'record_known':r is not None,
                'dataset':bool(r and r['dataset_id']==case['dataset']),
                'subject':bool(r and r['subject_id']==case['subject']),
                'session':bool(r and r['session_id']=='session_1'),
                'interval':bool(r and [r['event_start_seconds'],r['event_end_seconds']]==test['interval']),
                'quantity':bool(r and r['quantity']==test['quantity']),
                'unit':bool(r and r['unit']==test['unit']),
                'available':bool(r and r['evidence_state']=='available' and r['value'] is not None)}
        # Query the independent task oracle with a one-atom proposition. No
        # accepted/support flags are read and no new numerical tolerance is added.
        probe={**case,'propositions':{'test':[[token]]}}
        truth=reference(probe,events,time)['test']
        if checks['available']:
            numerical=r['value']>=test['threshold'] if test['operator']=='ge' else r['value']<=test['threshold']
        else:numerical=False
        assert truth==bool(all(checks.values()) and numerical)
        out[token]={'test':deepcopy(test),'resolved_record_id':r['record_id'] if r else None,
                    'resolved_value':r['value'] if r else None,'checks':checks,'numerical_comparison':bool(numerical),
                    'truth':truth,'knowledge_time':time}
    return out


def analyze_case(graph, case, candidate, replays, times):
    assert not validate_export(graph)
    claims=candidate['accepted'];cid=case['case_id'];mapping={c['claim_id']:cid+'/claim/'+c['claim_id'] for c in claims}
    rows={r['method']:r for r in replays if r['origin']=='generated' and r['condition']=='route_loss'}
    full=rows['M1'];direct=rows['B2'];before_time,after_time=sorted(times)
    revisions=full['revisions'];events=case['events']+revisions
    assert full['scope']==graph['scope'] and direct['revisions']==revisions
    rs=records(graph,after_time)
    for event in events:assert rs[event['record_id']]==event
    for c in claims:assert rs[mapping[c['claim_id']]]['metadata']['semantic_program']==c
    audit=audit_program(claims,case)
    assert all(r['grounded'] and r['complete_family'] and all(r['sound_witnesses']) for r in audit)
    states={};predicates={};cores={}
    for label,t in (('before',before_time),('after',after_time)):
        visible=records(graph,t)
        states[label]=runtime_support(claims,case,{rid:Record.from_dict(r) for rid,r in visible.items()})
        predicates[label]=predicate_rows(case,events,t)
        cores[label]=core(graph,cid,t,explanation_logical_id=cid+'/explanation')
    oracle_before=reference(case,events,before_time);oracle_after=reference(case,events,after_time)
    required={mapping[c['claim_id']] for c in claims if oracle_before[c['proposition']] and not oracle_after[c['proposition']]}
    changed={mapping[c['claim_id']] for c in claims if states['before'][c['claim_id']]!=states['after'][c['claim_id']]}
    assert required=={mapping[i] for i in direct['required_change_ids']}
    assert states['after']==full['states']
    dbnodes={n['properties'].get('id'):n for n in graph['nodes'] if n['properties'].get('payload')}
    dbids={n['id']:rid for rid,n in dbnodes.items()}
    dep_nodes={rid for rid,r in rs.items() if r['record_type'] in {'feature','claim'}}
    deps=[{'id':e['id'],'source':dbids[e['source']],'target':dbids[e['target']],'type':e['type']}
          for e in graph['edges'] if e['type']=='DEPENDS_ON' and dbids.get(e['source']) in dep_nodes
          and rs[dbids[e['source']]]['record_type']=='claim' and dbids.get(e['target']) in dep_nodes]
    logicals={r['logical_id'] for r in revisions}
    U={rid for rid,r in rs.items() if r['logical_id'] in logicals}
    R=reverse_reachable(deps,U)
    D={mapping[i] for i in direct['scheduled_ids']}
    recorded_direct={mapping[i] for i in direct['direct_scheduled_ids']}
    assert D==recorded_direct
    independently_direct={e['source'] for e in deps if e['target'] in U}
    assert D==independently_direct and changed<=R
    claim_ids=set(mapping.values());full_scheduled={mapping[i] for i in full['scheduled_ids']}
    assert full_scheduled==R & claim_ids
    xi=len(required-D)/len(required) if required else None
    assert xi==direct['xi']==full['xi']
    sets={'U_delta':sorted(U),'R_delta':sorted(R),'B_delta':sorted(changed),'A_delta':sorted(required),
          'D_delta':sorted(D),'reachable_claims':sorted(R & claim_ids),'full_scheduled_claims':sorted(full_scheduled)}
    visible_db=[n for n in graph['nodes'] if (n['properties'].get('known_at',float('inf'))<=after_time if n['semantic_type']=='assessment'
               else n['properties'].get('ingested',float('inf'))<=after_time)]
    return {'format':'classic_equation_analysis_v1','case_id':cid,'scope':graph['scope'],
            'knowledge_times':{'before':before_time,'after':after_time},'revision_arrival_time':full['knowledge_time'],
            'equation_labels':['eq:ontology','eq:construction','eq:core','eq:reviewview','eq:support','eq:locality','eq:exposure'],
            'admitted_claims':claims,'claim_id_map':mapping,'witness_audit':audit,'predicates':predicates,
            'support':states,'oracle':{'before':oracle_before,'after':oracle_after,'source':'immutable event/task oracle; no database assessments'},
            'cores':cores,'revision_logical_ids':sorted(logicals),'availability_subscription_ids':[],
            'sets':sets,'exposure':{'numerator':len(required-D),'denominator':len(required),'xi':xi},
            'direct_schedule_source':{'method':'B2','scope':direct['scope'],'field':'scheduled_ids','recorded_ids':direct['scheduled_ids']},
            'full_schedule_source':{'method':'M1','field':'scheduled_ids','recorded_ids':full['scheduled_ids']},
            'full_scope':{'stored_nodes':len(graph['nodes']),'stored_edges':len(graph['edges']),
                          'visible_database_nodes':len(visible_db),'visible_record_nodes':len(rs),
                          'dependency_node_ids':sorted(dep_nodes),'dependency_edges':deps,
                          'dependency_filter':'ClaimVersion DEPENDS_ON ClaimVersion/FeatureVersion only; versions remain separate, all revised-identity versions seed U.',
                          'recorded_backend_reachable_records':full['potential_affected_records'],
                          'backend_note':'Backend traversal also reaches explanation membership; it is excluded from theorem claim reachability.'}}


def annotate_view(view, graph, analysis):
    """Join already computed sets to a selected view; never recompute its oracle."""
    view=deepcopy(view);label='before' if view['knowledge_time']==analysis['knowledge_times']['before'] else 'after'
    assert view['knowledge_time']==analysis['knowledge_times'][label]
    core_ids={n['id'] for n in analysis['cores'][label]['nodes']}
    allsets={k:set(v) for k,v in analysis['sets'].items()};shown={n['id'] for n in view['nodes']}
    dbnodes={n['id']:n for n in graph['nodes']};dbedges={e['id']:e for e in graph['edges']}
    classes={r[0]:r[1] for r in NODE_RULES}
    for n in view['nodes']:
        n['ontology_class']=classes[n['type']]
        assert n['ontology_class'] in dbnodes[n['database_element_id']]['labels']
        n['construction_origin']=node_origin(dbnodes[n['database_element_id']])
        p=n['record']['metadata'].get('semantic_program')
        n['equations']={'in_core':n['id'] in core_ids,'membership':{k:n['id'] in v for k,v in allsets.items()},
                        'support_before':analysis['support']['before'].get(p['claim_id']) if p else None,
                        'support_after':analysis['support']['after'].get(p['claim_id']) if p else None,
                        'support_at_time':analysis['support'][label].get(p['claim_id']) if p else None,
                        'core_role':'display member' if n['id'] in {x['id'] for x in analysis['cores'][label]['nodes'] if x.get('displayed_member')}
                                    else 'declared ancestor/input' if n['id'] in core_ids else 'review context'}
    for e in view['edges']:e['construction_origin']=edge_origin(dbedges[e['id']],dbnodes)
    view['equation_annotations']={'analysis_format':analysis['format'],'recorded_state':label,
        'contrast_note':'Retrospective before/after contrast; future records are never drawn in the earlier snapshot.',
        'full_sets':analysis['sets'],'visible_sets':{k:sorted(v & shown) for k,v in allsets.items()},
        'core_ids':sorted(core_ids),'visible_core_ids':sorted(core_ids & shown),
        'context_ids':sorted(shown-core_ids),'exposure':analysis['exposure'],
        'full_scope':analysis['full_scope'],'claim_truths':analysis['support'],
        'view_counts':{'nodes':len(view['nodes']),'edges':len(view['edges']),
                       'node_types':dict(Counter(n['type'] for n in view['nodes'])),
                       'edge_types':dict(Counter(e['type'] for e in view['edges']))}}
    return view
