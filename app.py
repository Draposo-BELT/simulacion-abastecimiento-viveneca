import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).parent / '.matplotlib'))
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from simulation import Parameters, STAGES, NAMES, planning, run, simulate_one

st.set_page_config(page_title='VIVENECA | Abastecimiento',page_icon='🏭',layout='wide')
st.markdown('''<style>.stApp {background:#f5f7fb} h1,h2,h3 {color:#15364a} div[data-testid="stMetric"] {background:white;padding:16px;border-radius:12px;border-top:4px solid #008a91} </style>''',unsafe_allow_html=True)
st.title('Simulación de abastecimiento de materias primas importadas – VIVENECA')
st.caption('Ingeniería de Cadena de Suministro · Ventanas perimetrales · Proyecto Serrallés 305')
st.warning('SUPUESTOS ACADÉMICOS PARA MODELACIÓN – SUSTITUIR POR DATOS HISTÓRICOS REALES')
flow=['VIVENECA · solicitud / orden de compra','Proveedor / fábrica en China','Preparación y fabricación','Puerto de origen','Transporte marítimo · puerto a puerto','Puerto República Dominicana','Recepción / aduana','Transportista terrestre externo','VIVENECA · recepción de materia prima','Inventario disponible para producción']
st.markdown('<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center">'+'<span style="color:#008a91"> → </span>'.join('<div style="background:#15364a;color:white;padding:12px;border-radius:8px;max-width:185px">'+v+'</div>' for v in flow)+'</div>',unsafe_allow_html=True)
with st.expander('Datos confirmados del caso — proporcionados para este proyecto'):
    st.markdown('''- Insumos principales importados desde China. Aluminio: contacto con fábrica y gestión/intermediación de VIVENECA. Vidrio: contacto directo con fábrica.
- Contratación internacional puerto a puerto; un transportista externo traslada el contenedor desde el puerto dominicano a VIVENECA.
- Costo terrestre declarado: aproximadamente **RD$16,000 por contenedor de 20 pies**.
- Período estudiado: 2 pedidos de aluminio, 4 contenedores de vidrio y 4 pedidos de accesorios. Son antecedentes, no frecuencias impuestas al modelo.
- Una entrega prevista para junio llegó a finales de julio/agosto.
- Vidrio con flete internacional: referencia aproximada de US$7,000 al principio del año y cotización posterior similar de US$14,000. No se incorporan como costos del modelo.
- Aluminio reciente: aproximadamente 23,611 lb; **no es una capacidad contractual exacta** y no se convierte a ventanas.''')
with st.sidebar:
    st.header('Parámetros académicos')
    st.caption('Todos los tiempos se expresan en días hábiles, lunes a viernes. No se descuentan feriados.')
    d=st.number_input('Demanda media (ventanas/día)',0.,1000.,7.5,.5)
    sd=st.number_input('Desviación de demanda',0.,1000.,1.5,.1)
    st.caption('Referencia: 15 ventanas / 2 días = 7.5. Desviación inicial: 20%. Demanda normal truncada en cero; cantidades continuas equivalentes.')
    service=st.number_input('Nivel de servicio objetivo (%)',50.1,99.99,95.,.1)
    initial=[]; quantity=[]
    for name in ['aluminio','vidrio']:
        initial.append(st.number_input('Inventario inicial de '+name,0.,100000.,150.,10.))
        quantity.append(st.number_input('Cantidad por orden de '+name,1.,100000.,300.,10.))
    stages=[]
    for name,default in zip(STAGES,Parameters().stages):
        with st.expander(name):
            stages.append(tuple(st.number_input(label,0.,365.,float(value),1.,key=name+label) for label,value in zip(['Mínimo','Moda','Máximo'],default)))
    delay=st.number_input('Retraso extraordinario (días hábiles)',0,365,30)
    horizon=st.number_input('Horizonte (días hábiles)',1,2000,180)
    replicas=st.number_input('Réplicas por escenario',1,10000,1000)
    seed=st.number_input('Semilla',0,2147483647,20261013)
p=Parameters(d,sd,service,*[initial[0],initial[1],quantity[0],quantity[1]],tuple(stages),delay,horizon,replicas,seed)
try:
    plan=planning(p)
except ValueError as e:
    st.error(str(e)); st.stop()
