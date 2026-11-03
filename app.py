import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

# Configuración inicial de la página
st.set_page_config(page_title="Panel de Control y Seguimiento Operativo - Backbone", layout="wide")

# 🎨 ESTILOS CSS: Ocultar menús nativos y widgets de Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stStatusWidget {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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

# --- BARRA LATERAL (SIDEBAR LIMPIA) ---
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
                st.toast(f"✅ Archivo {uploaded_file.name}: {total_nuevos} nuevos, {total_duplicados} omitidos.", icon="📊")
            except Exception as e:
                st.toast(f"❌ Error en {uploaded_file.name}: {e}", icon="⚠️")
                
        st.success(f"¡Proceso completado! Casos nuevos incorporados: {total_nuevos}.")

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
            
            cursor.execute("SELECT COUNT(*) FROM tareas WHERE ticket = ?", (ticket_input.strip(),))
            if cursor.fetchone()[0] > 0:
                st.sidebar.warning(f"⚠️ El Ticket '{ticket_input}' ya existe.")
            else:
                cursor.execute("""
                    INSERT INTO tareas (ticket, region, pilar, descripcion, estado, fecha_creacion, fecha_cierre, nota_cierre)
                    VALUES (?, ?, ?, ?, ?, ?, '', '')
                """, (ticket_input.strip(), localidad_input, pilar_input, desc_completa, estado_input, fecha_actual))
                conn.commit()
                st.toast("¡Operación registrada con éxito!", icon="🚀")
        else:
            st.sidebar.warning("Complete el ticket y detalle.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Cierre Manual (Jefe Ops)")
df_pendientes_edicion = pd.read_sql("SELECT id, ticket, pilar, estado FROM tareas WHERE estado != 'COMPLETA'", conn)

