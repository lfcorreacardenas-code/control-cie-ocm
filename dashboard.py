import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portal OCM - Control e Inteligencia", layout="wide")

st.title("⚡ Monitoreo CIE - Control Estratégico")

# Función de abreviación
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
    df_raw = conn.read(ttl=0)
    df_datos = df_raw.copy()
    
    # Estandarización
    if 'Enviado' in df_datos.columns:
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')
    
    if 'Determinaciones' in df_datos.columns:
        df_datos['Determinaciones'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # --- MÉTRICAS SUPERIORES ---
    hoy = date.today()
    total = len(df_datos)
    pendientes = len(df_datos[df_datos['Enviado'] == False])
    # KPI de Eficiencia
    eficiencia = ((total - pendientes) / total * 100) if total > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Muestras Totales", total)
    m2.metric("Por Enviar", pendientes, delta=f"-{pendientes}", delta_color="inverse")
    m3.metric("Eficiencia Mensual", f"{eficiencia:.1f}%")
    m4.metric("Fecha Hoy", hoy.strftime("%d/%m/%Y"))

    # --- SECCIÓN VISUAL (Gráficos) ---
    st.markdown("---")
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("📊 Top 10 Clientes con mayor demanda")
        top_clientes = df_datos['Cliente'].value_counts().reset_index().head(10)
        top_clientes.columns = ['Cliente', 'Muestras']
        fig_bar = px.bar(top_clientes, x='Muestras', y='Cliente', orientation='h', 
                         color='Muestras', color_continuous_scale='Turbo', text_auto=True)
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=350)
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.subheader("🔬 Tipos de Análisis")
        tipo_análisis = df_datos['Determinaciones'].value_counts().reset_index().head(5)
        tipo_análisis.columns = ['Análisis', 'Cantidad']
        fig_pie = px.pie(tipo_análisis, values='Cantidad', names='Análisis', hole=0.4)
        fig_pie.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA DE CONTROL ---
    st.markdown("---")
    st.subheader("📋 Gestión de Reportes")
    
    # Filtro dinámico arriba de la tabla
    busqueda = st.text_input("🔍 Filtrar tabla por Projob o Cliente:")
    df_ver = df_datos.copy()
    if busqueda:
        df_ver = df_ver[df_ver.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]

    # Formatear fechas para mostrar
    df_ver['F. Ingreso'] = df_ver['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_ver['F. Límite'] = df_ver['Fecha Requerida'].dt.strftime('%d-%m-%Y')
    
    res = st.data_editor(
        df_ver[['Enviado', 'Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Límite']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Determinaciones": "🔬 Análisis"
        },
        disabled=['Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Límite'],
        key="main_editor"
    )

    if st.button("💾 Sincronizar Cambios con Google Sheets"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("¡Sincronización exitosa!", icon="🚀")
        st.rerun()

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
