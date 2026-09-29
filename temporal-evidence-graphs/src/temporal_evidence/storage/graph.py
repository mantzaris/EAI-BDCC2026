"""Neo4j Community property graph. DEPENDS_ON points dependent -> required."""
from __future__ import annotations

import json
from neo4j import GraphDatabase

from temporal_evidence.io import canonical
from temporal_evidence.schema import Record, dependency_order, with_entities, record_relations

LABELS = {"subject": "Subject", "sensor": "Sensor", "observation": "Observation",
          "feature": "FeatureVersion", "claim": "ClaimVersion", "explanation": "ExplanationVersion", "review": "ReviewEvent"}


class GraphStore:
    def __init__(self, uri="bolt://127.0.0.1:7687", scope="default", driver=None):
        self.scope = scope
        self.owns_driver = driver is None
        self.driver = driver or GraphDatabase.driver(uri, auth=None)
        self.driver.verify_connectivity()
        for statement in [
            "CREATE CONSTRAINT record_identity IF NOT EXISTS FOR (r:Record) REQUIRE (r.scope,r.id) IS UNIQUE",
            "CREATE INDEX record_temporal IF NOT EXISTS FOR (r:Record) ON (r.scope,r.dataset,r.subject,r.session,r.start,r.end,r.ingested)",
            "CREATE INDEX record_versions IF NOT EXISTS FOR (r:Record) ON (r.scope,r.logical_id,r.version,r.ingested)",
            "CREATE INDEX record_ingestion IF NOT EXISTS FOR (r:Record) ON (r.scope,r.ingested)",
        ]:
            self.driver.execute_query(statement)
        self._records = self.snapshot(float("inf"))

    def get(self, identifier):
        rows, _, _ = self.driver.execute_query("MATCH (r:Record {scope:$scope,id:$id}) RETURN r.payload AS payload",
                                              scope=self.scope, id=identifier)
        return None if not rows or rows[0]["payload"] is None else Record.from_dict(json.loads(rows[0]["payload"]))

    def put(self, record):
        self.put_many([record])

    def put_many(self, records):
        records = with_entities(list(records))
        existing = self._records.copy()
        for record in records:
            if record.record_id in existing and existing[record.record_id] != record:
                raise ValueError("Immutable record conflicts with existing value")
            existing[record.record_id] = record
        dependency_order(existing, set(existing))
        with self.driver.session() as session:
            def operation(tx):
                groups = {}
                relations = {}
                for record in records:
                    props = dict(scope=self.scope, id=record.record_id, logical_id=record.logical_id,
                                 kind=record.record_type, dataset=record.dataset_id, subject=record.subject_id,
                                 session=record.session_id, start=record.event_start_seconds, end=record.event_end_seconds,
                                 ingested=record.ingested_at_seconds, version=record.version, payload=canonical(record.to_dict()))
                    groups.setdefault(LABELS[record.record_type], []).append(props)
                    for dependent, source, relation in record_relations(record):
                        relations.setdefault(relation,[]).append({"id":dependent,"source":source})
                for label, rows in groups.items():
                    tx.run(f"UNWIND $rows AS props MERGE (r:Record {{scope:props.scope,id:props.id}}) SET r:{label} SET r += props",
                           rows=rows).consume()
                for relation, rows in relations.items():
                    if rows:
                        tx.run(f"""UNWIND $rows AS row MATCH (r:Record {{scope:$scope,id:row.id}})
                            MERGE (s:Record {{scope:$scope,id:row.source}}) MERGE (r)-[:{relation}]->(s)""",
                            scope=self.scope,rows=rows).consume()
            session.execute_write(operation)
        self._records = existing

    def snapshot(self, knowledge_time):
        rows, _, _ = self.driver.execute_query("MATCH (r:Record {scope:$scope}) WHERE r.ingested <= $time RETURN r.id AS id,r.payload AS payload",
                                              scope=self.scope, time=knowledge_time)
        return {row["id"]: Record.from_dict(json.loads(row["payload"])) for row in rows}

    def dependents(self, identifier, knowledge_time, transitive=True):
        return self.dependents_many([identifier],knowledge_time,transitive)

    def dependents_many(self, identifiers, knowledge_time, transitive=True):
        reach = "*1.." if transitive else ""
        rows, _, _ = self.driver.execute_query(f"""UNWIND $ids AS root_id
            MATCH p=(r:Record {{scope:$scope}})-[:DEPENDS_ON{reach}]->(s:Record {{scope:$scope,id:root_id}})
            WHERE all(n IN nodes(p) WHERE n.ingested <= $time)
            RETURN DISTINCT r.id AS id""", scope=self.scope, ids=list(identifiers), time=knowledge_time)
        return {row["id"] for row in rows}

    def assess(self, identifier, known_at, state, value, trigger):
        self.assess_many({identifier:{"state":state,"value":value}},known_at,trigger)

    def assess_many(self,assessments,known_at,trigger):
        rows=[{"id":identifier,**value} for identifier,value in assessments.items()]
        if not rows:
            return
        self.driver.execute_query("""UNWIND $rows AS row MATCH (r:Record {scope:$scope,id:row.id})
            MERGE (a:SupportAssessment {scope:$scope,id:row.id,known_at:$known_at,trigger_id:$trigger})
            ON CREATE SET a.state=row.state,a.value=row.value MERGE (r)-[:ASSESSED_AS]->(a)
            WITH row,r WHERE row.state='contradicted' MATCH (t:Record {scope:$scope,id:$trigger})
            MERGE (t)-[:CONTRADICTS]->(r)""",scope=self.scope,rows=rows,known_at=known_at,trigger=trigger)

    def close(self):
        if self.owns_driver:
            self.driver.close()
