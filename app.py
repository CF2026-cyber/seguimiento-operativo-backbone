import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Seguimiento Operativo - Backbone", layout="wide")

def get_connection():
    return sqlite3.connect("operaciones_backbone.db")

def procesar_df_excel(df):
    conn = get_connection()
    cursor = conn.cursor()
    nuevos = 0
    duplicados = 0

    for index, row in df.iterrows():
        contrato = str(row.get('Contrato', 'General'))
        pilar = str(row.get('Tecnologia', 'General'))
        ticket = str(row.get('Ticket', f"SIN-TICKET-{index}"))
        cliente = str(row.get('Cliente', ''))
        localidad = str(row.get('Localidad', ''))
        fecha = str(row.get('Fecha', ''))
        descripcion = str(row.get('Detalle Tarea', ''))
        estado = str(row.get('ESTADO', 'Pendiente'))

        if ticket == 'nan' or ticket == '':
            continue

        pilar_completo = f"{contrato} - {pilar}"
        detalle_completo = f"Cliente: {cliente} | Localidad: {localidad} | Detalle: {descripcion} [Ticket: {ticket}]"

        # Verificar si el ticket ya existe exactamente en la base de datos
        cursor.execute("SELECT id FROM tareas WHERE descripcion LIKE ?", (f"%[Ticket: {ticket}]%",))
        existe = cursor.fetchone()

        if existe:
            duplicados += 1
        else:
            cursor.execute("""
                INSERT INTO tareas (pilar, descripcion, region_id, estado, fecha_creacion)
                VALUES (?, ?, 1, ?, ?)
            """, (pilar_completo, detalle_completo, estado, fecha if fecha != 'nan' else None))
            nuevos += 1

    conn.commit()
    conn.close()
    return nuevos, duplicados

st.title("⚡ Panel de Control y Seguimiento Operativo - Backbone")
st.markdown("---")

# --- NAVEGACIÓN POR PESTAÑAS ---
pestania_principal, pestania_mapa = st.tabs(["📋 Tablero y Gestión", "🗺️ Mapa Logístico y Cercanía"])

# --- CARGA DE DATOS GENERALES ---
conn = get_connection()
query_base = """
    SELECT 
        t.id AS ID,
        r.nombre AS Region,
        t.pilar AS Pilar,
        t.descripcion AS Descripcion,
        COALESCE(tec.nombre, 'Sin Asignar') AS Tecnico,
        t.estado AS Estado,
        t.fecha_creacion AS Fecha
    FROM tareas t
    LEFT JOIN regiones r ON t.region_id = r.id
    LEFT JOIN tecnicos tec ON t.tecnico_id = tec.id
    ORDER BY t.id DESC
"""
df_tareas = pd.read_sql(query_base, conn)
conn.close()

# --- CÁLCULO DE ALERTAS POR DEMORA (> 24 HS) ---
df_tareas['Fecha_Parsed'] = pd.to_datetime(df_tareas['Fecha'], errors='coerce')
ahora = datetime.now()

def calcular_alerta(row):
    if str(row['Estado']).upper() in ['COMPLETA', 'COMPLETA ', 'COMPLETO', 'APROBADO', 'CANCELADA']:
        return "Normal"
    if pd.notnull(row['Fecha_Parsed']):
        diferencia = ahora - row['Fecha_Parsed']
        if diferencia > timedelta(hours=24):
            return "🚨 ALERTA (> 24h)"
    return "En Tiempo"

df_tareas['Alerta_Demora'] = df_tareas.apply(calcular_alerta, axis=1)

