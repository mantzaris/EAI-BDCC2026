"""Seeded spatial network drawing of a typed view with precomputed annotations.

Only coordinates and labels are computed here. Support, core and revision-set
memberships must be supplied by classic_analysis; layout never evaluates evidence.
"""
from collections import defaultdict
from io import BytesIO
import math
import os
os.environ.setdefault('MPLCONFIGDIR','.local/matplotlib')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import networkx as nx
import numpy as np

WIDTH=12.2/2.54*72
HEIGHT=402.0
FONT=9.2
EDGE_FONT=9.0
COLORS={'claim':'#E5F2E9','feature':'#E5EFF8','observation':'#F0F0F0'}
U_COLOR='#B34B16'
REACH_COLOR='#8065A4'
INK='#294651'


def short_label(n):
    """Short semantic names come from the record/program, never layout roles."""
    r=n['record'];mark='*' if n.get('equations',{}).get('in_core') else ''
    program=r['metadata'].get('semantic_program')
    if program:
        prop=program['proposition']
        if prop=='answer':key='R';meaning='either window'
        else:
            route=prop.split('_')[0];key='C'+route;meaning=route+' passes'
        e=n.get('equations',{});truth=lambda x:'T' if x else 'F'
        transition=truth(e['support_before'])+'→'+truth(e['support_after']) if e.get('support_before') is not None else n['support_state']
        return f'{key}{mark} v{r["version"]}\n{meaning}\n{transition}'
    if n['type']=='feature':
        quantities={'eda_median':'EDA median','eda_iqr':'EDA IQR','acceleration_magnitude_sd':'ACC SD','eda_missing_fraction':'EDA missing'}
        return f'{n["short_id"]}{mark} v{r["version"]}\n{quantities.get(r["quantity"],r["quantity"].replace("_"," "))}'
    channel=r['metadata'].get('channel','source').upper().replace('MOTION','ACC')
    return f'{n["short_id"]} v{r["version"]}\n{channel} window'


def edge_label(edge, view):
    if edge['type']=='SUPERSEDES':return 'revises'
    if edge['type']=='DERIVED_FROM':return 'from'
    by={n['id']:n for n in view['nodes']};source=by[edge['source']]
    p=source['record']['metadata'].get('semantic_program')
    if not p:return 'cites'
    target=by[edge['target']]
    if target['type']=='claim':
        route=target['record']['metadata']['semantic_program']['proposition'].split('_')[0]
        return 'OR '+route
    return 'AND '+target['short_id'][:1]


def text_size(text, size):
    font=FontProperties(family='DejaVu Sans',size=size)
    width=max(TextPath((0,0),line or ' ',prop=font).get_extents().width for line in text.split('\n'))
    return float(width),len(text.split('\n'))*size*1.16


def overlap(a,b,gap=0):
    return not (a[2]+gap<=b[0] or b[2]+gap<=a[0] or a[3]+gap<=b[1] or b[3]+gap<=a[1])


def rectangle(x,y,w,h):return (x-w/2,y-h/2,x+w/2,y+h/2)


def point_clear(p, obstacles):
    for x,y,w,h in obstacles:
        if ((p[0]-x)/(w/2+3))**2+((p[1]-y)/(h/2+3))**2<1:return False
    return True


def bezier(a,c,b,t):return (1-t)**2*a+2*(1-t)*t*c+t*t*b


def tangent(a,c,b,t):return 2*(1-t)*(c-a)+2*t*(b-c)


