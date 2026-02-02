import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de página
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
        /* Texto de métricas y etiquetas en negro puro */
        [data-testid="stMetricValue"] { color: #000000 !important; font-weight: bold !important; }
        [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 700 !important; }
        
        div[data-testid="stMetric"] {
            background-color: white !important;
            border-left: 6px solid #FF6B00 !important;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
        }
        /* Sidebar con texto negro */
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #000000 !important; font-weight: bold !important;
        }
        h1, h2, h3 { color: #CC5500 !important; font-weight: 800 !important; }
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

    # Estandarización
    if 'Enviado' not in df.columns: df.insert(0, 'Enviado', False)
    df['Enviado'] = df['Enviado'].fillna(False).astype(bool)
    df['Det_Resumen'] = df['Determinaciones'].apply(abreviar_analisis)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros")
    filtro_cliente = st.sidebar.selectbox("Cliente:", ["TODOS"] + sorted(df['Cliente'].dropna().unique().tolist()))
    filtro_analisis = st.sidebar.text_input("Buscar Análisis (ej: FQ):")
    solo_pendientes = st.sidebar.checkbox("Ver solo pendientes")

    # Aplicación de filtros al DataFrame de la vista
    if filtro_cliente != "TODOS":
        df = df[df['Cliente'] == filtro_cliente]
    if filtro_analisis:
        df = df[df['Det_Resumen'].str.contains(filtro_analisis, case=False, na=False)]
    if solo_pendientes:
        df = df[df['Enviado'] == False]

    # --- MÉTRICAS ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras en Vista", len(df))
    m2.metric("Pendientes", len(df[df['Enviado'] == False]))
    m3.metric("Filtro Actual", filtro_cliente if filtro_cliente != "TODOS" else "Global")

    # --- GRÁFICOS CORREGIDOS (NEGRO NORMAL) ---
    st.write("---")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("📊 Volumen de Muestras")
        eje_y = 'Det_Resumen' if filtro_cliente != "TODOS" else 'Cliente'
        data_bar = df[eje_y].value_counts().reset_index().head(10)
        
        fig_bar = px.bar(data_bar, x='count', y=eje_y, orientation='h', 
                         color_discrete_sequence=['#FF6B00'], text_auto=True, template="plotly_white")
        
        fig_bar.update_layout(
            font=dict(color="#000000", size=12), # Negro normal global
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=150) # Espacio para nombres largos de clientes
        )
        # Forzar color negro en las etiquetas de los clientes (eje Y)
        fig_bar.update_yaxes(tickfont=dict(color="#000000", size=11, family="Arial"))
        fig_bar.update_xaxes(tickfont=dict(color="#000000"))
        
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.subheader("🔬 Mix de Análisis")
        data_pie = df['Det_Resumen'].value_counts().reset_index()
        
        fig_pie = px.pie(data_pie, values='count', names='Det_Resumen', 
                         color_discrete_sequence=['#FF6B00', '#333333', '#666666', '#999999'],
                         template="plotly_white")
        
        fig_pie.update_layout(
            # Negro normal para la leyenda y etiquetas
            font=dict(color="#000000", size=12, family="Arial"),
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            legend=dict(
                font=dict(color="#000000", size=11), # Forzar negro en leyenda
                bgcolor="rgba(255, 255, 255, 0.6)", # Fondo blanco sutil para legibilidad
                bordercolor="#DDDDDD",
                borderwidth=1
            )
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent', textfont=dict(color="white"))
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA Y ACCIONES ---
    st.write("---")
    st.subheader("📋 Gestión de Envío")
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("✅ Marcar VISTA como Enviado"):
            df_original.loc[df.index, 'Enviado'] = True
            conn.update(data=df_original.drop(columns=['Det_Resumen'], errors='ignore'))
            st.rerun()

    # Editor de datos
    res = st.data_editor(
        df[['Enviado', 'Projob', 'Cliente', 'Det_Resumen']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Det_Resumen": "Análisis Simplificado"
        },
        key="editor_v6"
    )

    if st.button("💾 Guardar Cambios"):
        for i, row in res.iterrows():
            df_original.loc[df_original['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_original.drop(columns=['Det_Resumen'], errors='ignore'))
        st.toast("Actualizado")
        st.rerun()

except Exception as e:
    st.error(f"Error en tablero: {e}")