cols=st.columns(4)
for col,label,value in zip(cols,['Lead time medio','Desviación lead time','Inventario de seguridad','Punto de reorden'],[plan['L'],plan['sigmaL'],plan['SS'],plan['ROP']]): col.metric(label,f'{value:.2f}')
with st.expander('Cómo funciona el modelo y cómo interpretar las fórmulas',expanded=False):
    st.latex(r'SS=z\sqrt{L\sigma_d^2+d^2\sigma_L^2}\qquad ROP=dL+SS')
    st.write(f"d = {d:.2f} ventanas/día; σd = {sd:.2f}; z = {plan['z']:.3f}; L = {plan['L']:.2f} días hábiles; σL = {plan['sigmaL']:.2f} días. L y σL se estiman con 50,000 muestras reproducibles de las cuatro etapas triangulares independientes; se redondea el total hacia arriba para recibir al inicio de un día.")
    st.write(f"El colchón calculado es {plan['SS']:.1f} ventanas equivalentes. La propuesta compra cuando disponible + tránsito ≤ {plan['ROP']:.1f}. Si hace falta, genera varias órdenes hasta superar ese nivel. El objetivo de servicio de la fórmula no garantiza la tasa atendida de la simulación.")
    st.markdown('''**A:** reordena con disponible ≤ d×L y como máximo una orden pendiente por material (supuesto para evitar duplicados diarios). **B:** usa la posición de inventario y SS. **C:** usa el mismo ROP nominal que B y añade el retraso a **todas las órdenes de ambos materiales**, después de la etapa marítima.

Una unidad equivale al material de una ventana. Producir una unidad consume una de aluminio y una de vidrio. Se admite producción parcial; demanda no atendida se pierde y no se acumula. Un día de stockout es un día con demanda no atendida. No hay pedidos en tránsito al inicio ni período de calentamiento. Recepciones al inicio del día; consumo y compras al final. **Una orden representa un contenedor de 20 pies: supuesto académico**, no conversión física validada.

Inventario promedio: promedio diario de los dos materiales al cierre; máximo: mayor existencia de un material, incluyendo recepciones; mínimo: menor existencia de un material. Tránsito: suma de ambos materiales al cierre. Probabilidad de stockout: porcentaje de réplicas con al menos un día de falta. Los extremos y las estadísticas de lead time de la tabla son promedios entre réplicas. Los tiempos incluyen órdenes aún pendientes al cierre. Costo: solo contenedores recibidos × RD$16,000; no incluye otros costos.''')
    st.info('Con 150 unidades iniciales hay aproximadamente 20 días de cobertura frente a unos 40 días de importación. Las tres políticas pueden sufrir faltantes iniciales. Aumenta el inventario inicial para explorar una operación que ya cuente con cobertura.')
if st.button('EJECUTAR SIMULACIÓN',type='primary',width='stretch'):
    bar=st.progress(0.,text='Simulando los tres escenarios…')
    with st.spinner('Calculando resultados Monte Carlo…'):
        result=run(p,lambda value:bar.progress(value,text=f'Completado: {value:.0%}'))
    st.session_state['result']=(p,result)
if 'result' not in st.session_state:
    st.info('Configura los supuestos y pulsa EJECUTAR SIMULACIÓN. No se ejecutan réplicas automáticamente.'); st.stop()
saved,(plan,summary,details)=st.session_state['result']
if p!=saved: st.warning('Los controles cambiaron. Los resultados siguientes pertenecen a la última ejecución; pulsa EJECUTAR SIMULACIÓN para actualizarlos.')
p=saved
st.subheader('Resultados Monte Carlo')
st.caption(f'{p.replicas:,} réplicas por escenario · {p.horizon} días hábiles · semilla {p.seed} · resultados bajo supuestos académicos')
scenario=st.selectbox('Escenario para explorar',list(NAMES),format_func=lambda s:NAMES[s])
row=summary.set_index('Escenario').loc[scenario]
for col,key in zip(st.columns(6),['Probabilidad stockout (%)','Nivel de servicio (%)','Días sin material','Lead time promedio','Costo terrestre (RD$)','Órdenes realizadas']): col.metric(key,f'{row[key]:,.2f}')
st.dataframe(summary.round(2),hide_index=True,width='stretch')
for col,key in zip(st.columns(3),['Probabilidad stockout (%)','Nivel de servicio (%)','Días sin material']):
    with col:
        st.write(key); st.bar_chart(summary.set_index('Escenario')[[key]],color='#008a91')
st.caption('A: base académico · B: propuesta SS + ROP · C: estrés con retraso extraordinario')
replica=st.number_input('Réplica para explorar',1,p.replicas,1)
_,daily,orders=simulate_one(p,scenario,replica-1,plan,trace=True)
st.subheader('Inventario y eventos · réplica seleccionada')
fig,ax=plt.subplots(figsize=(13,4.6))
for material,color in [('Aluminio','#007f8b'),('Vidrio','#c18a16')]: ax.plot(daily['Día'],daily[material],label=material,color=color)
rop=plan['base'] if scenario=='A' else plan['ROP']; ss=0 if scenario=='A' else plan['SS']
ax.axhline(rop,color='#5746a0',linestyle='--',label='ROP / umbral de compra')
ax.axhline(ss,color='#557466',linestyle=':',label='Safety Stock')
for day in daily.loc[daily.Stockout,'Día']: ax.axvspan(day-.45,day+.45,color='red',alpha=.09)
for field,marker,color,label in [('placed','v','#15364a','Orden colocada'),('arrival','^','#008040','Orden recibida')]:
    events=[o for o in orders if o[field]<=p.horizon]
    ax.scatter([o[field] for o in events],[daily.iloc[o[field]-1][o['material']] for o in events],marker=marker,color=color,label=label,zorder=5)
