import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración y Estética
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def aplicar_estilos():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
            background-attachment: fixed;
        }
        [data-testid="stMetricValue"] { color: #000000 !important; font-weight: bold !important; }
        [data-testid="stMetricLabel"] { color: #1A1A1A !important; font-weight: 700 !important; }
        div[data-testid="stMetric"] {
            background-color: white;
            border-left: 6px solid #FF6B00;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
        }
        /* Forzar texto negro en Sidebar */
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #000000 !important; font-weight: bold !important;
        }
        h1, h2, h3 { color: #CC5500 !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_estilos()

# --- CARGA Y MAPEO DE DATOS ---
def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol and 2,6-di-tert-Butyl Phenol by IR Manual": "Contenido de Inhibidor",
        "Conteo de Partículas en Aceite Mineral Aislante por el Contador de Partículas Automático": "Conteo de Particulas",
        "Densidad, densidad relativa y gravedad API de líquidas por densitómetro(Densidad a 15ºC)": "FQ",
        "Bifenilos Policlorados": "PCB",
        "Color ASTM": "FQ",
        "Compuestos Furanos en Líquidos Aislantes Eléctricos (HPLC)": "Furanos",
        "Número de Acidez por Titulación - Indicación Color": "FQ",
        "Rigidez Dieléctrica del Aceite": "FQ",
        "Exámen Visual de los Aceites Eléctricos Usados": "FQ",
        "Tensión Interfacial -Método del Anillo": "FQ",
        "Agua por Titulación Columetrica Karl Fischer": "FQ",
        "Apariencia": "FQ"
    }
    for largo, corto in mapeo.items():
        if largo in texto: return corto
    return texto

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_original = conn.read(ttl=0)
    df = df_original.copy()

    # Limpieza
    if 'Enviado' not in df.columns: df.insert(0, 'Enviado', False)
    df['Enviado'] = df['Enviado'].fillna(False).astype(bool)
    df['Determinaciones_Resumen'] = df['Determinaciones'].apply(abreviar_analisis)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    filtro_cliente = st.sidebar.selectbox("Filtrar por Cliente:", ["TODOS"] + sorted(df['Cliente'].unique().tolist()))
    filtro_analisis = st.sidebar.text_input("Buscar por Análisis (ej: FQ, PCB):")
    solo_pendientes = st.sidebar.checkbox("Ver solo pendientes")

    # Aplicar Filtros
    if filtro_cliente != "TODOS":
        df = df[df['Cliente'] == filtro_cliente]
    if filtro_analisis:
        df = df[df['Determinaciones_Resumen'].str.contains(filtro_analisis, case=False, na=False)]
    if solo_pendientes:
        df = df[df['Enviado'] == False]

    # --- CUERPO PRINCIPAL ---
    st.title("⚡ Monitoreo CIE - Gestión Estratégica")
    
    # Métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras en Vista", len(df))
    m2.metric("Pendientes", len(df[df['Enviado'] == False]))
    m3.metric("Cliente Seleccionado", filtro_cliente if filtro_cliente != "TODOS" else "Global")

    # Gráficos
    st.write("---")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("📊 Volumen de Muestras")
        eje_y = 'Determinaciones_Resumen' if filtro_cliente != "TODOS" else 'Cliente'
        data_chart = df[eje_y].value_counts().reset_index().head(10)
        
        fig = px.bar(data_chart, x='count', y=eje_y, orientation='h', 
                     color_discrete_sequence=['#FF6B00'], text_auto=True, template="plotly_white")
        fig.update_layout(font=dict(color="black", size=12), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig.update_yaxes(tickfont=dict(color="black", size=11))
        st.plotly_chart(fig, use_container_width=True)

    # --- SECCIÓN DE TABLA Y ACCIONES ---
    st.write("---")
    st.subheader("📋 Panel de Control")
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("✅ Marcar TODO como Enviado"):
            df_original.loc[df.index, 'Enviado'] = True
            conn.update(data=df_original.drop(columns=['Determinaciones_Resumen'], errors='ignore'))
            st.rerun()

    # Editor de tabla
    df_display = df[['Enviado', 'Projob', 'Cliente', 'Determinaciones_Resumen']].copy()
    res = st.data_editor(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={"Enviado": st.column_config.CheckboxColumn("Enviado ✅")},
        key="editor_final"
    )

    if st.button("💾 Guardar Cambios Individuales"):
        for i, row in res.iterrows():
            df_original.loc[df_original['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_original.drop(columns=['Determinaciones_Resumen'], errors='ignore'))
        st.toast("Base de datos sincronizada")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
