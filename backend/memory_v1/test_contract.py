import json
import sqlite3
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import ValidationError, Draft202012Validator
from backend.memory_v1.build_schema import SCHEMA
from backend.memory_v1.examples import CHANGESET, INGEST, QUERY, RESULT, TEXT
from backend.memory_v1.validate import validate


class ContractTests(unittest.TestCase):
    def run_validation(self, doc):
        validate(doc, evidence_texts={"event-demo": TEXT})

    def test_schema_and_fixtures(self):
        Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(SCHEMA, json.loads(Path(__file__).with_name("contract.schema.json").read_text(encoding="utf-8")))
        for doc in (INGEST, CHANGESET, QUERY, RESULT):
            self.run_validation(doc)

    def test_unknown_field_and_owner_spoof(self):
        for key in ("sql", "owner_id"):
            doc = deepcopy(INGEST)
            doc[key] = "untrusted"
            with self.assertRaises(ValidationError):
                self.run_validation(doc)

    def test_evidence_quote(self):
        doc = deepcopy(CHANGESET)
        doc["operations"][0]["fact"]["evidence"][0]["quote"] = "任务已经完成"
        with self.assertRaisesRegex(ValueError, "quote mismatch"):
            self.run_validation(doc)

    def test_missing_evidence(self):
        with self.assertRaisesRegex(ValueError, "trusted evidence"):
            validate(CHANGESET)

    def test_dangling_edge(self):
        doc = deepcopy(CHANGESET)
        doc["operations"][0]["fact"]["object"]["node_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "dangling object"):
            self.run_validation(doc)

    def test_no_extractor_auto_approval(self):
        doc = deepcopy(CHANGESET)
        doc["operations"][0]["fact"]["status"] = "active"
        with self.assertRaisesRegex(ValueError, "candidates"):
            self.run_validation(doc)

    def test_timezone_and_reversed_range(self):
        doc = deepcopy(INGEST)
        doc["timezone"] = "Not/AZone"
        with self.assertRaises(ValueError):
            self.run_validation(doc)
        doc = deepcopy(QUERY)
        doc["filters"].update({"from": "2026-09-13T00:00:00Z", "to": "2026-09-12T00:00:00Z"})
        with self.assertRaises(ValueError):
            self.run_validation(doc)

    def test_citation_integrity(self):
        doc = deepcopy(RESULT)
        doc["answer"]["claims"][0]["fact_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "missing fact"):
            self.run_validation(doc)

    def test_unconfirmed_citation(self):
        doc = deepcopy(RESULT)
        doc["graph"]["facts"][0]["status"] = "candidate"
        with self.assertRaisesRegex(ValueError, "unconfirmed"):
            self.run_validation(doc)

    def test_insufficient_answer(self):
        doc = deepcopy(RESULT)
        doc["answer"] = {"status": "insufficient_evidence", "claims": [], "unknowns": ["缺少完成记录"]}
        self.run_validation(doc)

    def test_invalid_literal(self):
        doc = deepcopy(CHANGESET)
        doc["operations"][0]["fact"]["object"] = {"value": "NaN", "datatype": "decimal", "unit": None}
        with self.assertRaises(ValueError):
            self.run_validation(doc)

    def test_fresh_node_id(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            validate(CHANGESET, evidence_texts={"event-demo": TEXT}, existing_node_ids=["task-demo"])

    def test_schema_idempotent_and_cross_owner_fk(self):
        con = sqlite3.connect(":memory:")
        ddl = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        con.executescript(ddl)
        con.executescript(ddl)
        con.execute("INSERT INTO memory_nodes(owner_id,id,kind,label) VALUES ('a','n1','task','Test')")
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("""INSERT INTO memory_facts(owner_id,id,subject_id,predicate,object_value,datatype,status,epistemic,confidence,recorded_at)
                VALUES ('b','f1','n1','has_status','planned','text','candidate','reported',0.8,'2026-09-12T00:00:00Z')""")
        con.close()


if __name__ == "__main__":
    unittest.main()
