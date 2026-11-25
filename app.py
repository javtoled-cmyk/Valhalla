from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


COLUMNAS_TEXTO = ["Partida", "Categoria", "Unidad"]
COLUMNAS_NUMERICAS = ["Cantidad", "Rendimiento_Diario", "Cuadrillas"]
COLUMNAS = COLUMNAS_TEXTO + COLUMNAS_NUMERICAS
ESCENARIOS = ["Días optimistas", "Días estimados", "Días pesimistas"]


@st.cache_data
def leer_excel(contenido):
    datos = pd.read_excel(BytesIO(contenido), engine="openpyxl")
    datos.columns = [str(columna).strip() for columna in datos.columns]
    repetidas = [columna for columna in COLUMNAS if (datos.columns == columna).sum() > 1]
    if repetidas:
        raise ValueError(f"Hay columnas repetidas: {', '.join(repetidas)}.")
    faltantes = [columna for columna in COLUMNAS[:-1] if columna not in datos]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}.")
    if "Cuadrillas" not in datos:
        datos["Cuadrillas"] = 1
    datos = datos[COLUMNAS].copy()
    datos[COLUMNAS_TEXTO] = datos[COLUMNAS_TEXTO].astype("string")
    datos["Cuadrillas"] = datos["Cuadrillas"].where(
        datos["Cuadrillas"].notna(), 1
    )
    for columna in COLUMNAS_NUMERICAS:
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce").astype(float)
    return datos


def validar_partidas(datos):
    errores = []
    for columna in COLUMNAS_TEXTO:
        vacias = datos[columna].fillna("").str.strip().eq("")
        if vacias.any():
            filas = ", ".join(str(i + 1) for i in np.flatnonzero(vacias))
            errores.append(f"{columna}: completa las filas {filas}.")

    for columna in COLUMNAS_NUMERICAS:
        valores = datos[columna].to_numpy(dtype=float, na_value=np.nan)
        invalidas = ~np.isfinite(valores)
        if columna == "Cantidad":
            invalidas |= valores < 0
            requisito = "un número mayor o igual a 0"
        elif columna == "Cuadrillas":
            invalidas |= (valores < 1) | (valores != np.trunc(valores))
            requisito = "un entero mayor o igual a 1"
        else:
            invalidas |= valores <= 0
            requisito = "un número mayor que 0"
        if invalidas.any():
            filas = ", ".join(str(i + 1) for i in np.flatnonzero(invalidas))
            errores.append(f"{columna}: ingresa {requisito} en las filas {filas}.")
    return errores


def calcular_duraciones(datos, holgura, optimista, pesimista):
    resultado = datos.copy()
    resultado[COLUMNAS_TEXTO] = resultado[COLUMNAS_TEXTO].apply(
        lambda columna: columna.str.strip()
    )
    resultado["Días base"] = (
        resultado["Cantidad"] / resultado["Rendimiento_Diario"] / resultado["Cuadrillas"]
    )
    estimado = resultado["Días base"] * (1 + holgura / 100)
    resultado[ESCENARIOS[0]] = estimado * (1 - optimista / 100)
    resultado[ESCENARIOS[1]] = estimado
    resultado[ESCENARIOS[2]] = estimado * (1 + pesimista / 100)
    return resultado


@st.cache_data
def generar_excel(datos, hoja):
    archivo = BytesIO()
    with pd.ExcelWriter(archivo, engine="openpyxl") as escritor:
        datos.to_excel(escritor, sheet_name=hoja, index=False)
        for fila in escritor.sheets[hoja].iter_rows(min_row=2, max_col=len(COLUMNAS_TEXTO)):
            for celda in fila:
                if isinstance(celda.value, str):
                    celda.data_type = "s"
    return archivo.getvalue()


def partidas_de_ejemplo():
    return pd.DataFrame(
        [
            ("Excavación de fundaciones", "Obra gruesa", "m³", 120, 18, 1),
            ("Hormigón de fundaciones", "Obra gruesa", "m³", 42, 8, 1),
            ("Canalización eléctrica", "Electricidad", "m", 260, 35, 2),
            ("Pintura interior", "Terminaciones", "m²", 480, 55, 1),
        ],
        columns=COLUMNAS,
    ).astype({columna: float for columna in COLUMNAS_NUMERICAS})


def mostrar_grafico(titulo, etiquetas, series):
    fig, eje = plt.subplots(figsize=(10, max(2.8, len(etiquetas) * 0.40 + 1)))
    posiciones = np.arange(len(etiquetas))
    ancho = 0.75 / len(series)
    colores = ["#2563a6"] if len(series) == 1 else ["#25866a", "#2563a6", "#b75537"]
    for indice, ((nombre, valores), color) in enumerate(zip(series, colores)):
        desplazamiento = (indice - (len(series) - 1) / 2) * ancho
        eje.barh(posiciones + desplazamiento, valores, height=ancho, label=nombre, color=color)
    eje.set_yticks(posiciones, etiquetas)
    eje.invert_yaxis()
    eje.set_xlabel("Días")
    eje.set_title(titulo, loc="left")
    eje.set_axisbelow(True)
    eje.grid(axis="x", alpha=0.22)
    eje.spines[["top", "right"]].set_visible(False)
    if len(series) > 1:
        eje.legend()
    fig.tight_layout()
    try:
        st.pyplot(fig)
    finally:
        plt.close(fig)


