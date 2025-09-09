# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask


from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint("documentos", __name__)

@bp.route('/documentacion', endpoint="documentacion")
def documentacion():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obtener parámetros de búsqueda
        buscar_nombre = request.args.get('nombre', '').strip()
        buscar_nit = request.args.get('nit', '').strip()
        filtrar_estado = request.args.get('estado', '')
        filtrar_formato = request.args.get('formato', '')
        
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Consulta optimizada con JOIN y filtros
        query = """
            SELECT d.*, e.nombre as nombre_empresa,
                    DATE_FORMAT(d.fecha_vencimiento, '%%d/%%m/%%Y') as fecha_vencimiento_formateada
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE 1=1
        """
        params = []
        
        if buscar_nombre:
            query += " AND d.nombre LIKE %s"
            params.append(f"%{buscar_nombre}%")
        
        if buscar_nit:
            query += " AND d.nit_empresa LIKE %s"
            params.append(f"%{buscar_nit}%")
        
        if filtrar_estado:
            query += " AND d.estado = %s"
            params.append(filtrar_estado)
        
        if filtrar_formato:
            query += " AND d.formato = %s"
            params.append(filtrar_formato)
        
        query += " ORDER BY d.fecha_vencimiento DESC, d.id DESC"
        
        cursor.execute(query, params)
        documentos = cursor.fetchall()
        
        # Calcular estado de vencimiento
        hoy = datetime.now().date()
        for doc in documentos:
            if doc['fecha_vencimiento']:
                dias_restantes = (doc['fecha_vencimiento'] - hoy).days
                doc['vencido'] = dias_restantes < 0
                doc['proximo_vencer'] = 0 <= dias_restantes <= 30
                doc['dias_restantes'] = dias_restantes
        
        return render_template('documentacion.html',
                            documentos=documentos,
                            buscar_nombre=buscar_nombre,
                            buscar_nit=buscar_nit,
                            filtrar_estado=filtrar_estado,
                            filtrar_formato=filtrar_formato)
        
    except mysql.connector.Error as e:
        print(f"Error en documentacion: {e}")
        flash('Error al cargar la documentación', 'error')
        return render_template('documentacion.html', documentos=[])
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@bp.route('/agregar_documento', endpoint="agregar_documento")
def agregar_documento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa' ORDER BY nombre")
        empresas = cursor.fetchall()
        
        cursor.execute("SELECT id, nombre FROM formatos_globales ORDER BY nombre")
        formatos_globales = cursor.fetchall()
        
        return render_template('agregar_documento.html',
                            empresas=empresas,
                            formatos_globales=formatos_globales)
        
    except mysql.connector.Error as e:
        print(f"Error en agregar_documento: {e}")
        flash('Error al cargar datos del formulario', 'error')
        return redirect(url_for('documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@bp.route('/guardar_documento', methods=['POST'], endpoint="guardar_documento")
def guardar_documento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        # Validar campos obligatorios
        nit_empresa = request.form.get('nit_empresa', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not nit_empresa or not nombre:
            flash('Empresa y nombre del documento son obligatorios', 'error')
            return redirect(url_for('agregar_documento'))
        
        # Procesar archivo
        archivo = request.files.get('archivo')
        archivo_url = None
        
        if archivo and archivo.filename:
            if not allowed_file(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('agregar_documento'))
            
            filename = secure_filename(archivo.filename)
            unique_name = f"{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            archivo_url = os.path.join(UPLOAD_FOLDER, unique_name)
            archivo.save(archivo_url)
        
        # Insertar en base de datos
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO documentos_empresa (
                nit_empresa, formato_id, nombre, 
                archivo_url, fecha_vencimiento, 
                estado, formato
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            nit_empresa,
            request.form.get('formato_id') or None,
            nombre,
            archivo_url,
            request.form.get('fecha_vencimiento') or None,
            request.form.get('estado', 'Sin Diligenciar'),
            request.form.get('formato_archivo', 'PDF')
        ))
        
        connection.commit()
        flash('Documento guardado exitosamente', 'success')
        return redirect(url_for('documentacion'))
        
    except mysql.connector.Error as e:
        print(f"Error en guardar_documento: {e}")
        flash('Error al guardar el documento', 'error')
        return redirect(url_for('agregar_documento'))
    except Exception as e:
        print(f"Error inesperado en guardar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('agregar_documento'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@bp.route('/editar_documento/<int:documento_id>', endpoint="editar_documento")
def editar_documento(documento_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener documento con JOIN para nombre de empresa
        cursor.execute("""
            SELECT d.*, e.nombre as nombre_empresa
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE d.id = %s
        """, (documento_id,))
        documento = cursor.fetchone()
        
        if not documento:
            flash('Documento no encontrado', 'error')
            return redirect(url_for('documentacion'))
        
        # Obtener datos para selects
        cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa' ORDER BY nombre")
        empresas = cursor.fetchall()
        
        cursor.execute("SELECT id, nombre FROM formatos_globales ORDER BY nombre")
        formatos_globales = cursor.fetchall()
        
        return render_template('editar_documento.html',
                            documento=documento,
                            empresas=empresas,
                            formatos_globales=formatos_globales)
        
    except mysql.connector.Error as e:
        print(f"Error en editar_documento: {e}")
        flash('Error al cargar documento', 'error')
        return redirect(url_for('documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@bp.route('/actualizar_documento/<int:documento_id>', methods=['POST'], endpoint="actualizar_documento")
def actualizar_documento(documento_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        # Validar campos obligatorios
        nit_empresa = request.form.get('nit_empresa', '').strip()
        nombre = request.form.get('nombre', '').strip()
        if not nit_empresa or not nombre:
            flash('Empresa y nombre del documento son obligatorios', 'error')
            return redirect(url_for('editar_documento', documento_id=documento_id))
        
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Procesar archivo si se subió uno nuevo
        archivo = request.files.get('archivo')
        archivo_url = None
        
        if archivo and archivo.filename:
            if not allowed_file(archivo.filename):
                flash('Tipo de archivo no permitido', 'error')
                return redirect(url_for('editar_documento', documento_id=documento_id))
            
            filename = secure_filename(archivo.filename)
            unique_name = f"{nit_empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            archivo_url = os.path.join(UPLOAD_FOLDER, unique_name)
            archivo.save(archivo_url)
            
            # Obtener archivo anterior para eliminarlo después
            cursor.execute("SELECT archivo_url FROM documentos_empresa WHERE id = %s", (documento_id,))
            archivo_anterior = cursor.fetchone()['archivo_url']
        
        # Construir query de actualización
        if archivo_url:
            query = """
                UPDATE documentos_empresa 
                SET nit_empresa = %s, formato_id = %s, nombre = %s,
                    archivo_url = %s, fecha_vencimiento = %s,
                    estado = %s, formato = %s
                WHERE id = %s
            """
            params = (
                nit_empresa,
                request.form.get('formato_id') or None,
                nombre,
                archivo_url,
                request.form.get('fecha_vencimiento') or None,
                request.form.get('estado', 'Sin Diligenciar'),
                request.form.get('formato_archivo', 'PDF'),
                documento_id
            )
        else:
            query = """
                UPDATE documentos_empresa 
                SET nit_empresa = %s, formato_id = %s, nombre = %s,
                    fecha_vencimiento = %s, estado = %s, formato = %s
                WHERE id = %s
            """
            params = (
                nit_empresa,
                request.form.get('formato_id') or None,
                nombre,
                request.form.get('fecha_vencimiento') or None,
                request.form.get('estado', 'Sin Diligenciar'),
                request.form.get('formato_archivo', 'PDF'),
                documento_id
            )
        
        cursor.execute(query, params)
        connection.commit()
        
        # Eliminar archivo anterior si se subió uno nuevo
        if archivo_url and archivo_anterior and os.path.exists(archivo_anterior):
            try:
                os.remove(archivo_anterior)
            except Exception as e:
                print(f"Error al eliminar archivo anterior: {e}")
        
        flash('Documento actualizado exitosamente', 'success')
        return redirect(url_for('documentacion'))
        
    except mysql.connector.Error as e:
        print(f"Error en actualizar_documento: {e}")
        flash('Error al actualizar documento', 'error')
        return redirect(url_for('editar_documento', documento_id=documento_id))
    except Exception as e:
        print(f"Error inesperado en actualizar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('editar_documento', documento_id=documento_id))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@bp.route('/eliminar_documento/<int:documento_id>', methods=['POST'], endpoint="eliminar_documento")
def eliminar_documento(documento_id):
    if 'usuario' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener archivo para eliminarlo después
        cursor.execute("SELECT archivo_url FROM documentos_empresa WHERE id = %s", (documento_id,))
        documento = cursor.fetchone()
        
        if not documento:
            return jsonify({'success': False, 'message': 'Documento no encontrado'}), 404
        
        # Eliminar de la base de datos
        cursor.execute("DELETE FROM documentos_empresa WHERE id = %s", (documento_id,))
        connection.commit()
        
        # Eliminar archivo físico si existe
        if documento['archivo_url'] and os.path.exists(documento['archivo_url']):
            try:
                os.remove(documento['archivo_url'])
            except Exception as e:
                print(f"Error al eliminar archivo: {e}")
        
        return jsonify({'success': True, 'message': 'Documento eliminado correctamente'})
        
    except mysql.connector.Error as e:
        print(f"Error en eliminar_documento: {e}")
        return jsonify({'success': False, 'message': 'Error en la base de datos'}), 500
    except Exception as e:
        print(f"Error inesperado en eliminar_documento: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



@bp.route('/descargar_documento/<int:documento_id>', endpoint="descargar_documento")
def descargar_documento(documento_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='gestusSG',
            user='root',
            password="Anyi#1530"
        )
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT archivo_url, nombre FROM documentos_empresa WHERE id = %s", (documento_id,))
        documento = cursor.fetchone()
        
        if not documento or not documento['archivo_url']:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('documentacion'))
        
        if not os.path.exists(documento['archivo_url']):
            flash('El archivo físico no existe', 'error')
            return redirect(url_for('documentacion'))
        
        return send_file(
            documento['archivo_url'],
            as_attachment=True,
            download_name=f"{documento['nombre']}.{documento['archivo_url'].split('.')[-1]}"
        )
        
    except mysql.connector.Error as e:
        print(f"Error en descargar_documento: {e}")
        flash('Error al descargar documento', 'error')
        return redirect(url_for('documentacion'))
    except Exception as e:
        print(f"Error inesperado en descargar_documento: {e}")
        flash('Error interno del servidor', 'error')
        return redirect(url_for('documentacion'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
            
            


