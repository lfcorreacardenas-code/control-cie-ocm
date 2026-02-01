import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de página y Estilos CSS
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def local_css():
    st.markdown(
        """
        <style>
        /* Imagen de fondo de laboratorio con overlay oscuro */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
        }
        
        /* Títulos en Naranja */
        h1, h2, h3 {
            color: #FF6B00 !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        # 

        /* Estilo para las métricas (Tarjetas) */
        [data-testid="stMetricValue"] {
            color: #4F4F4F !important;
            font-weight: bold;
        }
        
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.9);
            border-left: 5px solid #FF6B00;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        }

        /* Botones personalizados en Naranja */
        .stButton>button {
            background-color: #FF6B00 !important;
            color: white !important;
            border-radius: 20px !important;
            border: none !important;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #E65A00 !important;
            transform: scale(1.05);
        }

        /* Tabla (Editor) */
        .stDataEditor {
            background-color: white !important;
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

local_css()

# --- LÓGICA DE DATOS (Mantenemos tu lógica anterior) ---

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
    
    if 'Enviado' in df_datos.columns:
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')
    
    if 'Determinaciones' in df_datos.columns:
        df_datos['Determinaciones'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # Encabezado
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    st.markdown("##### Gestión técnica de aceites dieléctricos")

    # Métricas principales
    hoy = date.today()
    total = len(df_datos)
    pendientes = len(df_datos[df_datos['Enviado'] == False])
    eficiencia = ((total - pendientes) / total * 100) if total > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Muestras Totales", total)
    m2.metric("Pendientes de Envío", pendientes)
    m3.metric("Eficiencia Operativa", f"{eficiencia:.1f}%")
    m4.metric("🚨 Urgentes", len(df_datos[(df_datos['Enviado'] == False) & (df_datos['Fecha Requerida'].dt.date <= hoy)]))

    # Gráficos con colores personalizados
    st.write("---")
    g1, g2 = st.columns([2, 1])
    
    with g1:
        st.subheader("📊 Volumen por Cliente")
        top_clientes = df_datos['Cliente'].value_counts().reset_index().head(10)
        top_clientes.columns = ['Cliente', 'Muestras']
        fig_bar = px.bar(top_clientes, x='Muestras', y='Cliente', orientation='h',
                         color_discrete_sequence=['#FF6B00']) # Color Naranja
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix de Análisis")
        mix = df_datos['Determinaciones'].value_counts().reset_index().head(5)
        fig_pie = px.pie(mix, values='count', names='Determinaciones', 
                         color_discrete_sequence=['#FF6B00', '#4F4F4F', '#828282', '#BDBDBD'])
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    # Tabla de datos
    st.write("---")
    st.subheader("📋 Panel de Control de Reportes")
    
    # Botón Masivo
    if st.button("✅ Marcar TODO como Enviado"):
        df_datos['Enviado'] = True
        conn.update(data=df_datos)
        st.success("Sincronizado!")
        st.rerun()

    df_ver = df_datos.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Límite'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Límite']],
        use_container_width=True,
        hide_index=True,
        column_config={"Enviado": st.column_config.CheckboxColumn("Enviado ✅")},
        key="tabla_pro"
    )

    if st.button("💾 Guardar Cambios Individuales"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("Actualizado", icon="✅")

except Exception as e:
    st.error(f"Error: {e}")
