import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# -------------------------------------------------
# Configuración de la página
# -------------------------------------------------
st.set_page_config(
    page_title="Dashboard Integral — UEBA y Biomed",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Carga de datos unificada
# -------------------------------------------------
@st.cache_data
def load_ueba_data():
    possible_paths = [
        Path("ueba_telemetry.csv"),
        Path("ueba_telemetry_5000.csv"),
        Path("/home/workdir/attachments/ueba_telemetry.csv"),
        Path("data/ueba_telemetry.csv"),
    ]
    for p in possible_paths:
        if p.exists():
            df = pd.read_csv(p)
            break
    else:
        st.error("No se encontró el archivo ueba_telemetry.csv ni ueba_telemetry_5000.csv")
        st.stop()

    df["hora"] = pd.to_datetime(df["hora_acceso"], format="%H:%M:%S", errors="coerce").dt.hour

    def severity_ueba(score):
        if score <= 40:
            return "Verde (Normal)"
        elif score <= 70:
            return "Amarilla (Observación)"
        else:
            return "Roja (Crítica)"

    df["severidad"] = df["risk_score"].apply(severity_ueba)
    return df

@st.cache_data
def load_biomed_data():
    possible_paths = [
        Path("biomed_metrics.csv"),
        Path("biomed_metrics_5000.csv"),
        Path("/home/workdir/attachments/biomed_metrics.csv"),
        Path("data/biomed_metrics.csv"),
    ]
    for p in possible_paths:
        if p.exists():
            df = pd.read_csv(p)
            break
    else:
        st.error("No se encontró el archivo biomed_metrics.csv ni biomed_metrics_5000.csv")
        st.stop()
    return df

df_ueba = load_ueba_data()
df_biomed = load_biomed_data()

# -------------------------------------------------
# Sidebar - Navegación y Filtros
# -------------------------------------------------
st.sidebar.header("🎛️ Navegación Principal")
modulo = st.sidebar.radio(
    "Selecciona el módulo",
    options=["🛡️ UEBA - Monitoreo de Identidad", "🏥 Biomed - Métricas Clínicas"]
)

st.sidebar.divider()

if modulo.startswith("🛡️"):
    st.sidebar.header("🔍 Filtros UEBA")
    roles_disponibles = ["Todos"] + sorted(df_ueba["rol"].unique().tolist())
    rol_seleccionado = st.sidebar.selectbox(
        "Filtrar por rol de usuario",
        options=roles_disponibles,
        index=0
    )

    ventana_horaria = st.sidebar.selectbox(
        "Filtrar por ventana horaria",
        options=[
            "Todas las horas",
            "Madrugada (00:00 - 06:59)",
            "Mañana (07:00 - 12:59)",
            "Tarde (13:00 - 18:59)",
            "Noche (19:00 - 23:59)"
        ],
        index=0
    )

    ventanas = {
        "Todas las horas": (0, 23),
        "Madrugada (00:00 - 06:59)": (0, 6),
        "Mañana (07:00 - 12:59)": (7, 12),
        "Tarde (13:00 - 18:59)": (13, 18),
        "Noche (19:00 - 23:59)": (19, 23)
    }
    h_min, h_max = ventanas[ventana_horaria]

    # Aplicar filtros UEBA
    df_ueba_filtrado = df_ueba.copy()
    if rol_seleccionado != "Todos":
        df_ueba_filtrado = df_ueba_filtrado[df_ueba_filtrado["rol"] == rol_seleccionado]
    df_ueba_filtrado = df_ueba_filtrado[(df_ueba_filtrado["hora"] >= h_min) & (df_ueba_filtrado["hora"] <= h_max)]

else:
    st.sidebar.header("🔍 Filtros Biomed")
    organos_disponibles = ["Todos"] + sorted(df_biomed["tipo_organo"].unique().tolist())
    organo_seleccionado = st.sidebar.selectbox(
        "Filtrar por tipo de órgano",
        options=organos_disponibles,
        index=0
    )

    estados_disponibles = ["Todos"] + sorted(df_biomed["estado_clinico"].unique().tolist())
    estado_seleccionado = st.sidebar.selectbox(
        "Filtrar por estado clínico",
        options=estados_disponibles,
        index=0
    )

    # Aplicar filtros Biomed
    df_biomed_filtrado = df_biomed.copy()
    if organo_seleccionado != "Todos":
        df_biomed_filtrado = df_biomed_filtrado[df_biomed_filtrado["tipo_organo"] == organo_seleccionado]
    if estado_seleccionado != "Todos":
        df_biomed_filtrado = df_biomed_filtrado[df_biomed_filtrado["estado_clinico"] == estado_seleccionado]


# -------------------------------------------------
# Renderizado del Módulo UEBA
# -------------------------------------------------
if modulo.startswith("🛡️"):
    st.title("🛡️ Dashboard UEBA — Monitoreo de Riesgo de Identidad")
    st.markdown("**Módulo 1**: Análisis de telemetría y comportamiento de usuarios")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Usuarios filtrados", len(df_ueba_filtrado))
    with col2:
        st.metric("🟢 Normal", len(df_ueba_filtrado[df_ueba_filtrado["severidad"] == "Verde (Normal)"]))
    with col3:
        st.metric("🟡 Observación", len(df_ueba_filtrado[df_ueba_filtrado["severidad"] == "Amarilla (Observación)"]))
    with col4:
        st.metric("🔴 Crítica", len(df_ueba_filtrado[df_ueba_filtrado["severidad"] == "Roja (Crítica)"]))

    st.divider()

    # Pestañas solicitadas
    tab_tendencia, tab_dispersion, tab_3d = st.tabs([
        "📈 Líneas de Tendencia Temporal",
        "📉 Gráfico de Dispersión",
        "🌐 Modelo 3D Interactivo"
    ])

    with tab_tendencia:
        st.subheader("📈 Tendencia de Risk Score por Hora de Acceso")
        if len(df_ueba_filtrado) == 0:
            st.warning("No hay datos disponibles con los filtros actuales.")
        else:
            df_tendencia = df_ueba_filtrado.groupby("hora", as_index=False)["risk_score"].mean()
            fig_tend = px.line(
                df_tendencia, x="hora", y="risk_score", markers=True,
                labels={"hora": "Hora del día (0-23)", "risk_score": "Risk Score Promedio"},
                title="Evolución temporal del Risk Score promedio por hora"
            )
            fig_tend.update_layout(height=500, template="plotly_white")
            st.plotly_chart(fig_tend, use_container_width=True)

    with tab_dispersion:
        st.subheader("📉 Gráfico de Dispersión: Volumen de Descarga vs Risk Score")
        if len(df_ueba_filtrado) == 0:
            st.warning("No hay datos disponibles con los filtros actuales.")
        else:
            color_map = {
                "Verde (Normal)": "#2ecc71",
                "Amarilla (Observación)": "#f1c40f",
                "Roja (Crítica)": "#e74c3c"
            }
            fig = px.scatter(
                df_ueba_filtrado, x="volumen_descarga_mb", y="risk_score", color="severidad",
                color_discrete_map=color_map,
                hover_data={"user_id": True, "rol": True, "hora_acceso": True, "ubicacion_ip": True,
                            "isolation_forest_score": ":.3f", "z_score_temporal": ":.3f",
                            "volumen_descarga_mb": ":.1f", "risk_score": True, "severidad": False},
                labels={"volumen_descarga_mb": "Volumen de descarga (MB)", "risk_score": "Risk Score (0-100)", "severidad": "Nivel de severidad"},
                category_orders={"severidad": ["Verde (Normal)", "Amarilla (Observación)", "Roja (Crítica)"]},
                title=f"Volumen de descarga vs Risk Score | Rol: {rol_seleccionado} | Horario: {ventana_horaria}"
            )
            fig.update_traces(marker=dict(size=14, opacity=0.85, line=dict(width=1, color="#2c3e50")))
            fig.add_hline(y=40, line_dash="dash", line_color="#27ae60", line_width=2, annotation_text="Umbral 40", annotation_position="bottom right")
            fig.add_hline(y=70, line_dash="dash", line_color="#e67e22", line_width=2, annotation_text="Umbral 70", annotation_position="top right")
            fig.update_layout(height=550, template="plotly_white", legend_title_text="Severidad", yaxis=dict(range=[-5, 105]), font=dict(family="Segoe UI, Arial", size=13))
            st.plotly_chart(fig, use_container_width=True)

    with tab_3d:
        st.subheader("🌐 Modelo 3D Interactivo: Volumen vs Z-Score Temporal vs Risk Score")
        if len(df_ueba_filtrado) == 0:
            st.warning("No hay datos disponibles con los filtros actuales.")
        else:
            fig_3d = px.scatter_3d(
                df_ueba_filtrado, x="volumen_descarga_mb", y="z_score_temporal", z="risk_score",
                color="severidad", color_discrete_map=color_map, opacity=0.8,
                labels={"volumen_descarga_mb": "Volumen Descarga (MB)", "z_score_temporal": "Z-Score Temporal", "risk_score": "Risk Score"},
                title="Espacio Tridimensional de Riesgo UEBA"
            )
            fig_3d.update_layout(height=650, template="plotly_white")
            st.plotly_chart(fig_3d, use_container_width=True)

    st.divider()
    
    # Menú desplegable único para mostrar/ocultar los registros
    with st.expander("📋 Ver detalle de registros UEBA", expanded=False):
        df_tabla_ueba = df_ueba_filtrado.sort_values("risk_score", ascending=False)[
            ["user_id", "rol", "hora_acceso", "ubicacion_ip",
             "volumen_descarga_mb", "isolation_forest_score",
             "z_score_temporal", "risk_score", "severidad"]
        ].reset_index(drop=True)

        def color_severidad_ueba(val):
            if "Verde" in str(val):
                return "background-color: #d5f5e3; color: #196f3d"
            elif "Amarilla" in str(val):
                return "background-color: #fcf3cf; color: #7d6608"
            elif "Roja" in str(val):
                return "background-color: #f5b7b1; color: #7b241c"
            return ""

        st.dataframe(
            df_tabla_ueba.style.map(color_severidad_ueba, subset=["severidad"]),
            use_container_width=True,
            height=400
        )


# -------------------------------------------------
# Renderizado del Módulo Biomed
# -------------------------------------------------
else:
    st.title("🏥 Dashboard Biomed — Métricas Clínicas y Biomarcadores")
    st.markdown("**Módulo 2**: Monitoreo de signos vitales, presión sistólica y biomarcadores")

    total_estudios = len(df_biomed_filtrado)
    normales = len(df_biomed_filtrado[df_biomed_filtrado["estado_clinico"] == "Normal"])
    precaucion = len(df_biomed_filtrado[df_biomed_filtrado["estado_clinico"] == "Precaución"])
    critico = len(df_biomed_filtrado[df_biomed_filtrado["estado_clinico"] == "Crítico"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Estudios filtrados", total_estudios)
    with col2:
        st.metric("🟢 Normal", normales)
    with col3:
        st.metric("🟡 Precaución", precaucion)
    with col4:
        st.metric("🔴 Crítico", critico)

    st.divider()

    # Pestañas correspondientes para el módulo Biomédico
    tab_tendencia_b, tab_dispersion_b, tab_3d_b = st.tabs([
        "📈 Líneas de Tendencia Temporal",
        "📉 Gráfico de Dispersión",
        "🌐 Modelo 3D Interactivo"
    ])

    with tab_tendencia_b:
        st.subheader("📈 Tendencia Biomarcador por Tipo de Órgano")
        if total_estudios == 0:
            st.warning("No hay datos disponibles.")
        else:
            df_tend_b = df_biomed_filtrado.groupby("tipo_organo", as_index=False)["nivel_biomarcador_mg_dl"].mean()
            fig_tend_b = px.bar(
                df_tend_b, x="tipo_organo", y="nivel_biomarcador_mg_dl", color="tipo_organo",
                labels={"tipo_organo": "Tipo de Órgano", "nivel_biomarcador_mg_dl": "Biomarcador Promedio (mg/dL)"},
                title="Nivel Promedio de Biomarcador por Órgano"
            )
            fig_tend_b.update_layout(height=500, template="plotly_white")
            st.plotly_chart(fig_tend_b, use_container_width=True)

    with tab_dispersion_b:
        st.subheader("📉 Gráfico de Dispersión: Presión Sistólica vs Frecuencia Cardíaca")
        if total_estudios == 0:
            st.warning("No hay datos biomédicos con los filtros seleccionados.")
        else:
            color_map_biomed = {
                "Normal": "#2ecc71",
                "Precaución": "#f1c40f",
                "Crítico": "#e74c3c"
            }
            fig_bio = px.scatter(
                df_biomed_filtrado, x="presion_sistolica_mmhg", y="frecuencia_cardiaca_bpm", color="estado_clinico",
                color_discrete_map=color_map_biomed,
                hover_data={"estudio_id": True, "tipo_organo": True, "saturacion_oxigeno": True,
                            "temperatura_corporal_c": True, "nivel_biomarcador_mg_dl": True, "estado_clinico": False},
                labels={"presion_sistolica_mmhg": "Presión Sistólica (mmHg)", "frecuencia_cardiaca_bpm": "Frecuencia Cardíaca (bpm)", "estado_clinico": "Estado Clínico"},
                category_orders={"estado_clinico": ["Normal", "Precaución", "Crítico"]},
                title=f"Presión Sistólica vs Frecuencia Cardíaca | Órgano: {organo_seleccionado} | Estado: {estado_seleccionado}"
            )
            fig_bio.update_traces(marker=dict(size=13, opacity=0.85, line=dict(width=1, color="#2c3e50")))
            fig_bio.update_layout(height=550, template="plotly_white", legend_title_text="Estado Clínico", font=dict(family="Segoe UI, Arial", size=13))
            st.plotly_chart(fig_bio, use_container_width=True)

    with tab_3d_b:
        st.subheader("🌐 Modelo 3D Interactivo: Temperatura vs SpO2 vs Biomarcador")
        if total_estudios == 0:
            st.warning("No hay datos disponibles.")
        else:
            fig_3d_b = px.scatter_3d(
                df_biomed_filtrado, x="temperatura_corporal_c", y="saturacion_oxigeno", z="nivel_biomarcador_mg_dl",
                color="estado_clinico", color_discrete_map=color_map_biomed, opacity=0.8,
                labels={"temperatura_corporal_c": "Temperatura (°C)", "saturacion_oxigeno": "SpO2 (%)", "nivel_biomarcador_mg_dl": "Biomarcador (mg/dL)"},
                title="Espacio Tridimensional Clínico"
            )
            fig_3d_b.update_layout(height=650, template="plotly_white")
            st.plotly_chart(fig_3d_b, use_container_width=True)

    st.divider()
    
    # Menú desplegable único para mostrar/ocultar los registros biomédicos
    with st.expander("📋 Ver detalle de registros biomédicos", expanded=False):
        df_tabla_biomed = df_biomed_filtrado.sort_values("nivel_biomarcador_mg_dl", ascending=False)[
            ["estudio_id", "tipo_organo", "frecuencia_cardiaca_bpm",
             "presion_sistolica_mmhg", "saturacion_oxigeno",
             "temperatura_corporal_c", "nivel_biomarcador_mg_dl", "estado_clinico"]
        ].reset_index(drop=True)

        def color_estado_clinico(val):
            if val == "Normal":
                return "background-color: #d5f5e3; color: #196f3d"
            elif val == "Precaución":
                return "background-color: #fcf3cf; color: #7d6608"
            elif val == "Crítico":
                return "background-color: #f5b7b1; color: #7b241c"
            return ""

        st.dataframe(
            df_tabla_biomed.style.map(color_estado_clinico, subset=["estado_clinico"]),
            use_container_width=True,
            height=400
        )