import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Portal OCM - Optimizado", layout="wide")

st.title("⚡ Monitoreo CIE - Control en Tiempo Real")
st.markdown("### Gestión de envíos y plazos")

# Función para abreviar las determinaciones
def abreviar_analisis(texto):
    if not isinstance(texto, str):
        return texto
    
    # Diccionario de traducciones (puedes añadir más aquí)
    mapeo = {
        "2,6-di-tert-Butyl-p-Cresol and 2,6-di-tert-Butyl Phenol by IR Manual": "Contenido de Inhibidor",
        "Conteo de Partículas en Aceite Mineral Aislante por el Contador de Partículas Automático": "Conteo de Particulas",
        "Densidad, densidad relativa y gravedad API de líquidas por densitómetro(Densidad a 15ºC)": "Densidad"
    }
    
    # Buscamos si el texto largo existe en nuestro diccionario
    for largo, corto in mapeo.items():
        if largo in texto:
            return corto
    return texto

# Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_datos = conn.read(ttl=0)
    
    # Limpieza de columna Enviado
    if 'Enviado' in df_datos.columns:
        df_datos['Enviado'] = df_datos['Enviado'].fillna(False).astype(bool)
    else:
        df_datos.insert(0, 'Enviado', False)

    # Formateo de fechas
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True, errors='coerce')
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True, errors='coerce')

    # --- APLICAR ABREVIACIONES ---
    if 'Determinaciones' in df_datos.columns:
        df_datos['Determinaciones'] = df_datos['Determinaciones'].apply(abreviar_analisis)

    # Sidebar y Filtros
    st.sidebar.header("Filtros")
    busqueda = st.sidebar.text_input("🔍 Buscar Projob, Cliente o Análisis:")
    solo_pendientes = st.sidebar.checkbox("Ver solo pendientes", value=False)
    
    df_filtrado = df_datos.copy()
    if busqueda:
        df_filtrado = df_filtrado[df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
    if solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Enviado'] == False]

    # Métricas
    hoy = date.today()
    pendientes = df_filtrado[df_filtrado['Enviado'] == False]
    vencidos = len(pendientes[pendientes['Fecha Requerida'].dt.date <= hoy].dropna(subset=['Fecha Requerida']))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Muestras Totales", len(df_filtrado))
    c2.metric("Pendientes", len(pendientes))
    c3.metric("🚨 Urgentes", vencidos)

    # Acción Masiva
    if st.button("✅ Marcar TODO como Enviado"):
        df_datos['Enviado'] = True
        conn.update(data=df_datos)
        st.success("Sincronización masiva completada")
        st.rerun()

    # Preparar tabla final
    df_display = df_filtrado.copy()
    df_display['F. Ingreso'] = df_display['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_display['F. Requerida'] = df_display['Fecha Requerida'].dt.strftime('%d-%m-%Y')
    
    cols_vista = ['Enviado', 'Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Requerida', 'Descripción']
    cols_finales = [c for c in cols_vista if c in df_display.columns or c in ['F. Ingreso', 'F. Requerida']]

    res = st.data_editor(
        df_display[cols_finales],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Determinaciones": st.column_config.TextColumn("🔬 Análisis", width="medium"),
        },
        disabled=['Projob', 'Cliente', 'Determinaciones', 'F. Ingreso', 'F. Requerida', 'Descripción'],
        key="main_table"
    )

    if st.button("💾 Guardar Cambios Manuales"):
        for i, row in res.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        conn.update(data=df_datos)
        st.toast("¡Sincronizado!", icon="✅")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
