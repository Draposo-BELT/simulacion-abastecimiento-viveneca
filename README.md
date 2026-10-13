# VIVENECA · Simulación de abastecimiento

Aplicación académica Streamlit para comparar políticas de inventario de aluminio y vidrio del proyecto Serrallés 305. Incluye Monte Carlo, inventario de seguridad, punto de reorden, gráficos, seguimiento de órdenes y exportación CSV.

## Ejecutar

Python 3.12:

```sh
pip install -r requirements.txt
streamlit run app.py
```

## Publicar en Streamlit Community Cloud

1. Subir el contenido de esta carpeta a la raíz de un repositorio GitHub.
2. Iniciar sesión en https://share.streamlit.io con GitHub.
3. Seleccionar Create app / Deploy a public app from GitHub.
4. Elegir el repositorio, rama main y archivo app.py. Seleccionar Python 3.12 en opciones avanzadas.
5. Publicar y comprobar que la visibilidad permita acceso público.
6. Abrir el enlace .streamlit.app en una ventana privada y ejecutar la simulación para comprobar el acceso sin iniciar sesión.

La aplicación no ejecuta Monte Carlo hasta pulsar EJECUTAR SIMULACIÓN. No necesita claves ni secretos. El alojamiento puede suspender aplicaciones inactivas según las reglas del proveedor.

## Alcance académico

Los antecedentes de la empresa se proporcionaron para este proyecto; no fueron verificados independientemente. Los tiempos, demanda, inventarios, cantidades por orden y políticas son supuestos académicos editables, identificados en la aplicación. Todos los plazos se expresan en días hábiles. Una orden equivale a un contenedor solo como supuesto de modelación de costos. El costo terrestre declarado es aproximadamente RD$16,000 por contenedor de 20 pies.

El escenario base no representa necesariamente la política real actual de VIVENECA. Las conclusiones dependen de los resultados. La interfaz incluye definiciones, fórmulas y limitaciones completas.

## Pruebas

```sh
python -m unittest -v
```
