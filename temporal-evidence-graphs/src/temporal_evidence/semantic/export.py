"""Read-only export of actual Neo4j nodes/relationships, including adapter objects."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from neo4j import GraphDatabase
from temporal_evidence.io import write_json, digest_file, utc_now
from temporal_evidence.semantic.ontology import kind, node_origin, edge_origin, validate_export

NODE_QUERY = "MATCH (n) WHERE n.scope STARTS WITH $prefix RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties ORDER BY n.scope, id"
EDGE_QUERY = "MATCH (n)-[r]->(m) WHERE n.scope STARTS WITH $prefix RETURN elementId(r) AS id, elementId(n) AS source, elementId(m) AS target, type(r) AS type, properties(r) AS properties, n.scope AS scope ORDER BY scope, id"
COUNT_QUERY = "MATCH (n) WHERE n.scope STARTS WITH $prefix OPTIONAL MATCH (n)-[r]->() RETURN n.scope AS scope, count(DISTINCT n) AS nodes, count(r) AS edges ORDER BY scope"
PATH_QUERY = "MATCH (c:ClaimVersion {scope:$scope})-[:DEPENDS_ON]->(f:FeatureVersion)-[:DERIVED_FROM]->(o:Observation) RETURN c.id AS claim, f.id AS feature, o.id AS observation ORDER BY claim, feature, observation LIMIT 5"


def write_gzip(path, value):
    with open(path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as stream:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def read_export(path):
    with gzip.open(path, "rt") as f: return json.load(f)


def export(prefix="minimum_v1/", directory="artifacts/analysis/semantic_analysis_v1/exports", uri="bolt://127.0.0.1:7687"):
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    queries = {"nodes": NODE_QUERY, "edges": EDGE_QUERY, "counts": COUNT_QUERY, "paths": PATH_QUERY}
    scopes = defaultdict(lambda: {"nodes": [], "edges": []})
    with GraphDatabase.driver(uri, auth=None) as driver:
        with driver.session() as session:
            counts = {r["scope"]: dict(r) for r in session.run(COUNT_QUERY, prefix=prefix)}
            for record in session.run(NODE_QUERY, prefix=prefix):
                node = dict(record); node["semantic_type"] = kind(node); node["construction_origin"] = node_origin(node)
                scopes[node["properties"]["scope"]]["nodes"].append(node)
            for record in session.run(EDGE_QUERY, prefix=prefix):
                edge = dict(record); scope = edge.pop("scope"); scopes[scope]["edges"].append(edge)
            for scope, graph in scopes.items():
                graph["representative_stored_paths"] = [dict(r) for r in session.run(PATH_QUERY, scope=scope)]
    manifest = {"exported_at": utc_now(), "instance": "actual retained Neo4j Community instance", "prefix": prefix,
        "queries": queries, "layout_seed": 20260929, "scopes": []}
    for scope, graph in sorted(scopes.items()):
        nodes = {n["id"]: n for n in graph["nodes"]}
        for e in graph["edges"]:
            e["construction_origin"] = edge_origin(e, nodes)
            e["directly_stored"] = True
        errors = validate_export(graph)
        assert not errors, (scope, errors[:10])
        assert (len(graph["nodes"]),len(graph["edges"])) == (counts[scope]["nodes"],counts[scope]["edges"])
        record_ids = {n["properties"].get("id"): n["id"] for n in graph["nodes"] if n["semantic_type"] != "assessment"}
        triples = {(e["source"],e["type"],e["target"]) for e in graph["edges"]}
        for path in graph["representative_stored_paths"]:
            assert (record_ids[path["claim"]], "DEPENDS_ON", record_ids[path["feature"]]) in triples
            assert (record_ids[path["feature"]], "DERIVED_FROM", record_ids[path["observation"]]) in triples
        graph.update(scope=scope, instance=manifest["instance"], knowledge_time="all retained history")
        filename = scope.replace("/", "__")+".json.gz"; write_gzip(out/filename, graph)
        manifest["scopes"].append({"scope": scope, "file": filename, "sha256": digest_file(out/filename),
            "nodes": len(nodes), "edges": len(graph["edges"]), "node_types": dict(Counter(n["semantic_type"] for n in graph["nodes"])),
            "edge_types": dict(Counter(e["type"] for e in graph["edges"])), "typed_errors": len(errors),
            "verified_paths": len(graph["representative_stored_paths"])})
    manifest["total_nodes"] = sum(r["nodes"] for r in manifest["scopes"])
    manifest["total_edges"] = sum(r["edges"] for r in manifest["scopes"])
    write_json(out/"manifest.json", manifest)
    (out/"queries.cypher").write_text("\n\n".join(f"// {k}\n{v};" for k,v in queries.items())+"\n")
    return {"scopes": len(scopes), "nodes": manifest["total_nodes"], "edges": manifest["total_edges"]}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--prefix", default="minimum_v1/"); parser.add_argument("--directory", default="artifacts/analysis/semantic_analysis_v1/exports")
    args=parser.parse_args(); print(export(args.prefix,args.directory))