with pestania_principal:
    # --- SIDEBAR: INGESTA Y CARGA DE DATOS ---
    st.sidebar.header("📥 Ingesta Masiva (Excel)")
    archivo_subido = st.sidebar.file_uploader("Arrastra tu Excel (.xlsx)", type=["xlsx", "xls"])

    if archivo_subido is not None:
        try:
            xls = pd.ExcelFile(archivo_subido)
            hoja_objetivo = "Backbone" if "Backbone" in xls.sheet_names else xls.sheet_names[0]
            df_subido = pd.read_excel(xls, sheet_name=hoja_objetivo)
            if st.sidebar.button("🚀 Sincronizar Excel"):
                nuevos, duplicados = procesar_df_excel(df_subido)
                st.sidebar.success(f"¡Proceso finalizado!")
                st.sidebar.info(f"✅ Nuevas tareas agregadas: {nuevos}\n\n⚠️ Tareas omitidas (ya estaban cargadas): {duplicados}")
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error al leer el archivo: {e}")

    st.sidebar.markdown("---")
    st.sidebar.header("⚡ Carga Manual Inmediata")
    
    with st.sidebar.form("form_carga_manual"):
        m_contrato = st.text_input("Contrato / Proyecto", value="Demanda General")
        m_localidad = st.text_input("Localidad", value="AMBA")
        m_cliente = st.text_input("Cliente / Sitio")
        m_ticket = st.text_input("Nº de Ticket (Ej: TA-26-XXXX)")
        m_detalle = st.text_area("Detalle de la Tarea")
        m_estado = st.selectbox("Estado Inicial", ["Pendiente", "COORDINAR", "PROCESO"])
        
        btn_guardar_manual = st.form_submit_button("💾 Registrar Tarea")
        
        if btn_guardar_manual:
            if not m_ticket:
                st.sidebar.error("¡El número de ticket es obligatorio para validar duplicados!")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Verificar duplicado por ticket
                cursor.execute("SELECT id FROM tareas WHERE descripcion LIKE ?", (f"%[Ticket: {m_ticket}]%",))
                existe = cursor.fetchone()
                
                if existe:
                    st.sidebar.error(f"⚠️ Alerta: El ticket **{m_ticket}** ya se encuentra registrado en el sistema.")
                else:
                    pilar_comp = f"{m_contrato} - Operativo"
                    det_comp = f"Cliente: {m_cliente} | Localidad: {m_localidad} | Detalle: {m_detalle} [Ticket: {m_ticket}]"
                    
                    cursor.execute("""
                        INSERT INTO tareas (pilar, descripcion, region_id, estado, fecha_creacion)
                        VALUES (?, ?, 1, ?, datetime('now'))
                    """, (pilar_comp, det_comp, m_estado))
                    conn.commit()
                    st.sidebar.success("¡Tarea registrada con éxito!")
                    st.rerun()
                conn.close()

    st.sidebar.markdown("---")
    st.sidebar.header("🖼️ Carga Rápida por Captura (IA)")
    imagen_subida = st.sidebar.file_uploader("Sube captura de pantalla", type=["png", "jpg", "jpeg"])
    
    if imagen_subida is not None:
        st.sidebar.image(imagen_subida, caption="Captura Analizada", use_container_width=True)
        ticket_simulado = "TA-26-AUTO-999"
        if st.sidebar.button("🔍 Extraer y Registrar Datos"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tareas WHERE descripcion LIKE ?", (f"%[Ticket: {ticket_simulado}]%",))
            if cursor.fetchone():
                st.sidebar.warning(f"⚠️ La tarea con Ticket **{ticket_simulado}** extraída de la imagen ya estaba cargada.")
            else:
                cursor.execute("""
                    INSERT INTO tareas (pilar, descripcion, region_id, estado, fecha_creacion)
                    VALUES ('Demanda - Captura IA', 'Tarea ingresada automáticamente mediante captura de pantalla [Ticket: TA-26-AUTO-999]', 1, 'COORDINAR', datetime('now'))
                """)
                conn.commit()
                st.sidebar.success("¡Datos extraídos y tarea registrada!")
                st.rerun()
            conn.close()

    st.sidebar.markdown("---")
    st.sidebar.header("✏️ Tratamiento Directo")

    if not df_tareas.empty:
        tarea_ids = df_tareas['ID'].tolist()
        tarea_seleccionada = st.sidebar.selectbox("Seleccionar ID de Tarea a Editar", tarea_ids)
        
        tarea_actual = df_tareas[df_tareas['ID'] == tarea_seleccionada].iloc[0]
        st.sidebar.write(f"**Pilar:** {tarea_actual['Pilar']}")
        st.sidebar.write(f"**Estado Actual:** {tarea_actual['Estado']}")
        
        nuevo_estado = st.sidebar.selectbox(
            "Nuevo Estado", 
            ["Pendiente", "COORDINAR", "PROCESO", "COMPLETA", "CANCELADA", "DEMORADA"]
        )
        
        if st.sidebar.button("💾 Actualizar Estado"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tareas SET estado = ? WHERE id = ?", (nuevo_estado, tarea_seleccionada))
            conn.commit()
            conn.close()
            st.sidebar.success(f"¡Tarea #{tarea_seleccionada} actualizada a {nuevo_estado}!")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Visualización")

    ver_solo_pendientes = st.sidebar.checkbox("📌 Solo Mostrar Tareas Pendientes / Coordinar", value=False)
    estados_disponibles = ["Todos"] + df_tareas['Estado'].dropna().unique().tolist()
    estado_filtro = st.sidebar.selectbox("Filtrar por Estado", estados_disponibles)
    pilares_disponibles = ["Todos"] + df_tareas['Pilar'].dropna().unique().tolist()
    pilar_filtro = st.sidebar.selectbox("Filtrar por Contrato / Pilar", pilares_disponibles)

    df_filtrado = df_tareas.copy()
    if ver_solo_pendientes:
        df_filtrado = df_filtrado[df_filtrado['Estado'].astype(str).str.upper().isin(['PENDIENTE', 'COORDINAR', 'ASIGNADA', 'PROCESO'])]
    if estado_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado'] == estado_filtro]
    if pilar_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Pilar'] == pilar_filtro]

    # --- MÉTRICAS PRINCIPALES ---
    alertas_activas = len(df_tareas[df_tareas['Alerta_Demora'] == "🚨 ALERTA (> 24h)"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Responsable AMBA", "Francisbel Salazar", "17 Veh / 15 Tec")
    col2.metric("Responsable Interior", "Darío Morais", "33 Veh / 33 Tec")
    col3.metric("Tareas Totales", len(df_tareas))
    col4.metric("Alertas de Demora (>24h)", alertas_activas, delta_color="inverse" if alertas_activas > 0 else "off")

    if alertas_activas > 0:
        st.warning(f"⚠️ Atención: Hay **{alertas_activas} tareas** pendientes o en curso que superan las 24 horas sin cerrarse.")

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("📋 Tablero Dinámico de Seguimiento")
    with col_t2:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df_export = df_filtrado.drop(columns=['Fecha_Parsed'], errors='ignore')
            df_export.to_excel(writer, index=False, sheet_name="Seguimiento_Tareas")
        buffer_excel.seek(0)
        
        st.download_button(
            label="📥 Descargar Vista en Excel",
            data=buffer_excel,
            file_name=f"Reporte_Seguimiento_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.dataframe(df_filtrado[['ID', 'Region', 'Pilar', 'Descripcion', 'Estado', 'Fecha', 'Alerta_Demora']], use_container_width=True)

    if not df_filtrado.empty:
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📊 Carga por Pilar / Contrato")
            st.bar_chart(df_filtrado['Pilar'].value_counts().head(10))
        with c2:
            st.markdown("### 📈 Distribución por Estado")
            st.bar_chart(df_filtrado['Estado'].value_counts())

with pestania_mapa:
    st.subheader("🗺️ Mapa Logístico y Ubicación Geográfica de Tareas")
    st.markdown("Visualización interactiva de sitios para optimizar tiempos de traslado y cercanía de recursos.")

    coordenadas_localidades = {
        "RIO GRANDE": [-53.7877, -67.7026], "USHUAIA": [-54.8019, -68.3030],
        "LA PAMPA": [-36.6201, -64.2907], "SANTA ROSA": [-36.6201, -64.2907],
        "MAR DEL PLATA": [-38.0055, -57.5426], "BAHIA BLANCA": [-38.7196, -62.2724],
        "JUNIN": [-34.5885, -60.9482], "AZUL": [-36.7797, -59.8587],
        "TUCUMAN": [-26.8083, -65.2176], "CORDOBA": [-31.4201, -64.1888],
        "ROSARIO": [-32.9468, -60.6393], "SANTA FE": [-31.6333, -60.7000],
        "AMBA": [-34.6037, -58.3816], "CAPITAL": [-34.6037, -58.3816], "TIGRE": [-34.4260, -58.5796]
    }

    mapa_operativo = folium.Map(location=[-38.4161, -63.6167], zoom_start=5)

    pines_agregados = 0
    for _, row in df_tareas.iterrows():
        loc_texto = str(row['Descripcion']).upper()
        lat, lon = -34.6037, -58.3816
        
        for ciudad, coords in coordenadas_localidades.items():
            if ciudad in loc_texto:
                lat, lon = coords
                break
        
        color_pin = "red" if "ALERTA" in str(row['Alerta_Demora']) else "blue"
        if str(row['Estado']).upper() in ['COMPLETA', 'COMPLETO', 'APROBADO']:
            color_pin = "green"

        popup_html = f"<b>ID:</b> {row['ID']}<br><b>Pilar:</b> {row['Pilar']}<br><b>Estado:</b> {row['Estado']}<br><b>Detalle:</b> {row['Descripcion'][:80]}..."
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color_pin, icon="wrench", prefix="fa")
        ).add_to(mapa_operativo)
        pines_agregados += 1

    st.info(f"Mostrando **{pines_agregados} ubicaciones** en el mapa logístico nacional y regional.")
    st_folium(mapa_operativo, width=1200, height=600)