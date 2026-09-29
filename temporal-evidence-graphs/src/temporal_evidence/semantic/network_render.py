"""Graphviz layout and labeled rendering of the shared review graph.

Coordinates and routed splines are computed on a union graph and reused for all
recorded times. The SVG shown by Streamlit is produced by this same renderer.
"""
import copy
import html
import json
import subprocess
from pathlib import Path

from temporal_evidence.io import digest_object, write_json

TYPE_STYLE = {"claim":("box","#E5F2E9"), "feature":("box","#E5EFF8"), "observation":("note","#F0F0F0")}
QUANTITIES = {"eda_median":"EDA median", "eda_iqr":"EDA IQR", "acceleration_magnitude_sd":"Acceleration SD", "eda_missing_fraction":"EDA missing"}
STATE_COLORS = {"contradicted":"#B34B16","unsupported":"#B34B16","needs_review":"#916000","ambiguous_same_time":"#916000"}


def number(v, digits=6):
    return f"{v:.{digits}g}" if v is not None else "unavailable"


def node_label(n):
    r=n["record"];kind=n["type"];unit=r["unit"].replace("uS","μS");short=n["short_id"]
    version=f"{short} · v{r['version']}"
    if kind=="observation":
        return f"{short} v{r['version']} · {r['metadata'].get('channel','recording').upper()} window\n{r['event_start_seconds']:g}–{r['event_end_seconds']:g} s\n{r['metadata'].get('rate_hz','?'):g} Hz · {n['availability']}" if isinstance(r['metadata'].get('rate_hz'),(int,float)) else f"{version}\nObservation window\n{r['event_start_seconds']:g}–{r['event_end_seconds']:g} s"
    if kind=="feature":
        q=QUANTITIES.get(r["quantity"],r["quantity"].replace("_"," "))
        q=q.replace("Acceleration SD","Acc. SD").replace("EDA missing","Missing EDA")
        if "evaluated_value" in n:
            return f"{version}\n{q}\n{number(n['evaluated_value'])} {unit} (current)\nRecorded value: {number(r['value'])}\n{n['support_state']}"
        if n.get("test"):
            test=n["test"];op="≥" if test["operator"]=="ge" else "≤"
            status="prior value" if n["version_status"]!="current" else n["availability"]
            if n["version_status"]=="current":
                passes=r["evidence_state"]=="available" and r["value"] is not None and (r["value"]>=test["threshold"] if test["operator"]=="ge" else r["value"]<=test["threshold"])
                status=f"{op} {number(test['threshold'],5)} · {'pass' if passes else 'FAIL'}"
            return f"{version}{' · new' if n['changed'] else ''}\n{q}\n{number(r['value'],5)} {unit}\n{status}"
        return f"{version}{' · new' if n['changed'] else ''}\n{'EDA' if r['quantity']=='eda_median' else q} {number(r['value'],5)} {unit}\n{r['event_start_seconds']:g}–{r['event_end_seconds']:g} s\n{n['availability']+(' · prior' if n['version_status']!='current' else '')}"
    c=r["metadata"].get("claim",{});p=r["metadata"].get("semantic_program")
    status="ambiguous" if n["support_state"]=="ambiguous_same_time" else n["support_state"].replace("supported_at_admission","admitted")
    if p:
        prop=p["proposition"]
        if prop=="answer":
            counts={len(w) for w in n.get("proposition_witnesses") or []}
            count=str(next(iter(counts))) if len(counts)==1 else "specified"
            routes=" or ".join(f"W{i}" for i in range(1,len(p['witnesses'])+1))
            meaning=f"One window passes\nall {count} tests\n"+("OR: " if len(p['witnesses'])>1 else "Route: ")+routes;short="R"
        else:
            route=prop.split("_")[0];count=prop.rsplit("_",1)[-1]
            grouping="AND within W1" if len(p["witnesses"])==1 else "AND per witness"
            meaning=f"Window {route} passes\nall {count} tests\n{grouping}";short="C"+route
        return f"{short} · v{r['version']}\n{meaning}\n{status.replace(' (admitted)',' at admission')}\n{n['display_state']}"
    if c:
        meaning=("Δ EDA claim" if c.get("operator")=="difference" else "Target median")
        meaning+=f"\n{number(c.get('value'),7)} {unit}"
    else:
        import textwrap
        meaning="\n".join(textwrap.wrap(r["metadata"].get("sentence",r["quantity"] or short),32))
    return f"{version}\n{meaning}\n{status}\n{n['display_state']}"


