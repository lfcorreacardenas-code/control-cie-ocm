import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. FUNCIÓN DE AUTENTICACIÓN (EL MURO) ---
def check_password():
    def password_entered():
        # Verificamos contra los Secrets de Streamlit
        if (
            st.session_state["username"] == st.secrets["usuarios"]["admin_user"]
            and st.session_state["password"] == st.secrets["usuarios"]["admin_password"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Seguridad: borrar password de memoria
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # PANTALLA DE LOGIN LIMPIA
        st.title("🔐 Acceso Privado CIE-OCM")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # LOGIN FALLIDO
        st.title("🔐 Acceso Privado CIE-OCM")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

# --- 2. VALIDACIÓN DE ACCESO ---
if not check_password():
    st.stop()  # SI NO HAY LOGIN, SE DETIENE AQUÍ. No se ejecuta nada más.

# --- 3. TODO EL PORTAL (SOLO SE VE SI EL LOGIN ES EXITOSO) ---

# Configuración de página y estilos
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

# --- CARGA DE DATOS CON CACHÉ ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def cargar_datos():
    return conn.read(ttl=0)

def abreviar_analisis(texto):
    if not isinstance(texto, str): return texto
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol and 2,6-di-tert-Butyl Phenol by IR Manual": "Contenido de Inhibidor",
        "Conteo de Partículas en Aceite Mineral Aislante por el Contador de Partículas Automático": "Conteo de Particulas",
        "Gases Disueltos en Aceite Aislante Eléctrico por GC-Headspace": "Gases Disueltos",
        "Elementos en Aceites Dieléctricos por ICP-AES": "Metales",
        "Color por Método Automático Triestimulo": "FQ",
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

try:
    df_original = cargar_datos()
    df = df_original.copy()

    # Procesamiento de Fechas y Columnas
    df['Recibido Laboratorio'] = pd.to_datetime(df['Recibido Laboratorio'], errors='coerce', dayfirst=True)
    df['Fecha Requerida'] = pd.to_datetime(df['Fecha Requerida'], errors='coerce', dayfirst=True)
    if 'Enviado' not in df.columns: df.insert(0, 'Enviado', False)
    df['Enviado'] = df['Enviado'].fillna(False).astype(bool)
    df['Det_Resumen'] = df['Determinaciones'].apply(abreviar_analisis)

    # URL Drive (Recursiva en Carpeta 2026)
    #def generar_url_drive(projob):
    #    if pd.isna(projob): return None
    #    return f"https://drive.google.com/drive/u/0/search?q={projob[:11]} parent:2026&sort=7&direction=d"

    # --- BARRA LATERAL ---
    st.sidebar.header("🔍 Panel de Control")
    lista_clientes = ["TODOS"] + sorted(df['Cliente'].dropna().unique().tolist())
    filtro_cliente = st.sidebar.selectbox("Cliente:", lista_clientes)
    
    if st.sidebar.button("🚪 Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

    if filtro_cliente != "TODOS":
        df = df[df['Cliente'] == filtro_cliente]

    # --- CUERPO DEL PORTAL ---
    st.title("⚡ Monitoreo CIE - Control Estratégico")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras Totales", len(df))
    m2.metric("Pendientes", len(df[df['Enviado'] == False]))
    m3.metric("Filtro Actual", filtro_cliente)

    # Gráficos
    # --- SECCIÓN DE GRÁFICOS OPTIMIZADA ---
    st.write("---")
    g1, g2 = st.columns([1.2, 1])
    with g1:
        st.subheader("📊 Volumen por Cliente")
        data_bar = df['Cliente'].value_counts().reset_index().head(10)
        fig_bar = px.bar(data_bar, x='count', y='Cliente', orientation='h', color_discrete_sequence=['#FF6B00'], text_auto=True, template="plotly_white",height=400)
        fig_bar.update_layout(font=dict(color="black"), paper_bgcolor='rgba(0,0,0,0.5)', plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=150, r=20, t=30, b=30))
        fig_bar.update_yaxes(tickmode='linear', automargin=True)
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("🔬 Mix de Análisis")
        data_pie = df['Det_Resumen'].value_counts().reset_index()
        fig_pie = px.pie(data_pie, values='count', names='Det_Resumen', color_discrete_sequence=['#FF6B00', '#262730', '#555555'], template="plotly_white")
        fig_pie.update_layout(font=dict(color="black"), paper_bgcolor='rgba(0,0,0,0)', 
                             legend=dict(font=dict(color="white"), bgcolor="#262730", bordercolor="#FF6B00", borderwidth=2))
        st.plotly_chart(fig_pie, use_container_width=True)
    # Tabla
    st.write("---")
    df_ver = df.copy()
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Requerida'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')
    #df_ver['Reporte'] = df_ver['Projob'].apply(generar_url_drive)

    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Det_Resumen', 'F. Ingreso', 'F. Requerida']],
        use_container_width=True, hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            #"Reporte": st.column_config.LinkColumn("PDF 📄", display_text="Ver Reporte"),
        },
        key="editor_final_seguro"
    )

    if st.button("💾 Guardar Cambios"):
        for i, row in res.iterrows():
            df_original.loc[df_original['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_original.drop(columns=['Det_Resumen'], errors='ignore'))
        st.cache_data.clear()
        st.success("¡Datos actualizados!")
        time.sleep(1)
        st.rerun()

except Exception as e:
    st.error(f"Error de conexión: {e}")








