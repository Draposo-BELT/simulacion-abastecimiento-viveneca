from dataclasses import replace
import unittest
import numpy as np
from simulation import Parameters, planning, simulate_one, run

class EngineTests(unittest.TestCase):
    def test_flow_and_balance(self):
        p=Parameters(replicas=3); plan=planning(p)
        row,daily,orders=simulate_one(p,'B',0,plan,True)
        self.assertGreater(len(orders),0); self.assertGreater(row['Contenedores recibidos'],0)
        self.assertGreater(row['Días sin material'],0)
        self.assertTrue((daily[['Aluminio','Vidrio']]>=0).all().all())
        for material,start,q in [('Aluminio',p.initial_aluminum,p.quantity_aluminum),('Vidrio',p.initial_glass,p.quantity_glass)]:
            receipts=sum(o['material']==material and o['arrival']<=p.horizon for o in orders)
            self.assertAlmostEqual(start+receipts*q-daily['Producción'].sum(),daily[material].iloc[-1])
        self.assertEqual(row['Costo terrestre (RD$)'],16000*row['Contenedores recibidos'])
        self.assertLess(daily.Aluminio.iloc[0],p.initial_aluminum)
        self.assertEqual(orders[0]['placed'],1)
    def test_reproducible_and_comparable(self):
        p=Parameters(replicas=3)
        _,a,da=run(p); _,b,db=run(p)
        self.assertTrue(da.equals(db)); self.assertTrue(a.equals(b))
        self.assertEqual(set(a.Escenario),{'A','B','C'})
        self.assertEqual(da.groupby('Réplica').Demandadas.nunique().max(),1)
    def test_no_shortage_and_zero_demand(self):
        p=Parameters(initial_aluminum=10000,initial_glass=10000,replicas=1)
        self.assertEqual(simulate_one(p,'B',0,planning(p))[0]['Stockout'],0)
        p=replace(p,demand=0,demand_sd=0)
        self.assertEqual(simulate_one(p,'B',0,planning(p))[0]['Nivel de servicio (%)'],100)
    def test_invalid_and_deterministic(self):
        with self.assertRaises(ValueError): planning(Parameters(stages=((5,1,3),)*4))
        p=Parameters(stages=((1,1,1),)*4)
        self.assertEqual(planning(p)['L'],4)
        self.assertEqual(planning(p)['sigmaL'],0)
    def test_trigger_and_delay(self):
        p=Parameters(horizon=90,replicas=1,demand=1,demand_sd=0,initial_aluminum=5,initial_glass=5,stages=((1,1,1),)*4,delay=30)
        plan=planning(p)
        _,_,a=simulate_one(p,'A',0,plan,True)
        _,_,c=simulate_one(p,'C',0,plan,True)
        self.assertEqual(a[0]['placed'],1)
        self.assertEqual(c[0]['lead'],a[0]['lead']+30)

if __name__=='__main__': unittest.main()