def mostrar_indicadores(resultado):
    total = resultado[ESCENARIOS].sum()
    indicadores = st.columns(4)
    indicadores[0].metric("Partidas", len(resultado))
    for indicador, escenario in zip(indicadores[1:], ESCENARIOS):
        indicador.metric(escenario, f"{total[escenario]:.2f}")
    st.caption("Los días totales son la suma de las partidas. Para obtener el plazo de obra hay que considerar dependencias y trabajos en paralelo.")


def mostrar_resultados(resultado):
    st.subheader("Duraciones calculadas")
    st.dataframe(
        resultado,
        hide_index=True,
        column_config={
            columna: st.column_config.NumberColumn(format="%.2f")
            for columna in ["Días base", *ESCENARIOS]
        },
    )
    excel, csv = st.columns(2)
    excel.download_button(
        "Descargar resultados en Excel",
        generar_excel(resultado, "Duraciones"),
        "duraciones.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    csv.download_button(
        "Descargar resultados en CSV",
        resultado.to_csv(index=False).encode("utf-8-sig"),
        "duraciones.csv",
        "text/csv",
    )

    ordenadas = resultado.sort_values(ESCENARIOS[1], ascending=False, kind="stable")
    acumulado = resultado.groupby("Categoria")[ESCENARIOS[1]].sum().sort_values(ascending=False)
    duracion, escenarios, categorias = st.tabs(["Por partida", "Escenarios", "Por categoría"])
    with duracion:
        mostrar_grafico("Duración estimada por partida", ordenadas["Partida"], [
            (ESCENARIOS[1], ordenadas[ESCENARIOS[1]]),
        ])
    with escenarios:
        mostrar_grafico("Comparación de escenarios por partida", ordenadas["Partida"], [
            (escenario, ordenadas[escenario]) for escenario in ESCENARIOS
        ])
    with categorias:
        mostrar_grafico("Duración estimada acumulada por categoría", acumulado.index, [
            (ESCENARIOS[1], acumulado),
        ])


def principal():
    st.set_page_config(page_title="Duración de partidas de construcción", layout="wide")
    st.title("Duración de partidas de construcción")
    ejemplo = partidas_de_ejemplo()
    st.download_button(
        "Descargar Excel de ejemplo",
        generar_excel(ejemplo, "Partidas"),
        "ejemplo_partidas.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    archivo = st.file_uploader("Cargar partidas desde Excel (.xlsx)", type=["xlsx"])
    if archivo is None:
        datos = ejemplo
        st.caption("Estás viendo partidas de ejemplo. Sube un Excel para analizar tu obra.")
    else:
        try:
            datos = leer_excel(archivo.getvalue())
        except ValueError as error:
            st.error(str(error))
            return
        except Exception:
            st.error("No se pudo leer el archivo. Comprueba que sea un Excel .xlsx válido.")
            return

    with st.sidebar:
        st.header("Supuestos de duración")
        holgura = st.slider("Holgura o riesgo (%)", 0, 100, 10)
        optimista = st.slider("Reducción optimista (%)", 0, 100, 10)
        pesimista = st.slider("Aumento pesimista (%)", 0, 100, 20)
        st.caption("La holgura se aplica a los días base. Los escenarios optimista y pesimista varían los días estimados.")

    indicadores = st.container()
    st.subheader("Editar partidas")
    datos = st.data_editor(
        datos,
        key=f"partidas-{archivo.file_id}" if archivo else "partidas-ejemplo",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Cantidad": st.column_config.NumberColumn(min_value=0.0),
            "Cuadrillas": st.column_config.NumberColumn(min_value=1, step=1, default=1),
        },
    )
    if datos.empty:
        st.info("Agrega al menos una partida para calcular su duración.")
        return
    datos["Cuadrillas"] = datos["Cuadrillas"].fillna(1)
    errores = validar_partidas(datos)
    if errores:
        st.error("Corrige las filas indicadas para calcular las duraciones.")
        for error in errores:
            st.write(error)
        return
    resultado = calcular_duraciones(datos, holgura, optimista, pesimista)
    if not np.isfinite(resultado[["Días base", *ESCENARIOS]].to_numpy(dtype=float)).all():
        st.error("Las duraciones superan el rango numérico. Revisa las cantidades y los rendimientos.")
        return
    with indicadores:
        mostrar_indicadores(resultado)
    mostrar_resultados(resultado)


if __name__ == "__main__":
    principal()
