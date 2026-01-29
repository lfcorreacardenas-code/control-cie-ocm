import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portal OCM - Real Time", layout="wide")

st.title("⚡ Monitoreo CIE - Control en Tiempo Real")
st.markdown("### Gestión de envíos y plazos")

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. Leer datos y forzar limpieza
    df_datos = conn.read(ttl=0)
    
    # SOLUCIÓN AL ERROR: Forzamos la columna Enviado a ser Booleana (True/False)
    if 'Enviado' in df_datos.columns:
        # Llenamos vacíos con False y convertimos a bool
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    # 2. Convertir fechas según tu tabla de Google
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')

    # 3. Filtros laterales
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

    # 4. Métricas
    hoy = date.today()
    # Evitamos errores si hay fechas nulas
    vencidos = len(df_filtrado[
        (df_filtrado['Enviado'] == False) & 
        (df_filtrado['Fecha Requerida'].dt.date <= hoy)
    ].dropna(subset=['Fecha Requerida']))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Muestras Totales", len(df_filtrado))
    c2.metric("Por Enviar", len(df_filtrado[df_filtrado['Enviado'] == False]))
    c3.metric("🚨 Urgentes", vencidos)

    # 5. ACCIÓN MASIVA: Botón para marcar todo
    if st.button("✅ Marcar TODO como Enviado"):
        df_datos['Enviado'] = True
        conn.update(data=df_datos)
        st.success("¡Base de datos actualizada! Todos marcados.")
        st.rerun()

    # 6. Preparar visualización
    df_editor = df_filtrado.copy()
    df_editor['F. Ingreso'] = df_editor['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_editor['F. Requerida'] = df_editor['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    # Columnas que vemos en tu Google Sheet (image_e44d9a.png)
    columnas_vista = ['Enviado', 'Projob', 'Cliente', 'F. Ingreso', 'F. Requerida', 'Descripción']

    # EL EDITOR INTERACTIVO
    edited_df = st.data_editor(
        df_editor[columnas_vista],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅", default=False),
            "F. Requerida": "📅 Límite Lab",
            "F. Ingreso": "Ingreso"
        },
        disabled=['Projob', 'Cliente', 'F. Ingreso', 'F. Requerida', 'Descripción'],
        key="tabla_gsheets"
    )

    # 7. GUARDADO INDIVIDUAL
    if st.button("💾 Guardar Cambios Manuales"):
        # Sincronizar los checks marcados con el dataframe original
        for i, row in edited_df.iterrows():
            # Buscamos por Projob para estar seguros de actualizar la fila correcta
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        
        conn.update(data=df_datos)
        st.toast("Cambios sincronizados en Google Sheets", icon="✅")
        st.rerun()

except Exception as e:
    st.error(f"Error detectado: {e}")
    st.info("💡 Tip: Revisa que la columna 'Enviado' en Google Sheets no tenga números, solo texto o esté vacía.")
