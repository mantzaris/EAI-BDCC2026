"""SQLite relational control with indexed recursive dependency traversal."""
from __future__ import annotations

import json
import sqlite3

from temporal_evidence.io import canonical
from temporal_evidence.schema import Record, dependency_order, with_entities, record_relations


class RelationalStore:
    def __init__(self, path=":memory:", scope="default"):
        self.scope = scope
        self.connection = sqlite3.connect(path)
        self.connection.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS records(
          scope TEXT, id TEXT, logical_id TEXT, kind TEXT, dataset TEXT, subject TEXT,
          session TEXT, start REAL, end REAL, ingested REAL, version INTEGER, payload TEXT,
          PRIMARY KEY(scope,id));
        CREATE INDEX IF NOT EXISTS temporal_lookup ON records(scope,dataset,subject,session,start,end,ingested);
        CREATE INDEX IF NOT EXISTS version_lookup ON records(scope,logical_id,version,ingested);
        CREATE INDEX IF NOT EXISTS ingestion_lookup ON records(scope,ingested);
        CREATE TABLE IF NOT EXISTS dependencies(scope TEXT, dependent TEXT, required TEXT,
          relation TEXT, PRIMARY KEY(scope,dependent,required,relation));
        CREATE INDEX IF NOT EXISTS reverse_dependencies ON dependencies(scope,required,relation,dependent);
        CREATE TABLE IF NOT EXISTS assessments(scope TEXT,id TEXT,known_at REAL,state TEXT,value REAL,
          trigger_id TEXT,PRIMARY KEY(scope,id,known_at,trigger_id));
        """)
        self._records = self.snapshot(float("inf"))

    def get(self, identifier):
        row = self.connection.execute("SELECT payload FROM records WHERE scope=? AND id=?", (self.scope, identifier)).fetchone()
        return None if row is None else Record.from_dict(json.loads(row[0]))

    def put(self, record: Record):
        self.put_many([record])

    def put_many(self, records):
        records = with_entities(list(records))
        # Cycle validation covers all proposed dependencies, including later arrivals.
        existing = self._records.copy()
        for record in records:
            if record.record_id in existing and existing[record.record_id] != record:
                raise ValueError("Immutable record conflicts with existing value")
            existing[record.record_id] = record
        dependency_order(existing, set(existing))
        with self.connection:
            for record in records:
                self.connection.execute("INSERT OR IGNORE INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
                    self.scope, record.record_id, record.logical_id, record.record_type,
                    record.dataset_id, record.subject_id, record.session_id, record.event_start_seconds,
                    record.event_end_seconds, record.ingested_at_seconds, record.version, canonical(record.to_dict())))
                for dependent, source, relation in record_relations(record):
                    self.connection.execute("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?)",
                                            (self.scope, dependent, source, relation))
        self._records = existing

    def snapshot(self, knowledge_time):
        rows = self.connection.execute("SELECT id,payload FROM records WHERE scope=? AND ingested<=?", (self.scope, knowledge_time))
        return {identifier: Record.from_dict(json.loads(payload)) for identifier, payload in rows}

    def dependents(self, identifier, knowledge_time, transitive=True):
        return self.dependents_many([identifier],knowledge_time,transitive)

    def dependents_many(self, identifiers, knowledge_time, transitive=True):
        identifiers=[identifier for identifier in identifiers if identifier in self._records
                     and self._records[identifier].ingested_at_seconds<=knowledge_time]
        roots=json.dumps(identifiers)
        if not transitive:
            rows = self.connection.execute("""SELECT d.dependent FROM dependencies d JOIN records r
                ON r.scope=d.scope AND r.id=d.dependent
                WHERE d.scope=? AND d.required IN (SELECT value FROM json_each(?)) AND d.relation='DEPENDS_ON' AND r.ingested<=?""",
                (self.scope, roots, knowledge_time))
        else:
            rows = self.connection.execute("""WITH RECURSIVE affected(id) AS (
                SELECT d.dependent FROM dependencies d JOIN records r ON r.scope=d.scope AND r.id=d.dependent
                WHERE d.scope=? AND d.required IN (SELECT value FROM json_each(?)) AND d.relation='DEPENDS_ON' AND r.ingested<=?
                UNION
                SELECT d.dependent FROM dependencies d JOIN affected a ON d.required=a.id
                  JOIN records r ON r.scope=d.scope AND r.id=d.dependent
                WHERE d.scope=? AND d.relation='DEPENDS_ON' AND r.ingested<=?) SELECT id FROM affected""",
                (self.scope, roots, knowledge_time, self.scope, knowledge_time))
        return {row[0] for row in rows}

    def assess(self, identifier, known_at, state, value, trigger):
        self.assess_many({identifier:{"state":state,"value":value}},known_at,trigger)

    def assess_many(self,assessments,known_at,trigger):
        with self.connection:
            self.connection.executemany("INSERT OR IGNORE INTO assessments VALUES(?,?,?,?,?,?)",
                [(self.scope,identifier,known_at,item["state"],item["value"],trigger) for identifier,item in assessments.items()])
            self.connection.executemany("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?)",
                [(self.scope,trigger,identifier,"CONTRADICTS") for identifier,item in assessments.items() if item["state"]=="contradicted"])

    def close(self):
        self.connection.close()
