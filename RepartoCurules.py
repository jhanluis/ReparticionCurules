import math
from collections import Counter
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math

st.set_page_config(page_title="Asignación de curules (MX)", layout="wide")

colores = {
    "PAN": "#27357e",
    "PRI": "#009905",
    "PRD": "#F0F400",
    "PT":  "#ff0000",
    "PVEM": "#2E8B57",
    "MC":  "#F28C28",
    "MORENA": "#af272f",
    "PES": "#6F42C1",
    "NA": "#00AEEF",
    "RSP": "#C2185B",
    "FXM": "#9C27B0",
    "INDEP": "#808080"
    }

# Cambiar color de fondo de la página a azul
st.markdown(
    """
    <style>
        .stApp {
            background-color: #042861; /* Azul fuerte */
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ------------------------------
# Orden fijo y utilidades
# ------------------------------
PARTY_ORDER = ["PAN","PRI","PRD","PT","PVEM","MC","MORENA","PES","NA","RSP","FXM","INDEP"]

def sort_parties_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena un DataFrame con columna 'Partido' usando PARTY_ORDER primero;
    cualquier partido extra queda al final en orden alfabético."""
    df = df.copy()
    extras = sorted([p for p in df["Partido"] if p not in PARTY_ORDER])
    full_order = PARTY_ORDER + [p for p in extras if p not in PARTY_ORDER]
    cat = pd.Categorical(df["Partido"], categories=full_order, ordered=True)
    df["_ord"] = cat
    df = df.sort_values(["_ord", "Partido"]).drop(columns="_ord")
    return df

# ------------------------------
# Funciones de cálculo
# ------------------------------
def aplica_umbral(votos: dict[str, int | float], umbral: float = 0.03) -> dict[str, float]:
    total = sum(votos.values())
    if total <= 0:
        return {}
    return {p: v for p, v in votos.items() if (v / total) >= umbral}

def porcentajes(votos: dict[str, int | float]) -> dict[str, float]:
    total = sum(votos.values())
    if total <= 0:
        return {p: 0.0 for p in votos}
    return {p: v / total for p, v in votos.items()}

def cociente_natural(votos: dict[str, int | float], s: int = 200) -> float:
    total_validos = sum(votos.values())
    return (total_validos / s) if s > 0 else 0.0

def asigna_resto_mayor(votos: dict[str, int | float], s: int = 200) -> dict[str, int]:
    total = sum(votos.values())
    if s <= 0 or total <= 0:
        return {p: 0 for p in votos}
    q = total / s
    base = {p: int(v // q) for p, v in votos.items()}
    asignadas = sum(base.values())
    rem = {p: (v - base[p] * q) for p, v in votos.items()}
    faltan = s - asignadas
    if faltan > 0:
        orden = sorted(rem.items(), key=lambda x: x[1], reverse=True)
        for p, _ in orden[:faltan]:
            base[p] += 1
    elif faltan < 0:
        orden = sorted(rem.items(), key=lambda x: x[1])
        for p, _ in orden[:(-faltan)]:
            base[p] = max(0, base[p] - 1)
    return base

def df_from_presets(votos: dict, mr: dict) -> pd.DataFrame:
    """Une claves de votos y MR en un DataFrame Partido/Votos/MR (faltantes=0) respetando orden fijo."""
    partidos = list({*votos.keys(), *mr.keys()})
    # orden fijo + extras
    ordered = [p for p in PARTY_ORDER if p in partidos] + [p for p in partidos if p not in PARTY_ORDER]
    rows = [{"Partido": p, "Votos": int(votos.get(p, 0)), "MR": int(mr.get(p, 0))} for p in ordered]
    return pd.DataFrame(rows)

# ------------------------------
# Presets (2018, 2021, 2024)
# ------------------------------
PRESETS = {
    2018: {
        "anio": 2018,
        "votacion_total_emitida": 55946772,
        "votos_eliminar": {"Nulos": 2226781, "NoRegistrados": 32611},
        "votos": {
            "PAN": 10033157, "PRI": 9271950, "PRD": 2959800, "PT": 2201192,
            "PVEM": 2685677, "MC": 2473056, "MORENA": 20790623, "PES": 1347540,
            "NA": 1385421, "INDEP": 538964
        },
        "mr": {
            "PAN": 40, "PRI": 7, "PRD": 9, "PT": 58, "PVEM": 5, "MC": 17,
            "MORENA": 106, "PES": 56, "NA": 2, "INDEP": 0
        }
    },
    2021: {
        "anio": 2021,
        "votacion_total_emitida": 48813142,
        "votos_eliminar": {"Nulos": 1660363, "NoRegistrados": 41558},
        "votos": {
            "PAN": 8896470, "PRI": 8663257, "PRD": 1785351, "PT": 1588152,
            "PVEM": 2659178, "MC": 3425006, "MORENA": 16629905,
            "PES": 1344835, "RSP": 864391, "FXM": 1210384, "INDEP": 44292
        },
        "mr": {
            "PAN": 73, "PRI": 30, "PRD": 7, "PT": 30, "PVEM": 31, "MC": 7,
            "MORENA": 122, "PES": 0, "RSP": 0, "FXM": 0, "INDEP": 0
        }
    },
    2024: {
        "anio": 2024,
        "votacion_total_emitida": 59447863,
        "votos_eliminar": {"Nulos": 2189171, "NoRegistrados": 49305},
        "votos": {
            "PAN": 10046629, "PRI": 6622242, "PRD": 1449176, "PT": 3253564,
            "PVEM": 4992286, "MC": 6495521, "MORENA": 24277957, "INDEP": 72012
        },
        "mr": {
            "PAN": 31, "PRI": 10, "PRD": 1, "PT": 34, "PVEM": 40, "MC": 1,
            "MORENA": 182, "INDEP": 1
        }
    }
}

# ------------------------------
# Encabezado y carga de presets (arriba)
# ------------------------------
st.title("Calculadora de diputaciones por Representación Proporcional.")
st.caption("Calcula curules asignados de RP.")

colA, colB = st.columns([2,3])
with colA:
    st.subheader("Cargar datos predefinidos")
    preset_choice = st.selectbox("Elegir año", [2018, 2021, 2024], index=2, key="preset_choice_main")
    load = st.button("Cargar preset", type="primary", use_container_width=True)

with colB:
    st.subheader("Parámetros globales")
    seats_mr = st.number_input("Curules de MR", min_value=0, max_value=500, value=300, step=1, help="Mayoría Relativa")
    seats_rp = st.number_input("Curules de RP", min_value=0, max_value=500, value=200, step=1, help="Representación Proporcional")
    # umbral = st.number_input("Umbral legal (p.ej. 0.03 = 3%)", min_value=0.0, max_value=1.0, value=0.03, step=0.01, format="%.2f")
    # bonus_cap = st.number_input("Tope de sobrerrepresentación (extra)", min_value=0.0, max_value=1.0, value=0.08, step=0.01, format="%.2f",
    #                             help="Máximo permitido = porcentaje válido + este extra, sobre el total de curules MR+RP.")
    umbral = .03
    bonus_cap = .08
    st.markdown("---")
    st.subheader("Votos no válidos / a eliminar")
    if "nulos" not in st.session_state: st.session_state["nulos"] = 0
    if "no_reg" not in st.session_state: st.session_state["no_reg"] = 0
    if "otros_excl" not in st.session_state: st.session_state["otros_excl"] = 0
    nulos = st.number_input("Nulos", min_value=0, value=st.session_state["nulos"], step=1, key="nulos_input_main")
    no_reg = st.number_input("No registrados", min_value=0, value=st.session_state["no_reg"], step=1, key="noreg_input_main")
    otros_excl = st.number_input("Otros excluidos (opcional)", min_value=0, value=st.session_state["otros_excl"], step=1, key="otros_input_main")

# Estado inicial
if "df_data" not in st.session_state:
    st.session_state["df_data"] = pd.DataFrame({"Partido": PARTY_ORDER, "Votos": [0]*len(PARTY_ORDER), "MR": [0]*len(PARTY_ORDER)})
if "anio_actual" not in st.session_state:
    st.session_state["anio_actual"] = None

# Cargar preset
if load:
    preset = PRESETS.get(preset_choice)
    if preset:
        st.session_state["df_data"] = df_from_presets(preset["votos"], preset["mr"])
        st.session_state["df_data"] = sort_parties_df(st.session_state["df_data"])
        st.session_state["nulos"] = preset["votos_eliminar"].get("Nulos", 0)
        st.session_state["no_reg"] = preset["votos_eliminar"].get("NoRegistrados", 0)
        st.session_state["anio_actual"] = preset.get("anio", None)
        st.toast(f"Preset {preset_choice} cargado")

total_seats = seats_mr + seats_rp

# ------------------------------
# Tabla de edición con orden fijo
# ------------------------------
st.markdown("### Votos por partido y curules de MR")
st.write("La tabla mantiene un **orden fijo de partidos**. Puedes editar valores o agregar filas adicionales.")
data = st.data_editor(
    sort_parties_df(st.session_state["df_data"]),
    num_rows="dynamic",
    use_container_width=True,
    key="tabla_partidos",
)

# ------------------------------
# Cálculo
# ------------------------------
if st.button("Calcular asignación", type="primary"):
    df_clean = data.copy()
    df_clean["Partido"] = df_clean["Partido"].astype(str).str.strip()
    df_clean["Votos"] = pd.to_numeric(df_clean["Votos"], errors="coerce").fillna(0).astype(int)
    df_clean["MR"] = pd.to_numeric(df_clean["MR"], errors="coerce").fillna(0).astype(int)
    df_clean = df_clean[df_clean["Partido"] != ""]
    df_clean = sort_parties_df(df_clean)  # imponer orden fijo

    # Persistir
    st.session_state["df_data"] = df_clean.copy()

    # Diccionarios completos
    votos_all = dict(zip(df_clean["Partido"], df_clean["Votos"]))
    mr_all = dict(zip(df_clean["Partido"], df_clean["MR"]))

    # No válidos
    nulos_val = st.session_state.get("nulos", nulos)
    no_reg_val = st.session_state.get("no_reg", no_reg)
    otros_excl_val = st.session_state.get("otros_excl", otros_excl)

    votos_excluidos = nulos_val + no_reg_val + otros_excl_val
    total_emitida = sum(votos_all.values()) + votos_excluidos
    votos_validos_total = sum(votos_all.values())

    # Filtrar por umbral
    partidos_validos = aplica_umbral(votos_all, umbral=umbral)
    mr_validos = {p: mr_all.get(p, 0) for p in partidos_validos.keys()}
    rp_validos = asigna_resto_mayor(partidos_validos, s=seats_rp)
    curules_totales = dict(Counter(mr_validos) + Counter(rp_validos))

    # Cap
    total_validos_para_cap = sum(partidos_validos.values())
    porcentaje_valido = {k: (v / total_validos_para_cap) if total_validos_para_cap > 0 else 0.0
                         for k, v in partidos_validos.items()}
    porcentaje_maximo = {k: porcentaje_valido.get(k, 0.0) + bonus_cap for k in curules_totales}
    curules_maximos = {k: int((porcentaje_maximo.get(k, 0.0)) * total_seats) for k in curules_totales}

    # Resultados (orden fijo)
    partidos_out = [p for p in PARTY_ORDER if p in curules_totales] + [p for p in curules_totales if p not in PARTY_ORDER]
    df_res = pd.DataFrame({
        "Partido": partidos_out,
        "MR":    [mr_validos.get(k, 0) for k in partidos_out],
        "RP":    [rp_validos.get(k, 0) for k in partidos_out],
        "Total": [curules_totales.get(k, 0) for k in partidos_out],
        "Máximo permitido": [curules_maximos.get(k, 0) for k in partidos_out],
    })
    df_res["⚠️ Excede tope"] = df_res["Total"] > df_res["Máximo permitido"]

    # Métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    anio_label = st.session_state.get("anio_actual", "")
    col1.metric("Año (preset)", anio_label if anio_label else "—")
    col2.metric("Votación emitida (calc.)", f"{total_emitida:,}".replace(",", " "))
    col3.metric("Votos válidos totales", f"{votos_validos_total:,}".replace(",", " "))
    col4.metric("Partidos ≥ umbral", f"{len(partidos_validos)}")
    col5.metric("Curules totales (MR)", f"{sum(mr_all.values()):,}".replace(",", " "))

    st.markdown("### Resultados por partido (≥ umbral)")
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    # Advertencias
    exceden = df_res[df_res["⚠️ Excede tope"]]
    if not exceden.empty:
        st.warning("Algunos partidos válidos exceden el tope de sobrerrepresentación. Requiere ajuste conforme a la ley.")
        for _, r in exceden.iterrows():
            st.write(f"• {r['Partido']}: Total = {r['Total']} vs Máximo = {r['Máximo permitido']}  → Excede por {r['Total'] - r['Máximo permitido']} curules.")
    else:
        st.success("Ningún partido válido excede el tope con los parámetros dados.")

    # Gráfica
    # st.markdown("### Curules totales (MR + RP) — solo válidos")
    # fig, ax = plt.subplots(figsize=(10, 5))
    # ax.bar(df_res["Partido"], df_res["Total"])
    # ax.set_xlabel("Partido")
    # ax.set_ylabel("Curules")
    # title = "Curules asignados (partidos ≥ umbral)"
    # if anio_label:
    #     title += f" — {anio_label}"
    # ax.set_title(title)
    # plt.xticks(rotation=45)
    # st.pyplot(fig)


# Colores sugeridos (ajústalos si quieres)


    # Parámetros del hemiciclo
    filas = 10
    r_min, r_max = 1.0, 3.5
    theta_ini, theta_fin = math.pi, 0.0

    total_curules = sum(curules_totales.values())
    radios = np.linspace(r_min, r_max, filas)
    pesos = radios / radios.sum()
    asientos_por_fila = np.floor(pesos * total_curules).astype(int)
    faltan = total_curules - asientos_por_fila.sum()
    for i in np.argsort(-radios)[:faltan]:
        asientos_por_fila[i] += 1

    # Generar puntos
    puntos, angulos = [], []
    for r, n in zip(radios, asientos_por_fila):
        if n <= 0: 
            continue
        thetas = np.linspace(theta_ini, theta_fin, n, endpoint=True)
        xs, ys = r*np.cos(thetas), r*np.sin(thetas)
        for x, y, th in zip(xs, ys, thetas):
            puntos.append({"x": float(x), "y": float(y)})
            angulos.append(th)

    # Ordenar por ángulo y asignar etiquetas en bloques
    orden_idx = np.argsort(angulos)
    puntos = [puntos[i] for i in orden_idx]
    etiquetas = []
    for llave, n in curules_totales.items():
        etiquetas.extend([llave]*n)
    for i, p in enumerate(puntos):
        p["partido"] = etiquetas[i]

    # Plot
    fig, ax = plt.subplots(figsize=(4, 4))
    for llave in curules_totales.keys():
        xs = [q["x"] for q in puntos if q["partido"] == llave]
        ys = [q["y"] for q in puntos if q["partido"] == llave]
        ax.scatter(xs, ys,
                s=35, edgecolors="k", linewidths=0.3, alpha=0.9,
                c=colores.get(llave, "#808080"), label=llave)

    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.legend(ncol=max(1, min(6, len(curules_totales))),
            loc="upper center", bbox_to_anchor=(0.5, 1.12),
            frameon=False)
    ax.set_title(f"Hemiciclo de {total_curules} curules", pad=10)

    st.pyplot(fig, clear_figure=True)



#####################



    # Descargas
    st.markdown("### Descargar resultados (solo válidos)")
    csv = df_res.to_csv(index=False).encode("utf-8")
    fname_tag = anio_label if anio_label else "sin_anio"
    st.download_button("Descargar CSV", data=csv, file_name=f"Curules_Asignados_{fname_tag}.csv", mime="text/csv")

    lines = [f"Curules asignados (solo válidos){' — ' + str(anio_label) if anio_label else ''}"]
    for _, row in df_res.iterrows():
        lines.append(f"{row['Partido']}: MR={row['MR']}, RP={row['RP']}, Total={row['Total']} (Máx={row['Máximo permitido']})")
    txt = "\n".join(lines).encode("utf-8")
    st.download_button("Descargar TXT", data=txt, file_name=f"curules_validos_{fname_tag}.txt", mime="text/plain")



else:
    st.info("Edita la tabla o carga un preset y pulsa **Calcular asignación**. Nota: partidos bajo umbral no participan en los cálculos.")