def edge_label(e, view):
    by={n["id"]:n for n in view["nodes"]}
    if e["type"]=="SUPERSEDES":return "supersedes"
    if e["type"]=="DERIVED_FROM":return "derived\nfrom"
    if by[e["source"]]["record"]["metadata"].get("semantic_program"):
        groups={w["id"]:w for w in view["witness_groups"]}
        ws=[groups[i] for i in e["witness_groups"]]
        return "needs "+", ".join(f"W{w['index']}" for w in ws)
    return "requires" if by[e["target"]]["type"]=="claim" else "cites"


def drawing_objects(view):
    """Group disjoint multi-input witnesses into labeled record enclosures.

Every row maps to one stored feature; one visibly labeled bundle represents the
stored dependency edges. Enclosures/bundles are presentation constructs only.
Supersession still ends at the precise old-version row via its named port.
"""
    nodes={n["id"]:copy.deepcopy(n) for n in view["nodes"]};ports={};bundles=[];used=set()
    for w in view["witness_groups"]:
        owner=nodes[w["owner"]]
        if not owner["record"]["metadata"].get("semantic_program") or not w["complete"] or len(w["inputs"])<3:continue
        if not all(i in nodes and nodes[i]["type"]=="feature" and i not in used for i in w["inputs"]):continue
        gid="enclosure/"+w["id"];members=[nodes[i] for i in w["inputs"]]
        for j,n in enumerate(members):ports[n["id"]]=(gid,"p"+str(j));used.add(n["id"])
        nodes[gid]={"id":gid,"type":"witness_enclosure","members":members,"group":w,
                    "label":f"W{w['index']} · AND enclosure (view)","port_map":{i:ports[i][1] for i in w["inputs"]}}
        bundles.append({"id":"bundle/"+w["id"],"source":w["owner"],"target":gid,"type":"WITNESS_INPUT_BUNDLE",
                        "label":f"needs all {len(members)}\nW{w['index']} (AND)","directly_stored":False,
                        "meaning":"Rendering bundle of the listed stored DEPENDS_ON edges; jointly required inputs.",
                        "witness_edge_ids":w["stored_edge_ids"],"witness_group":w["id"]})
    grouped={i for b in bundles for i in b["witness_edge_ids"]}
    edges=[{**e,"label":edge_label(e,view)} for e in view["edges"] if e["id"] not in grouped]+bundles
    return {"nodes":[n for i,n in nodes.items() if i not in used],"edges":edges,"ports":ports,
            "enclosure_note":"Rows are actual immutable feature records; enclosing boxes and dependency bundles are rendering constructs, not extra database objects."}


def enclosure_label(n, highlight=None):
    rows=['<TR><TD BGCOLOR="#F7F9FB"><B>AND witness (view)</B><BR/>all '+str(len(n['members']))+' inputs required</TD></TR>']
    for item in n["members"]:
        r=item["record"];t=item["test"];unit=r["unit"].replace("uS","μS")
        name=QUANTITIES.get(r["quantity"],r["quantity"]).replace("Acceleration SD","Acc. SD")
        title=f"{item['short_id']} v{r['version']} · {name}"
        if item["version_status"]!="current":value=f"{number(r['value'],5)} {unit} · prior value"
        else:
            op="≥" if t["operator"]=="ge" else "≤"
            passed=r["evidence_state"]=="available" and r["value"] is not None and (r["value"]>=t["threshold"] if op=="≥" else r["value"]<=t["threshold"])
            value=f"{number(r['value'],5)} {op} {number(t['threshold'],5)} {unit}"
            value+="<BR/>"+("pass" if passed else "FAIL")
        rows.append('<TR><TD PORT="'+n["port_map"][item["id"]]+'" BGCOLOR="'+('#F6E6F0' if item['id']==highlight else '#E5EFF8')+'">'+html.escape(title)+'<BR/>'+value+'</TD></TR>')
    return '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6" COLOR="#416779">'+"".join(rows)+'</TABLE>>'


