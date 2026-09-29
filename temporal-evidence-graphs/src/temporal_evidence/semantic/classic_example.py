"""Reproduce the ontology-instance worked network from the retained saved case."""
from pathlib import Path
from copy import deepcopy

from temporal_evidence.io import read_json, write_json, digest_file, digest_object
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.network_examples import make_views
from temporal_evidence.semantic.review_view import validate_view
from temporal_evidence.semantic.classic_analysis import analyze_case, annotate_view
from temporal_evidence.semantic.classic_render import spring_layout, render_bytes, short_label, edge_label

ROOT=Path('artifacts/analysis/classic_network_v1')
FIGURE=Path('artifacts/figures/semantic_analysis_v1/ontology_instance_network')
CONFIG=Path('artifacts/analysis/review_views_v1/structural_alternatives/config.json')


def focused_provenance(view):
    """Keep EDA windows in the overview; ACC windows remain expandable context."""
    view=deepcopy(view)
    omitted={n['id'] for n in view['nodes'] if n['type']=='observation' and n['record']['metadata'].get('channel')!='eda'}
    view['nodes']=[n for n in view['nodes'] if n['id'] not in omitted]
    view['edges']=[e for e in view['edges'] if e['source'] not in omitted and e['target'] not in omitted]
    view['context']['provenance_channel_filter']=['eda']
    view['context']['omitted_provenance_ids']=sorted(set(view['context']['omitted_provenance_ids'])|omitted)
    view['context']['selection_note']='EDA observation windows included; motion observation windows available by expanding provenance.'
    view['budget']['required_nodes']-=len(omitted)
    view['budget']['shown_nodes']=len(view['nodes'])
    return view


def prepare():
    config=read_json(CONFIG);graph=read_export(config['export'])
    candidate=read_json(config['candidate_path']);replays=read_json(config['replay_path'])
    analysis=analyze_case(graph,config['program_case'],candidate,replays,config['times'].values())
    views=[annotate_view(focused_provenance(v),graph,analysis) for v in make_views(config,expand=True,budget=20)]
    for v in views:validate_view(v,graph)
    return config,analysis,views


