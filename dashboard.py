import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración y Estilo Visual Corregido (Contraste Alto)
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def local_css():
    st.markdown(
        """
        <style>
        /* Fondo con overlay para mejorar legibilidad general */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
        }
        
        /* Títulos en Naranja Oscuro para mejor contraste */
        h1, h2, h3, .stSubheader {
            color: #E65A00 !important; 
            font-weight: 800 !important;
        }

        /* TEXTO DE MÉTRICAS EN NEGRO (Solución al problema de visibilidad) */
        [data-testid="stMetricValue"] {
            color: #1A1A1A !important;
            font-weight: bold !important;
        }
        [data-testid="stMetricLabel"] {
            color: #333333 !important;
            font-size: 1.1rem !important;
        }
        
        div[data-testid="stMetric"] {
            background-color: white;
            border-left: 5px solid #FF6B00;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        }

        /* Texto general y etiquetas laterales */
        .stMarkdown, p, span {
            color: #262730 !important;
        }

        /* Estilo para los botones */
        .stButton>button {
            background-color: #FF6B00 !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

local_css()

# --- LÓGICA DE DATOS ---

def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol and 2,6-di-tert-Butyl Phenol by IR Manual": "Contenido de Inhibidor",
        "Conteo de Partículas en Aceite Mineral Aislante por el Contador de Partículas Automático": "Conteo de Particulas",
        "Densidad, densidad relativa y gravedad API de líquidas por densitómetro(Densidad a 15ºC)": "Densidad",
        "Bifenilos Policlorados": "PCB"
    }
    for largo, corto in mapeo.items():
        if largo in texto: return corto
    return texto

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_datos = conn.read(ttl=0)
    
    # Estandarización de columnas
    if 'Enviado' in df_datos.columns:
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')
    
    if 'Determinaciones' in df_datos.columns:
        df_datos['Determinaciones'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # --- ENCABEZADO Y MÉTRICAS ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    
    hoy = date.today()
    total = len(df_datos)
    pendientes = len(df_datos[df_datos['Enviado'] == False])
    eficiencia = ((total - pendientes) / total * 100) if total > 0 else 0
    urgentes = len(df_datos[(df_datos['Enviado'] == False) & (df_datos['Fecha Requerida'].dt.date <= hoy)].dropna(subset=['Fecha Requerida']))
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Muestras Totales", total)
    m2.metric("Pendientes", pendientes)
    m3.metric("Eficiencia", f"{eficiencia:.1f}%")
    m4.metric("🚨 Urgentes", urgentes)

    # --- GRÁFICOS CON TEXTO OSCURO ---
    st.write("---")
    g1, g2 = st.columns([2, 1])
    
    with g1:
        st.subheader("📊 Volumen por Cliente")
        top_clientes = df_datos['Cliente'].value_counts().reset_index().head(10)
        top_clientes.columns = ['Cliente', 'Muestras']
        fig_bar = px.bar(top_clientes, x='Muestras', y='Cliente', orientation='h',
                         color_discrete_sequence=['#FF6B00'], text_auto=True)
        # Ajuste de color de texto en el gráfico
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color="black"),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix de Análisis")
        mix = df_datos['Determinaciones'].value_counts().reset_index().head(5)
        fig_pie = px.pie(mix, values='count', names='Determinaciones', 
                         color_discrete_sequence=['#FF6B00', '#4F4F4F', '#828282', '#BDBDBD'])
        fig_pie.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color="black")
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA Y GUARDADO ---
    st.write("---")
    st.subheader("📋 Panel de Gestión")
    
    df_ver = df_datos.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Límite'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Límite']],
        use_container_width=True,
        hide_index=True,
        column_config={"Enviado": st.column_config.CheckboxColumn("Enviado ✅")},
        key="tabla_visible"
    )

    if st.button("💾 Sincronizar con Google Sheets"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("Base de datos actualizada", icon="✅")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
