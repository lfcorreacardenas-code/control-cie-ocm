import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de página y Estilos de ALTO CONTRASTE
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def aplicar_estilos():
    st.markdown(
        """
        <style>
        /* Fondo con imagen y capa blanca (Overlay) */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
            background-attachment: fixed;
        }
        
        /* Títulos en Naranja Oscuro (Contraste alto) */
        h1, h2, h3, .stSubheader {
            color: #CC5500 !important;
            font-weight: 800 !important;
        }

        /* TEXTO DE MÉTRICAS - FORZADO A NEGRO PURO */
        [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: bold !important;
        }
        [data-testid="stMetricLabel"] {
            color: #000000 !important;
            font-size: 1.1rem !important;
            font-weight: 700 !important;
        }
        
        /* Tarjetas de métricas blancas sólidas */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #CCCCCC;
            border-left: 6px solid #FF6B00;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 4px 10px rgba(0,0,0,0.1);
        }

        /* Texto de Sidebar y general en NEGRO */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label,
        .stMarkdown, p, span, label {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# EJECUCIÓN DE LA FUNCIÓN (Corregido)
aplicar_estilos()

# --- CARGA DE DATOS ---
def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol": "Inhibidor",
        "Conteo de Partículas": "Partículas",
        "Bifenilos Policlorados": "PCB",
        "Densidad": "Densidad"
    }
    for largo, corto in mapeo.items():
        if largo in texto: return corto
    return texto

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_datos = conn.read(ttl=0)
    
    # Preparación de datos
    if 'Enviado' not in df_datos.columns:
        df_datos.insert(0, 'Enviado', False)
    df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')
    
    if 'Determinaciones' in df_datos.columns:
        df_datos['Det_Corto'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Panel de Filtros")
    lista_clientes = ["TODOS"] + sorted(df_datos['Cliente'].dropna().unique().tolist())
    cliente_sel = st.sidebar.selectbox("Seleccionar Cliente:", lista_clientes)

    # Aplicar Filtro
    df_filtrado = df_datos.copy()
    if cliente_sel != "TODOS":
        df_filtrado = df_datos[df_datos['Cliente'] == cliente_sel]

    # --- ENCABEZADO Y MÉTRICAS ---
    st.title("⚡ Monitoreo CIE - Gestión Operativa")
    
    m1, m2, m3, m4 = st.columns(4)
    total = len(df_filtrado)
    pendientes = len(df_filtrado[df_filtrado['Enviado'] == False])
    eficiencia = ((total - pendientes) / total * 100) if total > 0 else 0
    
    m1.metric("Muestras Totales", total)
    m2.metric("Por Enviar", pendientes)
    m3.metric("Eficiencia", f"{eficiencia:.1f}%")
    m4.metric("Cliente", cliente_sel if cliente_sel != "TODOS" else "General")

    # --- GRÁFICOS (TEXTO FORZADO A NEGRO) ---
    st.write("---")
    g1, g2 = st.columns([1.5, 1])
    
    with g1:
        st.subheader("📊 Análisis por Cliente")
        eje_y = 'Det_Corto' if cliente_sel != "TODOS" else 'Cliente'
        top_data = df_filtrado[eje_y].value_counts().reset_index().head(10)
        top_data.columns = [eje_y, 'Muestras']
        
        fig_bar = px.bar(top_data, x='Muestras', y=eje_y, orientation='h',
                         color_discrete_sequence=['#FF6B00'], text_auto=True,
                         template="plotly_white")
        
        fig_bar.update_layout(
            font=dict(color="#000000", size=13), # TEXTO NEGRO PARA NOMBRES
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix de Determinaciones")
        mix = df_filtrado['Det_Corto'].value_counts().reset_index()
        
        fig_pie = px.pie(mix, values='count', names='Det_Corto', 
                         color_discrete_sequence=['#FF6B00', '#222222', '#555555', '#888888'],
                         template="plotly_white")
        
        fig_pie.update_layout(
            font=dict(color="#000000", size=13), # TEXTO NEGRO PARA LEYENDA
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA ---
    st.write("---")
    st.subheader("📋 Detalle de la Operación")
    
    df_ver = df_filtrado.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Límite'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    cols_view = ['Enviado', 'Projob', 'Cliente', 'Det_Corto', 'F. Ingreso', 'F. Límite']
    
    res = st.data_editor(
        df_ver[cols_view],
        use_container_width=True,
        hide_index=True,
        column_config={"Enviado": st.column_config.CheckboxColumn("Enviado ✅")},
        key="tabla_final_v5"
    )

    if st.button("💾 Guardar y Actualizar Hoja"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        
        df_datos_save = df_datos.drop(columns=['Det_Corto'])
        conn.update(data=df_datos_save)
        st.toast("✅ Base de datos actualizada con éxito")
        st.rerun()

except Exception as e:
    st.error(f"Se detectó un inconveniente: {e}")
