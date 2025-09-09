# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask


from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint("empresas", __name__)

@bp.route('/empresas', endpoint="empresas")
def empresas():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    empresas_list = []
    
    try:
        # Conectar directamente a la base de datos
        connection = mysql.connector.connect(
            host='localhost',  # Cambia por tu host
            database='gestusSG',
            user='root',  # Cambia por tu usuario
            password="Anyi#1530"  # Cambia por tu contraseña
        )
        
        cursor = connection.cursor(dictionary=True)
        
        # Obtener parámetros de búsqueda y filtrado
        buscar_nombre = request.args.get('nombre', '')
        buscar_nit = request.args.get('nit', '')
        filtrar_estado = request.args.get('estado', '')
        
        # Construir la consulta SQL dinámicamente
        query = "SELECT nit_empresa, nombre, estado, certificado_representacion FROM empresas WHERE 1=1"
        params = []
        
        if buscar_nombre:
            query += " AND nombre LIKE %s"
            params.append(f"%{buscar_nombre}%")
        
        if buscar_nit:
            query += " AND nit_empresa LIKE %s"
            params.append(f"%{buscar_nit}%")
        
        if filtrar_estado and filtrar_estado != 'Todos los estados':
            query += " AND estado = %s"
            params.append(filtrar_estado)
        
        query += " ORDER BY nombre"
        
        cursor.execute(query, params)
        empresas_list = cursor.fetchall()
        
    except mysql.connector.Error as e:
        print(f"Error al consultar empresas: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return render_template('empresas.html', 
                            empresas=empresas_list,
                            buscar_nombre=buscar_nombre,
                            buscar_nit=buscar_nit,
                            filtrar_estado=filtrar_estado)




@bp.route('/cambiar_estado_empresa', methods=['POST'], endpoint="cambiar_estado_empresa")
def cambiar_estado_empresa():
    # Lógica para cambiar estado
    data = request.get_json()
    nit = data.get('nit')
    nuevo_estado = data.get('estado')
    
    try:
        # Conectar directamente a la base de datos
        connection = mysql.connector.connect(
            host='localhost',  # Cambia por tu host
            database='gestusSG',
            user='root',  # Cambia por tu usuario
            password="Anyi#1530"  # Cambia por tu contraseña
        )
        cursor = connection.cursor()
        cursor.execute("UPDATE empresas SET estado = %s WHERE nit_empresa = %s", (nuevo_estado, nit))
        connection.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error al cambiar estado: {e}")
        return {"success": False}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'connection' in locals(): connection.close()
    


@bp.route('/editar_empresa/<nit>', methods=['GET', 'POST'], endpoint="editar_empresa")
def editar_empresa(nit):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    connection = mysql.connector.connect(
        host='localhost',
        database='gestusSG',
        user='root',
        password="Anyi#1530"
    )
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        nombre = request.form['nombre']
        archivo = request.files.get('certificado')

        certificado_url = None
        if archivo and archivo.filename:
            nombre_seguro = secure_filename(archivo.filename)
            ruta_archivo = os.path.join(UPLOAD_CERT_FOLDER, f"{nit}_{nombre_seguro}")
            archivo.save(ruta_archivo)

            certificado_url = f"{nit}_{nombre_seguro}"

            cursor.execute("""
                UPDATE empresas 
                SET nombre = %s, certificado_representacion = %s
                WHERE nit_empresa = %s
            """, (nombre, certificado_url, nit))
        else:
            cursor.execute("""
                UPDATE empresas 
                SET nombre = %s
                WHERE nit_empresa = %s
            """, (nombre, nit))

        connection.commit()
        flash("Empresa actualizada correctamente", "success")
        cursor.close()
        connection.close()
        return redirect(url_for('empresas'))

    # -------------------------------
    # GET: cargar datos de la empresa
    # -------------------------------
    cursor.execute("SELECT * FROM empresas WHERE nit_empresa = %s", (nit,))
    empresa = cursor.fetchone()
    cursor.close()
    connection.close()

    if empresa:
        return render_template('editar_empresa.html', empresa=empresa)
    else:
        flash("Empresa no encontrada", "error")
        return redirect(url_for('empresas'))



