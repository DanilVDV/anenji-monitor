"""Regression test: the ESP8266 LED panel needs the legacy /api/rgb contract.

Runs without serial hardware, BMS, or pyserial. Executes just the HTTP handler
methods with stubbed telemetry and validates exact panel-facing JSON keys.
"""
import ast
import json
import pathlib
import time
import unittest
from urllib.parse import urlparse

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "anenji_web.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
handler = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == "H")
methods = [n for n in handler.body if isinstance(n, ast.FunctionDef) and n.name in ("do_GET", "RGB")]
assert len(methods) == 2, "LED panel route / serializer missing"
fake_class = ast.ClassDef(name="Handler", bases=[], keywords=[], body=methods, decorator_list=[])
scope = {
    "urlparse": urlparse, "json": json, "time": time,
    "RGB_CHARGE_DETECT_W": 20,
    "energy_summary": lambda: {
        "battery_power_w": -120, "battery_discharging": False,
        "eta_to_reserve_sec": None, "battery_soc_pct": 81,
        "pv_w": 400, "load_w": 350, "grid_w": -25,
        "grid_present": True, "battery_voltage_v": 52.4,
        "attention_required": False
    },
}
exec(compile(ast.Module(body=[fake_class], type_ignores=[]), str(SOURCE), "exec"), scope)


class PanelCompatibilityTests(unittest.TestCase):
    def test_compact_api_has_all_led_bridge_fields(self):
        class TestHandler(scope["Handler"]):
            path = "/api/rgb"
            def RGB(self, data, code=200):
                self.response = data
                self.code = code
        client = TestHandler()
        client.do_GET()
        self.assertEqual(client.code, 200)
        self.assertEqual(set(client.response), {"p","l","g","r","b","v","c","d","a","e","t","s"})
        self.assertEqual(client.response["r"], 1)
        self.assertEqual(client.response["c"], 81)
        self.assertEqual(client.response["s"], -1)
        self.assertEqual(client.response["e"], -1)
        self.assertEqual(client.response["t"].count(":"), 1)

    def test_api_still_uses_ascii_compact_json(self):
        class TestHandler(scope["Handler"]):
            def send_response(self, code): self.status = code
            def send_header(self, name, val): self.headers[name] = val
            def end_headers(self): pass
            headers = None
            def __init__(self):
                import io
                self.headers = {}
                self.wfile = io.BytesIO()
        client = TestHandler()
        client.RGB({"p":100,"l":200,"g":0,"r":1,"b":-25,
                    "v":52.4,"c":75,"d":1,"a":0,"e":-1,"t":"12:34","s":1})
        self.assertEqual(client.status, 200)
        self.assertEqual(client.headers["Content-Type"], "application/json")
        self.assertEqual(client.headers["Cache-Control"], "no-store")
        self.assertEqual(client.wfile.getvalue()[:5], b'{"p":')
        self.assertEqual(json.loads(client.wfile.getvalue())["r"], 1)


if __name__ == "__main__":
    unittest.main()
