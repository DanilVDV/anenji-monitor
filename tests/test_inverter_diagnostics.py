"""Unit tests for inverter diagnostics, without hardware or pyserial dependency."""
import ast
import pathlib
import time
import unittest
from collections import deque

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "anenji_web.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
NAMES = {"INVERTER_FAULTS", "INVERTER_WARNINGS"}
FUNCTIONS = {"_mask_items", "decode_inverter_diagnostics", "_inverter_event", "update_inverter_mode", "update_inverter_diagnostics"}
nodes = []
for node in TREE.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in node.targets):
        nodes.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS:
        nodes.append(node)
scope = {"time": time, "deque": deque, "MODE": {2: "Mains", 3: "Off-Grid", 4: "Bypass"}}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
scope["INVERTER_EVENTS"] = deque(maxlen=100)
scope["INVERTER_EVENT_STATE"] = {"mode": None, "masks": None, "since": {}}


class DiagnosticTests(unittest.TestCase):
    def test_high_and_low_words_and_named_bits(self):
        # Fault bits 0 and 26; warning bits 8 and 20; unmasked bit 14.
        regs = [1 << (26-16), 1, 0, 0, 0, 1 << 14, 0, 0, 1 << (20-16), 1 << 8]
        out = scope["decode_inverter_diagnostics"](regs)
        self.assertEqual(out["fault_raw"], (1 << 26) | 1)
        self.assertEqual([x["bit"] for x in out["faults"]], [0, 26])
        self.assertEqual(out["faults"][1]["name"], "Parallel versions incompatible")
        self.assertEqual([x["bit"] for x in out["warnings"]], [8, 20])
        self.assertEqual(out["warnings"][0]["name"], "Battery low voltage")
        self.assertEqual([x["bit"] for x in out["warnings_unmasked"]], [14])

    def test_unknown_bits_are_preserved(self):
        out = scope["decode_inverter_diagnostics"]([1 << 15, 0, 0, 0, 0, 0, 0, 0, 1 << 15, 0])
        self.assertEqual(out["faults"], [{"bit": 31, "name": "Unknown bit 31"}])
        self.assertEqual(out["warnings"], [{"bit": 31, "name": "Unknown bit 31"}])

    def test_empty_masks_and_invalid_block(self):
        out = scope["decode_inverter_diagnostics"]([0]*10)
        self.assertTrue(out["available"])
        self.assertEqual(out["faults"], [])
        self.assertEqual(out["warnings"], [])
        with self.assertRaises(ValueError):
            scope["decode_inverter_diagnostics"]([0]*9)

    def setUp(self):
        scope["INVERTER_EVENTS"].clear()
        scope["INVERTER_EVENT_STATE"] = {"mode": None, "masks": None, "since": {}}

    def test_power_mode_transitions_logged_after_baseline(self):
        update = scope["update_inverter_mode"]
        update(2, 1000.0)
        self.assertEqual(len(scope["INVERTER_EVENTS"]), 0)
        update(3, 1010.0)
        self.assertEqual(scope["INVERTER_EVENTS"][0]["message"], "Переход на питание от батарей (Off-Grid)")
        self.assertEqual(scope["INVERTER_EVENTS"][0]["timestamp"], 1010.0)
        update(3, 1020.0)
        self.assertEqual(len(scope["INVERTER_EVENTS"]), 2)
        update(2, 1030.0)
        self.assertEqual(scope["INVERTER_EVENTS"][0]["message"], "Выход из автономного режима (Off-Grid)")

    def test_warning_first_seen_and_clear(self):
        decode = scope["decode_inverter_diagnostics"]
        update = scope["update_inverter_diagnostics"]
        first = update(decode([0,0,0,0,0,0,0,0,0,1]), 2000.0)
        self.assertTrue(first["warnings"][0]["first_observed"])
        self.assertEqual(first["warnings"][0]["since"], 2000.0)
        next_read = update(decode([0,0,0,0,0,0,0,0,0,1]), 2010.0)
        self.assertEqual(next_read["warnings"][0]["since"], 2000.0)
        cleared = update(decode([0]*10), 2020.0)
        self.assertEqual(cleared["warnings"], [])
        self.assertFalse(cleared["events"][0]["active"])
        self.assertEqual(cleared["events"][0]["timestamp"], 2020.0)
        self.assertFalse(cleared["events"][0]["observed"])


if __name__ == "__main__":
    unittest.main()
