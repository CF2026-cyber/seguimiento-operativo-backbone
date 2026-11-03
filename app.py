import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium

# Configuración inicial de la página
st.set_page_config(page_title="Panel de Control y Seguimiento Operativo - Backbone", layout="wide")

# Función para conectar a la base de datos e inicializar tablas
def get_connection():
    conn = sqlite3.connect("operaciones_backbone.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            region_id INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT,
            pilar TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion TEXT
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM regiones")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO regiones (nombre) VALUES ('AMBA')")
        cursor.execute("INSERT INTO regiones (nombre) VALUES ('Interior')")
        cursor.execute("INSERT INTO tecnicos (nombre, region_id) VALUES ('Francisbel Salazar', 1)")
        cursor.execute("INSERT INTO tecnicos (nombre, region_id) VALUES ('Darío Morais', 2)")
        conn.commit()
        
    return conn

conn = get_connection()
cursor = conn.cursor()

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.markdown("### 📁 Ingesta Masiva (Excel)")
uploaded_files = st.sidebar.file_uploader("Arrastra tus archivos Excel / CSV", type=["xlsx", "xls", "csv"], accept_multiple_files=True)

if uploaded_files:
    if st.sidebar.button("⚙️ Procesar e Importar Archivos"):
        total_nuevos = 0
        for uploaded_file in uploaded_files:
            try:
                df_temp = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded_file)
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for _, row in df_temp.iterrows():
                    reg = str(row.get('Región', row.get('region', row.get('Zona', 'AMBA'))))
                    pil = str(row.get('Pilar', row.get('pilar', row.get('Contrato', 'Demand General'))))
                    desc = str(row.get('Descripción', row.get('descripcion', row.get('Detalle', 'Carga Masiva Excel'))))
                    est = str(row.get('Estado', row.get('estado', 'PENDIENTE'))).upper()
                    
                    cursor.execute("""
                        INSERT INTO tareas (region, pilar, descripcion, estado, fecha_creacion)
                        VALUES (?, ?, ?, ?, ?)
                    """, (reg, pil, desc, est, fecha_actual))
                    total_nuevos += 1
                conn.commit()
                st.sidebar.success(f"¡{uploaded_file.name} importado ({len(df_temp)} registros)!")
            except Exception as e:
                st.sidebar.error(f"Error procesando {uploaded_file.name}: {e}")
        st.sidebar.success(f"¡Proceso finalizado! Se registraron {total_nuevos} filas en total.")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Carga Manual Inmediata")

with st.sidebar.form("form_carga_manual", clear_on_submit=True):
    pilar_input = st.selectbox("Contrato / Proyecto", ["Demand General", "Mant ME - Nut", "Mant ME - Mediterráneo - FO", "Backbone - Electro"])
    localidad_input = st.selectbox("Localidad", ["AMBA", "Córdoba", "Rosario", "Catamarca"])
    cliente_input = st.text_input("Cliente / Sitio", placeholder="Ej: CLIENTE ARGENTINA S.A.")
    ticket_input = st.text_input("N° de Boleta", placeholder="T4-26-0000")
    detalle_input = st.text_area("Detalle de la Tarea", placeholder="Describa la novedad u operación...")
    estado_input = st.selectbox("Estado Inicial", ["PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"])
    
    submit_tarea = st.form_submit_button("Registrar Tarea")
    
    if submit_tarea:
        if detalle_input.strip() and ticket_input.strip():
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            desc_completa = f"Ticket: {ticket_input} | Cliente: {cliente_input} | Detalle: {detalle_input.strip()}"
            
            cursor.execute("SELECT COUNT(*) FROM tareas WHERE descripcion LIKE ?", (f"%{ticket_input}%",))
            if cursor.fetchone()[0] > 0:
                st.sidebar.warning(f"⚠️ Alerta: El ticket {ticket_input} ya registra una tarea previa.")
            
            cursor.execute("""
                INSERT INTO tareas (region, pilar, descripcion, estado, fecha_creacion)
                VALUES (?, ?, ?, ?, ?)
            """, (localidad_input, pilar_input, desc_completa, estado_input, fecha_actual))
            conn.commit()
            st.sidebar.success("¡Operación registrada!")
        else:
            st.sidebar.warning("Por favor, complete el N° de boleta y el detalle.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtros de Visualización")
