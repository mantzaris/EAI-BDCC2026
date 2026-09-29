"""Read-only database and disk accounting after the experiments."""
from pathlib import Path
from collections import defaultdict
import json
import sqlite3
from neo4j import GraphDatabase
from temporal_evidence.io import write_json, utc_now


def directory_bytes(path):
    path = Path(path)
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else None


def displayed_counts(rows):
    latest = {}
    for scope, payload in rows:
        record = json.loads(payload)
        key = (scope, record["logical_id"])
        if key not in latest or record["version"] > latest[key]["version"]:
            latest[key] = record
    claims = defaultdict(set)
    explanations = defaultdict(int)
    for (scope, _), record in latest.items():
        method = scope.rsplit("/", 1)[-1]
        claims[method].update((scope, identifier) for identifier in record["source_ids"])
        explanations[method] += 1
    return [{"method": method, "latest_explanations": explanations[method],
             "retained_claim_nodes": len(claims[method])} for method in sorted(explanations)]


def main():
    driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=None)
    queries = {
        "nodes": "MATCH (r:Record) WHERE r.scope STARTS WITH $prefix RETURN split(r.scope,'/')[-1] AS method,r.kind AS kind,count(*) AS count",
        "edges": "MATCH (r:Record)-[e]->() WHERE r.scope STARTS WITH $prefix RETURN split(r.scope,'/')[-1] AS method,type(e) AS relation,count(*) AS count",
        "chains": "MATCH (r:Record) WHERE r.scope STARTS WITH $prefix WITH r.scope AS scope,r.logical_id AS logical_id,count(*) AS versions RETURN split(scope,'/')[-1] AS method,max(versions) AS longest_chain,avg(versions) AS mean_chain",
        "support_assessments": "MATCH (a:SupportAssessment) WHERE a.scope STARTS WITH $prefix RETURN split(a.scope,'/')[-1] AS method,count(*) AS count",
    }
    graph = {}
    for name, query in queries.items():
        rows, _, _ = driver.execute_query(query, prefix="minimum_v1/")
        graph[name] = [dict(row) for row in rows]
    rows, _, _ = driver.execute_query("MATCH (r:Record) WHERE r.scope STARTS WITH $prefix AND r.kind='explanation' RETURN r.scope AS scope,r.payload AS payload", prefix="minimum_v1/")
    graph["active_displays"] = displayed_counts((row["scope"], row["payload"]) for row in rows)
    driver.close()
    path = Path(".local/minimum_v1.sqlite")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    relational = {"nodes": connection.execute("SELECT scope,kind,count(*) FROM records GROUP BY scope,kind").fetchall(),
                  "edges": connection.execute("SELECT scope,relation,count(*) FROM dependencies GROUP BY scope,relation").fetchall(),
                  "chains": connection.execute("SELECT scope,max(n),avg(n) FROM (SELECT scope,logical_id,count(*) n FROM records GROUP BY scope,logical_id) GROUP BY scope").fetchall(),
                  "support_assessments": connection.execute("SELECT scope,count(*) FROM assessments GROUP BY scope").fetchall(),
                  "active_displays": displayed_counts(connection.execute("SELECT scope,payload FROM records WHERE kind='explanation'"))}
    connection.close()
    write_json("artifacts/manifests/database_accounting.json", {
        "collected_at": utc_now(), "neo4j_matched_run": graph, "sqlite_matched_run": relational,
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_database_bytes": sum(p.stat().st_size for p in path.parent.glob(path.name+"*")),
        "neo4j_database_directory_bytes": directory_bytes(".runtime/neo4j-community-5.26.0/data/databases/neo4j"),
        "neo4j_transaction_directory_bytes": directory_bytes(".runtime/neo4j-community-5.26.0/data/transactions/neo4j"),
        "scope_note": "Logical counts filter minimum_v1. Neo4j physical disk includes development and systems scopes; SQLite file includes B0/B1/B3 of minimum_v1. Physical sizes are not an equal-content engine comparison.",
        "active_display_definition": "Unique claim nodes retained in the latest immutable version of each generated explanation, at each scenario's final checkpoint. Includes B0's unverified statements; this is a display count, not an independent validity score."})


if __name__ == "__main__":
    main()
