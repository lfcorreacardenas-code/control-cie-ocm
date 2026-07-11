import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. CONFIGURACIÓN Y ESTILOS ---
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
        [data-testid="stMetricValue"] { color: #CC5500 !important; font-weight: bold !important; }
        [data-testid="stMetricLabel"] { color: #555555 !important; font-weight: bold !important; }
        
        div[data-testid="stMetric"] {
            background-color: white !important;
            border-left: 6px solid #FF6B00 !important;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
            padding: 15px;
        }
        h1, h2, h3 { color: #CC5500 !important; font-weight: 800 !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_estilos()

# --- 2. CARGA Y PREPARACIÓN DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_datos():
    return conn.read(ttl=0)

def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol and 2,6-di-tert-Butyl Phenol by IR Manual": "Inhibidor",
        "Conteo de Partículas en Aceite Mineral Aislante": "Conteo Particulas",
        "Gases Disueltos en Aceite Aislante Eléctrico": "Gases Disueltos",
        "Elementos en Aceites Dieléctricos por ICP-AES": "Metales",
        "Bifenilos Policlorados": "PCB",
        "Compuestos Furanos": "Furanos",
        "Elementos por ICP-AES":"Metales",
        "Karl Fischer": "FQ",
        "Factor de Potencia de disipación y permitividad relativa de los aceites aislantes(Factor Disipación (tan delta), 100C...": "FQ",
        "Rigidez Dieléctrica": "FQ",
        "Los sedimentos y lodos soluble en Servicio de edad aceites aislantes" : "Lodos y Sedimentos",
        "Azufre Corrosivo en Aceites Eléctricos Aislantes":"FQ",
        "Color": "FQ",
        "Densidad": "FQ",
        "Acidez": "FQ",
        "Tensión Interfacial": "FQ",
        "Apariencia": "FQ",
        "Exámen Visual": "FQ"
    }
    for largo, corto in mapeo.items():
        if largo in texto: return corto
    return texto

try:
    df_original = cargar_datos().copy()
    
    # Asegurar que existan las columnas para evitar errores de actualización en la estructura
    if 'Enviado' not in df_original.columns: 
        df_original['Enviado'] = False
    df_original['Enviado'] = df_original['Enviado'].fillna(False).astype(bool)

    if 'Observaciones' not in df_original.columns:
        df_original['Observaciones'] = ""
    df_original['Observaciones'] = df_original['Observaciones'].fillna("").astype(str)
    
    # --- PROCESAMIENTO BASE ---
    df_base = df_original.copy()
    df_base['Recibido Laboratorio'] = pd.to_datetime(df_base['Recibido Laboratorio'], errors='coerce', dayfirst=True)
    df_base['Fecha Requerida'] = pd.to_datetime(df_base['Fecha Requerida'], errors='coerce', dayfirst=True)
    
    df_base['Estado'] = df_base['Enviado'].map({True: 'Enviado ✅', False: 'Pendiente ⏳'})
    df_base['Det_Resumen'] = df_base['Determinaciones'].apply(abreviar_analisis)

    # --- FILTROS (BARRA LATERAL) ---
    st.sidebar.header("🔍 Panel de Control")
    lista_clientes = ["TODOS"] + sorted(df_base['Cliente'].dropna().unique().tolist())
    filtro_cliente = st.sidebar.selectbox("Cliente:", lista_clientes)
    solo_no_enviados = st.sidebar.checkbox("Ver solo no enviados", value=False)

    # --- DATOS FILTRADOS PARA LA TABLA ---
    df_vista = df_base.copy()
    if filtro_cliente != "TODOS":
        df_vista = df_vista[df_vista['Cliente'] == filtro_cliente]
    if solo_no_enviados:
        df_vista = df_vista[df_vista['Enviado'] == False]

    # --- CUERPO DEL PORTAL ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras en Vista", len(df_vista))
    pendientes_totales = len(df_base[(df_base['Enviado'] == False) & 
                                     ((df_base['Cliente'] == filtro_cliente) if filtro_cliente != "TODOS" else True)])
    m2.metric("Pendientes Totales", pendientes_totales)
    m3.metric("Filtro Actual", filtro_cliente)

    # --- SECCIÓN DE GRÁFICOS ---
    st.write("---")
    st.markdown("### 📈 Dashboard Operativo Global")
    g1, g2 = st.columns([1.2, 0.8])
    
    with g1:
        st.subheader("📊 Progreso por Cliente (Top 10)")
        top_10_names = df_base['Cliente'].value_counts().nlargest(10).index
        df_plot_bar = df_base[df_base['Cliente'].isin(top_10_names)]
        data_bar = df_plot_bar.groupby(['Cliente', 'Estado']).size().reset_index(name='Cantidad')
        
        fig_bar = px.bar(data_bar, x='Cantidad', y='Cliente', color='Estado',
                         orientation='h', 
                         color_discrete_map={'Pendiente ⏳': '#FF6B00', 'Enviado ✅': '#00ff80'},
                         category_orders={"Cliente": top_10_names.tolist()},
                         template="plotly_white", height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix Total de Ensayos")
        data_pie = df_base['Det_Resumen'].value_counts().reset_index()
        fig_pie = px.pie(data_pie, values='count', names='Det_Resumen', 
                         color_discrete_sequence=['#FF8000', '#262730', '#555555'], 
                         template="plotly_white", height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- ANÁLISIS TEMPORAL ---
    st.write("---")
    st.markdown("### 📊 Análisis de Tendencias Mensuales")
    
    df_timeline = df_base.dropna(subset=['Recibido Laboratorio']).copy()
    df_timeline['Mes'] = df_timeline['Recibido Laboratorio'].dt.strftime('%Y-%m')
    
    gt1, gt2 = st.columns(2)
    
    with gt1:
        st.subheader("📅 Evolución Total de Muestras")
        data_timeline = df_timeline.groupby('Mes').size().reset_index(name='Cantidad').sort_values('Mes')
        fig_line = px.line(data_timeline, x='Mes', y='Cantidad', markers=True, template="plotly_white", height=400)
        fig_line.update_traces(line_color='#FF6B00')
        st.plotly_chart(fig_line, use_container_width=True)
        
    with gt2:
        st.subheader("🏆 Clientes Principales por Mes")
        top_5_clientes = df_base['Cliente'].value_counts().nlargest(5).index.tolist()
        df_top_mes = df_timeline[df_timeline['Cliente'].isin(top_5_clientes)].copy()
        data_top_mes = df_top_mes.groupby(['Mes', 'Cliente']).size().reset_index(name='Cantidad').sort_values('Mes')
        
        fig_top_bar = px.bar(data_top_mes, x='Mes', y='Cantidad', color='Cliente', barmode='stack', template="plotly_white", height=400)
        st.plotly_chart(fig_top_bar, use_container_width=True)
    
    # --- TABLA OPERATIVA ---
    st.write("---")
    st.subheader("📋 Gestión de Reportes")
    df_ver = df_vista.copy()
    
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio']
    df_ver['F. Requerida'] = df_ver['Fecha Requerida']

    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Det_Resumen', 'F. Ingreso', 'F. Requerida', 'Observaciones']],
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "F. Ingreso": st.column_config.DateColumn("F. Ingreso", format="DD-MM-YYYY"),
            "F. Requerida": st.column_config.DateColumn("F. Requerida", format="DD-MM-YYYY"),
            "Observaciones": st.column_config.TextColumn("Observaciones", width="large"),
        },
        key="editor_final_seguro"
    )

    if st.button("💾 Guardar Cambios"):
        # Mapeo seguro usando 'Projob' como clave para evitar desajustes de índice por filtros
        for _, row in res.iterrows():
            idx_original = df_original[df_original['Projob'] == row['Projob']].index
            if not idx_original.empty:
                df_original.loc[idx_original, 'Enviado'] = row['Enviado']
                df_original.loc[idx_original, 'Observaciones'] = row['Observaciones']
            
        # Limpieza estricta de columnas calculadas que no pertenecen al archivo original
        columnas_a_borrar = ['Det_Resumen', 'Estado', 'F. Ingreso', 'F. Requerida']
        df_guardar = df_original.drop(columns=columnas_a_borrar, errors='ignore')
        
        conn.update(data=df_guardar)
        st.cache_data.clear()
        st.success("¡Datos actualizados con éxito!")
        time.sleep(1)
        st.rerun()

except Exception as e:
    st.error(f"⚠️ Error en la aplicación: {e}")
