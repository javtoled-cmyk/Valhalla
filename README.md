# Duración de partidas de construcción

Abre `vista.html` en el navegador para explorar los gráficos y escenarios con datos de ejemplo. La vista HTML funciona sin conexión y sin instalar dependencias.

Desde esta carpeta, ejecuta:

```powershell
pip install streamlit pandas matplotlib openpyxl
streamlit run app.py
```

La app se abre con partidas de ejemplo. Puedes descargar esa planilla o cargar tu propio archivo `.xlsx`. La primera hoja debe tener los encabezados en la primera fila.

| Columna | Contenido |
| --- | --- |
| `Partida` | Nombre de la partida |
| `Categoria` | Categoría o especialidad |
| `Unidad` | Unidad de medida, como m² o m³ |
| `Cantidad` | Cantidad mayor o igual a cero |
| `Rendimiento_Diario` | Cantidad ejecutada por cuadrilla en un día, mayor que cero |
| `Cuadrillas` | Entero mayor o igual a uno. Si falta la columna o una celda está vacía, se usa 1 |

Edita los datos en la primera tabla. Los resultados y gráficos se recalculan al confirmar una edición o mover un control. Puedes descargar las partidas con sus duraciones calculadas en Excel o CSV.

Los días base se calculan dividiendo la cantidad por el rendimiento diario y por el número de cuadrillas. Los días estimados incluyen la holgura. Los escenarios optimista y pesimista aplican, respectivamente, una reducción y un aumento sobre el estimado. Los totales suman duraciones de partidas. El plazo de obra depende también de las dependencias y de las partidas ejecutadas en paralelo.
