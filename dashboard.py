import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. Configuración y Estilos de Alto Contraste
st.set_page_config(page_title="Portal CIE-OCM Pro", layout="wide")

def aplicar_estilos():
    st.markdown(
        """
        <style>
        /* Fondo con imagen y capa blanca para resaltar texto negro */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.75)), 
                        url("https://images.unsplash.com/photo-1581093588401-fbb62a02f120?q=80&w=2070");
            background-size: cover;
            background-attachment: fixed;
        }
        
        /* Títulos en Naranja Oscuro */
        h1, h2, h3, .stSubheader {
            color: #CC5500 !important;
            font-weight: 800 !important;
        }

        /* TEXTO DE MÉTRICAS - NEGRO PURO */
        [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: bold !important;
        }
        [data-testid="stMetricLabel"] {
            color: #1A1A1A !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
        }
        
        /* Tarjetas de métricas blancas sólidas */
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 1);
            border: 1px solid #DDDDDD;
            border-left: 6px solid #FF6B00;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 4px 8px rgba(0,0,0,0.15);
        }

        /* Texto de la barra lateral (Sidebar) */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label {
            color: #000000 !important;
            font-weight: bold !important;
        }

        /* Texto general */
        .stMarkdown, p, span {
            color: #000000 !important;
