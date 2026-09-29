"""Regression tests for the grader. Run: python -m pytest tests  (or python -m unittest discover tests)"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import toolcard as tc  # noqa: E402

AIR = {t for t, k in tc.BUILTIN["airline"].items() if k == "WRITE"}
RET = {t for t, k in tc.BUILTIN["retail"].items() if k == "WRITE"}


def call(cid, name, args):
    return {"role": "assistant", "tool_calls": [{"id": cid, "function": {"name": name, "arguments": args}}]}


def result(cid, content="ok"):
    return {"role": "tool", "tool_call_id": cid, "content": content}


def ep(actions, traj):
    return {"actions": actions, "traj": traj}


def cats(rows):
    return sorted((r["tool"], r["cat"]) for r in rows)


class TestGrade(unittest.TestCase):
    def setUp(self):
        tc.ORDERED = False

    def test_ok(self):
        rows, _ = tc.grade(ep([{"name": "cancel_reservation", "kwargs": {"reservation_id": "A1"}}],
                              [call("1", "cancel_reservation", {"reservation_id": "A1"}), result("1")]), AIR)
        self.assertEqual(cats(rows), [("cancel_reservation", "OK")])

    def test_wrong_args_names_the_argument(self):
        rows, _ = tc.grade(ep([{"name": "send_certificate", "kwargs": {"user_id": "u", "amount": 100}}],
                              [call("1", "send_certificate", {"user_id": "u", "amount": 150}), result("1")]), AIR)
        self.assertEqual(rows[0]["cat"], "WRONG_ARGS")
        self.assertEqual(rows[0]["why"], "amount")

    def test_compare_args_ignores_other_arguments(self):
        rows, _ = tc.grade(ep([{"name": "send_certificate", "kwargs": {"user_id": "u", "amount": 100},
                                "compare": ["user_id"]}],
                              [call("1", "send_certificate", {"user_id": "u", "amount": 999}), result("1")]), AIR)
        self.assertEqual(rows[0]["cat"], "OK")

    def test_missing_and_extra_arguments(self):
        rows, _ = tc.grade(ep([{"name": "send_certificate", "kwargs": {"user_id": "u", "amount": 100}}],
                              [call("1", "send_certificate", {"user_id": "u", "note": "x"}), result("1")]), AIR)
        self.assertEqual(rows[0]["cat"], "WRONG_ARGS")
        self.assertEqual(set(rows[0]["why"].split(",")), {"amount", "note"})

    def test_unwanted_and_duplicate(self):
        traj = [call("1", "cancel_reservation", {"reservation_id": "A1"}), result("1"),
                call("2", "cancel_reservation", {"reservation_id": "B2"}), result("2"),
                call("3", "cancel_reservation", {"reservation_id": "B2"}), result("3")]
        rows, _ = tc.grade(ep([{"name": "cancel_reservation", "kwargs": {"reservation_id": "A1"}}], traj), AIR)
        self.assertEqual(cats(rows), [("cancel_reservation", "DUPLICATE"), ("cancel_reservation", "OK"),
                                      ("cancel_reservation", "UNWANTED")])

    def test_rejected_write_is_not_a_failure(self):
        traj = [call("1", "cancel_reservation", {"reservation_id": "A1"}), result("1", "Error: not allowed"),
                call("2", "cancel_reservation", {"reservation_id": "A1"}), result("2")]
        rows, _ = tc.grade(ep([{"name": "cancel_reservation", "kwargs": {"reservation_id": "A1"}}], traj), AIR)
        self.assertEqual(cats(rows), [("cancel_reservation", "OK"), ("cancel_reservation", "REJECTED")])

    def test_missing_tool_call_ids(self):
        traj = [{"role": "assistant", "tool_calls": [{"function": {"name": "cancel_reservation",
                                                                    "arguments": {"reservation_id": "A1"}}}]},
                {"role": "tool", "content": "Error: nope"}]
        rows, _ = tc.grade(ep([], traj), AIR)
        self.assertEqual(cats(rows), [("cancel_reservation", "REJECTED")])

    def test_handed_off_and_missed(self):
        want = [{"name": "cancel_pending_order", "kwargs": {"order_id": "#1", "reason": "no longer needed"}}]
        rows, _ = tc.grade(ep(want, [call("1", "transfer_to_human_agents", {"summary": "x"}), result("1")]), RET)
        self.assertEqual(rows[0]["cat"], "HANDED_OFF")
        rows, _ = tc.grade(ep(want, []), RET)
        self.assertEqual(rows[0]["cat"], "MISSED")

    def test_wrong_tool_on_same_order(self):
        want = [{"name": "cancel_pending_order", "kwargs": {"order_id": "#1", "reason": "x"}}]
        traj = [call("1", "modify_pending_order_address", {"order_id": "#1", "address1": "a"}), result("1")]
        rows, _ = tc.grade(ep(want, traj), RET)
        self.assertEqual(rows[0]["cat"], "WRONG_TOOL")

    def test_list_order_is_ignored_by_default_and_checked_with_ordered(self):
        want = [{"name": "return_delivered_order_items",
                 "kwargs": {"order_id": "#1", "item_ids": ["a", "b"], "payment_method_id": "p"}}]
        traj = [call("1", "return_delivered_order_items",
                     {"order_id": "#1", "item_ids": ["b", "a"], "payment_method_id": "p"}), result("1")]
        self.assertEqual(tc.grade(ep(want, traj), RET)[0][0]["cat"], "OK")
        tc.ORDERED = True
        self.assertEqual(tc.grade(ep(want, traj), RET)[0][0]["cat"], "WRONG_ARGS")

    def test_string_arguments_and_float_ints(self):
        want = [{"name": "send_certificate", "kwargs": {"user_id": "u", "amount": 100}}]
        traj = [call("1", "send_certificate", json.dumps({"user_id": "u", "amount": 100.0})), result("1")]
        self.assertEqual(tc.grade(ep(want, traj), AIR)[0][0]["cat"], "OK")

    def test_malformed_arguments_dont_crash(self):
        traj = [call("1", "send_certificate", "{not json"), result("1")]
        rows, _ = tc.grade(ep([], traj), AIR)
        self.assertEqual(rows[0]["cat"], "UNWANTED")


class TestCoverage(unittest.TestCase):
    def test_builtin_writes(self):
        self.assertEqual(len(AIR), 6)
        self.assertEqual(len(RET), 7)

    def test_unknown_tool_fails_loudly(self):
        with self.assertRaises(tc.UnknownTools) as e:
            tc.check_coverage(tc.BUILTIN, {"airline": {"cancel_reservation", "refund_everything"}})
        self.assertIn("refund_everything", str(e.exception))
        with self.assertRaises(tc.UnknownTools):
            tc.check_coverage(tc.BUILTIN, {"telecom": {"x"}})
        tc.check_coverage(tc.BUILTIN, {"retail": {"get_order_details", "cancel_pending_order"}})

    def test_reads_tool_types_from_tau2_source(self):
        root = tempfile.mkdtemp()
        d = os.path.join(root, "src", "tau2", "domains", "shop")
        os.makedirs(d)
        with open(os.path.join(d, "tools.py"), "w") as f:
            f.write("class T:\n    @is_tool(ToolType.WRITE)\n    def refund(self): ...\n\n"
                    "    @is_tool(ToolType.READ)\n    def look(self): ...\n\n"
                    "    @is_tool(ToolType.WRITE, mutates_state=True)\n    def wipe(self): ...\n")
        self.assertEqual(tc.tool_types(root), {"shop": {"refund": "WRITE", "look": "READ", "wipe": "WRITE"}})


class TestLoad(unittest.TestCase):
    def write(self, name, body):
        p = os.path.join(tempfile.mkdtemp(), name)
        with open(p, "w") as f:
            json.dump(body, f)
        return p

    def body(self, info=None):
        return {"info": info or {}, "tasks": [{"id": "1", "evaluation_criteria": {"actions": []}}],
                "simulations": [{"task_id": "1", "trial": 0, "messages": [],
                                 "reward_info": {"reward": 1, "db_check": {"db_match": True}}}]}

    def test_model_and_domain_from_file_contents(self):
        p = self.write("weird_name_with_underscores.json",
                       self.body({"agent_info": {"llm": "my_model_v2"}, "environment_info": {"domain_name": "retail"}}))
        m, d, _ = next(tc.load(p))
        self.assertEqual((m, d), ("my_model_v2", "retail"))

    def test_old_files_fall_back_to_the_filename(self):
        m, d, e = next(tc.load(self.write("gpt-4.1_airline_default.json", self.body())))
        self.assertEqual((m, d, e["ref_ok"]), ("gpt-4.1", "airline", True))


if __name__ == "__main__":
    unittest.main()
