# -*- coding: utf-8 -*-
"""
Created on Tue Apr 22 10:09:51 2025

@author: jperezr
"""

import streamlit as st
import pandas as pd
import sqlite3
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(page_title="Tablero Geoespacial FGJCDMX", layout="wide")

# -----------------------------
# Conexión a la base de datos
# -----------------------------
def conectar_base_datos(nombre_db, contrasena):
    contrasena_correcta = "admin123"
    if contrasena == contrasena_correcta:
        try:
            conn = sqlite3.connect(nombre_db)
            return conn, True  # Retorna la conexión y un True para indicar éxito
        except sqlite3.Error as e:
            st.error(f"Error al conectar a la base de datos: {e}")
            return None, False
    else:
        st.error("Contraseña incorrecta.")
        return None, False

# Interfaz para que el usuario ingrese la base de datos y la contraseña
st.sidebar.header("Conexión a la Base de Datos")
base_datos_usuario = st.sidebar.text_input("Introduce el nombre de la base de datos", "incidencia_cdmx.db")
contrasena_usuario = st.sidebar.text_input("Introduce la contraseña", type="password")

# Definir una variable de conexión que sea inicializada en None
conn = None

# Botón para intentar conectar
if st.sidebar.button("Conectar"):
    if base_datos_usuario and contrasena_usuario:
        conn, exito = conectar_base_datos(base_datos_usuario, contrasena_usuario)
        if exito:
            st.sidebar.success(f"✅ Se estableció la conexión con la base de datos: {base_datos_usuario}")
        else:
            st.sidebar.error("❌ No se pudo conectar. Verifica la base de datos y la contraseña.")
    else:
        st.sidebar.error("❌ Por favor, completa todos los campos.")

# -----------------------------
# Cargar datos desde SQLite
# -----------------------------
@st.cache_data
def cargar_datos(_conn):
    query = '''
    SELECT d.id, d.fecha AS Fecha, a.nombre AS Alcaldía, d.tipo_delito AS "Tipo de delito", 
           d.latitud AS Latitud, d.longitud AS Longitud
    FROM delitos d
    JOIN alcaldias a ON d.alcaldia_id = a.id
    '''
    try:
        df = pd.read_sql_query(query, _conn, parse_dates=['Fecha'])
        return df
    except Exception as e:
        st.error(f"Error al ejecutar la consulta SQL: {e}")
        return pd.DataFrame()

# Verificar si la conexión es exitosa antes de intentar cargar los datos
if conn:
    data = cargar_datos(conn)

    # -----------------------------
    # Interfaz Streamlit
    # -----------------------------
    st.title("📍 Tablero Geoespacial de Incidencia Delictiva - CDMX")

    st.sidebar.header("Filtros")
    alcaldias = sorted(data['Alcaldía'].unique())
    delitos = sorted(data['Tipo de delito'].unique())
    alcaldia_sel = st.sidebar.multiselect("Selecciona alcaldías", options=alcaldias, default=alcaldias)
    delito_sel = st.sidebar.multiselect("Selecciona tipo de delito", options=delitos, default=delitos)
    fecha_ini = st.sidebar.date_input("Fecha inicio", value=datetime.today() - timedelta(days=60))
    fecha_fin = st.sidebar.date_input("Fecha fin", value=datetime.today())

    # -----------------------------
    # Filtrado de datos
    # -----------------------------
    data_filtrada = data[(
        data['Alcaldía'].isin(alcaldia_sel)) &
        (data['Tipo de delito'].isin(delito_sel)) &
        (data['Fecha'] >= pd.to_datetime(fecha_ini)) &
        (data['Fecha'] <= pd.to_datetime(fecha_fin))
    ]

    # Asignar color por tipo de delito
    color_map = {
        'Robo a transeúnte': [255, 0, 0, 160],
        'Homicidio': [0, 0, 255, 160],
        'Lesiones': [0, 255, 0, 160],
        'Secuestro': [255, 255, 0, 160],
        'Extorsión': [255, 165, 0, 160]
    }
    data_filtrada['color'] = data_filtrada['Tipo de delito'].map(color_map)
    data_filtrada['Fecha_str'] = data_filtrada['Fecha'].dt.strftime("%d-%m-%Y")  # Para el tooltip

    # -----------------------------
    # Mapa interactivo con Pydeck
    # -----------------------------
    st.subheader("🗺️ Mapa de incidentes")
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(
            latitude=19.35,
            longitude=-99.15,
            zoom=10,
            pitch=40,
        ),
        layers=[
            pdk.Layer(
                'ScatterplotLayer',
                data=data_filtrada,
                get_position='[Longitud, Latitud]',
                get_fill_color='color',
                get_radius=250,
                pickable=True,
            )
        ],
        tooltip={
            "html": "<b>Delito:</b> {Tipo de delito}<br/><b>Alcaldía:</b> {Alcaldía}<br/><b>Fecha:</b> {Fecha_str}",
            "style": {"backgroundColor": "steelblue", "color": "white"}
        }
    ))

    # -----------------------------
    # Gráfico de barras
    # -----------------------------
    st.subheader("📊 Delitos por alcaldía")
    conteo = data_filtrada.groupby(['Alcaldía', 'Tipo de delito']).size().reset_index(name='Total')
    fig = px.bar(conteo, x='Alcaldía', y='Total', color='Tipo de delito', barmode='group', height=400)
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Mostrar tabla de datos
    # -----------------------------
    with st.expander("🔍 Ver datos filtrados"):
        st.dataframe(data_filtrada.reset_index(drop=True))

    # -----------------------------
    # Descarga de datos filtrados
    # -----------------------------
    @st.cache_data
    def convertir_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convertir_csv(data_filtrada)
    st.download_button("📥 Descargar datos filtrados", data=csv, file_name="datos_filtrados.csv", mime='text/csv')

else:
    st.warning("🔒 No se ha establecido conexión con la base de datos. Por favor, ingresa la contraseña correcta para continuar.")
