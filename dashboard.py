import streamlit as st
import pandas as pd
import os
from datetime import date

# Configuración visual
st.set_page_config(page_title="Dashboard OCM - Alertas CIE", layout="wide")

st.title("⚡ Monitoreo de Análisis de Aceite Dieléctrico")
st.markdown("### Control de Plazos y Envíos a Clientes")

ruta_archivo = "Reporte_Refinado.xlsx"

if os.path.exists(ruta_archivo):
    # 1. Carga de datos y persistencia
    if 'df_datos' not in st.session_state:
        df_base = pd.read_excel(ruta_archivo)
        if 'Enviado' not in df_base.columns:
            df_base['Enviado'] = False
        
        # Convertir a datetime
        df_base['Recibido Laboratorio'] = pd.to_datetime(df_base['Recibido Laboratorio'], dayfirst=True)
        if 'Fecha Requerida' in df_base.columns:
            df_base['Fecha Requerida'] = pd.to_datetime(df_base['Fecha Requerida'], dayfirst=True)
            
        st.session_state.df_datos = df_base

    # 2. Sidebar con Filtros
    st.sidebar.header("Panel de Control")
    busqueda = st.sidebar.text_input("🔍 Buscar Projob o Cliente:")
    ver_solo_pendientes = st.sidebar.checkbox("Mostrar solo pendientes de envío", value=False)
    
    df_filtrado = st.session_state.df_datos.copy()
    
    if busqueda:
        mask = (df_filtrado['Projob'].astype(str).str.contains(busqueda, case=False) | 
                df_filtrado['Cliente'].astype(str).str.contains(busqueda, case=False))
        df_filtrado = df_filtrado[mask]
        
    if ver_solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Enviado'] == False]

    # 3. Métricas con Alerta
    hoy = date.today()
    pendientes_vencidos = len(df_filtrado[(df_filtrado['Enviado'] == False) & 
                                          (df_filtrado['Fecha Requerida'].dt.date <= hoy)])

    m1, m2, m3 = st.columns(3)
    m1.metric("Muestras en Pantalla", len(df_filtrado))
    m2.metric("Pendientes Totales", len(df_filtrado[df_filtrado['Enviado'] == False]))
    m3.metric("🚨 Vencidos o Hoy", pendientes_vencidos, delta_color="inverse")

    # 4. Tabla Interactiva
    st.write("#### Detalle de Programación")
    
    df_editor = df_filtrado.copy()
    df_editor['Ingreso Lab'] = df_editor['Recibido Laboratorio'].dt.strftime('%d-%m-%Y')
    df_editor['Plazo Reporte'] = df_editor['Fecha Requerida'].dt.strftime('%d-%m-%Y')

    # Aplicar Estilos: Resaltar en rojo si está vencido y NO enviado
    def resaltar_vencidos(s):
        is_vencido = (s['Fecha Requerida'].date() <= hoy) and (not s['Enviado'])
        return ['background-color: #ff4b4b; color: white' if is_vencido else '' for _ in s]

    # Columnas a mostrar
    cols = ['Enviado', 'Projob', 'Cliente', 'Ingreso Lab', 'Plazo Reporte', 'Descripción']

    st.data_editor(
        df_editor[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enviado": st.column_config.CheckboxColumn("Enviado ✅"),
            "Plazo Reporte": "📅 Fecha Requerida",
            "Ingreso Lab": "Fecha Ingreso",
        },
        disabled=['Projob', 'Cliente', 'Ingreso Lab', 'Plazo Reporte', 'Descripción'],
        key="tabla_vencimientos"
    )

    # 5. Guardado
    if st.button("💾 Guardar y Actualizar Excel"):
        # Sincronización (basada en Projob como ID único)
        editor_state = st.session_state.tabla_vencimientos
        for i, row in df_editor.iterrows():
            # Revisar si hubo cambios en la tabla para esta fila
            # Nota: El editor de streamlit devuelve solo las filas editadas en su estado
            pass # La lógica de guardado anterior es más robusta:
        
        # Actualización simplificada para el guardado
        for i, row in st.session_state.tabla_vencimientos['edited_rows'].items():
            idx_original = df_filtrado.index[i]
            st.session_state.df_datos.at[idx_original, 'Enviado'] = row['Enviado']
            
        try:
            st.session_state.df_datos.to_excel(ruta_archivo, index=False)
            st.success("Cambios guardados. El Excel ha sido actualizado.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}. Cierre el Excel si está abierto.")

else:
    st.error("Archivo no encontrado.")

