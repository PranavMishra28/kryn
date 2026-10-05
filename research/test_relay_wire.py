"""Offline inference-wire receipts; no model or Docker process is started."""

import copy
import http.client
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import learning


class RelayWireTests(unittest.TestCase):
    def test_full_controls_are_stable_sensitive_and_content_free(self):
        forwarded = []
        client_class = http.client.HTTPConnection

        class Response:
            status = 200

            def __init__(self):
                self.done = False

            def getheader(self, *_):
                return "application/json"

            def read1(self, *_):
                if self.done:
                    return b""
                self.done = True
                return b"{}"

        class Upstream:
            def __init__(self, *_args, **_kwargs):
                self.sock = self

            def connect(self):
                pass

            def settimeout(self, *_):
                pass

            def request(self, _method, _path, body, _headers):
                forwarded.append(body)

            def getresponse(self):
                return Response()

            def close(self):
                pass

        base = {
            "model": "test-model", "max_tokens": 100, "max_completion_tokens": 120,
            "thinking_budget": 32, "temperature": .4, "stream": True,
            "tool_choice": {"type": "function", "function": {"name": "SECRET-TOOL"}},
            "parallel_tool_calls": False, "response_format": {"schema": "SECRET-SCHEMA"},
            "stop": ["SECRET-STOP"], "n": 1, "seed": 7,
            "messages": [{"role": "user", "content": "SECRET-PROMPT"}], "tools": [{"name": "shell"}],
        }
        reordered = dict(reversed(list(base.items())))
        different_content = dict(base, messages=[{"role": "user", "content": "different"}],
                                 tools=[{"name": "read"}])
        changed_budget = dict(base, thinking_budget=33)
        future_control = dict(base, future_parameter={"opaque": "SECRET-FUTURE"})
        payloads = [base, reordered, different_content, changed_budget, future_control]

        with patch.object(learning.http.client, "HTTPConnection", Upstream):
            with learning.InferenceRelay("test-model", max_tokens=128) as relay:
                for value in payloads:
                    client = client_class("127.0.0.1", relay.port, timeout=2)
                    try:
                        client.request("POST", "/v1/chat/completions", json.dumps(value))
                        self.assertEqual(client.getresponse().read(), b"{}")
                    finally:
                        client.close()
                records = copy.deepcopy(relay.records)

        self.assertEqual(forwarded, [json.dumps(value).encode() for value in payloads])
        self.assertEqual(len(records), 5)
        for value, record in zip(payloads, records):
            self.assertEqual({key: record[key] for key in
                              ("body_control_keys", "body_controls_sha256", "sampler")},
                             learning.inference_controls(value))
        expected_controls = {key: value for key, value in base.items() if key not in {"messages", "tools"}}
        self.assertEqual(records[0]["body_controls_sha256"], learning.digest(expected_controls))
        self.assertEqual(records[0]["body_control_keys"], sorted(expected_controls))
        self.assertEqual(records[0]["body_controls_sha256"], records[1]["body_controls_sha256"])
        self.assertEqual(records[0]["body_controls_sha256"], records[2]["body_controls_sha256"])
        self.assertNotEqual(records[0]["tool_schema_sha256"], records[2]["tool_schema_sha256"])
        self.assertNotEqual(records[0]["body_controls_sha256"], records[3]["body_controls_sha256"])
        self.assertNotEqual(records[0]["body_controls_sha256"], records[4]["body_controls_sha256"])
        self.assertIn("future_parameter", records[4]["body_control_keys"])
        self.assertEqual(records[0]["sampler"]["thinking_budget"], 32)
        self.assertEqual(records[3]["sampler"]["thinking_budget"], 33)
        for key in ("max_completion_tokens", "stream", "parallel_tool_calls", "n", "seed"):
            self.assertEqual(records[0]["sampler"][key], base[key])
        for key in ("tool_choice", "response_format", "stop"):
            self.assertEqual(records[0]["sampler"][key], {"sha256": learning.digest(base[key])})
        self.assertEqual(records[0]["tool_schema_sha256"], learning.digest(base["tools"]))
        self.assertEqual(records[0]["numeric"], {"max_tokens": 100, "temperature": .4})
        self.assertNotIn("SECRET-", json.dumps(records))

    def test_expected_tool_wire_rejects_drift_before_upstream_connect(self):
        client_class = http.client.HTTPConnection
        connections = []

        class Upstream:
            def __init__(self, *_args, **_kwargs):
                connections.append(self)
                self.sock = self

            def connect(self):
                pass

            def settimeout(self, *_):
                pass

            def request(self, *_):
                pass

            def getresponse(self):
                class Response:
                    status = 200

                    def getheader(self, *_):
                        return "application/json"

                    def read1(self, *_):
                        return b""

                return Response()

            def close(self):
                pass

        base = {"model": "test-model", "max_tokens": 50, "thinking_budget": 16,
                "messages": [], "tools": [{"name": "shell"}]}
        expected = {"body_controls_sha256": learning.inference_controls(base)["body_controls_sha256"],
                    "tool_schema_sha256": learning.digest(base["tools"])}

        def send(port, value):
            client = client_class("127.0.0.1", port, timeout=2)
            try:
                client.request("POST", "/v1/chat/completions", json.dumps(value))
                response = client.getresponse()
                response.read()
                return response.status
            finally:
                client.close()

        with patch.object(learning.http.client, "HTTPConnection", Upstream):
            with learning.InferenceRelay("test-model", max_tokens=64, expected_wire=expected) as relay:
                self.assertEqual(send(relay.port, dict(base, tools=[])), 200)
                self.assertEqual(send(relay.port, base), 200)
                self.assertEqual(len(connections), 2)
                self.assertIsNone(relay.wire_rejection)

            for changed in (dict(base, thinking_budget=17),
                            dict(base, future_parameter={"opaque": "SECRET-FUTURE"})):
                with self.subTest(changed=sorted(changed)):
                    before = len(connections)
                    with learning.InferenceRelay("test-model", max_tokens=64, expected_wire=expected) as relay:
                        self.assertEqual(send(relay.port, changed), 403)
                        self.assertEqual(len(connections), before)
                        self.assertTrue(relay.cancelled.is_set())
                        self.assertEqual(relay.wire_rejection["expected"], expected)
                        self.assertEqual(relay.wire_rejection["observed"], {
                            "body_controls_sha256": relay.records[-1]["body_controls_sha256"],
                            "tool_schema_sha256": relay.records[-1]["tool_schema_sha256"]})
                        self.assertNotEqual(relay.wire_rejection["observed"], expected)
                        self.assertNotIn("SECRET-", json.dumps(relay.records))

            child = dict(base, tools=[{"name": "read"}])
            allowlist = {"body_controls_sha256": expected["body_controls_sha256"],
                         "tool_schema_sha256s": [expected["tool_schema_sha256"],
                                                 learning.digest(child["tools"])]}
            with learning.InferenceRelay("test-model", max_tokens=64, expected_wire=allowlist) as relay:
                self.assertEqual(send(relay.port, base), 200)
                self.assertEqual(send(relay.port, child), 200)
                self.assertIsNone(relay.wire_rejection)
            for changed in (dict(base, tools=[{"name": "unknown"}]),
                            dict(child, thinking_budget=17)):
                with self.subTest(allowlist_changed=changed):
                    before = len(connections)
                    with learning.InferenceRelay("test-model", max_tokens=64, expected_wire=allowlist) as relay:
                        self.assertEqual(send(relay.port, changed), 403)
                        self.assertEqual(len(connections), before)
                        self.assertTrue(relay.cancelled.is_set())
                        self.assertEqual(relay.wire_rejection["expected"], allowlist)
            with self.assertRaisesRegex(ValueError, "allowlist"):
                learning.InferenceRelay("test-model", expected_wire={
                    "body_controls_sha256": expected["body_controls_sha256"], "tool_schema_sha256s": []})
            with self.assertRaisesRegex(ValueError, "allowlist"):
                learning.InferenceRelay("test-model", expected_wire={
                    **allowlist, "tool_schema_sha256": expected["tool_schema_sha256"]})

    def test_tool_free_sampling_limits_reject_before_upstream_connect(self):
        connections = []

        class Upstream:
            def __init__(self, *_args, **_kwargs):
                connections.append(self)

        base = {"model": "test-model", "messages": [], "tools": []}
        invalid = (
            {"max_tokens": 0}, {"max_tokens": 65}, {"max_tokens": True},
            {"max_completion_tokens": 0}, {"max_completion_tokens": 65},
            {"max_completion_tokens": True},
            {"max_tokens": 50, "max_completion_tokens": 65},
            {"max_tokens": 65, "max_completion_tokens": 50},
            {"n": 0}, {"n": 2}, {"n": True}, {"n": 1.0},
        )
        client_class = http.client.HTTPConnection
        with patch.object(learning.http.client, "HTTPConnection", Upstream):
            for controls in invalid:
                with self.subTest(controls=controls), learning.InferenceRelay("test-model", max_tokens=64) as relay:
                    value = {**base, **controls}
                    client = client_class("127.0.0.1", relay.port, timeout=2)
                    try:
                        client.request("POST", "/v1/chat/completions", json.dumps(value))
                        response = client.getresponse()
                        response.read()
                        self.assertEqual(response.status, 403)
                    finally:
                        client.close()
                    self.assertTrue(relay.cancelled.is_set())
                    self.assertEqual(relay.records, [])
                    self.assertEqual(relay.request_rejection, {key: learning.inference_controls(value)[key]
                        for key in ("body_control_keys", "body_controls_sha256")})
        self.assertEqual(connections, [])

    def test_missing_token_cap_is_added_to_forwarded_body_and_receipt(self):
        client_class = http.client.HTTPConnection
        upstream = Mock()
        upstream.getresponse.return_value.status = 200
        upstream.getresponse.return_value.getheader.return_value = "application/json"
        upstream.getresponse.return_value.read1.return_value = b""
        original = {"model": "test-model", "messages": [], "tools": [], "n": 1}
        with patch.object(learning.http.client, "HTTPConnection", return_value=upstream):
            with learning.InferenceRelay("test-model", max_tokens=64) as relay:
                client = client_class("127.0.0.1", relay.port, timeout=2)
                try:
                    client.request("POST", "/v1/chat/completions", json.dumps(original))
                    response = client.getresponse()
                    response.read()
                    self.assertEqual(response.status, 200)
                finally:
                    client.close()
                actual = json.loads(upstream.request.call_args.args[2])
                self.assertEqual(actual, {**original, "max_tokens": 64})
                self.assertEqual(relay.records[0]["max_tokens"], 64)
                self.assertEqual(relay.records[0]["body_controls_sha256"],
                                 learning.inference_controls(actual)["body_controls_sha256"])


if __name__ == "__main__":
    unittest.main()