def run():
    config,analysis,views=prepare();layout=spring_layout(views)
    ROOT.mkdir(parents=True,exist_ok=True)
    write_json(ROOT/'analysis.json',analysis);write_json(ROOT/'layout.json',layout)
    for label,view in zip(('before','after'),views):
        write_json(ROOT/(label+'.json'),view)
        for ext in ('svg','pdf','png'):(ROOT/(label+'.'+ext)).write_bytes(render_bytes(view,layout,ext))
    for ext in ('svg','pdf','png'):FIGURE.with_suffix('.'+ext).write_bytes(render_bytes(views[-1],layout,ext))
    source_paths=[CONFIG,Path(config['export']),Path(config['candidate_path']),Path(config['replay_path']),Path('artifacts/runs/structure_study_v1/cases.json')]
    code=[Path('src/temporal_evidence/semantic')/name for name in ('classic_example.py','classic_analysis.py','classic_render.py','projection.py','review_view.py','ontology.py')]
    code += [Path('src/temporal_evidence/structure')/name for name in ('program.py','oracle.py')]
    manifest={'format':'classic_network_v1','case_id':config['case_id'],'scope':views[-1]['scope'],
        'selection':'Preserve the existing smallest witness-complete eligible primary generated case; add its two EDA source observations; keep motion observations in expandable context. No new case search or inference.',
        'source_hashes':{str(p):digest_file(p) for p in source_paths},'code_hashes':{str(p):digest_file(p) for p in code},
        'knowledge_times':config['times'],'revision':'recorded primary-route loss; M1 maintenance',
        'analysis_path':str(ROOT/'analysis.json'),'analysis_sha256':digest_file(ROOT/'analysis.json'),
        'views':{label:{'path':str(ROOT/(label+'.json')),'sha256':digest_object(v)} for label,v in zip(('before','after'),views)},
        'selected_record_ids':[n['id'] for n in views[-1]['nodes']], 'stored_edge_ids':[e['id'] for e in views[-1]['edges']],
        'node_type_map':{n['id']:n['ontology_class'] for n in views[-1]['nodes']},
        'edge_type_map':{e['id']:e['type'] for e in views[-1]['edges']},
        'node_labels':{n['id']:short_label(n) for n in views[-1]['nodes']},
        'edge_labels':{e['id']:edge_label(e,views[-1]) for e in views[-1]['edges']},
        'relation_filter':views[-1]['context']['hidden_relations'],
        'edge_label_mapping':{'AND A / AND B':'DEPENDS_ON; complete four-input witness jointly required by CA / CB',
                              'OR A / OR B':'DEPENDS_ON; singleton-parent alternative witnesses at R',
                              'from':'DERIVED_FROM','revises':'SUPERSEDES'},
        'witness_groups':views[-1]['witness_groups'],'derived_resolution_paths':views[-1]['derived_paths'],
        'visible_derived_edges':[],'visual_junction_nodes':[],
        'annotation_mapping':views[-1]['equation_annotations'],
        'layout':layout,'new_gpu_calls':0,
        'figure_hashes':{str(FIGURE.with_suffix('.'+ext)):digest_file(FIGURE.with_suffix('.'+ext)) for ext in ('svg','pdf','png')}}
    write_json(ROOT/'manifest.json',manifest);write_json(FIGURE.with_suffix('.manifest.json'),manifest)
    a=analysis['predicates']['before']['A1'];b=analysis['predicates']['after']['A1'];ann=views[-1]['equation_annotations']
    macros={'ClassicNodes':len(views[-1]['nodes']),'ClassicEdges':len(views[-1]['edges']),
        'ClassicCore':len(ann['visible_core_ids']),'ClassicContext':len(ann['context_ids']),
        'ClassicScopeNodes':analysis['full_scope']['stored_nodes'],'ClassicScopeEdges':analysis['full_scope']['stored_edges'],
        'ClassicDependencyNodes':len(analysis['full_scope']['dependency_node_ids']),'ClassicDependencyEdges':len(analysis['full_scope']['dependency_edges']),
        'ClassicInputVersions':len(analysis['sets']['U_delta']),'ClassicReach':len(analysis['sets']['R_delta']),
        'ClassicReachClaims':len(analysis['sets']['reachable_claims']),'ClassicChanged':len(analysis['sets']['B_delta']),
        'ClassicRequired':len(analysis['sets']['A_delta']),'ClassicDirect':len(analysis['sets']['D_delta']),
        'ClassicExposure':str(analysis['exposure']['xi']),'ClassicBefore':analysis['knowledge_times']['before'],
        'ClassicAfter':analysis['knowledge_times']['after'],'ClassicArrival':analysis['revision_arrival_time'],
        'ClassicOldValue':f"{a['resolved_value']:.8f}".rstrip('0').rstrip('.'),
        'ClassicNewValue':f"{b['resolved_value']:.8f}".rstrip('0').rstrip('.'),
        'ClassicThreshold':f"{a['test']['threshold']:.8f}".rstrip('0').rstrip('.')}
    out=Path('paper/generated/classic_network');out.mkdir(parents=True,exist_ok=True)
    (out/'macros.tex').write_text('\n'.join(r'\newcommand{\%s}{%s}'%(k,v) for k,v in macros.items())+'\n')
    labels={c['claim_id']:('R' if c['proposition']=='answer' else 'C_{'+c['proposition'].split('_')[0]+'}') for c in analysis['admitted_claims']}
    expression=[]
    for c in analysis['admitted_claims']:
        terms=[]
        for witness in c['witnesses']:
            terms.append(r'\land '.join('b_{'+token+'}(t)' if token in config['program_case']['tests'] else 'S('+labels[token]+',t)' for token in witness))
        expression.append('S('+labels[c['claim_id']]+r',t)&='+r'\lor '.join(terms))
    (out/'witness_expression.tex').write_text('\\[\n\\begin{aligned}\n'+r'\\'.join(expression)+'\n\\end{aligned}\n\\]\n')
    write_json(out/'manifest.json',{'inputs':{str(ROOT/'manifest.json'):digest_file(ROOT/'manifest.json')},
        'generated_tex':{str(p):digest_file(p) for p in sorted(out.glob('*.tex'))}})
    print({'nodes':len(views[-1]['nodes']),'edges':len(views[-1]['edges']),'core':len(ann['visible_core_ids']),
           'support':analysis['support'],'sets':{k:len(v) for k,v in analysis['sets'].items()},'exposure':analysis['exposure']})


if __name__=='__main__':run()
