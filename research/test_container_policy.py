import json
import unittest

from research.container_policy import END_TITLE, parse_log, policy_during_tools


class NativePolicyTests(unittest.TestCase):
    def log(self, kinds):
        kinds = [*kinds, ("session.renamed", {"title": END_TITLE})]
        events = [{"type": kind, "data": data, "durable": {"aggregateID": "session", "seq": i}}
                  for i, (kind, data) in enumerate(kinds, 1)]
        return events, "".join("data: " + json.dumps(event) + "\n\n" for event in
            [{"type": "log.synced", "aggregateID": "session", "seq": 0},
             *events, {"type": "log.synced", "aggregateID": "session", "seq": len(events)}])

    def test_restored_changes_are_visible_but_cli_selection_is_not_tool_mutation(self):
        events, raw = self.log([
            ("session.agent.selected", {"agent": "agent"}),
            ("session.tool.input.started", {"id": "t", "name": "shell"}),
            ("session.tool.called", {"id": "t", "executed": False}),
            ("session.agent.selected", {"agent": "plan"}),
            ("session.agent.selected", {"agent": "agent"}),
            ("session.tool.success", {"id": "t"})])
        parsed = parse_log(raw, "session")
        self.assertEqual(parsed, events)
        mutations = policy_during_tools(parsed)
        self.assertEqual([m["data"]["agent"] for m in mutations], ["plan", "agent"])
        self.assertEqual(mutations[0]["tools"], {"t": "shell"})
        with self.assertRaisesRegex(ValueError, "unfinished"):
            policy_during_tools(parsed[:-2])

    def test_incomplete_duplicate_foreign_and_post_sync_logs_fail(self):
        _, raw = self.log([("session.created", {}), ("session.agent.selected", {"agent": "agent"})])
        for broken in (raw[:-1], raw[:raw.rindex('data: {"type": "log.synced"')],
                       raw.replace('"seq": 1', '"seq": 0', 1),
                       raw.replace('"aggregateID": "session"', '"aggregateID": "other"', 1),
                       raw + raw):
            with self.subTest(raw=broken), self.assertRaises(ValueError):
                parse_log(broken, "session")

    def test_private_event_gaps_are_not_mistaken_for_missing_public_events(self):
        _, raw = self.log([("session.agent.selected", {"agent": "agent"})])
        # UsageRecorded is private; the public SSE stream can skip its sequence.
        values = [json.loads(block[6:]) for block in raw.strip().split("\n\n")]
        values[1]["durable"]["seq"] = 2
        values[2]["durable"]["seq"] = 4
        values[3]["seq"] = 4
        parsed = parse_log("".join("data: " + json.dumps(v) + "\n\n" for v in values), "session")
        self.assertEqual(len(parsed), 2)


if __name__ == "__main__":
    unittest.main()
