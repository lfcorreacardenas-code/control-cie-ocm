import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portal OCM - Inteligencia de Datos", layout="wide")

st.title("⚡ Monitoreo CIE - Control y Estadísticas")

# Función de abreviación mejorada
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
    
    # Estandarización de datos
    if 'Enviado' in df_datos.columns:
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')
    
    if 'Determinaciones' in df_datos.columns:
        df_datos['Determinaciones'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # --- PANEL DE CONTROL (SIDEBAR) ---
    st.sidebar.header("Filtros de Visualización")
    busqueda = st.sidebar.text_input("🔍 Buscar (Projob, Cliente, Análisis):")
    solo_pendientes = st.sidebar.checkbox("Mostrar solo pendientes", value=False)
    
    df_filtrado = df_datos.copy()
    if busqueda:
        df_filtrado = df_filtrado[df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
    if solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Enviado'] == False]

    # --- MÉTRICAS E INDICADORES ---
    hoy = date.today()
    total = len(df_filtrado)
    enviados = len(df_filtrado[df_filtrado['Enviado'] == True])
    porcentaje_avance = (enviados / total * 100) if total > 0 else 0
    vencidos = len(df_filtrado[(df_filtrado['Enviado'] == False) & (df_filtrado['Fecha Requerida'].dt.date <= hoy)].dropna(subset=['Fecha Requerida']))
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Muestras Totales", total)
    m2.metric("Pendientes", total - enviados)
    m3.metric("🚨 Urgentes", vencidos)
    m4.metric("📈 Eficiencia de Envío", f"{porcentaje_avance:.1f}%")

    # --- SECCIÓN DE GRÁFICOS ---
    st.write("---")
    col_chart, col_empty = st.columns([2, 1]) # El gráfico ocupa 2/3 del ancho
    
    with col_chart:
        st.subheader("📊 Top 10 Clientes por Volumen de Muestras")
        # Contamos muestras por cliente
        df_counts = df_filtrado['Cliente'].value_counts().reset_index().head(10)
        df_counts.columns = ['Cliente', 'Muestras']
        
        fig = px.bar(df_counts, x='Muestras', y='Cliente', orientation='h',
                     text='Muestras', color='Muestras', color_continuous_scale='Blues')
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # --- TABLA DE DATOS ---
    st.subheader("📋 Detalle de Programación")
    
    # Botón Masivo
    if st.button("✅ Marcar TODA LA VISTA como Enviado"):
        df_datos.loc[df_filtrado.index, 'Enviado'] = True
        conn.update(data=df_datos)
        st.success("Registros actualizados correctamente.")
        st.rerun()

    df_display = df_filtrado.copy()
    df_display['F. Ingreso'] = df_display['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_display['F. Requerida'] = df_display['Fecha Requerida'].dt.strftime('%d-%m-%Y')
    
    cols = ['Enviado', 'Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Requerida']
    
    res = st.data_editor(
        df_display[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Determinaciones": st.column_config.TextColumn("🔬 Análisis"),
        },
        disabled=['Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Requerida'],
        key="tabla_final_v3"
    )

    if st.button("💾 Guardar Cambios Individuales"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("Base de datos sincronizada", icon="✅")
        st.rerun()

except Exception as e:
    st.error(f"Error en la aplicación: {e}")
    st.error(f"Error: {e}")


