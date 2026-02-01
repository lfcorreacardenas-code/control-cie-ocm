import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración y Estilos de Alto Contraste
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def aplicar_estilos():
    st.markdown(
        """
        <style>
        /* Fondo con imagen y capa blanca para resaltar texto negro */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.75)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
            background-attachment: fixed;
        }
        
        /* Títulos en Naranja Oscuro */
        h1, h2, h3, .stSubheader {
            color: #CC5500 !important;
            font-weight: 800 !important;
        }

        /* TEXTO DE MÉTRICAS - NEGRO PURO */
        [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: bold !important;
        }
        [data-testid="stMetricLabel"] {
            color: #1A1A1A !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
        }
        
        /* Tarjetas de métricas blancas sólidas */
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 1);
            border: 1px solid #DDDDDD;
            border-left: 6px solid #FF6B00;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.15);
        }

        /* Texto de la barra lateral (Sidebar) */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label {
            color: #000000 !important;
            font-weight: bold !important;
        }

        /* Texto general */
        .stMarkdown, p, span {
            color: #000000 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_os_estilos()

# --- CARGA DE DATOS ---
def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol": "Inhibidor",
        "Conteo de Partículas": "Partículas",
        "Bifenilos Policlorados": "PCB"
    }
    for largo, corto in mapeo.items():
        if largo in texto: return corto
    return texto

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_datos = conn.read(ttl=0)
    
    # Limpieza básica
    if 'Enviado' not in df_datos.columns:
        df_datos.insert(0, 'Enviado', False)
    df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')
    
    if 'Determinaciones' in df_datos.columns:
        df_datos['Determinaciones_Corto'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros de Control")
    lista_clientes = ["TODOS"] + sorted(df_datos['Cliente'].unique().tolist())
    cliente_sel = st.sidebar.selectbox("Seleccionar Cliente:", lista_clientes)

    # Aplicar Filtro
    df_filtrado = df_datos.copy()
    if cliente_sel != "TODOS":
        df_filtrado = df_datos[df_datos['Cliente'] == cliente_sel]

    # --- CUERPO PRINCIPAL ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    
    # Métricas Dinámicas
    total = len(df_filtrado)
    pendientes = len(df_filtrado[df_filtrado['Enviado'] == False])
    eficiencia = ((total - pendientes) / total * 100) if total > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Muestras Totales", total)
    m2.metric("Pendientes de Envío", pendientes)
    m3.metric("Eficiencia Operativa", f"{eficiencia:.1f}%")
    m4.metric("Cliente Seleccionado", cliente_sel if cliente_sel != "TODOS" else "Global")

    # --- GRÁFICOS ---
    st.write("---")
    g1, g2 = st.columns([1.5, 1])
    
    with g1:
        st.subheader("📊 Volumen de Muestras")
        # Si es un cliente específico, mostramos por análisis; si es global, por cliente
        eje_y = 'Determinaciones_Corto' if cliente_sel != "TODOS" else 'Cliente'
        top_data = df_filtrado[eje_y].value_counts().reset_index().head(10)
        top_data.columns = [eje_y, 'Muestras']
        
        fig_bar = px.bar(top_data, x='Muestras', y=eje_y, orientation='h',
                         color_discrete_sequence=['#FF6B00'], text_auto=True,
                         template="plotly_white")
        
        fig_bar.update_layout(
            font=dict(color="black", size=12),
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix de Análisis")
        mix = df_filtrado['Determinaciones_Corto'].value_counts().reset_index()
        
        fig_pie = px.pie(mix, values='count', names='Determinaciones_Corto', 
                         color_discrete_sequence=['#FF6B00', '#333333', '#666666', '#999999', '#CCCCCC'],
                         template="plotly_white")
        
        fig_pie.update_layout(
            font=dict(color="black", size=12),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA DE EDICIÓN ---
    st.write("---")
    st.subheader(f"📋 Detalle de Muestras: {cliente_sel}")
    
    df_ver = df_filtrado.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Límite'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    columnas_tabla = ['Enviado', 'Projob', 'Cliente', 'Determinaciones_Corto', 'F. Ingreso', 'F. Límite']
    
    res = st.data_editor(
        df_ver[columnas_tabla],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Determinaciones_Corto": "Análisis"
        },
        key="tabla_interactiva"
    )

    if st.button("💾 Guardar y Actualizar Excel"):
        # Actualizar solo las filas visibles en el DataFrame original
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        
        # Eliminar columna temporal antes de subir
        if 'Determinaciones_Corto' in df_datos.columns:
            df_datos_save = df_datos.drop(columns=['Determinaciones_Corto'])
        
        conn.update(data=df_datos_save)
        st.success("¡Datos actualizados correctamente en Google Sheets!")
        st.rerun()

except Exception as e:
    st.error(f"Error cargando el tablero: {e}")
