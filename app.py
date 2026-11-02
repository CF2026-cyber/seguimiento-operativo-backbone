import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Seguimiento Operativo - Backbone", layout="wide")

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
    
    # Crear la tabla de tecnicos si no existe
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
    
    # Insertar una región y técnico por defecto si está vacía
    cursor.execute("SELECT COUNT(*) FROM regiones")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO regiones (nombre) VALUES ('Nacional / General')")
        cursor.execute("INSERT INTO tecnicos (nombre, region_id) VALUES ('Sin Asignar', 1)")
        conn.commit()
        
    return conn