solo_pendientes = st.sidebar.checkbox("Solo Mostrar Tareas Pendientes / Coordinar")
filtro_estado = st.sidebar.selectbox("Filtrar por Estado", ["Todos", "PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"])
filtro_pilar = st.sidebar.selectbox("Filtrar por Contrato / Pilar", ["Todos", "Demand General", "Mant ME - Nut", "Mant ME - Mediterráneo - FO", "Backbone - Electro"])


# --- INTERFAZ PRINCIPAL ---
st.markdown("### ⚡ Panel de Control y Seguimiento Operativo - Backbone")
st.markdown("---")

tab_gestion, tab_mapa = st.tabs(["📊 Tablero y Gestión", "🗺️ Mapa Logístico y Cercanía"])

with tab_gestion:
    # Consulta general de tareas
    query_base = "SELECT * FROM tareas WHERE 1=1"
    params = []
    if solo_pendientes:
        query_base += " AND estado IN ('PENDIENTE', 'COORDINAR', 'PROCESO')"
    if filtro_estado != "Todos":
        query_base += " AND estado = ?"
        params.append(filtro_estado)
    if filtro_pilar != "Todos":
        query_base += " AND pilar = ?"
        params.append(filtro_pilar)
        
    df_todas = pd.read_sql(query_base, conn, params=params)
    total_tareas = len(df_todas)
    demoras = len(df_todas[df_todas['estado'].isin(['PENDIENTE', 'PROCESO'])]) if not df_todas.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**Responsable AMBA**")
        st.text("Francisbel Salazar")
        st.caption("🟢 17 vehículos / 15 técnicos")
    with col2:
        st.markdown("**Responsable Interior**")
        st.text("Darío Morais")
        st.caption("🟢 33 vehículos / 31 Téc.")
    with col3:
        st.markdown("**Tareas Totales**")
        st.markdown(f"### {total_tareas}")
    with col4:
        st.markdown("**Alertas de Demora (>24h)**")
        st.markdown(f"### {demoras}")

    if demoras > 0:
        st.warning(f"⚠️ Atención: Hay {demoras} tareas pendientes o en curso que superan las 24 horas sin cerrarse.")

    st.markdown("#### 📋 Tablero Dinámico de Seguimiento")

    if not df_todas.empty:
        df_mostrar = df_todas[['id', 'region', 'pilar', 'descripcion', 'estado', 'fecha_creacion']].copy()
        df_mostrar.columns = ['ID', 'Región', 'Pilar', 'Descripción', 'Estado', 'Fecha']
        df_mostrar['Alerta Demora'] = df_mostrar['Estado'].apply(lambda x: 'En Tiempo' if x == 'COMPLETA' else 'Demora')
        
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
    else:
        st.info("No hay tareas registradas con los filtros seleccionados.")

    st.markdown("---")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("#### 📊 Carga por Pilar / Contrato")
        if not df_todas.empty:
            conteo_pilar = df_todas['pilar'].value_counts()
            st.bar_chart(conteo_pilar)
        else:
            st.info("Sin datos para graficar.")
            
    with col_g2:
        st.markdown("#### 📈 Distribución por Estado")
        if not df_todas.empty:
            conteo_estado = df_todas['estado'].value_counts()
            st.bar_chart(conteo_estado)
        else:
            st.info("Sin datos para graficar.")

with tab_mapa:
    st.markdown("#### 🗺️ Módulo Geográfico y Cobertura Operativa")
    m = folium.Map(location=[-34.6037, -58.3816], zoom_start=6)
    folium.Marker([-34.6037, -58.3816], popup="Base AMBA - Francisbel Salazar", tooltip="AMBA").add_to(m)
    folium.Marker([-31.4201, -64.1888], popup="Base Córdoba - Darío Morais", tooltip="Córdoba").add_to(m)
    st_folium(m, width=1100, height=500)
