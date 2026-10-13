from dataclasses import dataclass, asdict
from statistics import NormalDist
import math
import numpy as np
import pandas as pd

STAGES = ['Preparación / fabricación', 'Transporte marítimo', 'Puerto / aduana', 'Transporte terrestre']
NAMES = {'A': 'Escenario base académico – sin inventario de seguridad', 'B': 'Propuesta – planificación anticipada con SS + ROP', 'C': 'Estrés – retraso extraordinario de importación'}

@dataclass(frozen=True)
class Parameters:
    demand: float = 7.5
    demand_sd: float = 1.5
    service: float = 95.0
    initial_aluminum: float = 150.0
    initial_glass: float = 150.0
    quantity_aluminum: float = 300.0
    quantity_glass: float = 300.0
    stages: tuple = ((5.,10.,15.),(18.,23.,30.),(2.,4.,7.),(1.,1.,2.))
    delay: int = 30
    horizon: int = 180
    replicas: int = 1000
    seed: int = 20261013

    def validate(self):
        for v in (self.demand,self.demand_sd,self.initial_aluminum,self.initial_glass,self.delay):
            if not math.isfinite(v) or v < 0: raise ValueError('Los valores deben ser finitos y no negativos.')
        if min(self.quantity_aluminum,self.quantity_glass) <= 0: raise ValueError('La cantidad por orden debe ser positiva.')
        if not 50 < self.service < 100: raise ValueError('Nivel objetivo entre 50 y 100%.')
        if not 1 <= self.horizon <= 2000 or not 1 <= self.replicas <= 10000: raise ValueError('Horizonte 1–2000; réplicas 1–10000.')
        if self.seed < 0: raise ValueError('Semilla no negativa.')
        if len(self.stages) != 4: raise ValueError('Se requieren cuatro etapas.')
        for low,mode,high in self.stages:
            if not all(math.isfinite(x) for x in (low,mode,high)) or not 0 <= low <= mode <= high: raise ValueError('Cada etapa requiere 0 ≤ mínimo ≤ moda ≤ máximo.')

def sample_stages(rng,p,size=None):
    return np.stack([np.full(size if size is not None else (),a) if a == c else rng.triangular(a,b,c,size=size) for a,b,c in p.stages],axis=-1)

def planning(p):
    p.validate()
    samples = np.maximum(1,np.ceil(sample_stages(np.random.default_rng(np.random.SeedSequence([p.seed,999])),p,50000).sum(axis=1)))
    mean,sd = float(samples.mean()),float(samples.std(ddof=1))
    z = 1.65 if p.service == 95 else NormalDist().inv_cdf(p.service/100)
    ss = z*math.sqrt(mean*p.demand_sd**2+p.demand**2*sd**2)
    return dict(L=mean,sigmaL=sd,z=z,SS=ss,ROP=p.demand*mean+ss,base=p.demand*mean)

def simulate_one(p,scenario,replica,plan,trace=False):
    # Demand and per-material order streams are shared across scenarios for fair comparisons.
    demand_rng = np.random.default_rng(np.random.SeedSequence([p.seed,replica,0]))
    order_rng = [np.random.default_rng(np.random.SeedSequence([p.seed,replica,m+1])) for m in range(2)]
    demands = np.maximum(0,demand_rng.normal(p.demand,p.demand_sd,p.horizon))
    stock = [p.initial_aluminum,p.initial_glass]
    quantities = [p.quantity_aluminum,p.quantity_glass]
    pending = [[],[]]
    records,orders = [],[]
    sum_stock=sum_transit=lost=0.
    maximum=max(stock); minimum=min(stock)
    stockout=received=0
    threshold=plan['base'] if scenario=='A' else plan['ROP']
    for day,demand in enumerate(demands,1):
        # Receipts available at start of day; purchases placed after consumption.
        for m in range(2):
            arrivals=[o for o in pending[m] if o['arrival']<=day]
            stock[m]+=sum(o['quantity'] for o in arrivals)
            received+=len(arrivals)
            pending[m]=[o for o in pending[m] if o['arrival']>day]
        maximum=max(maximum,*stock)
        produced=min(demand,*stock)
        stock=[max(0,x-produced) for x in stock]
        shortage=max(0,demand-produced)
        lost+=shortage
        stockout+=int(shortage>1e-9)
        for m in range(2):
            position=stock[m]+sum(o['quantity'] for o in pending[m])
            # Base: one outstanding order per material to avoid duplicate daily purchases.
            eligible=(stock[m]<=threshold and not pending[m]) if scenario=='A' else position<=threshold
            while eligible:
                durations=sample_stages(order_rng[m],p).tolist()
                extra=p.delay if scenario=='C' else 0
                lead=max(1,math.ceil(sum(durations)))+extra
                order=dict(id=len(orders)+1,material=['Aluminio','Vidrio'][m],placed=day,arrival=day+lead,quantity=quantities[m],lead=lead,stages=durations,extra=extra)
                orders.append(order); pending[m].append(order)
                position+=quantities[m]
                eligible=scenario!='A' and position<=threshold
        transit=sum(o['quantity'] for queue in pending for o in queue)
        sum_stock+=sum(stock)/2
        sum_transit+=transit
        minimum=min(minimum,*stock)
        if trace: records.append(dict(Día=day,Aluminio=stock[0],Vidrio=stock[1],Demanda=demand,Producción=produced,No_producidas=shortage,Stockout=shortage>1e-9,Tránsito=transit))
    leads=[o['lead'] for o in orders]
    total=float(demands.sum())
    row={'Escenario':scenario,'Réplica':replica+1,'Stockout':int(stockout>0),'Días sin material':stockout,'Ventanas no producidas':lost,'Demandadas':total,'Atendidas':total-lost,'Nivel de servicio (%)':100*(total-lost)/total if total else 100.,'Inventario promedio':sum_stock/p.horizon,'Inventario máximo':maximum,'Inventario mínimo':minimum,'Órdenes realizadas':len(orders),'Lead time promedio':float(np.mean(leads)) if leads else np.nan,'Desviación lead time':float(np.std(leads,ddof=1)) if len(leads)>1 else np.nan,'Material en tránsito':sum_transit/p.horizon,'Costo terrestre (RD$)':received*16000,'Contenedores recibidos':received}
    return row,pd.DataFrame(records),orders

def run(p,progress=None):
    plan=planning(p); rows=[]
    for s in NAMES:
        for r in range(p.replicas):
            rows.append(simulate_one(p,s,r,plan)[0])
            done=len(rows)
            if progress and (done%max(1,p.replicas//20)==0 or done==3*p.replicas): progress(done/(3*p.replicas))
    details=pd.DataFrame(rows)
    summary=details.drop(columns='Réplica').groupby('Escenario',sort=False).mean()
    summary['Probabilidad stockout (%)']=summary.pop('Stockout')*100
    summary['Nivel de servicio (%)']=np.where(summary['Demandadas']>0,100*summary['Atendidas']/summary['Demandadas'],100)
    return plan,summary.reset_index(),details
