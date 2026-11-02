import sqlite3

def inicializar_db():
    conn = sqlite3.connect("operaciones_backbone.db")
    cursor = conn.cursor()

    # 1. Tabla de Regiones / Responsables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            responsable TEXT NOT NULL,
            vehiculos_totales INTEGER,
            tecnicos_totales INTEGER
        )
    ''')

    # 2. Tabla de Bases Operativas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_id INTEGER,
            nombre_base TEXT NOT NULL,
            FOREIGN KEY (region_id) REFERENCES regiones (id)
        )
    ''')

    # 3. Tabla de Personal Técnico
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tecnicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            base_id INTEGER,
            FOREIGN KEY (base_id) REFERENCES bases (id)
        )
    ''')

    # 4. Tabla de Tareas y Seguimiento
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tareas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pilar TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            region_id INTEGER,
            tecnico_id INTEGER,
            estado TEXT DEFAULT 'Pendiente',
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (region_id) REFERENCES regiones (id),
            FOREIGN KEY (tecnico_id) REFERENCES tecnicos (id)
        )
    ''')

    # Carga de Regiones Principales
    cursor.execute("INSERT OR IGNORE INTO regiones (id, nombre, responsable, vehiculos_totales, tecnicos_totales) VALUES (1, 'AMBA', 'Francisbel Salazar', 17, 15)")
    cursor.execute("INSERT OR IGNORE INTO regiones (id, nombre, responsable, vehiculos_totales, tecnicos_totales) VALUES (2, 'Interior', 'Dario Morais', 33, 33)")

    # Carga de Bases
    bases_data = [
        # AMBA
        (1, "Base AMBA Corporativo"),
        # Interior - BALP
        (2, "BALP - Base Azul"), (2, "BALP - Base Bahía Blanca"), (2, "BALP - Base Junín"), (2, "BALP - Base La Pampa"), (2, "BALP - Base MDQ"),
        # Interior - Cuyo / Med.
        (2, "Cuyo - Base Córdoba"), (2, "Cuyo - Base Mendoza"), (2, "Cuyo - Base Río Cuarto"),
        # Interior - Litoral
        (2, "Litoral - Base Rosario"), (2, "Litoral - Base Posadas"), (2, "Litoral - Base Corrientes"), (2, "Litoral - Base Formosa"), (2, "Litoral - Base Goya"), (2, "Litoral - Base Paraná"), (2, "Litoral - Base Resistencia"),
        # Interior - NOA
        (2, "NOA - Base Tucumán"), (2, "NOA - Base Salta"), (2, "NOA - Base Catamarca"),
        # Interior - Patagonia
        (2, "Patagonia - Base Ushuaia"), (2, "Patagonia - Base Río Grande"), (2, "Patagonia - Base Trelew"), (2, "Patagonia - Base Comodoro Rivadavia"), (2, "Patagonia - Base Río Gallegos")
    ]
    cursor.executemany("INSERT OR IGNORE INTO bases (region_id, nombre_base) VALUES (?, ?)", bases_data)

    # Carga Inicial de Técnicos AMBA
    tecnicos_amba = [
        ("Vega, Emmanuel Ezequiel", 1), ("Acevedo, Tomas German", 1), ("Ziegan, Alexis Gabriel", 1),
        ("Marelli, Sergio Eduardo", 1), ("Zamudio, Leandro Gaston", 1), ("Alvarez, Pedro Martin", 1),
        ("Gutierrez, Gustavo Roberto", 1), ("Miranda, Leandro Ezequiel", 1), ("Corvalan, Leandro Guido", 1),
        ("Saucedo Daniel Hector", 1), ("Villalba, Nicolas Alberto", 1), ("Sanchez, Pablo Esteban", 1),
        ("Becerra, Sergio Luis", 1), ("Guzman, Hernan Javier", 1), ("Zabala, Hernan Alberto", 1),
        ("Flores, Gonzalo Félix", 1), ("Gallo, Emanuel", 1), ("Saucedo, Juan Alejandro", 1),
        ("Burgueño, Jonathan Ezequiel", 1)
    ]
    cursor.executemany("INSERT OR IGNORE INTO tecnicos (nombre, base_id) VALUES (?, ?)", tecnicos_amba)

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    inicializar_db()