def detour(a,b,obstacles,ymin,width,height):
    """Shortest visibility path around expanded node envelopes; no new relation."""
    points=[a,b]
    for x,y,w,h in obstacles:
        points.extend(np.array([x+sx*(w/2+7),y+sy*(h/2+7)]) for sx in (-1,1) for sy in (-1,1))
    points=points[:2]+[p for p in points[2:] if 3<p[0]<width-3 and ymin<p[1]<height-3 and point_clear(p,obstacles)]
    graph=nx.Graph();graph.add_nodes_from(range(len(points)))
    for i in range(len(points)):
        for j in range(i+1,len(points)):
            delta=points[j]-points[i];length=np.linalg.norm(delta)
            if all(point_clear(points[i]+t*delta,obstacles) for t in np.linspace(0,1,max(10,int(length/2)))):
                graph.add_edge(i,j,weight=float(length))
    if not nx.has_path(graph,0,1):
        # Corners alone can miss a narrow passage beside an ellipse, especially
        # near the canvas edge. Add clearance points around its actual envelope.
        candidates=[np.array([x+(w/2+7)*math.cos(t),y+(h/2+7)*math.sin(t)])
                    for x,y,w,h in obstacles for t in np.linspace(0,2*math.pi,16,endpoint=False)]
        for p in candidates:
            if not (3<p[0]<width-3 and ymin<p[1]<height-3 and point_clear(p,obstacles)):continue
            i=len(points);graph.add_node(i)
            for j,q in enumerate(points):
                delta=q-p;length=np.linalg.norm(delta)
                if all(point_clear(p+t*delta,obstacles) for t in np.linspace(0,1,max(10,int(length/2)))):
                    graph.add_edge(i,j,weight=float(length))
            points.append(p)
    return [points[i] for i in nx.shortest_path(graph,0,1,weight='weight')]


def rounded_path(points):
    vertices=[points[0]];codes=[MplPath.MOVETO]
    for prev,p,nxt in zip(points,points[1:],points[2:]):
        p=np.array(p);v=p-np.array(prev);w=np.array(nxt)-p
        radius=min(4.,np.linalg.norm(v)/3,np.linalg.norm(w)/3)
        vertices.extend([p-radius*v/np.linalg.norm(v),p,p+radius*w/np.linalg.norm(w)])
        codes.extend([MplPath.LINETO,MplPath.CURVE3,MplPath.CURVE3])
    vertices.append(points[-1]);codes.append(MplPath.LINETO)
    return MplPath(vertices,codes)


