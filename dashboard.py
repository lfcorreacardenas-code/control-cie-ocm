import streamlit as st
import pandas as pd  # CORREGIDO: Era 'import pandas as pd'
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection
import time

# --- CONFIGURACIÓN DE SEGURIDAD ---
def check_password():
    """Devuelve True si el usuario introdujo la contraseña correcta."""

    def password_entered():
        """Verifica si la contraseña introducida es correcta."""
        if (
            st.session_state["username"] == st.secrets["usuarios"]["admin_user"]
            and st.session_state["password"] == st.secrets["usuarios"]["admin_password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No guardar la contraseña
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primera vez, mostrar formulario de login
        st.title("🔐 Acceso al Portal CIE-OCM")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta, mostrar formulario de nuevo
        st.title("🔐 Acceso al Portal CIE-OCM")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("😕 Usuario o contraseña incorrectos")
        return False
    else:
        # Contraseña correcta
        return True

# --- VALIDACIÓN INICIAL ---
if check_password():
    # AQUÍ VA TODO EL RESTO DE TU CÓDIGO (aplicar_estilos, carga de datos, gráficos, etc.)
    st.sidebar.success("Sesión iniciada correctamente")

# 1. Configuración de página y Estética de Alto Contraste
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
        [data-testid="stMetricLabel"] { color: #000000 !important; font-weight: 700 !important; }
        div[data-testid="stMetric"] {
            background-color: white !important;
            border-left: 6px solid #FF6B00 !important;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.1);
            padding: 15px;
        }
        section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
            color: #000000 !important; font-weight: bold !important;
        }
        h1, h2, h3 { color: #CC5500 !important; font-weight: 800 !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_estilos()

# --- CARGA DE DATOS CON CACHÉ INTELIGENTE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60) # Evita saturar a Google consultando solo cada 60 segundos
def cargar_datos_seguro():
    return conn.read(ttl=0)

def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol and 2,6-di-tert-Butyl Phenol by IR Manual": "Contenido de Inhibidor",
        "Conteo de Partículas en Aceite Mineral Aislante por el Contador de Partículas Automático": "Conteo de Particulas",
        "Densidad, densidad relativa y gravedad API de líquidas por densitómetro(Densidad a 15ºC)": "FQ",
        "Bifenilos Policlorados": "PCB",
        "Color ASTM": "FQ",
        "Color por Método Automático Triestimulo": "FQ",
        "Gases Disueltos en Aceite Aislante Eléctrico por GC-Headspace": "Gases Disueltos",
        "Elementos en Aceites Dieléctricos por ICP-AES": "Metales",
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

try:
    df_original = cargar_datos_seguro()
    df = df_original.copy()

    # --- NUEVA LÓGICA DE PROCESAMIENTO DE FECHAS ---
    # Convertimos a fecha forzando errores a 'NaT' (Not a Time) para evitar el 'None'
    df['Recibido Laboratorio'] = pd.to_datetime(df['Recibido Laboratorio'], errors='coerce', dayfirst=True)
    df['Fecha Requerida'] = pd.to_datetime(df['Fecha Requerida'], errors='coerce', dayfirst=True)

    # Si después de la conversión siguen apareciendo vacíos, podrías rellenarlos temporalmente
    # df['Fecha Requerida'] = df['Fecha Requerida'].fillna(pd.Timestamp.now()) 

    # Estandarización de otras columnas
    if 'Enviado' not in df.columns: df.insert(0, 'Enviado', False)
    df['Enviado'] = df['Enviado'].fillna(False).astype(bool)
    df['Det_Resumen'] = df['Determinaciones'].apply(abreviar_analisis)
    df['Recibido Laboratorio'] = pd.to_datetime(df['Recibido Laboratorio'], errors='coerce')
    df['Fecha Requerida'] = pd.to_datetime(df['Fecha Requerida'], errors='coerce')

    # --- BARRA LATERAL ---
    st.sidebar.header("🔍 Panel de Control")
    lista_clientes = ["TODOS"] + sorted(df['Cliente'].dropna().unique().tolist())
    filtro_cliente = st.sidebar.selectbox("Cliente:", lista_clientes)
    filtro_projob = st.sidebar.text_input("Buscar Projob:")
    solo_pendientes = st.sidebar.checkbox("Ocultar Enviados")

    if filtro_cliente != "TODOS": df = df[df['Cliente'] == filtro_cliente]
    if filtro_projob: df = df[df['Projob'].str.contains(filtro_projob, case=False, na=False)]
    if solo_pendientes: df = df[df['Enviado'] == False]

    # --- MÉTRICAS ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras Totales", len(df))
    m2.metric("Por Enviar", len(df[df['Enviado'] == False]))
    m3.metric("Filtro", filtro_cliente if filtro_cliente != "TODOS" else "Global")

    # --- GRÁFICOS ---
    st.write("---")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("📊 Volumen por Cliente")
        eje_y = 'Det_Resumen' if filtro_cliente != "TODOS" else 'Cliente'
        data_bar = df[eje_y].value_counts().reset_index().head(10)
        fig_bar = px.bar(data_bar, x='count', y=eje_y, orientation='h', color_discrete_sequence=['#FF6B00'], text_auto=True, template="plotly_white")
        fig_bar.update_layout(font=dict(color="black", size=12), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=150))
        fig_bar.update_yaxes(tickfont=dict(color="black"))
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.subheader("🔬 Mix de Análisis")
        data_pie = df['Det_Resumen'].value_counts().reset_index()
        fig_pie = px.pie(data_pie, values='count', names='Det_Resumen', color_discrete_sequence=['#FF6B00', '#262730', '#555555', '#888888'], template="plotly_white")
        fig_pie.update_layout(
            font=dict(color="black"), paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(font=dict(color="white"), bgcolor="#262730", bordercolor="#FF6B00", borderwidth=2)
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA Y GESTIÓN ---
    st.write("---")
    st.subheader("📋 Gestión de Muestras y Plazos")
    
    df_ver = df.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Requerida'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')
    
    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Det_Resumen', 'F. Ingreso', 'F. Requerida']],
        use_container_width=True, hide_index=True,
        column_config={"Enviado": st.column_config.CheckboxColumn("Enviado ✅")},
        key="editor_v10"
    )

    # Botones con protección de cuota
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Guardar"):
            try:
                for i, row in res.iterrows():
                    df_original.loc[df_original['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
                conn.update(data=df_original.drop(columns=['Det_Resumen'], errors='ignore'))
                st.cache_data.clear()
                st.toast("✅ Cambios guardados")
                time.sleep(1)
                st.rerun()
            except Exception:
                st.warning("Google está saturado. Reintenta en 15 segundos.")

except Exception as e:
    st.error(f"Error de sistema: {e}")