def dot_source(view, *, rankdir="TB", layout=None, highlight=None, font_size=16):
    q=lambda s:json.dumps(str(s),ensure_ascii=False)
    attrs=lambda d:",".join(f"{k}={q(v)}" for k,v in d.items())
    lines=['digraph review {', f'graph [{attrs({"rankdir":rankdir,"nodesep":"0.22","ranksep":"0.60","pad":"0.10","margin":"0","splines":"spline","outputorder":"edgesfirst","bgcolor":"white","fontname":"DejaVu Sans","ordering":"out"})}];',
        f'node [fontname="DejaVu Sans",fontsize={font_size},margin="0.12,0.09",penwidth=1.25];',
        f'edge [fontname="DejaVu Sans",fontsize={font_size-1},arrowsize=0.7,color="#52616B",penwidth=1.15];']
    highlighted=set()
    if highlight:
        group=next((w for w in view["witness_groups"] if w["id"]==highlight),None)
        if group:highlighted=set(group["stored_edge_ids"])
        elif any(e["id"]==highlight for e in view["edges"]):highlighted={highlight}
    drawing=drawing_objects(view)
    for n in drawing["nodes"]:
        if n["type"]=="witness_enclosure":
            a={"shape":"none","margin":0}
            if layout:
                pos=layout["nodes"][n["id"]];a.update(pos=pos["pos"],width=pos["width"],height=pos["height"],fixedsize="true",pin="true")
            lines.append(q(n["id"])+" ["+attrs(a)+",label="+enclosure_label(n,highlight)+"];")
            continue
        shape,fill=TYPE_STYLE[n["type"]]
        color=STATE_COLORS.get(n["support_state"],"#416779") if n["type"]=="claim" else "#B34B16" if n["changed"] else "#416779"
        style="rounded,filled" if shape=="box" else "filled"
        if n["version_status"]=="historical version" and n["type"]!="claim":style+=",dashed"
        a={"label":node_label(n),"shape":shape,"style":style,"fillcolor":fill,"color":color,
           "penwidth":2.1 if n["affected"] or n["changed"] else 1.25,"tooltip":n["id"]}
        if highlight==n["id"] or any(e["id"] in highlighted and n["id"] in {e["source"],e["target"]} for e in view["edges"]):a.update(color="#CC79A7",penwidth=3)
        if layout:
            pos=layout["nodes"][n["id"]];a.update(pos=pos["pos"],width=pos["width"],height=pos["height"],fixedsize="true",pin="true")
        lines.append(q(n["id"])+" ["+attrs(a)+"];")
    for e in drawing["edges"]:
        a={"label":e["label"],"id":e["id"],"tooltip":e["type"]+": "+e["meaning"]}
        if not e["directly_stored"]:a["style"]="dashed"
        if e["type"]=="SUPERSEDES":a.update(color="#B34B16",fontcolor="#A3481A",penwidth=1.8,constraint="false" if any(n["record"]["metadata"].get("semantic_program") for n in view["nodes"]) else "true")
        if e["type"]=="DERIVED_FROM" and any(n["record"]["metadata"].get("semantic_program") for n in view["nodes"]) and next(n for n in view["nodes"] if n["id"]==e["source"])["record"].get("supersedes_id"):a["constraint"]="false"
        if e["id"] in highlighted or set(e["witness_edge_ids"]) & highlighted:a.update(color="#CC79A7",fontcolor="#7A3970",penwidth=2.8)
        if layout:
            path=layout["edges"][e["id"]];a["pos"]=path["pos"]
            if path.get("lp"):a["lp"]=path["lp"]
        endpoint=lambda rid:(q(drawing["ports"][rid][0])+":"+q(drawing["ports"][rid][1]) if rid in drawing["ports"] else q(rid))
        lines.append(endpoint(e["source"])+" -> "+endpoint(e["target"])+" ["+attrs(a)+"];")
    if layout:
        # Invisible layout anchors keep the union canvas fixed when a version is
        # not yet visible. They carry no database or semantic assertion.
        x0,y0,x1,y1=layout["bb"].split(",")
        for k,x,y in (("min",x0,y0),("max",x1,y1)):
            lines.append(f'"__layout_{k}" [label="",shape=point,width=0,height=0,style=invis,pos="{x},{y}!",pin=true];')
    return "\n".join(lines+["}"])