def spring_layout(views, seed=20260929, strict=True, rotation_degrees=0):
    nodes={};edges={}
    for v in views:
        for n in v['nodes']:nodes[n['id']]=n
        for e in v['edges']:edges[e['id']]=e
    # Expansion grows the canvas instead of shrinking the readable labels.
    # The 14-record publication view retains its exact physical dimensions.
    scale=1.+.18*max(0,len(nodes)-14)
    width,height=WIDTH*scale,88+(HEIGHT-88)*scale
    order=sorted(nodes);g=nx.Graph();g.add_nodes_from(order)
    g.add_edges_from(sorted({tuple(sorted((e['source'],e['target']))) for e in edges.values()}))
    initial=nx.spring_layout(g,seed=seed,iterations=500,k=.60,weight=None,threshold=1e-6)
    xy=np.array([initial[i] for i in order]);xy-=xy.mean(axis=0)
    # A global rotation and rescaling fit the canvas; neither adds graph edges.
    if len(order)>1:
        _,_,axes=np.linalg.svd(xy,full_matrices=False);xy=xy@axes.T
    angle=math.radians(rotation_degrees);xy=xy@np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
    sizes={}
    for v in views:
        for n in v['nodes']:
            w,h=text_size(short_label(n),FONT)
            old=sizes.get(n['id'],(0,0));sizes[n['id']]=(max(old[0],w*1.14+9,46),max(old[1],h*1.35+4,31))
    ymin,ymax=88.,height-9
    for dim,(lo,hi) in enumerate(((9.,width-9),(ymin,ymax))):
        radii=np.array([sizes[i][dim]/2 for i in order])
        amin,amax=xy[:,dim].min(),xy[:,dim].max()
        xy[:,dim]=lo+radii.max()+(xy[:,dim]-amin)/(amax-amin)*(hi-lo-2*radii.max()) if amax>amin else (lo+hi)/2
    start=xy.copy()
    # Minimize overlap penalties around the spring embedding, using ellipse
    # clearance rather than imposing ranks or grid slots.
    from scipy.optimize import minimize
    from scipy import __version__ as scipy_version
    dims=np.array([sizes[i] for i in order])
    bounds=[bound for w,h in dims for bound in ((w/2+5,width-w/2-5),(ymin+h/2,ymax-h/2))]
    pairs=[(i,j,(dims[i]+dims[j])/2+np.array([8,9])) for i in range(len(order)) for j in range(i+1,len(order))]
    ii=np.array([i for i,j,r in pairs],dtype=int);jj=np.array([j for i,j,r in pairs],dtype=int);radii=np.array([r for i,j,r in pairs])
    connected={frozenset(e) for e in g.edges()}
    radii=np.array([r+np.array([17,17]) if frozenset((order[i],order[j])) in connected else r for i,j,r in pairs]).reshape((-1,2))
    def objective(flat):
        p=flat.reshape((-1,2));offset=(p[ii]-p[jj])/radii
        distance=np.maximum(np.linalg.norm(offset,axis=1),1e-9)
        intrusion=np.maximum(0,1.04-distance)
        value=.002*np.sum((p-start)**2)+10000*np.sum(intrusion**2)
        grad=.004*(p-start)
        push=(-20000*intrusion/distance)[:,None]*offset/radii
        np.add.at(grad,ii,push);np.add.at(grad,jj,-push)
        return value,grad.ravel()
    optimized=minimize(objective,xy.ravel(),jac=True,method='L-BFGS-B',bounds=bounds,
                       options={'maxiter':1200,'ftol':1e-12,'maxfun':80000})
    xy=optimized.x.reshape((-1,2))
    positions={rid:{'x':float(p[0]),'y':float(p[1]),'width':sizes[rid][0],'height':sizes[rid][1]} for rid,p in zip(order,xy)}
    boxes={rid:rectangle(n['x'],n['y'],n['width'],n['height']) for rid,n in positions.items()}
    collisions=[(order[i],order[j]) for i,j,r in pairs if np.linalg.norm((xy[j]-xy[i])/r)<1.01]
    if collisions:raise ValueError(('overlapping node labels',collisions))
    union={**views[-1],'nodes':list(nodes.values()),'edges':list(edges.values())}
    routes={};label_boxes=[];issues=[];parallel=defaultdict(list);used_curvatures=defaultdict(set)
    for e in edges.values():parallel[(e['source'],e['target'])].append(e['id'])
    # Long routes are harder to annotate, so place those labels first.
    ordered=sorted(edges.values(),key=lambda e:(-len(edge_label(e,union)),e['id']))
    for e in ordered:
        pa=positions[e['source']];pb=positions[e['target']]
        a=np.array([pa['x'],pa['y']]);b=np.array([pb['x'],pb['y']]);normal=np.array([-(b-a)[1],(b-a)[0]])
        obstacles=[(p['x'],p['y'],p['width'],p['height']) for rid,p in positions.items() if rid not in {e['source'],e['target']}]
        label=edge_label(e,union);lw,lh=text_size(label,EDGE_FONT);lw+=4;lh+=3
        alternatives=[]
        pair=(e['source'],e['target'])
        for rad in (0.,.12,-.12,.24,-.24,.40,-.40,.6,-.6,.9,-.9):
            if rad in used_curvatures[pair]:continue
            c=(a+b)/2+normal*rad
            def port(p,toward):
                d=toward-np.array([p['x'],p['y']]);d/=np.linalg.norm(d)
                radius=1/math.sqrt((d[0]/(p['width']/2+1.8))**2+(d[1]/(p['height']/2+1.8))**2)
                return np.array([p['x'],p['y']])+d*radius
            aa,bb=port(pa,c),port(pb,c)
            samples=np.array([bezier(aa,c,bb,t) for t in np.linspace(0,1,45)])
            hits=sum(not point_clear(p,obstacles) for p in samples)
            outside=sum(not (2<p[0]<width-2 and ymin-5<p[1]<height-2) for p in samples)
            # Each edge gets its own annotation; no row/edge bundles exist here.
            for t in (.50,.38,.62,.27,.73,.17,.83):
                p=bezier(aa,c,bb,t);v=tangent(aa,c,bb,t);perp=np.array([-v[1],v[0]])/np.linalg.norm(v)
                for offset in (0,8,-8,14,-14,21,-21,28,-28):
                    labelxy=p+offset*perp;box=rectangle(*labelxy,lw,lh)
                    if box[0]<2 or box[2]>width-2 or box[1]<ymin-3 or box[3]>height-2:continue
                    conflicts=sum(overlap(box,n,3) for n in boxes.values())+sum(overlap(box,n,3) for n in label_boxes)
                    score=hits*1000+outside*10000+conflicts*100000+abs(rad)*15+abs(offset)*.15+abs(t-.5)*8
                    alternatives.append((score,hits,outside,conflicts,aa,c,bb,labelxy,box,rad))
        chosen=min(alternatives,key=lambda x:x[0])
        score,hits,outside,conflicts,aa,c,bb,labelxy,box,rad=chosen
        polyline=None
        if hits or outside or conflicts:
            polyline=detour(a,b,obstacles,ymin-2,width,height)
            polyline[0]=port(pa,polyline[1]);polyline[-1]=port(pb,polyline[-2])
            placements=[]
            for first,last in zip(polyline,polyline[1:]):
                v=last-first;perp=np.array([-v[1],v[0]])/np.linalg.norm(v)
                for t in (.5,.3,.7):
                    for offset in (0,8,-8,14,-14,21,-21):
                        p=first+t*v+offset*perp;candidate=rectangle(*p,lw,lh)
                        if candidate[0]<2 or candidate[2]>width-2 or candidate[1]<ymin-3 or candidate[3]>height-2:continue
                        overlaps=sum(overlap(candidate,n,3) for n in boxes.values())+sum(overlap(candidate,n,3) for n in label_boxes)
                        placements.append((overlaps*10000+abs(offset)+abs(t-.5)*8,overlaps,p,candidate))
            _,conflicts,labelxy,box=min(placements,key=lambda x:x[0])
            hits=outside=0
        if conflicts or outside or hits:
            issues.append([e['id'],hits,outside,conflicts])
            if strict:raise ValueError(('no clear edge route/label',label,e['id'],hits,outside,conflicts))
        label_boxes.append(box);used_curvatures[pair].add(rad)
        routes[e['id']]={'start':aa.tolist(),'control':c.tolist(),'end':bb.tolist(),'label':label,
                         'label_position':labelxy.tolist(),'label_bounds':list(box),'curvature':rad,
                         'polyline':[p.tolist() for p in polyline] if polyline is not None else None}
    return {'engine':'NetworkX spring_layout + deterministic label separation and quadratic routing',
            'networkx_version':nx.__version__,'matplotlib_version':matplotlib.__version__,
            'scipy_version':scipy_version,
            'seed':seed,'rotation_degrees':rotation_degrees,'iterations':500,'k':.60,'threshold':1e-6,'positioning_projection':'undirected simple union; no semantic analysis on this projection',
            'rendering_graph':'original typed directed multigraph; all selected edges individually retained',
            'parallel_policy':'distinct curvatures per source/target pair',
            'separation':{'tether_weight':.002,'overlap_penalty':10000,'ellipse_clearance':[8,9],'edge_extra_clearance':17,'optimizer':'L-BFGS-B, analytic gradient, 1200 iterations maximum'},
            'width_points':width,'height_points':height,'canvas_policy':'expand beyond 14 records; keep font sizes fixed','font_size':FONT,'edge_font_size':EDGE_FONT,
            'nodes':positions,'edges':routes,'node_collisions':collisions,'edge_node_intersections':0,'label_collisions':sum(i[3] for i in issues),'routing_issues':issues}


