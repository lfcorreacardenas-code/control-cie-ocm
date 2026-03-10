import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. FUNCIÓN DE AUTENTICACIÓN ---
def check_password():
    def password_entered():
        if (
            st.session_state["username"] == st.secrets["usuarios"]["admin_user"]
            and st.session_state["password"] == st.secrets["usuarios"]["admin_password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Privado CIE-OCM")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Acceso Privado CIE-OCM")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. CONFIGURACIÓN Y ESTILOS ---
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

# --- 3. CARGA Y PREPARACIÓN DE DATOS ---
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
        "Karl Fischer": "FQ",
        "Rigidez Dieléctrica": "FQ",
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
    df_original = cargar_datos()
    
    # --- PROCESAMIENTO BASE ---
    df_base = df_original.copy()
    df_base['Recibido Laboratorio'] = pd.to_datetime(df_base['Recibido Laboratorio'], errors='coerce', dayfirst=True)
    df_base['Fecha Requerida'] = pd.to_datetime(df_base['Fecha Requerida'], errors='coerce', dayfirst=True)
    if 'Enviado' not in df_base.columns: df_base.insert(0, 'Enviado', False)
    df_base['Enviado'] = df_base['Enviado'].fillna(False).astype(bool)
    df_base['Estado'] = df_base['Enviado'].map({True: 'Enviado ✅', False: 'Pendiente ⏳'})
    df_base['Det_Resumen'] = df_base['Determinaciones'].apply(abreviar_analisis)

    # --- FILTROS (BARRA LATERAL) ---
    st.sidebar.header("🔍 Panel de Control")
    lista_clientes = ["TODOS"] + sorted(df_base['Cliente'].dropna().unique().tolist())
    filtro_cliente = st.sidebar.selectbox("Cliente:", lista_clientes)
    solo_no_enviados = st.sidebar.checkbox("Ver solo no enviados", value=False)
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

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

    # --- SECCIÓN DE GRÁFICOS (CONTEXTO GLOBAL) ---
    st.write("---")
    st.markdown("### 📈 Dashboard Operativo Global")
    g1, g2 = st.columns([1.2, 0.8])
    
    with g1:
        st.subheader("📊 Progreso por Cliente (Top 10)")
        # Lógica para gráfico apilado:
        # 1. Obtenemos el orden del top 10 basado en el TOTAL
        top_10_names = df_base['Cliente'].value_counts().nlargest(10).index
        df_plot_bar = df_base[df_base['Cliente'].isin(top_10_names)]
        
        # 2. Agrupamos por Cliente y Estado
        data_bar = df_plot_bar.groupby(['Cliente', 'Estado']).size().reset_index(name='Cantidad')
        
        fig_bar = px.bar(data_bar, x='Cantidad', y='Cliente', color='Estado',
                         orientation='h', 
                         color_discrete_map={'Pendiente ⏳': '#FF6B00', 'Enviado ✅': '#555555'},
                         category_orders={"Cliente": top_10_names.tolist()},
                         template="plotly_white", height=400)
        
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=150, r=20, t=10, b=10),
            xaxis_title="Número de Muestras", yaxis_title=None,
            legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix Total de Ensayos")
        data_pie = df_base['Det_Resumen'].value_counts().reset_index()
        fig_pie = px.pie(data_pie, values='count', names='Det_Resumen', 
                         color_discrete_sequence=['#FF6B00', '#262730', '#555555', '#888888'], 
                         template="plotly_white", height=400)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA OPERATIVA ---
    st.write("---")
    st.subheader("📋 Gestión de Reportes")
    df_ver = df_vista.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Requerida'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Det_Resumen', 'F. Ingreso', 'F. Requerida']],
        use_container_width=True, hide_index=True,
        column_config={"Enviado": st.column_config.CheckboxColumn("Enviado ✅")},
        key="editor_final_seguro"
    )

    if st.button("💾 Guardar Cambios"):
        for i, row in res.iterrows():
            df_original.loc[df_original['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_original.drop(columns=['Det_Resumen', 'Estado'], errors='ignore'))
        st.cache_data.clear()
        st.success("¡Datos actualizados!")
        time.sleep(1)
        st.rerun()

except Exception as e:
    st.error(f"Error de sistema: {e}")
