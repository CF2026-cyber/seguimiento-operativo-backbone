import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

# Configuración inicial de la página
st.set_page_config(page_title="Seguimiento Operativo - Backbone", layout="wide")

# Función para conectar a la base de datos e inicializar tablas
def get_connection():
    conn = sqlite3.connect("operaciones_backbone.db")
    cursor = conn.cursor()
    
    # Crear la tabla de regiones si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
    """)
    
    # Crear la tabla de técnicos si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            region_id INTEGER
        )
    """)
    
    # Crear la tabla de tareas si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pilar TEXT,
            descripcion TEXT,
            region_id INTEGER,
            tecnico_id INTEGER,
            estado TEXT,
            fecha_creacion TEXT
        )
    """)
    
    # Insertar valores por defecto si las tablas están vacías
    cursor.execute("SELECT COUNT(*) FROM regiones")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO regiones (nombre) VALUES ('Nacional / General')")
        cursor.execute("INSERT INTO tecnicos (nombre, region_id) VALUES ('Sin Asignar', 1)")
        conn.commit()
        
    return conn

# Inicializamos la conexión a la base de datos
conn = get_connection()

# --- INTERFAZ GRÁFICA PRINCIPAL ---
st.title("🛡️ Seguimiento Operativo - Backbone")
st.subheader("Sistema de Gestión y Control - Seguridad Física Fnet")

# Pestañas de navegación para organizar el sistema operativo
tab1, tab2, tab3, tab4 = st.tabs(["📋 Panel Principal", "➕ Registrar Tarea", "📊 Reportes y Datos", "🗺️ Mapa Operativo"])

with tab1:
    st.markdown("### Estado General de Operaciones")
    st.success("Base de datos conectada correctamente. Las tablas están activas.")
    
    # Consulta rápida de tareas para mostrar en pantalla
    df_tareas = pd.read_sql("SELECT * FROM tareas", conn)
    if not df_tareas.empty:
        st.dataframe(df_tareas, use_container_width=True)
    else:
        st.info("Aún no hay tareas registradas en el sistema. Utiliza la pestaña 'Registrar Tarea' para comenzar.")

with tab2:
    st.markdown("### Registro de Nuevas Tareas / Actividades")
    with st.form("form_tarea"):
        pilar = st.selectbox("Seleccione el Pilar", ["Operativo", "Administrativo", "Infraestructura", "Logística"])
        descripcion = st.text_area("Descripción de la Tarea o Novedad")
        
        # Cargar regiones para el formulario
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM regiones")
        regiones = cursor.fetchall()
        regiones_dict = {nombre: rid for rid, nombre in regiones}
        
        region_seleccionada = st.selectbox("Región / Zona", list(regiones_dict.keys()))
        
        submitted = st.form_submit_button("Guardar Tarea")
        if submitted:
            if descripcion.strip() != "":
                reg_id = regiones_dict[region_seleccionada]
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO tareas (pilar, descripcion, region_id, tecnico_id, estado, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pilar, descripcion, reg_id, 1, "Pendiente", fecha_actual))
                conn.commit()
                st.success("¡Tarea registrada con éxito!")
                st.rerun()
            else:
                st.warning("Por favor, complete la descripción de la tarea.")

with tab3:
    st.markdown("### Análisis y Métricas")
    st.write("Aquí podrás visualizar el estado de cumplimiento y métricas del personal operativo.")
    if not df_tareas.empty:
        st.metric(label="Total de Tareas Registradas", value=len(df_tareas))
    else:
        st.write("Sin datos suficientes para mostrar métricas.")

with tab4:
    st.markdown("### Visualización Geográfica")
    st.write("Mapa de despliegue operativo en tiempo real.")
    
    # Mapa base con Folium de ejemplo
    m = folium.Map(location=[-34.6037, -58.3816], zoom_start=11) # Centrado en Buenos Aires por defecto
    st_folium(m, width=700, height=450)
