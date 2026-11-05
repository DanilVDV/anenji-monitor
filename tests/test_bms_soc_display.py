import ast
import pathlib
import unittest

p=pathlib.Path(__file__).resolve().parents[1]/'anenji_web.py'
t=ast.parse(p.read_text())
f=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name=='select_battery_soc')
g={'BMS_ENABLE':True,'BMS_STALE_AFTER_SEC':180,'BMS_EXPECTED_PACKS':4}
exec(compile(ast.Module(body=[f],type_ignores=[]),str(p),'exec'),g)

def packs():
    return [dict(_online=True,_stale=False,_last_success=995,pack={'soc_pct':n}) for n in (26,27,26,27)]

class SocTests(unittest.TestCase):
    def test_four_fresh_packs(self):
        x=g['select_battery_soc'](58,packs(),995,1000)
        self.assertEqual(x['battery_soc_pct'],26.5)
        self.assertEqual(x['inverter_battery_soc_pct'],58)
        self.assertEqual(x['battery_soc_source'],'bms')

    def test_missing_or_stale_fallback(self):
        f=g['select_battery_soc']
        self.assertEqual(f(58,packs()[:3],995,1000)['battery_soc_pct'],58)
        self.assertEqual(f(58,packs(),800,1000)['battery_soc_source'],'inverter')
        d=packs();d[0]['_stale']=True
        self.assertEqual(f(58,d,995,1000)['battery_soc_pct'],58)

if __name__=='__main__': unittest.main()
