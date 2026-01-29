import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# Configuración visual
st.set_page_config(page_title="Portal OCM - Control Total", layout="wide")

st.title("⚡ Monitoreo CIE - Control en Tiempo Real")
st.markdown("### Gestión de envíos y plazos")

# 1. Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leer los datos (ttl=0 para lectura siempre fresca)
    df_datos = conn.read(ttl=0)
    
    # Asegurar formatos de fecha
    df_datos['Recibido Laboratorio'] = pd.to_datetime(df_datos['Recibido Laboratorio'], dayfirst=True)
    df_datos['Fecha Requerida'] = pd.to_datetime(df_datos['Fecha Requerida'], dayfirst=True)

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Panel de Control")
    busqueda = st.sidebar.text_input("🔍 Buscar Projob o Cliente:")
    ver_solo_pendientes = st.sidebar.checkbox("Mostrar solo pendientes", value=False)
    
    # Aplicar filtros
    df_filtrado = df_datos.copy()
    if busqueda:
        mask = (df_filtrado['Projob'].astype(str).str.contains(busqueda, case=False) | 
                df_filtrado['Cliente'].astype(str).str.contains(busqueda, case=False))
        df_filtrado = df_filtrado[mask]
    if ver_solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Enviado'] == False]

    # --- MÉTRICAS ---
    hoy = date.today()
    vencidos = len(df_filtrado[(df_filtrado['Enviado'] == False) & (df_filtrado['Fecha Requerida'].dt.date <= hoy)])
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Muestras en Lista", len(df_filtrado))
    c2.metric("Pendientes", len(df_filtrado[df_filtrado['Enviado'] == False]))
    c3.metric("🚨 Urgentes (Hoy/Vencidos)", vencidos)

    # --- ACCIONES MASIVAS ---
    st.write("#### Acciones rápidas")
    col_btn1, col_btn2 = st.columns([1, 4])
    
    # BOTÓN PARA MARCAR TODO
    if col_btn1.button("✅ Marcar TODO como Enviado"):
        df_datos['Enviado'] = True
        conn.update(data=df_datos)
        st.success("Se han marcado todos los registros como enviados.")
        st.rerun()

    # --- EDITOR DE TABLA ---
    st.write("---")
    df_editor = df_filtrado.copy()
    df_editor['Ingreso'] = df_editor['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_editor['Plazo'] = df_editor['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    columnas_vista = ['Enviado', 'Projob', 'Cliente', 'Ingreso', 'Plazo', 'Descripción']

    # Aplicar estilo visual: si está vencido y no enviado, mostrar alerta
    # (El resaltado de filas completo requiere st.dataframe estándar, 
    # en data_editor lo manejamos con la métrica de alerta superior)

    edited_df = st.data_editor(
        df_editor[columnas_vista],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Plazo": "📅 Fecha Requerida",
            "Ingreso": "Fecha Ingreso"
        },
        disabled=['Projob', 'Cliente', 'Ingreso', 'Plazo', 'Descripción'],
        key="tabla_control_nube"
    )

    # --- BOTÓN DE GUARDADO MANUAL ---
    if st.button("💾 Guardar Cambios Individuales"):
        # Sincronizar cambios del editor al dataframe original
        for i, row in edited_df.iterrows():
            df_datos.loc[df_datos['Projob'] == row['Projob'], 'Enviado'] = row['Enviado']
        
        conn.update(data=df_datos)
        st.toast("Cambios guardados en la nube", icon="💾")
        st.rerun()

except Exception as e:
    st.error(f"Error de conexión: {e}")





