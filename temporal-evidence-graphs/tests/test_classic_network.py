"""Scientific annotations and shared rendering, without a desired-picture oracle."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from temporal_evidence.io import read_json, digest_object
from temporal_evidence.semantic.classic_example import prepare, ROOT, FIGURE
from temporal_evidence.semantic.classic_analysis import analyze_case, predicate_rows, reverse_reachable
from temporal_evidence.semantic.classic_render import render_bytes, spring_layout
from temporal_evidence.semantic.export import read_export
from temporal_evidence.semantic.review_view import validate_view
from temporal_evidence.dashboard.network_panel import load_classic


@pytest.fixture(scope='module')
def case():return prepare()


def test_actual_instance_identity_time_types_and_unbundled_relations(case):
    config,analysis,views=case;graph=read_export(config['export'])
    for view in views:
        validate_view(view,graph)
        assert 10<=len(view['nodes'])<=20
        assert not view['budget']['partial']
        assert all(e['directly_stored'] for e in view['edges'])
        assert all(n['record']['ingested_at_seconds']<=view['knowledge_time'] for n in view['nodes'])
        assert all(n['ontology_class'] in {'ClaimVersion','FeatureVersion','Observation'} for n in view['nodes'])
    assert len(views[1]['nodes'])==len(views[0]['nodes'])+1
    assert all(n['id'] not in {x['id'] for x in views[0]['nodes']} for n in views[1]['nodes'] if n['record']['version']==2)


def test_support_witnesses_and_independent_required_changes(case):
    config,a,views=case;claims=a['admitted_claims'];mapping=a['claim_id_map'];program=config['program_case']
    assert a['support']['before']=={c['claim_id']:True for c in claims}
    roots=[c for c in claims if c['proposition']=='answer']
    assert len(roots)==1 and a['support']['after'][roots[0]['claim_id']]
    assert any(not a['support']['after'][c['claim_id']] for c in claims)
    for c in claims:
        expected=[[program['tests'][t]['source_id'] if t in program['tests'] else mapping[t] for t in w] for w in c['witnesses']]
        actual=[w['inputs'] for w in views[-1]['witness_groups'] if w['owner']==mapping[c['claim_id']]]
        assert actual==expected
    assert a['sets']['A_delta']==a['sets']['D_delta']==a['sets']['B_delta']
    assert a['exposure']=={'numerator':0,'denominator':len(a['sets']['A_delta']),'xi':0.0}
    assert a['predicates']['before']['A1']['truth'] and not a['predicates']['after']['A1']['truth']
    assert a['predicates']['after']['A1']['checks']['available']


def test_annotations_ignore_stored_outcome_flags_and_match_full_sets(case):
    config,a,views=case;g=deepcopy(read_export(config['export']))
    for n in g['nodes']:
        if n['semantic_type']=='assessment':n['properties']['state']='invented_outcome'
    changed=analyze_case(g,config['program_case'],read_json(config['candidate_path']),read_json(config['replay_path']),config['times'].values())
    assert a['sets']==changed['sets'] and a['support']==changed['support'] and a['exposure']==changed['exposure']
    assert reverse_reachable(a['full_scope']['dependency_edges'],a['sets']['U_delta'])==set(a['sets']['R_delta'])
    assert all(e['type']=='DEPENDS_ON' for e in a['full_scope']['dependency_edges'])
    for v in views:
        ids={n['id'] for n in v['nodes']}
        for key,full in a['sets'].items():
            assert set(v['equation_annotations']['visible_sets'][key])==set(full)&ids
            assert {n['id'] for n in v['nodes'] if n['equations']['membership'][key]}==set(full)&ids


def test_core_context_and_wrong_subject_predicate_are_distinct(case):
    config,a,views=case;v=views[-1]
    old=next(n for n in v['nodes'] if n['id']==config['program_case']['tests']['A1']['source_id'])
    new=next(n for n in v['nodes'] if n['record'].get('supersedes_id')==old['id'])
    assert not old['equations']['in_core'] and new['equations']['in_core']
    withdrawn=next(n for n in v['nodes'] if n['type']=='claim' and n['display_state']=='withdrawn')
    assert withdrawn['equations']['in_core'] and withdrawn['equations']['core_role']=='declared ancestor/input'
    events=deepcopy(config['program_case']['events'])
    altered=next(e for e in events if e['record_id']==old['id']);altered['subject_id']='wrong participant'
    assert not predicate_rows(config['program_case'],events,a['knowledge_times']['before'])['A1']['truth']
    altered['subject_id']=config['program_case']['subject'];altered['value']=0
    assert not predicate_rows(config['program_case'],events,a['knowledge_times']['before'])['A1']['truth']


def test_publication_dashboard_objects_and_individual_svg_edges(case):
    for state,v in zip(('before','after'),case[2]):
        ui,layout=load_classic(state)
        assert digest_object(v)==digest_object(ui)
        svg=render_bytes(ui,layout,'svg')
        assert svg==(ROOT/(state+'.svg')).read_bytes()
        xml=ET.fromstring(svg);ids={n.get('id') for n in xml.iter() if n.get('id')}
        assert {n['id'] for n in v['nodes']}=={i[5:] for i in ids if i.startswith('node-') and not i.startswith('node-label-')}
        assert {e['id'] for e in v['edges']}=={i[5:] for i in ids if i.startswith('edge-') and not i.startswith('edge-label-')}
        assert all('edge-label-'+e['id'] in ids for e in v['edges'])
        assert layout['label_collisions']==layout['edge_node_intersections']==0
        assert not layout['routing_issues'] and min(layout['font_size'],layout['edge_font_size'])>=9
    assert render_bytes(case[2][-1],layout,'svg')==FIGURE.with_suffix('.svg').read_bytes()


def test_classic_dashboard_controls_share_the_recorded_case():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file('src/temporal_evidence/dashboard/app.py',default_timeout=60).run()
    app.sidebar.selectbox[0].select('structural_alternatives').run()
    next(s for s in app.sidebar.selectbox if s.label=='Layout').select('Classic network').run()
    assert not app.exception
    next(s for s in app.sidebar.radio if s.label=='Recorded state').set_value('Before revision').run()
    assert not app.exception
    next(s for s in app.sidebar.slider if s.label=='Maximum record nodes').set_value(1).run()
    assert not app.exception and any('Partial view' in w.value for w in app.warning)
    next(s for s in app.sidebar.slider if s.label=='Maximum record nodes').set_value(40).run()
    app.sidebar.checkbox[0].check().run()
    assert not app.exception and not app.warning
