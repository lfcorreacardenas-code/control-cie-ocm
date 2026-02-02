import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración de página y Estilos de Alto Contraste
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def aplicar_estilos():
    st.markdown(
        """
        <style>
        /* Fondo con imagen y capa blanca (Overlay) para legibilidad */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
            background-attachment: fixed;
        }
        
        /* Títulos en Naranja CIE */
        h1, h2, h3, .stSubheader {
            color: #CC5500 !important;
            font-weight: 800 !important;
        }

        /* MÉTRICAS: Texto negro sobre fondo blanco sólido */
        [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: bold !important;
        }
        [data-testid="stMetricLabel"] {
            color: #000000 !important;
            font-size: 1.1rem !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border-left: 6px solid #FF6B00 !important;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
            padding: 15px;
        }

        /* Sidebar: Texto Negro */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label {
            color: #000000 !important;
            font-weight: bold !important;
        }
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

    # Estandarización de columnas
    if 'Enviado' not in df.columns: df.insert(0, 'Enviado', False)
    df['Enviado'] = df['Enviado'].fillna(False).astype(bool)
    df['Det_Resumen'] = df['Determinaciones'].apply(abreviar_analisis)
    
    # Asegurar que las fechas sean objetos datetime
    df['Recibido Laboratorio'] = pd.to_datetime(df['Recibido Laboratorio'], errors='coerce')
    df['Fecha Requerida'] = pd.to_datetime(df['Fecha Requerida'], errors='coerce')

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros de Control")
    lista_clientes = ["TODOS"] + sorted(df['Cliente'].dropna().unique().tolist())
    filtro_cliente = st.sidebar.selectbox("Seleccionar Cliente:", lista_clientes)
    filtro_projob = st.sidebar.text_input("Buscar Projob:")
    solo_pendientes = st.sidebar.checkbox("Ver solo pendientes")

    # Aplicar Filtros
    if filtro_cliente != "TODOS":
        df = df[df['Cliente'] == filtro_cliente]
    if filtro_projob:
        df = df[df['Projob'].str.contains(filtro_projob, case=False, na=False)]
    if solo_pendientes:
        df = df[df['Enviado'] == False]

    # --- MÉTRICAS ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras en Vista", len(df))
    m2.metric("Pendientes", len(df[df['Enviado'] == False]))
    m3.metric("Filtro Cliente", filtro_cliente if filtro_cliente != "TODOS" else "Global")

    # --- GRÁFICOS ---
    st.write("---")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("📊 Volumen por Cliente")
        eje_y = 'Det_Resumen' if filtro_cliente != "TODOS" else 'Cliente'
        data_bar = df[eje_y].value_counts().reset_index().head(10)
        
        fig_bar = px.bar(data_bar, x='count', y=eje_y, orientation='h', 
                         color_discrete_sequence=['#FF6B00'], text_auto=True, template="plotly_white")
        
        fig_bar.update_layout(
            font=dict(color="#000000", size=12), # Negro normal
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=150)
        )
        fig_bar.update_yaxes(tickfont=dict(color="#000000", size=11))
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.subheader("🔬 Mix de Análisis")
        data_pie = df['Det_Resumen'].value_counts().reset_index()
        
        fig_pie = px.pie(data_pie, values='count', names='Det_Resumen', 
                         color_discrete_sequence=['#FF6B00', '#262730', '#555555', '#888888'],
                         template="plotly_white")
        
        fig_pie.update_layout(
            font=dict(color="#000000", size=12),
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(
                font=dict(color="#FFFFFF", size=11), # Letras blancas en leyenda
                bgcolor="#262730", # FONDO SÓLIDO OSCURO para resaltar
                bordercolor="#FF6B00",
                borderwidth=2
            )
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA DE GESTIÓN (FECHAS RESTAURADAS) ---
    st.write("---")
    st.subheader("📋 Panel de Control de Plazos")
    
    # Formatear fechas para la tabla
    df_ver = df.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Requerida'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    columnas_orden = ['Enviado', 'Projob', 'Cliente', 'Det_Resumen', 'F. Ingreso', 'F. Requerida']
    
    res = st.data_editor(
        df_ver[columnas_orden],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Det_Resumen": "Análisis",
            "F. Ingreso": st.column_config.Column("Fecha Ingreso", width="medium"),
            "F. Requerida": st.column_config.Column("Plazo Límite", width="medium")
        },
        key="editor_final_completo"
    )

    # --- BOTONES DE ACCIÓN ---
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("💾 Guardar Cambios"):
            for i, row in res.iterrows():
                df_original.loc[df_original['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
            
            # Subir sin la columna auxiliar de resumen
            conn.update(data=df_original.drop(columns=['Det_Resumen'], errors='ignore'))
            st.success("✅ Sincronizado con Google Sheets")
            st.rerun()

    with col_btn2:
        if st.button("✅ Marcar Vista Actual como Enviado"):
            df_original.loc[df.index, 'Enviado'] = True
            conn.update(data=df_original.drop(columns=['Det_Resumen'], errors='ignore'))
            st.rerun()

except Exception as e:
    st.error(f"Error en el sistema: {e}")