ax.set(xlabel='Día hábil (día 1 = lunes)',ylabel='Ventanas equivalentes'); ax.legend(ncol=3); ax.grid(alpha=.15); fig.tight_layout(); st.pyplot(fig); plt.close(fig)
st.caption('Franjas rojas: demanda no atendida. Las líneas muestran inventario al cierre. Una compra depende de la posición de inventario en B/C, no solo de la línea de existencias.')
left,right=st.columns(2)
with left:
    st.subheader('Distribución del lead time')
    st.caption('Órdenes generadas en la réplica seleccionada, incluidas las pendientes.')
    if orders:
        fig,ax=plt.subplots(figsize=(6,3)); ax.hist([o['lead'] for o in orders],bins='auto',color='#008a91',edgecolor='white'); ax.set(xlabel='Días hábiles',ylabel='Órdenes'); st.pyplot(fig); plt.close(fig)
with right:
    st.subheader('Timeline de una orden')
    if orders:
        index=st.selectbox('Orden',range(len(orders)),format_func=lambda i:f"#{orders[i]['id']} · {orders[i]['material']} · solicitud día {orders[i]['placed']}")
        o=orders[index]; labels=STAGES.copy(); durations=o['stages'].copy()
        if o['extra']: labels.insert(2,'Retraso extraordinario'); durations.insert(2,o['extra'])
        padding=o['lead']-sum(durations)
        if padding>1e-9: labels.append('Ajuste al día de recepción'); durations.append(padding)
        fig,ax=plt.subplots(figsize=(6,3)); starts=np.cumsum([0]+durations[:-1])+o['placed']; ax.barh(labels,durations,left=starts,color='#008a91')
        for y,(start,length) in enumerate(zip(starts,durations)): ax.text(start+length/2,y,f'{length:.1f}',ha='center',va='center',fontsize=8)
        ax.invert_yaxis(); ax.set_xlabel('Día hábil'); st.pyplot(fig); plt.close(fig)
        st.write(f"Solicitud: día {o['placed']} → recepción: día {o['arrival']}. Total: {o['lead']} días. Estado al cierre: {'recibido' if o['arrival']<=p.horizon else 'en tránsito / pendiente'}.")
if orders:
    st.subheader('Seguimiento de órdenes · réplica seleccionada')
    table=pd.DataFrame([{**{k:v for k,v in o.items() if k!='stages'},'Estado':'Recibido' if o['arrival']<=p.horizon else 'Pendiente'} for o in orders])
    st.dataframe(table,hide_index=True,width='stretch')
with st.expander('Registro diario'): st.dataframe(daily,hide_index=True,width='stretch')
st.subheader('Interpretación automática')
a,b,c=[summary.set_index('Escenario').loc[s] for s in 'ABC']
diff=b['Probabilidad stockout (%)']-a['Probabilidad stockout (%)']
verb='reduce' if diff<0 else 'aumenta' if diff>0 else 'mantiene'
st.write(f"Bajo los supuestos académicos utilizados, la propuesta {verb} la probabilidad de al menos un stockout: A = {a['Probabilidad stockout (%)']:.1f}% y B = {b['Probabilidad stockout (%)']:.1f}%. El nivel de servicio pasa de {a['Nivel de servicio (%)']:.1f}% a {b['Nivel de servicio (%)']:.1f}%, y los días promedio con faltantes de {a['Días sin material']:.1f} a {b['Días sin material']:.1f}. Con retraso extraordinario, C atiende {c['Nivel de servicio (%)']:.1f}% de la demanda. Estos resultados son una comparación del modelo, no una validación de la política real de VIVENECA.")
st.caption('El faltante inicial puede hacer que la probabilidad sea 100% en todos los escenarios; en ese caso compara también días sin material y demanda atendida. El SS supone independencia de demanda y plazos, y no garantiza protección frente al estrés extraordinario.')
for col,frame,name in zip(st.columns(2),[summary,details],['resultados_resumen.csv','resultados_replicas.csv']):
    col.download_button('Descargar '+name,frame.to_csv(index=False).encode('utf-8-sig'),file_name=name,mime='text/csv')


