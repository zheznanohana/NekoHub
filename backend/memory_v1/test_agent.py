import hashlib
import json
import unittest
from copy import deepcopy

from backend.memory_v1.agent import AgentError, ChatCompletions, MemoryAgent, POLICY_VERSION
from backend.memory_v1.examples import CHANGESET, INGEST


def proposal():
    value = deepcopy(CHANGESET)
    value.update(request_id="job-1", idempotency_key=hashlib.sha256(b"job-1").hexdigest(), extractor_version=POLICY_VERSION)
    return value


class AgentTests(unittest.TestCase):
    def call(self, complete, **kwargs):
        return MemoryAgent(complete).propose(job_id="job-1", mode="ingest", events=[{"event_id": "event-demo", "ingest": INGEST}], **kwargs)

    def test_valid_proposal(self):
        expected = proposal()
        self.assertEqual(self.call(lambda _: json.dumps(expected)), expected)

    def test_one_repair(self):
        responses = iter(["not json", json.dumps(proposal())])
        self.assertEqual(self.call(lambda _: next(responses))["kind"], "memory.changeset")

    def test_bounded_failure(self):
        calls = []
        def invalid(messages):
            calls.append(messages)
            return "{}"
        with self.assertRaises(AgentError):
            self.call(invalid)
        self.assertEqual(len(calls), 2)

    def test_skip(self):
        result = {"schema_version": "1.0", "kind": "memory.skip", "request_id": "job-1", "reason": "重复通知"}
        self.assertEqual(self.call(lambda _: json.dumps(result)), result)

    def test_stale_target(self):
        result = proposal()
        result["operations"][0].update(op="supersede", target_id="old-fact", expected_version=1, reason="新计划")
        with self.assertRaises(AgentError):
            self.call(lambda _: json.dumps(result), known_facts=[{"id": "old-fact", "version": 2}])

    def test_evidence_hallucination(self):
        result = proposal()
        result["operations"][0]["fact"]["evidence"][0]["event_id"] = "another-user-event"
        with self.assertRaises(AgentError):
            self.call(lambda _: json.dumps(result))

    def test_remote_plaintext_rejected(self):
        with self.assertRaises(ValueError):
            ChatCompletions("http://example.com/v1", "key", "model")

    def test_loopback_allowed(self):
        client = ChatCompletions("http://127.0.0.1:8080/v1", "", "local-model")
        self.assertTrue(client.url.endswith("/v1/chat/completions"))


if __name__ == "__main__":
    unittest.main()