def graphviz(dot, format="json", fixed=False):
    command=["neato","-n2"] if fixed else ["dot"]
    r=subprocess.run(command+["-T"+format],input=dot.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    if b"Warning" in r.stderr:
        raise RuntimeError(r.stderr.decode())
    return r.stdout


def union_layout(views, rankdir="TB", font_size=16):
    nodes={};edges={};groups={};sizes={}
    for v in views:
        for n in v["nodes"]:
            nodes[n["id"]]=n
        edges.update({e["id"]:e for e in v["edges"]});groups.update({w["id"]:w for w in v["witness_groups"]})
        measured=json.loads(graphviz(dot_source(v,rankdir=rankdir,font_size=font_size)))
        for n in measured.get("objects",[]):
            if "pos" not in n:continue
            old=sizes.get(n["name"],(0,0));sizes[n["name"]]=(max(old[0],float(n["width"])+.05),max(old[1],float(n["height"])+.05))
    union={**views[-1],"nodes":list(nodes.values()),"edges":list(edges.values()),"witness_groups":list(groups.values())}
    dot=dot_source(union,rankdir=rankdir,font_size=font_size)
    extra=[json.dumps(rid)+f' [width="{w}",height="{h}",fixedsize=true];' for rid,(w,h) in sizes.items()]
    dot=dot[:-1]+"\n"+"\n".join(extra)+"\n}"
    data=json.loads(graphviz(dot))
    # Dot avoids node/edge-label overlap but can leave adjacent edge labels
    # visually concatenated. Reserve a clear gap, keeping each label close to
    # its routed path. This deterministic annotation adjustment is saved in p.
    obstacles=[]
    for n in data["objects"]:
        if "pos" not in n:continue
        x,y=map(float,n["pos"].split(","));w=float(n["width"])*72;h=float(n["height"])*72
        obstacles.append((x-w/2-3,y-h/2-3,x+w/2+3,y+h/2+3))
    label_adjustments={}
    overlap=lambda a,b:not(a[2]<b[0] or b[2]<a[0] or a[3]<b[1] or b[3]<a[1])
    for e in sorted(data.get("edges",[]),key=lambda x:x["id"]):
        texts=[x for x in e.get("_ldraw_",[]) if x["op"]=="T"]
        if not texts or not e.get("lp"):continue
        width=max(x["width"] for x in texts);height=len(texts)*(font_size-1)*1.2
        x,y=map(float,e["lp"].split(","));original=[x,y]
        candidates=sorted(((dx,dy) for dy in range(-48,49,12) for dx in range(-72,73,12)),key=lambda p:(p[0]*p[0]+p[1]*p[1],abs(p[1]),p))
        for dx,dy in candidates:
            rectangle=(x+dx-width/2-6,y+dy-height/2-3,x+dx+width/2+6,y+dy+height/2+3)
            if not any(overlap(rectangle,r) for r in obstacles):
                e["lp"]=f"{x+dx:g},{y+dy:g}";obstacles.append(rectangle)
                label_adjustments[e["id"]]={"original":original,"placed":[x+dx,y+dy]}
                break
        else:raise ValueError("No legible label placement for "+e["id"])
    return {"engine":"Graphviz dot → neato -n2 (fixed routed splines)","version":subprocess.check_output(["dot","-V"],stderr=subprocess.STDOUT,text=True).strip(),
            "seed":None,"determinism":"sorted immutable IDs, deterministic dot; no random seed",
            "rankdir":rankdir,"nodesep":.22,"ranksep":.60,"font_size":font_size,"edge_font_size":font_size-1,
            "bb":data["bb"],"label_adjustments":label_adjustments,"nodes":{n["name"]:{k:n[k] for k in ("pos","width","height")} for n in data["objects"] if "pos" in n},
            "edges":{e["id"]:{k:e.get(k) for k in ("pos","lp")} for e in data.get("edges",[])},
            "layout_only_objects":["__layout_min","__layout_max"],"layout_only_edges":[e["id"] for e in data.get("edges",[]) if e["id"].startswith("__order/")],"union_view_hashes":[digest_object(v) for v in views]}


def render_bytes(view, layout, format="svg", highlight=None):
    return graphviz(dot_source(view,layout=layout,rankdir=layout["rankdir"],font_size=layout["font_size"],highlight=highlight),format,fixed=True)


def save_network(view, layout, path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    for ext in ("pdf","svg","png"):
        path.with_suffix("."+ext).write_bytes(render_bytes(view,layout,ext))
    path.with_suffix(".dot").write_text(dot_source(view,layout=layout,rankdir=layout["rankdir"],font_size=layout["font_size"]))
    manifest={"view_sha256":digest_object(view),"scope":view["scope"],"case_id":view["case_id"],"knowledge_time":view["knowledge_time"],
              "source":view["source"],"node_ids":[n["id"] for n in view["nodes"]],"edge_ids":[e["id"] for e in view["edges"]],
              "hidden_relations":view["context"]["hidden_relations"],"witness_groups":view["witness_groups"],"derived_paths":view["derived_paths"],
              "layout":layout,"drawing_objects":drawing_objects(view),"budget":view["budget"],"labels":{"nodes":{n["id"]:node_label(n) for n in view["nodes"]},
              "edges":{e["id"]:edge_label(e,view) for e in view["edges"]}},
              "edge_label_mapping":{"cites":"DEPENDS_ON (evidence)","requires":"DEPENDS_ON (parent)","needs":"DEPENDS_ON (witness input)",
                                    "derived from":"DERIVED_FROM","supersedes":"SUPERSEDES"}}
    write_json(path.with_suffix(".manifest.json"),manifest)
    return manifest
