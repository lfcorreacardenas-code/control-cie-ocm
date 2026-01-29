import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portal OCM - Control Total", layout="wide")

st.title("⚡ Monitoreo CIE - Control en Tiempo Real")
st.markdown("### Gestión de envíos y plazos")

# Conexión profesional con Service Account
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. Leer datos
    df_datos = conn.read(ttl=0)
    
    # Limpieza de columna Enviado
    if 'Enviado' in df_datos.columns:
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    # 2. Fechas (Ajustado a tus columnas: Recibido Laboratorio y Fecha Requerida)
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')

    # 3. Sidebar
    st.sidebar.header("Filtros")
    busqueda = st.sidebar.text_input("🔍 Buscar Projob o Cliente:")
    solo_pendientes = st.sidebar.checkbox("Ver solo pendientes", value=False)
    
    df_filtrado = df_datos.copy()
    if busqueda:
        df_filtrado = df_filtrado[df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
    if solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Enviado'] == False]

    # 4. Métricas
    hoy = date.today()
    pendientes = df_filtrado[df_filtrado['Enviado'] == False]
    vencidos = len(pendientes[pendientes['Fecha Requerida'].dt.date <= hoy].dropna(subset=['Fecha Requerida']))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Muestras Totales", len(df_filtrado))
    c2.metric("Pendientes", len(pendientes))
    c3.metric("🚨 Urgentes", vencidos)

    # 5. Botón Masivo
    if st.button("✅ Marcar TODO como Enviado"):
        df_datos['Enviado'] = True
        conn.update(data=df_datos)
        st.success("¡Sincronización masiva completada!")
        st.rerun()

    # 6. Tabla Editor
    df_editor = df_filtrado.copy()
    df_editor['F. Ingreso'] = df_editor['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_editor['F. Requerida'] = df_editor['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    cols_vista = ['Enviado', 'Projob', 'Cliente', 'F. Ingreso', 'F. Requerida', 'Descripción']
    
    # Solo mostramos columnas que existan para evitar errores
    cols_existentes = [c for c in cols_vista if c in df_editor.columns or c in ['F. Ingreso', 'F. Requerida']]

    res = st.data_editor(
        df_editor[cols_existentes],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "F. Requerida": "📅 Límite",
            "F. Ingreso": "Ingreso"
        },
        disabled=['Projob', 'Cliente', 'F. Ingreso', 'F. Requerida', 'Descripción'],
        key="main_table"
    )

    # 7. Guardado Manual
    if st.button("💾 Guardar Cambios Manuales"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("Guardado correctamente", icon="✅")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
