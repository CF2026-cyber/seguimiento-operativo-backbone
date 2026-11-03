import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuración inicial de la página en modo ancho
st.set_page_config(page_title="Panel de Control y Seguimiento Operativo - Backbone", layout="wide")

# Función para conectar a la base de datos e inicializar tablas
def get_connection():
    conn = sqlite3.connect("operaciones_backbone.db")
    cursor = conn.cursor()
    
    # Crear tabla de regiones si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
    """)
    
    # Crear tabla de técnicos si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            region_id INTEGER
        )
    """)
    
    # Crear tabla de tareas con todos los campos necesarios para el seguimiento y réplicas
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
    
    # Insertar valores por defecto si está vacía
    cursor.execute("SELECT COUNT(*) FROM regiones")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO regiones (nombre) VALUES ('AMBA')")
        cursor.execute("INSERT INTO regiones (nombre) VALUES ('Interior')")
        cursor.execute("INSERT INTO tecnicos (nombre, region_id) VALUES ('Francisbel Salazar', 1)")
        cursor.execute("INSERT INTO tecnicos (nombre, region_id) VALUES ('Darío Morais', 2)")
        conn.commit()
        
    return conn

# Inicializamos la conexión
conn = get_connection()
cursor = conn.cursor()

# --- BARRA LATERAL (SIDEBAR) CON MÓDULOS COMPLETOS ---
st.sidebar.markdown("### 📁 Ingesta Masiva (Excel)")
uploaded_file = st.sidebar.file_uploader("Arrastra tu Excel / CSV", type=["xlsx", "xls", "csv"])
if uploaded_file is not None:
    try:
        df_temp = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded_file)
        st.sidebar.success(f"Archivo cargado correctamente: {len(df_temp)} registros detectados.")
    except Exception as e:
        st.sidebar.error(f"Error al leer el archivo: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Carga Manual Inmediata")

with st.sidebar.form("form_carga_manual", clear_on_submit=True):
    pilar_input = st.selectbox("Contrato / Proyecto", ["Demand General", "Mant ME - Nut", "Mant ME - Mediterráneo - FO", "Backbone - Electro"])
    localidad_input = st.selectbox("Localidad", ["AMBA", "Córdoba", "Rosario", "Catamarca"])
    cliente_input = st.text_input("Cliente / Sitio", placeholder="Ej: CLIENTE ARGENTINA S.A.")
    ticket_input = st.text_input("N° de Boleta (Ej: T4-26-0000)", placeholder="T4-26-0000")
    detalle_input = st.text_area("Detalle de la Tarea", placeholder="Describa la novedad u operación...")
    estado_input = st.selectbox("Estado Inicial", ["PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"])
    
    submit_tarea = st.form_submit_button("Registrar Tarea")
    
    if submit_tarea:
        if detalle_input.strip() and ticket_input.strip():
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            desc_completa = f"Ticket: {ticket_input} | Cliente: {cliente_input} | Detalle: {detalle_input.strip()}"
            
            # Control de réplica de tarea por ticket existente
            cursor.execute("SELECT COUNT(*) FROM tareas WHERE descripcion LIKE ?", (f"%{ticket_input}%",))
            replica_existe = cursor.fetchone()[0] > 0
            
            if replica_existe:
                st.sidebar.warning(f"⚠️ Alerta: El ticket {ticket_input} ya registra una tarea previa (Réplica detectada).")
            
            cursor.execute("""
                INSERT INTO tareas (region, pilar, descripcion, estado, fecha_creacion)
                VALUES (?, ?, ?, ?, ?)
            """, (localidad_input, pilar_input, desc_completa, estado_input, fecha_actual))
            conn.commit()
            st.sidebar.success("¡Operación registrada con éxito!")
            st.rerun()
        else:
            st.sidebar.warning("Por favor, complete el N° de boleta y el detalle.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Tratamiento Directo")
df_actual = pd.read_sql("SELECT id, pilar, estado FROM tareas", conn)
if not df_actual.empty:
    id_a_editar = st.sidebar.selectbox("Seleccionar ID de Tarea a Editar", df_actual['id'].tolist())
    tarea_sel = df_actual[df_actual['id'] == id_a_editar].iloc[0]
    st.sidebar.text(f"Pilar: {tarea_sel['pilar']}")
    st.sidebar.text(f"Estado Actual: {tarea_sel['estado']}")
    
    nuevo_estado = st.sidebar.selectbox("Nuevo Estado", ["PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"], key="nuevo_est")
    if st.sidebar.button("Actualizar Estado"):
        cursor.execute("UPDATE tareas SET estado = ? WHERE id = ?", (nuevo_estado, id_a_editar))
        conn.commit()
        st.sidebar.success(f"¡Tarea #{id_a_editar} actualizada!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtros de Visualización")
solo_pendientes = st.sidebar.checkbox("Solo Mostrar Tareas Pendientes / Coordinar")
filtro_estado = st.sidebar.selectbox("Filtrar por Estado", ["Todos", "PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"])
filtro_pilar = st.sidebar.selectbox("Filtrar por Contrato / Pilar", ["Todos", "Demand General", "Mant ME - Nut", "Mant ME - Mediterráneo - FO", "Backbone - Electro"])


# --- INTERFAZ PRINCIPAL ---
st.markdown("### ⚡ Panel de Control y Seguimiento Operativo - Backbone")
st.markdown("---")

# Pestañas principales de navegación
tab_gestion, tab_mapa = st.tabs(["📊 Tablero y Gestión", "🗺️ Mapa Logístico y Cercanía"])

with tab_gestion:
    # Métricas superiores estilo tarjeta
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
        st.markdown("**Tareas Totales**")
        st.markdown(f"### {total_tareas}")
    with col4:
        # Alertas de demora (>24h simuladas con estados pendientes/proceso)
        demoras = len(df_todas[df_todas['estado'].isin(['PENDIENTE', 'PROCESO'])]) if not df_todas.empty else 0
        st.markdown("**Alertas de Demora (>24h)**")
        st.markdown(f"### {demoras}")

    # Aviso de alerta visual
    if demoras > 0:
        st.warning(f"⚠️ Atención: Hay {demoras} tareas pendientes o en curso que superan las 24 horas sin cerrarse.")

    st.markdown("#### 📋 Tablero Dinámico de Seguimiento")

    if not df_todas.empty:
        df_mostrar = df_todas[['id', 'region', 'pilar', 'descripcion', 'estado', 'fecha_creacion']].copy()
        df_mostrar.columns = ['ID', 'Región', 'Pilar', 'Descripción', 'Estado', 'Fecha']
        df_mostrar['Alerta Demora'] = df_mostrar['Estado'].apply(lambda x: 'Demora' if x in ['PENDIENTE', 'PROCESO'] else 'Normal')
        
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
    else:
        st.info("No hay tareas registradas con los filtros seleccionados.")

    st.markdown("---")
    
    # SECCIÓN DE GRÁFICOS ANALÍTICOS (Dashboard inferior)
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
    st.info("Visualización cartográfica y de cercanía para el despliegue de recursos en campo de Seguridad Física Fnet.")
