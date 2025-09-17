import math
from collections import Counter, defaultdict
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import math
import io, json


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

st.sidebar.title("Navegación:")
pagina = st.sidebar.radio("Elige un programa:", ["Cálculo de sobrerrepresentación", "Reparto de curules por RP"])

if pagina == "Cálculo de sobrerrepresentación":
    st.title("Ejecutando Cálculo de sobrerrepresentación")
    # tu código del primer programa aquí
    st.set_page_config(page_title="Asignación de curules (MX)", layout="wide")

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
        col_plot, _ = st.columns([1, 2])
        with col_plot:
            fig, ax = plt.subplots(figsize=(4.6, 3.2), dpi=150)

            marker_size = max(10, int(1400 / max(1, total_curules)))

            for llave in curules_totales.keys():
                xs = [q["x"] for q in puntos if q["partido"] == llave]
                ys = [q["y"] for q in puntos if q["partido"] == llave]
                ax.scatter(
                    xs, ys,
                    s=marker_size,
                    edgecolors="k",
                    linewidths=0.25,
                    alpha=0.95,
                    c=colores.get(llave, "#808080"),
                    label=llave
                )

            ax.set_aspect("equal", adjustable="box")
            ax.axis("off")

            # título bien arriba
            ax.set_title(
                f"Distribución de curules por partido",
                pad=2, fontsize=12, weight="bold"
            )

            # leyenda abajo centrada
            ax.legend(
                ncol=min(6, len(curules_totales)),
                loc="lower center",
                bbox_to_anchor=(0.5, -0.15),
                frameon=False,
                fontsize=8,
                markerscale=0.8,
                handlelength=1.0,
                handletextpad=0.4,
                columnspacing=0.8
            )

            plt.subplots_adjust(top=0.9, bottom=0.25, left=0.05, right=0.95)

            st.pyplot(fig, clear_figure=True, use_container_width=False)





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