if not df_pendientes_edicion.empty:
    tarea_opciones = {f"ID #{row['id']} - Ticket: {row['ticket']} ({row['pilar']})": row['id'] for _, row in df_pendientes_edicion.iterrows()}
    seleccion_key = st.sidebar.selectbox("Seleccionar Caso Pendiente", list(tarea_opciones.keys()))
    id_objetivo = tarea_opciones[seleccion_key]
    
    nuevo_estado_jefe = st.sidebar.selectbox("Modificar Estado", ["COMPLETA", "PROCESO", "COORDINAR", "CANCELADA"], key="est_jefe")
    nota_justificacion = st.sidebar.text_area("Nota / Justificación (Obligatoria si hay atraso)", placeholder="Motivo de corrección...")
    
    if st.sidebar.button("Aplicar Cierre Manual"):
        fecha_correccion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE tareas 
            SET estado = ?, fecha_cierre = ?, nota_cierre = ?
            WHERE id = ?
        """, (nuevo_estado_jefe, fecha_correccion, nota_justificacion, id_objetivo))
        conn.commit()
        st.toast(f"¡Caso #{id_objetivo} actualizado!", icon="🔒")
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Limpiar Base de Datos (Cero)"):
    cursor.execute("DELETE FROM tareas")
    conn.commit()
    st.toast("Base de datos reiniciada.", icon="🗑️")
    st.rerun()


# --- INTERFAZ PRINCIPAL ---
st.markdown("### ⚡ Panel de Control y Seguimiento Operativo - Backbone")
st.markdown("---")

tab_gestion, tab_mapa = st.tabs(["📊 Tablero y Gestión", "🗺️ Mapa Logístico y Cercanía"])

with tab_gestion:
    # 🔍 BARRA DE FILTROS SUPERIOR
    with st.expander("🔍 Filtros de Visualización Avanzada y Búsqueda", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            solo_pendientes = st.checkbox("Solo Mostrar Pendientes / Coordinar")
        with f_col2:
            filtro_estado = st.selectbox("Filtrar por Estado", ["Todos", "PENDIENTE", "PROCESO", "COMPLETA", "COORDINAR", "RECOORDINADA", "CANCELADA"])
        with f_col3:
            filtro_pilar = st.selectbox("Filtrar por Contrato / Pilar", ["Todos", "Demand General", "Mant ME - Nut", "Mant ME - Mediterráneo - FO", "Backbone - Electro"])

    st.markdown("")

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

    # Tarjetas de Métricas Superiores
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

    st.markdown("<br>", unsafe_allow_html=True)
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

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    
    # --- DASHBOARD ANALÍTICO MEJORADO ---
    st.markdown("#### 📊 Dashboard y Métricas Analíticas")
    
    dash_filtro = st.radio(
        "Filtrar vista del Dashboard:",
        ["General (Todos)", "🟢 Completa", "⏳ Pendiente / En Proceso", "⚠️ Con Alerta SLA (>24h)"],
        horizontal=True
    )
    
    df_dash = df_todas.copy()
    if dash_filtro == "🟢 Completa":
        df_dash = df_dash[df_dash['estado'].str.upper() == 'COMPLETA']
    elif dash_filtro == "⏳ Pendiente / En Proceso":
        df_dash = df_dash[df_dash['estado'].str.upper().isin(['PENDIENTE', 'PROCESO', 'COORDINAR'])]
    elif dash_filtro == "⚠️ Con Alerta SLA (>24h)":
        ids_con_alerta = []
        for _, row in df_dash.iterrows():
            if str(row['estado']).upper() in ['PENDIENTE', 'PROCESO', 'COORDINAR']:
                try:
                    f_cr = datetime.strptime(str(row['fecha_creacion']), "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - f_cr) > timedelta(hours=24):
                        ids_con_alerta.append(row['id'])
                except:
                    pass
        df_dash = df_dash[df_dash['id'].isin(ids_con_alerta)]

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("##### 📊 Carga por Pilar / Contrato")
        if not df_dash.empty:
            conteo_pilar = df_dash['pilar'].value_counts()
            st.bar_chart(conteo_pilar)
        else:
            st.info("Sin datos para graficar con el filtro seleccionado.")
            
    with col_g2:
        st.markdown("##### 📈 Distribución por Estado")
        if not df_dash.empty:
            conteo_estado = df_dash['estado'].value_counts()
            st.bar_chart(conteo_estado)
        else:
            st.info("Sin datos para graficar con el filtro seleccionado.")

with tab_mapa:
    st.markdown("#### 🗺️ Módulo Geográfico y Cobertura Operativa")
    st.write("Visualización cartográfica en tiempo real de los posicionamientos registrados en los archivos y cargas.")
    
    m = folium.Map(location=[-34.6037, -58.3816], zoom_start=5)
    
    coordenadas_regiones = {
        'AMBA': [-34.6037, -58.3816],
        'BUENOS AIRES': [-34.6037, -58.3816],
        'CORDOBA': [-31.4201, -64.1888],
        'ROSARIO': [-32.9468, -60.6393],
        'SANTA FE': [-31.6333, -60.7000],
        'CATAMARCA': [-28.4696, -65.7795],
        'TUCUMAN': [-26.8083, -65.2176],
        'MENDOZA': [-32.8894, -68.8458],
        'SALTA': [-24.7821, -65.4232],
        'NEUQUEN': [-38.9516, -68.0591]
    }
    
    df_mapa_data = pd.read_sql("SELECT DISTINCT region, ticket, pilar, descripcion FROM tareas", conn)
    
    if not df_mapa_data.empty:
        for _, row in df_mapa_data.iterrows():
            reg_key = str(row['region']).strip().upper()
            coords = [-34.6037, -58.3816]
            for key, val in coordenadas_regiones.items():
                if key in reg_key:
                    coords = val
                    break
            
            popup_text = f"<b>Ticket:</b> {row['ticket']}<br><b>Región:</b> {row['region']}<br><b>Pilar:</b> {row['pilar']}"
            
            # Corrección aplicada aquí (separación del Popup limpio)
            popup_popup = folium.Popup(popup_text, max_width=300)
            folium.Marker(
                location=coords,
                popup=popup_popup,
                tooltip=f"Región: {row['region']} (Ticket: {row['ticket']})"
            ).add_to(m)
            
    st_folium(m, width=1100, height=550)
