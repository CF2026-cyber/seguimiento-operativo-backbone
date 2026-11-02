import pandas as pd
import sqlite3
import os

def procesar_archivo_excel(ruta_archivo):
    print("===================================================")
    print(f"   Procesando: {ruta_archivo}")
    print("===================================================\n")

    if not os.path.exists(ruta_archivo):
        print(f"[ERROR] No se encuentra el archivo {ruta_archivo}")
        return

    conn = sqlite3.connect("operaciones_backbone.db")
    cursor = conn.cursor()

    try:
        xls = pd.ExcelFile(ruta_archivo)
        
        # Verificar si existe la hoja Backbone o similar
        hoja_objetivo = "Backbone" if "Backbone" in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=hoja_objetivo)

        registros_procesados = 0
        actualizados = 0
        nuevos = 0

        for index, row in df.iterrows():
            contrato = str(row.get('Contrato', 'General'))
            pilar = str(row.get('Tecnologia', 'General'))
            ticket = str(row.get('Ticket', f"SIN-TICKET-{index}"))
            cliente = str(row.get('Cliente', ''))
            localidad = str(row.get('Localidad', ''))
            fecha = str(row.get('Fecha', ''))
            descripcion = str(row.get('Detalle Tarea', ''))
            estado = str(row.get('ESTADO', 'Pendiente'))
            tecnico = str(row.get('Tecnico', 'Sin Asignar'))

            if ticket == 'nan' or ticket == '':
                continue

            # Verificar si el ticket ya existe en la base de datos (para actualizar sin duplicar)
            cursor.execute("id FROM tareas WHERE descripcion LIKE ?", (f"%[Ticket: {ticket}]%",))
            existe = cursor.fetchone()

            pilar_completo = f"{contrato} - {pilar}"
            detalle_completo = f"Cliente: {cliente} | Localidad: {localidad} | Detalle: {descripcion} [Ticket: {ticket}]"

            if existe:
                # Actualizar estado y detalles si ya estaba cargado
                cursor.execute("""
                    UPDATE tareas 
                    SET estado = ?, pilar = ?, descripcion = ?
                    WHERE id = ?
                """, (estado, pilar_completo, detalle_completo, existe[0]))
                actualizados += 1
            else:
                # Insertar nueva tarea si no existía
                cursor.execute("""
                    INSERT INTO tareas (pilar, descripcion, region_id, estado, fecha_creacion)
                    VALUES (?, ?, 1, ?, ?)
                """, (pilar_completo, detalle_completo, estado, fecha if fecha != 'nan' else None))
                nuevos += 1

            registros_procesados += 1

        conn.commit()
        print(f"[ÉXITO] Procesamiento finalizado.")
        print(f"   - Registros evaluados: {registros_procesados}")
        print(f"   - Nuevas tareas incorporadas: {nuevos}")
        print(f"   - Tareas actualizadas: {actualizados}")

    except Exception as e:
        print(f"[ERROR] Ocurrió un error al procesar el archivo: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    # Permite buscar cualquier archivo excel en la carpeta de forma dinámica
    archivos_excel = [f for f in os.listdir(".") if f.endswith('.xlsx') and not f.startswith('~$')]
    
    if archivos_excel:
        # Tomar el archivo de seguimiento más reciente o el especificado
        archivo_a_usar = archivos_excel[0] 
        procesar_archivo_excel(archivo_a_usar)
    else:
        print("[AVISO] No se encontraron archivos Excel para procesar.")