elif pagina == "Reparto de curules por RP":
    PARTY_ORDER = ["PAN","PRI","PRD","PT","PVEM","MC","MORENA"]

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

    def df_from_presets(votos: dict, mr: dict) -> pd.DataFrame:
        """Une claves de votos y MR en un DataFrame Partido/Votos/MR (faltantes=0) respetando orden fijo."""
        partidos = list({*votos.keys(), *mr.keys()})
        # orden fijo + extras
        ordered = [p for p in PARTY_ORDER if p in partidos] + [p for p in partidos if p not in PARTY_ORDER]
        rows = [{"Partido": p, "Votos": int(votos.get(p, 0)), "MR": int(mr.get(p, 0))} for p in ordered]
        return pd.DataFrame(rows)

    st.set_page_config(page_title="Asignación de curules (MX)", layout="wide")

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

    ### ---------------------------------------------
    # PARÁMETROS
    # ---------------------------------------------
    PRESETS = {
        2024: {
            "anio": 2024,
            "votos": {
                "PRIMERA": {"PAN": 1886007, "PRI": 1162528, "PT": 517448, "PVEM": 704142, "MC": 1774320, "MORENA": 4519464, "PRD": 172802},
                "SEGUNDA": {"PAN": 2682634, "PRI": 1521683, "PT": 417610, "PVEM": 997339, "MC": 1330554, "MORENA": 3722803, "PRD": 202004},
                "TERCERA": {"PAN": 1320664, "PRI": 945965, "PT": 810826, "PVEM": 1266771, "MC": 960131, "MORENA": 5433356, "PRD": 304534},
                "CUARTA":  {"PAN": 2305701, "PRI": 1267427, "PT": 905405, "PVEM": 1128025, "MC": 1234896, "MORENA": 5755609, "PRD": 426966},
                "QUINTA":  {"PAN": 1851623, "PRI": 1724639, "PT": 602275, "PVEM": 896009, "MC": 1195620, "MORENA": 4846725, "PRD": 342869},
            },
            "mr": {"PAN": 31, "PRI": 10, "MC": 1, "MORENA": 182, "PVEM": 40, "PT": 34, "PRD": 1},
            "votos_eliminar": {
                "NoRegistrados": 49305,
                "Independientes": 72012,
                "Nulos": 2189171
            }
        }
    }

    # ------------------------------
    # Encabezado y carga de presets (arriba)
    # ------------------------------
    st.title("Calculadora de diputaciones por Representación Proporcional.")

    colA, colB = st.columns([2,3])
    with colA:
        st.subheader("Cargar datos predefinidos")
        st.markdown("Selecciona un preset para cargar votos por circunscripción y curules de Mayoría Relativa.")
        preset_choice = st.selectbox("Elegir año", [2024], index=0, key="preset_choice_main")
        load = st.button("Cargar datos predefinidos", type="primary", use_container_width=True)

    with colB:
        st.subheader("Parámetros")
        st.markdown("El cálculo se hará con base en 300 curules de MR más el parámetro elegido.")
        seats_rp = st.number_input("Curules de RP", min_value=0, max_value=200, value=200, step=1, help="Representación Proporcional")
        st.markdown("---")
        st.subheader("Votos no válidos / a eliminar")
        if "nulos" not in st.session_state: st.session_state["nulos"] = 0
        if "no_reg" not in st.session_state: st.session_state["no_reg"] = 0
        if "otros_excl" not in st.session_state: st.session_state["otros_excl"] = 0
        nulos = st.number_input("Nulos", min_value=0, value=st.session_state["nulos"], step=1000, key="nulos_input_main")
        no_reg = st.number_input("No registrados", min_value=0, value=st.session_state["no_reg"], step=1000, key="noreg_input_main")
        otros_excl = st.number_input("Otros excluidos (Independientes, etc.)", min_value=0, value=st.session_state["otros_excl"], step=1000, key="otros_input_main")

    # ------------------------------
    # Estado inicial
    # ------------------------------
    if "df_data" not in st.session_state:
        st.session_state["df_data"] = pd.DataFrame({
            "Partido": PARTY_ORDER,
            "PRIMERA": [0]*len(PARTY_ORDER),
            "SEGUNDA": [0]*len(PARTY_ORDER),
            "TERCERA": [0]*len(PARTY_ORDER),
            "CUARTA":  [0]*len(PARTY_ORDER),
            "QUINTA":  [0]*len(PARTY_ORDER),
            # "Votos":   [0]*len(PARTY_ORDER),
            "MR":      [0]*len(PARTY_ORDER),
        })

    for k, v in [("anio_actual", None), ("nulos", 0), ("no_reg", 0), ("otros_excl", 0), ("votos_por_circun", {})]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ------------------------------
    # Cargar preset (circunscripciones + nacional)
    # ------------------------------
    if load:
        preset = PRESETS.get(preset_choice)
        if preset:
            votos_circ = preset["votos"]                # dict: {CIRCUN: {PARTIDO: votos}}
            mr_dict    = preset.get("mr", {})           # dict: {PARTIDO: MR}

            # Guarda detalle por circunscripción
            st.session_state["votos_por_circun"] = votos_circ

            # Construir DF con columnas PRIMERA..QUINTA, Votos (suma) y MR
            circ_cols = ["PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA"]
            # Recolectar todos los partidos presentes
            partidos_presentes = set(PARTY_ORDER)
            for c in circ_cols:
                partidos_presentes |= set(votos_circ.get(c, {}).keys())
            partidos_ordenados = [p for p in PARTY_ORDER if p in partidos_presentes] + \
                                sorted([p for p in partidos_presentes if p not in PARTY_ORDER])

            filas = []
            for p in partidos_ordenados:
                fila = {"Partido": p}
                total_p = 0
                for c in circ_cols:
                    v = int(votos_circ.get(c, {}).get(p, 0))
                    fila[c] = v
                    total_p += v
                # fila["Votos"] = total_p
                fila["MR"]    = int(mr_dict.get(p, 0))
                filas.append(fila)

            df = pd.DataFrame(filas)
            st.session_state["df_data"] = sort_parties_df(df)

            # Votos a eliminar (acepta variantes y agrupa el resto en 'otros_excl')
            ve = preset.get("votos_eliminar", {})
            nulos  = int(ve.get("Nulos", 0))
            no_reg = int(ve.get("NoRegistrados", ve.get("No registrados", 0)))
            otros  = sum(int(v) for k, v in ve.items() if k not in ("Nulos", "NoRegistrados", "No registrados"))

            st.session_state["nulos"] = nulos
            st.session_state["no_reg"] = no_reg
            st.session_state["otros_excl"] = otros

            st.session_state["anio_actual"] = preset.get("anio", None)
            st.toast(f"Preset {preset_choice} cargado")

    # ------------------------------
    # Tabla de edición con orden fijo
    # ------------------------------
    st.markdown("### Votos por partido y circunscripción")
    st.write("La tabla mantiene un **orden fijo de partidos**. Puedes editar valores o agregar filas adicionales.")
    data = st.data_editor(
        sort_parties_df(st.session_state["df_data"]),
        num_rows="dynamic",
        use_container_width=True,
        key="tabla_partidos",
    )

    # Persistir en sesión cualquier edición hecha en la tabla
    if isinstance(data, pd.DataFrame):
        st.session_state["df_data"] = sort_parties_df(data)

    # === Continúa en el mismo archivo de tu app Streamlit ===

    # ------------------------------
    # Botón de cálculo 
    # ------------------------------
    st.markdown("---")
    calcular = st.button("Asignación de Representación Proporcional", type="primary", use_container_width=True)

    if calcular:
        # Reconstruir insumos desde la tabla editable y los controles
        circ_cols = ["PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA"]
        df_in = sort_parties_df(st.session_state["df_data"]).fillna(0)

        # Dict votos_por_circun: {CIRC: {PARTIDO: votos}}
        votos_por_circun = {
            circ: {str(row["Partido"]): int(row[circ]) for _, row in df_in.iterrows() if circ in df_in.columns}
            for circ in circ_cols
        }

        # Dict curules_mr: {PARTIDO: MR}
        curules_mr = {str(row["Partido"]): int(row["MR"]) for _, row in df_in.iterrows() if "MR" in df_in.columns}

        # Dict votos_eliminar según tus inputs (usa las mismas llaves que tu código)
        votos_eliminar = {
            "No registrados": int(st.session_state.get("no_reg", 0)),
            "Independientes": int(st.session_state.get("otros_excl", 0)),
            "Nulos": int(st.session_state.get("nulos", 0)),
        }

        # =======================
        # =======================
        curules = int(seats_rp)  # usa el número de RP del control
        curules_por_circ = int(curules // 5)
        umbral = 0.03  # 3%

        # 1. Suma de votos nacionales por partido
        # votos_por_partido = {
        #     "PAN": sum(votos_por_circun[c].get("PAN", 0) for c in votos_por_circun),
        #     "PRI": sum(votos_por_circun[c].get("PRI", 0) for c in votos_por_circun),
        #     "MC": sum(votos_por_circun[c].get("MC", 0) for c in votos_por_circun),
        #     "MORENA": sum(votos_por_circun[c].get("MORENA", 0) for c in votos_por_circun),
        #     "PVEM": sum(votos_por_circun[c].get("PVEM", 0) for c in votos_por_circun),
        #     "PT": sum(votos_por_circun[c].get("PT", 0) for c in votos_por_circun),
        #     "PRD": sum(votos_por_circun[c].get("PRD", 0) for c in votos_por_circun),
        # }
        votos_por_partido = {
        p: sum(votos_por_circun[c].get(p, 0) for c in votos_por_circun)
        for p in df_in["Partido"]
        }

        # 2. Total de votos emitidos
        votacion_total_emitida = sum(votos_por_partido.values()) + sum(votos_eliminar.values())

        # 3. Votación válida emitida
        votacion_valida_emitida = votacion_total_emitida - votos_eliminar["Nulos"] - votos_eliminar["No registrados"]

        # 4. Partidos con derecho (>= 3%)
        partidos_con_derecho = {
            p: v / votacion_valida_emitida
            for p, v in votos_por_partido.items()
            if v / votacion_valida_emitida >= 0.03
        }

        # 5. Votos de partidos con derecho
        votos_partido_con_derecho = {p: v for p, v in votos_por_partido.items() if p in partidos_con_derecho}

        # 6. Votación nacional emitida para repartir RP
        votacion_nacional_emitida = (
            votacion_total_emitida
            - sum(votos_eliminar.values())
            - sum(v for p, v in votos_por_partido.items() if p not in partidos_con_derecho)
        )

        # 7. Cociente natural
        cociente_natural = votacion_nacional_emitida / curules

        # Asignación por Hare
        asignacion_curules = {p: int(v // cociente_natural) for p, v in votos_partido_con_derecho.items()}
        curules_asignadas = sum(asignacion_curules.values())
        curules_restantes = curules - curules_asignadas
        restos = {
            p: votos_partido_con_derecho[p] - asignacion_curules[p] * cociente_natural
            for p in asignacion_curules
        }
        partidos_ordenados = sorted(restos.items(), key=lambda x: x[1], reverse=True)
        for i in range(curules_restantes):
            partido = partidos_ordenados[i][0]
            asignacion_curules[partido] += 1

        # Totales y tope de sobrerrepresentación
        curules_totales = {
            p: asignacion_curules.get(p, 0) + curules_mr.get(p, 0)
            for p in set(asignacion_curules) | set(curules_mr)
        }
        curules_maximas = {
            p: int(((v / votacion_nacional_emitida) + 0.08) * (300 + curules))
            for p, v in votos_partido_con_derecho.items()
        }
        sobrerepresentados = {
            p: curules_totales[p]
            for p in curules_totales
            if p in partidos_con_derecho and curules_totales[p] > curules_maximas.get(p, 0)
        }

        votos_por_curul_sobrerepresentados = {
            p: votos_partido_con_derecho[p] / (asignacion_curules[p] - (curules_totales[p] - curules_maximas[p]))
            for p in sobrerepresentados
        }
        resultado_division = {
            partido: {
                circ: votos_por_circun[circ][partido] / votos_por_curul_sobrerepresentados[partido]
                for circ in votos_por_circun
            }
            for partido in votos_por_curul_sobrerepresentados
        }
        curules_por_circun_sobrerep_entero = {
            partido: {circ: int(valor) for circ, valor in circuns.items()}
            for partido, circuns in resultado_division.items()
        }
        for partido, circuns in curules_por_circun_sobrerep_entero.items():
            suma_curules = sum(circuns.values())
            if suma_curules < (asignacion_curules[partido] - (curules_totales[partido] - curules_maximas[partido])):
                faltan = (asignacion_curules[partido] - (curules_totales[partido] - curules_maximas[partido])) - suma_curules
                restos_ordenados = sorted(
                    resultado_division[partido].items(),
                    key=lambda x: x[1] - int(x[1]),
                    reverse=True
                )
                for i in range(faltan):
                    circ = restos_ordenados[i][0]
                    curules_por_circun_sobrerep_entero[partido][circ] += 1

        nuevas_diputaciones_por_asignar = curules - sum(
            sum(curules_por_circun_sobrerep_entero[p].values()) for p in sobrerepresentados
        )
        nueva_votacion_nacional_efectiva = votacion_nacional_emitida - sum(
            votos_partido_con_derecho[p] for p in sobrerepresentados
        )
        cociente_natural_ajustado = nueva_votacion_nacional_efectiva / nuevas_diputaciones_por_asignar

        partidos_no_sobrerepresentados = [p for p in asignacion_curules if p not in sobrerepresentados]

        votos_por_curul_no_sobrerep = {
            p: int(votos_partido_con_derecho[p] / cociente_natural_ajustado)
            for p in partidos_no_sobrerepresentados
        }
        suma_curules_no_sobrerep = sum(votos_por_curul_no_sobrerep.values())
        if suma_curules_no_sobrerep < nuevas_diputaciones_por_asignar:
            faltan_no_sobrerep = nuevas_diputaciones_por_asignar - suma_curules_no_sobrerep
            restos_no_sobrerep = {
                p: (votos_partido_con_derecho[p] / cociente_natural_ajustado)
                - int(votos_partido_con_derecho[p] / cociente_natural_ajustado)
                for p in partidos_no_sobrerepresentados
            }
            partidos_ordenados_no_sobrerep = sorted(restos_no_sobrerep.items(), key=lambda x: x[1], reverse=True)
            for i in range(faltan_no_sobrerep):
                partido = partidos_ordenados_no_sobrerep[i][0]
                votos_por_curul_no_sobrerep[partido] += 1

        votacion_por_circun_menos_sobre = {
            circ: sum(
                votos_por_circun[circ][p]
                for p in votos_por_circun[circ]
                if p in partidos_con_derecho and p not in sobrerepresentados
            )
            for circ in votos_por_circun
        }
        curules_remanente = {
            circ: 40 - sum(curules_por_circun_sobrerep_entero[p][circ] for p in sobrerepresentados)
            for circ in (next(iter(curules_por_circun_sobrerep_entero.values())).keys()
                        if len(curules_por_circun_sobrerep_entero) > 0 else votos_por_circun.keys())
        }
        cociente_distribucion = {
            circ: votacion_por_circun_menos_sobre[circ] / curules_remanente[circ]
            for circ in votacion_por_circun_menos_sobre
        }
        votos_multiplicados_por_cociente = {
            partido: {
                circ: votos_por_circun[circ][partido] / cociente_distribucion[circ]
                for circ in votos_por_circun
            }
            for partido in partidos_no_sobrerepresentados
        }
        curules_por_circun_no_sobrerep_entero = {
            partido: {circ: int(valor) for circ, valor in circuns.items()}
            for partido, circuns in votos_multiplicados_por_cociente.items()
        }
        curules_por_partido_asignadas = {
            partido: sum(curules_por_circun_no_sobrerep_entero[partido][circ]
                        for circ in curules_por_circun_no_sobrerep_entero[partido])
            for partido in curules_por_circun_no_sobrerep_entero
        }
        diferencia_votos_curul_vs_curules_asignadas = {
            partido: votos_por_curul_no_sobrerep[partido] - curules_por_partido_asignadas.get(partido, 0)
            for partido in votos_por_curul_no_sobrerep
        }
        curules_por_circun_todos = {**curules_por_circun_no_sobrerep_entero, **curules_por_circun_sobrerep_entero}
        curules_totales_por_circun = {
            circ: sum(curules_por_circun_todos[p][circ] for p in curules_por_circun_todos)
            for circ in circ_cols
        }
        cociente_por_curules = {
            partido: {
                circ: cociente_distribucion[circ] * curules_por_circun_no_sobrerep_entero[partido][circ]
                for circ in curules_por_circun_no_sobrerep_entero[partido]
            }
            for partido in curules_por_circun_no_sobrerep_entero
        }
        votos_por_circun_no_sobrerep = {
            partido: {circ: votos_por_circun[circ][partido] for circ in votos_por_circun}
            for partido in partidos_no_sobrerepresentados
        }
        diferencia_votos_cociente = {
            partido: {
                circ: votos_por_circun_no_sobrerep[partido][circ] - cociente_por_curules[partido][circ]
                for circ in votos_por_circun_no_sobrerep[partido]
            }
            for partido in votos_por_circun_no_sobrerep
        }
        diferencia_votos_cociente_ordenado = {
            partido: sorted(circuns.items(), key=lambda x: x[1], reverse=True)
            for partido, circuns in diferencia_votos_cociente.items()
        }
        partidos_ordenados_por_votos = sorted(
            diferencia_votos_cociente_ordenado.keys(),
            key=lambda p: votos_por_partido[p],
            reverse=True
        )
        diferencia_votos_cociente_ordenado_sorted = {p: diferencia_votos_cociente_ordenado[p] for p in partidos_ordenados_por_votos}
        df_diferencia_votos_cociente = pd.DataFrame.from_dict(
            {p: dict(circuns) for p, circuns in diferencia_votos_cociente_ordenado_sorted.items()}
        )
        prioridades = df_diferencia_votos_cociente.rank(ascending=False)
        curules_por_circun_todos = {**curules_por_circun_no_sobrerep_entero, **curules_por_circun_sobrerep_entero}
        df_curules_por_circun = pd.DataFrame({p: curules_por_circun_todos[p] for p in curules_por_circun_todos}).T

        # Diferencias a repartir
        for partido, extras in diferencia_votos_curul_vs_curules_asignadas.items():
            orden_circuns = prioridades[partido].sort_values().index.tolist()
            while extras > 0:
                asignado_en_esta_ronda = False
                for circun in orden_circuns:
                    if extras == 0:
                        break
                    if curules_totales_por_circun[circun] < 40:
                        df_curules_por_circun.loc[partido, circun] += 1
                        curules_totales_por_circun[circun] += 1
                        extras -= 1
                        asignado_en_esta_ronda = True
                if not asignado_en_esta_ronda:
                    break

        # ------------------------------
        # Salidas en pantalla
        # ------------------------------

        # Coloca los recuadros en dos columnas, uno junto al otro
        col1, col2 = st.columns(2, gap="small")

        with col1:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
                    color: #fff;
                    padding: 18px 32px;
                    border-radius: 14px;
                    box-shadow: 0 4px 16px rgba(30,60,114,0.12);
                    font-size: 1.2em;
                    font-weight: 600;
                    margin-bottom: 18px;
                    display: inline-block;
                    border: 2px solid #fff;
                ">
                    <span style="font-size:1.1em;letter-spacing:0.5px;">🧮 Votos necesarios para obtener un curul:</span>
                    <br>
                    <span style="font-size:1.5em;">{cociente_natural:,.2f}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            if sobrerepresentados:
                partidos_sobre = ", ".join(
                f"{p} (+{curules_totales[p] - curules_maximas[p]})"
                for p in sobrerepresentados
                )
                st.markdown(
                f"""
                <div style="
                    background: linear-gradient(90deg, #ff512f 0%, #f09819 100%);
                    color: #fff;
                    padding: 18px 32px;
                    border-radius: 14px;
                    box-shadow: 0 4px 16px rgba(240,152,25,0.18);
                    font-size: 1.2em;
                    font-weight: 700;
                    margin-bottom: 18px;
                    display: inline-block;
                    border: 2px solid #fff;
                ">
                    <span style="font-size:1.1em;letter-spacing:0.5px;">⚠️ Sobrerepresentación</span>
                    <br>
                    <span style="font-size:1.05em; font-weight:600;">
                    Partidos sobrerepresentados: {partidos_sobre}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
                )
            else:
                st.markdown(
                """
                <div style="
                    background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
                    color: #fff;
                    padding: 18px 32px;
                    border-radius: 14px;
                    box-shadow: 0 4px 16px rgba(240,152,25,0.18);
                    font-size: 1.2em;
                    font-weight: 700;
                    margin-bottom: 18px;
                    display: inline-block;
                    border: 2px solid #fff;
                ">
                    <span style="font-size:1.1em;letter-spacing:0.5px;">⚠️ Atención</span>
                    <br>
                    <span style="font-size:1.05em; font-weight:600;">
                    No hay sobrerepresentación.
                    </span>
                </div>
                """,
                unsafe_allow_html=True
                )


        st.subheader("Curules por circunscripción y partido (RP)")
        st.dataframe(df_curules_por_circun.astype(int), use_container_width=True)

        # Mostrar resumen por partido en 5 columnas
        st.subheader("Resumen por partido")

        # Calcular totales finales por partido
        resumen_partidos = []
        for partido in sort_parties_df(df_in)["Partido"]:
            votos = votos_por_partido.get(partido, 0)
            porcentaje = votos / votacion_valida_emitida if votacion_valida_emitida else 0
            curules_mr_val = curules_mr.get(partido, 0)
            curules_rp_val = df_curules_por_circun.loc[partido].sum() if partido in df_curules_por_circun.index else 0
            curules_total = curules_mr_val + curules_rp_val
            curules_max = curules_maximas.get(partido, 0)
            resumen_partidos.append({
                "Partido": partido,
                "Votos": votos,
                "% Válida": f"{porcentaje:.2%}",
                "Curules MR": curules_mr_val,
                "Curules RP": curules_rp_val,
                "Curules Totales": curules_total,
                "Curules Máximas": curules_max if curules_max else "N/A"
            })
        

        df_resumen = pd.DataFrame(resumen_partidos)
        df_resumen = sort_parties_df(df_resumen)
        
        cols = st.columns(6)
        with cols[0]:
            st.markdown("**Partido**")
            for p in df_resumen["Partido"]:
                st.markdown(f"{p}")
        with cols[1]:
            st.markdown("**Votos**")
            for v in df_resumen["Votos"]:
                st.markdown(f"{v:,}")
        with cols[2]:
            st.markdown("**Curules MR**")
            for mr in df_resumen["Curules MR"]:
                st.markdown(f"{mr}")
        with cols[3]:
            st.markdown("**Curules RP**")
            for rp in df_resumen["Curules RP"]:
                st.markdown(f"{rp}")
        with cols[4]:
            st.markdown("**Curules Totales**")
            for total in df_resumen["Curules Totales"]:
                st.markdown(f"{total}")
        with cols[5]:
            st.markdown("**Curules Máximas**")
            for max in df_resumen["Curules Máximas"]:
                st.markdown(f"{max}")



        st.markdown("Puedes descargar el resumen y los parámetros usados en un archivo CSV para análisis o respaldo.")
        # Botón para descargar el resumen en CSV
        # Unir resumen y votos por partido/circunscripción en un solo CSV
        df_votos = sort_parties_df(df_in.copy())
        # Renombrar columnas de votos para evitar colisión
        votos_cols = [c for c in df_votos.columns if c not in ["Partido", "MR"]]
        df_votos_renamed = df_votos.rename(columns={col: f"Votos {col}" for col in votos_cols})
        # Unir por "Partido"
        df_todo = pd.merge(df_resumen, df_votos_renamed, on="Partido", how="outer")
        # Agregar parámetros como filas al final
        parametros = {
            "Curules RP": seats_rp,
            "Nulos": st.session_state.get("nulos", 0),
            "No registrados": st.session_state.get("no_reg", 0),
            "Otros excluidos": st.session_state.get("otros_excl", 0),
            "Curules MR": curules_mr,
        }
        # Convertir parámetros a DataFrame de una columna
        df_param = pd.DataFrame(list(parametros.items()), columns=["Parámetro", "Valor"])
        # Convertir ambos a CSV y unir con separador claro
        csv_todo = df_todo.to_csv(index=False, encoding='utf-8')
        csv_param = df_param.to_csv(index=False, encoding='utf-8')
        csv_final = csv_todo + "\n\n# Parámetros usados\n" + csv_param
        st.download_button(
            label="Descargar CSV",
            data=csv_final,
            file_name="AsignacionRP_Simulacion.csv",
            mime="text/csv",
            use_container_width=False,
            help="Descarga el resumen y parámetros en un solo archivo.",
            key="descargar_csv_btn"
        )
        # Botón para descargar el resumen en TXT
        txt_final = df_todo.to_string(index=False) + "\n\n# Parámetros usados\n" + df_param.to_string(index=False)
        st.download_button(
            label="Descargar TXT",
            data=txt_final,
            file_name="AsignacionRP_Simulacion.txt",
            mime="text/plain",
            use_container_width=False,
            help="Descarga el resumen y parámetros en un archivo de texto.",
            key="descargar_txt_btn"
        )
        st.markdown(
            """
            <style>
            button[data-testid="descargar_csv_btn"] {
                background: linear-gradient(90deg, #ff512f 0%, #f09819 100%) !important;
                color: #fff !important;
                font-weight: bold !important;
                border-radius: 8px !important;
                padding: 0.3em 1.2em !important;
                font-size: 1.1em !important;
                border: 2px solid #fff !important;
                box-shadow: 0 2px 8px rgba(240,152,25,0.18) !important;
                margin-top: 0.5em !important;
            }
            button[data-testid="descargar_txt_btn"] {
                background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%) !important;
                color: #fff !important;
                font-weight: bold !important;
                border-radius: 8px !important;
                padding: 0.3em 1.2em !important;
                font-size: 1.1em !important;
                border: 2px solid #fff !important;
                box-shadow: 0 2px 8px rgba(30,60,114,0.12) !important;
                margin-top: 0.5em !important;
                margin-left: 0.5em !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )