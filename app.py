import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
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
            ticket TEXT,
            region TEXT,
            pilar TEXT,
            descripcion TEXT,
            estado TEXT,
            fecha_creacion TEXT,
            fecha_cierre TEXT,
            nota_cierre TEXT
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
    if st.sidebar.button("⚙️ Procesar por Ticket (Sin Duplicados)"):
        total_nuevos = 0
        total_duplicados = 0
        
        for uploaded_file in uploaded_files:
            try:
                df_temp = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded_file)
                df_temp.columns = [str(c).strip().lower() for c in df_temp.columns]
                
                for _, row in df_temp.iterrows():
                    # Extraer número de ticket único
                    ticket_val = str(row.get('ticket', row.get('n° de boleta', row.get('boleta', row.get('caso', 'S/N'))))).strip()
                    reg = str(row.get('región', row.get('region', row.get('zona', row.get('localidad', 'AMBA')))))
                    pil = str(row.get('pilar', row.get('contrato', row.get('proyecto', 'Demand General'))))
                    
                    partes_desc = []
                    for col in df_temp.columns:
                        val = row.get(col)
                        if pd.notna(val) and col not in ['ticket', 'n° de boleta', 'boleta', 'caso', 'región', 'region', 'zona', 'localidad', 'pilar', 'contrato', 'proyecto', 'estado', 'status', 'fecha', 'fecha_creacion']:
                            partes_desc.append(f"{col.capitalize()}: {val}")
                    
                    desc = " | ".join(partes_desc) if partes_desc else str(row.to_dict())
                    est = str(row.get('estado', row.get('status', 'PENDIENTE'))).upper()
                    fecha_raw = row.get('fecha', row.get('fecha_creacion', None))
                    fecha_creacion = str(fecha_raw) if pd.notna(fecha_raw) else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 🛡️ NORMA TÉCNICA: Control de unicidad estricto por N° de Ticket
                    if ticket_val != 'S/N' and ticket_val != '':
                        cursor.execute("SELECT COUNT(*) FROM tareas WHERE ticket = ?", (ticket_val,))
                        existe = cursor.fetchone()[0] > 0
                    else:
                        cursor.execute("SELECT COUNT(*) FROM tareas WHERE descripcion = ?", (desc,))
                        existe = cursor.fetchone()[0] > 0
                    
                    if not existe:
                        cursor.execute("""
                            INSERT INTO tareas (ticket, region, pilar, descripcion, estado, fecha_creacion, fecha_cierre, nota_cierre)
                            VALUES (?, ?, ?, ?, ?, ?, '', '')
                        """, (ticket_val, reg, pil, desc, est, fecha_creacion))
                        total_nuevos += 1
                    else:
                        total_duplicados += 1
                        
                conn.commit()
                st.sidebar.success(f"Archivo {uploaded_file.name}: {total_nuevos} nuevos, {total_duplicados} duplicados por ticket omitidos.")
            except Exception as e:
                st.sidebar.error(f"Error procesando {uploaded_file.name}: {e}")
                
        st.sidebar.success(f"¡Proceso completado! Total de casos nuevos incorporados: {total_nuevos}.")

if st.sidebar.button("🗑️ Limpiar Base de Datos (Reiniciar a Cero)"):
    cursor.execute("DELETE FROM tareas")
    conn.commit()
    st.sidebar.warning("Base de datos limpiada correctamente.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Carga Manual Inmediata")

with st.sidebar.form("form_carga_manual", clear_on_submit=True):
    pilar_input = st.selectbox("Contrato / Proyecto", ["Demand General", "Mant ME - Nut", "Mant ME - Mediterráneo - FO", "Backbone - Electro"])
    localidad_input = st.selectbox("Localidad", ["AMBA", "Córdoba", "Rosario", "Catamarca"])
    cliente_input = st.text_input("Cliente / Sitio", placeholder="Ej: CLIENTE ARGENTINA S.A.")
    ticket_input = st.text_input("N° de Boleta / Ticket", placeholder="T4-26-0000")
    detalle_input = st.text_area("Detalle de la Tarea", placeholder="Describa la novedad u operación...")
    estado_input = st.selectbox("Estado Inicial", ["PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"])
    
    submit_tarea = st.form_submit_button("Registrar Tarea")
    
    if submit_tarea:
        if detalle_input.strip() and ticket_input.strip():
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            desc_completa = f"Cliente: {cliente_input} | Detalle: {detalle_input.strip()}"
            
            # Validación por Ticket
            cursor.execute("SELECT COUNT(*) FROM tareas WHERE ticket = ?", (ticket_input.strip(),))
            if cursor.fetchone()[0] > 0:
                st.sidebar.warning(f"⚠️ El Ticket '{ticket_input}' ya se encuentra registrado en el sistema.")
            else:
                cursor.execute("""
                    INSERT INTO tareas (ticket, region, pilar, descripcion, estado, fecha_creacion, fecha_cierre, nota_cierre)
                    VALUES (?, ?, ?, ?, ?, ?, '', '')
                """, (ticket_input.strip(), localidad_input, pilar_input, desc_completa, estado_input, fecha_actual))
                conn.commit()
                st.sidebar.success("¡Operación registrada con éxito!")
        else:
            st.sidebar.warning("Por favor, complete el N° de boleta/ticket y el detalle.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Cierre Manual y Auditoría (Jefe de Operaciones)")
df_pendientes_edicion = pd.read_sql("SELECT id, ticket, pilar, estado FROM tareas WHERE estado != 'COMPLETA'", conn)

if not df_pendientes_edicion.empty:
    tarea_opciones = {f"ID #{row['id']} - Ticket: {row['ticket']} ({row['pilar']})": row['id'] for _, row in df_pendientes_edicion.iterrows()}
    seleccion_key = st.sidebar.selectbox("Seleccionar Caso Pendiente", list(tarea_opciones.keys()))
    id_objetivo = tarea_opciones[seleccion_key]
    
    nuevo_estado_jefe = st.sidebar.selectbox("Modificar Estado", ["COMPLETA", "PROCESO", "COORDINAR", "CANCELADA"], key="est_jefe")
    nota_justificacion = st.sidebar.text_area("Nota / Justificación Operativa (Obligatorio si hay fuera de fecha)", placeholder="Motivo del cierre manual...")
    
    if st.sidebar.button("Aplicar Cierre / Modificación"):
        fecha_correccion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE tareas 
            SET estado = ?, fecha_cierre = ?, nota_cierre = ?
            WHERE id = ?
        """, (nuevo_estado_jefe, fecha_correccion, nota_justificacion, id_objetivo))
        conn.commit()
        st.sidebar.success(f"¡Caso #{id_objetivo} actualizado correctamente con fecha {fecha_correccion}!")
        st.rerun()
else:
    st.sidebar.caption("No hay casos pendientes para cierre manual.")

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
    
    # Cálculo de demoras (>24h y sin cierre manual)
    demoras = 0
    ahora = datetime.now()
    if not df_todas.empty:
        for _, row in df_todas.iterrows():
            if str(row['estado']).upper() in ['PENDIENTE', 'PROCESO', 'COORDINAR']:
                try:
                    f_creacion = datetime.strptime(str(row['fecha_creacion']), "%Y-%m-%d %H:%M:%S")
                    if (ahora - f_creacion) > timedelta(hours=24):
                        demoras += 1
                except:
                    pass

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
        st.warning(f"⚠️ Atención: Hay {demoras} tareas pendientes o en curso que superan las 24 horas de SLA sin cerrarse.")

    st.markdown("#### 📋 Tablero Dinámico de Seguimiento")

    if not df_todas.empty:
        df_mostrar = df_todas[['id', 'ticket', 'region', 'pilar', 'descripcion', 'estado', 'fecha_creacion', 'fecha_cierre', 'nota_cierre']].copy()
        df_mostrar.columns = ['ID', 'Ticket', 'Región', 'Pilar', 'Descripción', 'Estado', 'Creación', 'Cierre Manual', 'Nota Auditoría']
        
        def evaluar_demora(row):
            if str(row['Estado']).upper() in ['COMPLETA', 'CANCELADA']:
                return 'Normal (Cerrado)'
            try:
                f_creacion = datetime.strptime(str(row['Creación']), "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - f_creacion) > timedelta(hours=24):
                    return 'Demora SLA (>24h)'
            except:
                pass
            return 'En Tiempo'

        df_mostrar['Alerta SLA'] = df_mostrar.apply(evaluar_demora, axis=1)
        
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
