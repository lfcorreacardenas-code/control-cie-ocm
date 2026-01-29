import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portal OCM - Real Time", layout="wide")

st.title("⚡ Monitoreo CIE - Control en Tiempo Real")
st.markdown("### Gestión de envíos y plazos")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leer datos. ttl=0 evita que Streamlit use datos viejos guardados en memoria
    df_datos = conn.read(ttl=0)
    
    # Si la columna Enviado no existe por algún motivo, la creamos temporalmente para evitar el error
    if 'Enviado' not in df_datos.columns:
        df_datos.insert(0, 'Enviado', False)

    # Convertir fechas (Ajustado a los nombres de tu imagen)
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True)
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True)

    # Filtros laterales
    st.sidebar.header("Panel de Control")
    busqueda = st.sidebar.text_input("🔍 Buscar Projob o Cliente:")
    ver_solo_pendientes = st.sidebar.checkbox("Mostrar solo pendientes", value=False)
    
    df_filtrado = df_datos.copy()
    if busqueda:
        mask = (df_filtrado['Projob'].astype(str).str.contains(busqueda, case=False) | 
                df_filtrado['Cliente'].astype(str).str.contains(busqueda, case=False))
        df_filtrado = df_filtrado[mask]
    if ver_solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Enviado'] == False]

    # Métricas
    hoy = date.today()
    vencidos = len(df_filtrado[(df_filtrado['Enviado'] == False) & (df_filtrado['Fecha Requerida'].dt.date <= hoy)])
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Muestras Totales", len(df_filtrado))
    c2.metric("Por Enviar", len(df_filtrado[df_filtrado['Enviado'] == False]))
    c3.metric("🚨 Urgentes", vencidos)

    # Acciones Masivas
    if st.button("✅ Marcar TODO como Enviado"):
        df_datos['Enviado'] = True
        conn.update(data=df_datos)
        st.success("Todo marcado como enviado.")
        st.rerun()

    # Preparar visualización
    df_editor = df_filtrado.copy()
    df_editor['F. Ingreso'] = df_editor['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_editor['F. Requerida'] = df_editor['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    # Columnas que vemos en tu Google Sheet
    columnas_vista = ['Enviado', 'Projob', 'Cliente', 'F. Ingreso', 'F. Requerida', 'Descripción']

    edited_df = st.data_editor(
        df_editor[columnas_vista],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "F. Requerida": "📅 Límite Lab",
            "F. Ingreso": "Ingreso"
        },
        disabled=['Projob', 'Cliente', 'F. Ingreso', 'F. Requerida', 'Descripción'],
        key="tabla_gsheets"
    )

    if st.button("💾 Guardar Cambios"):
        for i, row in edited_df.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("¡Sincronizado!", icon="✅")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")