def draw(view, layout, highlight=None):
    fig=plt.figure(figsize=(layout['width_points']/72,layout['height_points']/72),dpi=144)
    ax=fig.add_axes((0,0,1,1));ax.set_xlim(0,layout['width_points']);ax.set_ylim(0,layout['height_points']);ax.axis('off')
    groups={w['id']:w for w in view['witness_groups']}
    highlighted=set(groups[highlight]['stored_edge_ids']) if highlight in groups else {highlight}
    by={n['id']:n for n in view['nodes']}
    for e in view['edges']:
        r=layout['edges'][e['id']];color=U_COLOR if e['type']=='SUPERSEDES' else '#7B868D' if e['type']=='DERIVED_FROM' else '#416779'
        if e['id'] in highlighted:color='#AB4083'
        path=rounded_path(r['polyline']) if r.get('polyline') else MplPath([r['start'],r['control'],r['end']],[MplPath.MOVETO,MplPath.CURVE3,MplPath.CURVE3])
        patch=FancyArrowPatch(path=path,arrowstyle='-|>',mutation_scale=8,linewidth=1.7 if e['id'] in highlighted else .95,
                              color=color,zorder=2)
        patch.set_gid('edge-'+e['id']);ax.add_patch(patch)
        ax.text(*r['label_position'],r['label'],fontsize=EDGE_FONT,ha='center',va='center',color=color,zorder=5,
                bbox={'facecolor':'white','edgecolor':'none','pad':.25},gid='edge-label-'+e['id'])
    for n in view['nodes']:
        p=layout['nodes'][n['id']];eq=n.get('equations',{});member=eq.get('membership',{})
        if member.get('reachable_claims'):
            ax.add_patch(Ellipse((p['x'],p['y']),p['width']+7,p['height']+7,fill=False,edgecolor=REACH_COLOR,linestyle=(0,(2,2)),linewidth=1.25,zorder=3))
        color=U_COLOR if member.get('U_delta') or member.get('B_delta') else INK
        if n['id']==highlight:color='#AB4083'
        patch=Ellipse((p['x'],p['y']),p['width'],p['height'],facecolor=COLORS[n['type']],edgecolor=color,
                      linewidth=1.9 if member.get('U_delta') or member.get('B_delta') or n['id']==highlight else .8,zorder=4)
        patch.set_gid('node-'+n['id']);ax.add_patch(patch)
        if member.get('B_delta'):
            ax.add_patch(Ellipse((p['x'],p['y']),p['width']-4,p['height']-4,fill=False,edgecolor=color,linewidth=.8,zorder=4))
        ax.text(p['x'],p['y'],short_label(n),fontsize=FONT,ha='center',va='center',linespacing=1.05,color='#182C35',zorder=6,gid='node-label-'+n['id'])
    # Compact, separate annotation strip: ontology fill and equation outline do
    # not share a visual channel. All numerical content below is precomputed.
    for x,typ,label in ((10,'claim','ClaimVersion'),(125,'feature','FeatureVersion'),(251,'observation','Observation')):
        ax.add_patch(Ellipse((x,69),9,7,facecolor=COLORS[typ],edgecolor=INK,lw=.7))
        ax.text(x+8,69,label,fontsize=9,va='center')
    ax.text(4,51,'* in current core K; unstarred nodes are review context',fontsize=9,va='center')
    ax.text(4,36,'Orange: input versions Uδ; dotted: reachable claims',fontsize=9,va='center')
    ax.text(4,21,'Double outline: changed support Bδ; labels: before → after',fontsize=9,va='center')
    ann=view['equation_annotations'];xi=ann['exposure'];claim_count=len(ann['full_sets']['reachable_claims']);changed=len(ann['full_sets']['B_delta'])
    exposure='NA' if xi['xi'] is None else f"{xi['numerator']}/{xi['denominator']} = {xi['xi']:g}"
    ax.text(4,6,f'Full claim sets: reachable {claim_count}; changed {changed}; ξδ = {exposure}',fontsize=9,va='center')
    return fig


def render_bytes(view, layout, format='svg', highlight=None):
    with plt.rc_context({'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'classic_network_v1'}):
        fig=draw(view,layout,highlight);buffer=BytesIO()
        metadata={'Date':None} if format=='svg' else {'CreationDate':None,'ModDate':None} if format=='pdf' else None
        fig.savefig(buffer,format=format,dpi=210,metadata=metadata)
        plt.close(fig)
        return buffer.getvalue()
