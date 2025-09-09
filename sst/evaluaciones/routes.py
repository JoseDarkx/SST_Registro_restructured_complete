# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask


from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint("evaluaciones", __name__)

@bp.route('/evaluaciones_medicas', methods=['GET'], endpoint="evaluaciones_medicas")
def evaluaciones_medicas():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Obtener filtros del formulario (si los hay)
    filtro_id = request.args.get('id', '').strip()
    nombre = request.args.get('nombre', '').strip()
    nit_empresa = request.args.get('nit_empresa', '').strip()

    # Consulta SQL base
    query = """
        SELECT em.*, p.nombre_completo, p.documento_identidad, e.nombre AS empresa
        FROM evaluaciones_medicas em
        JOIN personal p ON em.personal_id = p.id
        JOIN empresas e ON em.nit_empresa = e.nit_empresa
        WHERE 1=1
    """
    params = []

    if filtro_id:
        query += " AND em.id = %s"
        params.append(filtro_id)
        
    if nombre:
        query += " AND em.medico_examinador LIKE %s"
        params.append(f"%{nombre}%")

    if nit_empresa:
        query += " AND em.nit_empresa = %s"
        params.append(nit_empresa)

    cursor.execute(query, params)
    evaluaciones = cursor.fetchall()

    # Obtener todas las empresas activas para el filtro
    cursor.execute("SELECT nit_empresa, nombre FROM empresas")
    empresas = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('evaluaciones_medicas.html',
                           evaluaciones=evaluaciones,
                           empresas=empresas,
                           filtro_id=filtro_id,
                           filtro_nombre=nombre,
                           filtro_empresa=nit_empresa)




@bp.route('/agregar_evaluaciones', methods=['GET', 'POST'], endpoint="agregar_evaluaciones")
def agregar_evaluaciones():
    # Verificar si el usuario está logueado
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Obtener lista de personal con su empresa
    cursor.execute("""
        SELECT p.id, p.nombre_completo, p.documento_identidad, e.nombre AS empresa, p.nit_empresa
        FROM personal p
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE p.estado = 'Activo'
    """)
    personal = cursor.fetchall()

    # Procesar formulario si se envió por POST
    if request.method == 'POST':
        try:

            # Obtener datos del formulario
            personal_id = int(request.form['personal_id'])
            nit_empresa = request.form['nit_empresa']
            fecha = request.form['fecha']
            tipo_evaluacion = request.form['tipo_evaluacion']
            medico_examinador = request.form['medico_examinador']
            restricciones = request.form['restricciones']
            observaciones = request.form['observaciones']
            recomendaciones = request.form['recomendaciones']


            # Procesar archivo adjunto si se sube
            archivo = request.files.get('archivo')
            archivo_url = None

            if archivo and archivo.filename != '':
                nombre_archivo = secure_filename(archivo.filename)
                carpeta_destino = os.path.join('static', 'uploads', 'archivos_evaluaciones')

                if not os.path.exists(carpeta_destino):
                    os.makedirs(carpeta_destino)

                ruta_archivo = os.path.join(carpeta_destino, nombre_archivo)
                archivo.save(ruta_archivo)

                archivo_url = f"uploads/archivos_evaluaciones/{nombre_archivo}"

            # Insertar evaluación médica
            cursor.execute("""
                INSERT INTO evaluaciones_medicas (
                    personal_id, nit_empresa, fecha, tipo_evaluacion, medico_examinador,
                    archivo_url, restricciones, observaciones, recomendaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                personal_id, nit_empresa, fecha, tipo_evaluacion, medico_examinador,
                archivo_url, restricciones, observaciones, recomendaciones
            ))

            conexion.commit()
            flash('Evaluación médica agregada correctamente', 'success')
            return redirect(url_for('evaluaciones_medicas'))

        except Exception as e:
            flash(f'Error al guardar la evaluación: {str(e)}', 'danger')


    # Cerrar conexión a la base de datos
    cursor.close()
    conexion.close()

    # Renderizar formulario HTML
    return render_template('agregar_evaluaciones.html', personal=personal)




@bp.route('/ver_evaluaciones/<int:evaluacion_id>', endpoint="ver_evaluacion_medica")
def ver_evaluacion_medica(evaluacion_id):
    # Verifica si el usuario ha iniciado sesión
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Consulta para obtener los datos de la evaluación médica junto con información del personal y la empresa
    cursor.execute("""
        SELECT em.*, p.nombre_completo, p.documento_identidad, e.nombre AS nombre_empresa
        FROM evaluaciones_medicas em
        JOIN personal p ON em.personal_id = p.id
        JOIN empresas e ON em.nit_empresa = e.nit_empresa
        WHERE em.id = %s
    """, (evaluacion_id,))
    
    evaluacion = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not evaluacion:
        flash("Evaluación no encontrada", "warning")
        return redirect(url_for('evaluaciones_medicas'))

    # Renderiza la plantilla con los datos obtenidos
    return render_template('ver_evaluaciones.html', evaluacion=evaluacion)



@bp.route('/editar_evaluaciones/<int:evaluacion_id>', methods=['GET', 'POST'], endpoint="editar_evaluaciones")
def editar_evaluaciones(evaluacion_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)

    # Obtener datos de la evaluación médica
    cursor.execute("""
        SELECT em.*, p.nombre_completo, p.documento_identidad, e.nombre AS empresa
        FROM evaluaciones_medicas em
        JOIN personal p ON em.personal_id = p.id
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE em.id = %s
    """, (evaluacion_id,))
    evaluacion = cursor.fetchone()

    if not evaluacion:
        flash("Evaluación no encontrada", "danger")
        return redirect(url_for('evaluaciones_medicas'))

    if request.method == 'POST':
        fecha = request.form['fecha']
        tipo_evaluacion = request.form['tipo_evaluacion']
        medico_examinador = request.form['medico_examinador']
        restricciones = request.form['restricciones']
        observaciones = request.form['observaciones']
        recomendaciones = request.form['recomendaciones']

        archivo = request.files.get('archivo')
        archivo_url = evaluacion['archivo_url']  # mantener archivo actual si no se sube uno nuevo

        if archivo and archivo.filename != '':
            nombre_archivo = secure_filename(archivo.filename)
            ruta_archivo = os.path.join('static/uploads/archivos_evaluaciones', nombre_archivo)
            archivo.save(ruta_archivo)
            archivo_url = ruta_archivo

        # Actualizar datos
        cursor.execute("""
            UPDATE evaluaciones_medicas
            SET fecha=%s, tipo_evaluacion=%s, medico_examinador=%s, archivo_url=%s,
                restricciones=%s, observaciones=%s, recomendaciones=%s
            WHERE id = %s
        """, (
            fecha, tipo_evaluacion, medico_examinador, archivo_url,
            restricciones, observaciones, recomendaciones, evaluacion_id
        ))
        conexion.commit()
        flash('Evaluación actualizada correctamente', 'success')
        return redirect(url_for('evaluaciones_medicas'))

    cursor.close()
    conexion.close()
    return render_template('editar_evaluaciones.html', evaluacion=evaluacion)




@bp.route('/capacitaciones', endpoint="capacitaciones")
def capacitaciones():
    """Mostrar listado de capacitaciones con evaluaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener capacitaciones con nombre de empresa
        cursor.execute("""
            SELECT c.*, e.nombre as nombre_empresa
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            ORDER BY c.fecha DESC
        """)
        capacitaciones_list = cursor.fetchall()
        
        # Obtener empresas activas para el formulario
        cursor.execute("""
            SELECT nit_empresa, nombre 
            FROM empresas 
            WHERE estado = 'Activa' 
            ORDER BY nombre
        """)
        empresas = cursor.fetchall()
        
        # Obtener evaluaciones de capacitación
        cursor.execute("""
            SELECT * FROM evaluaciones_capacitacion
            ORDER BY participante
        """)
        evaluaciones = cursor.fetchall()
        
        return render_template('capacitaciones.html', 
                             capacitaciones=capacitaciones_list,
                             empresas=empresas,
                             evaluaciones=evaluaciones)
        
    except mysql.connector.Error as e:
        print(f"Error en capacitaciones: {e}")
        flash('Error al cargar las capacitaciones', 'error')
        return render_template('capacitaciones.html', 
                             capacitaciones=[], empresas=[], evaluaciones=[])
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()




@bp.route('/crear_capacitacion', methods=['POST'], endpoint="crear_capacitacion")
def crear_capacitacion():
    """Crear nueva capacitación"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        # Obtener datos del formulario
        nit_empresa = request.form['empresa']
        fecha = request.form['fecha']
        responsable = request.form['responsable']
        estado = request.form['estado']
        
        # Validar campos obligatorios
        if not nit_empresa or not fecha or not responsable:
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('capacitaciones'))
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor()
        
        # Insertar nueva capacitación
        cursor.execute("""
            INSERT INTO capacitaciones (nit_empresa, fecha, responsable, estado, fecha_creacion)
            VALUES (%s, %s, %s, %s, NOW())
        """, (nit_empresa, fecha, responsable, estado))
        
        connection.commit()
        flash('Capacitación creada exitosamente', 'success')
        
    except mysql.connector.Error as e:
        print(f"Error al crear capacitación: {e}")
        flash('Error al crear la capacitación', 'error')
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return redirect(url_for('capacitaciones'))




@bp.route('/editar_capacitacion/<int:capacitacion_id>', methods=['GET', 'POST'], endpoint="editar_capacitacion")
def editar_capacitacion(capacitacion_id):
    """Editar capacitación existente"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Actualizar capacitación
            nit_empresa = request.form['empresa']
            fecha = request.form['fecha']
            responsable = request.form['responsable']
            estado = request.form['estado']
            
            cursor.execute("""
                UPDATE capacitaciones 
                SET nit_empresa = %s, fecha = %s, responsable = %s, estado = %s
                WHERE id = %s
            """, (nit_empresa, fecha, responsable, estado, capacitacion_id))
            
            connection.commit()
            flash('Capacitación actualizada exitosamente', 'success')
            return redirect(url_for('capacitaciones'))
        
        else:
            # Obtener datos de la capacitación
            cursor.execute("SELECT * FROM capacitaciones WHERE id = %s", (capacitacion_id,))
            capacitacion = cursor.fetchone()
            
            if not capacitacion:
                flash('Capacitación no encontrada', 'error')
                return redirect(url_for('capacitaciones'))
            
            # Obtener empresas para el select
            cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa'")
            empresas = cursor.fetchall()
            
            return render_template('editar_capacitacion.html', 
                                 capacitacion=capacitacion, empresas=empresas)
            
    except mysql.connector.Error as e:
        print(f"Error al editar capacitación: {e}")
        flash('Error al editar la capacitación', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()




@bp.route('/eliminar_capacitacion/<int:capacitacion_id>', methods=['POST'], endpoint="eliminar_capacitacion")
def eliminar_capacitacion(capacitacion_id):
    """Eliminar capacitación"""
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor()
        
        # Verificar si existe la capacitación
        cursor.execute("SELECT id FROM capacitaciones WHERE id = %s", (capacitacion_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'Capacitación no encontrada'}), 404
        
        # Eliminar evaluaciones asociadas primero (si existen)
        cursor.execute("DELETE FROM evaluaciones_capacitacion WHERE capacitacion_id = %s", (capacitacion_id,))
        
        # Eliminar la capacitación
        cursor.execute("DELETE FROM capacitaciones WHERE id = %s", (capacitacion_id,))
        
        connection.commit()
        return jsonify({'success': True, 'message': 'Capacitación eliminada correctamente'})
        
    except mysql.connector.Error as e:
        print(f"Error al eliminar capacitación: {e}")
        return jsonify({'success': False, 'message': 'Error en la base de datos'}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()




@bp.route('/agregar_evaluacion', methods=['GET', 'POST'], endpoint="agregar_evaluacion")
def agregar_evaluacion():
    """Agregar nueva evaluación de capacitación"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Obtener datos del formulario
            capacitacion_id = request.form.get('capacitacion_id')
            participante = request.form['participante']
            pre_test = request.form['pre_test']
            post_test = request.form['post_test']
            
            # Calcular resultado automáticamente
            pre_test_num = float(pre_test) if pre_test else 0
            post_test_num = float(post_test) if post_test else 0
            
            if post_test_num >= 70:  # Criterio de aprobación
                resultado = 'Aprobado'
            elif post_test_num < 70 and post_test_num >= 60:
                resultado = 'Requiere'
            else:
                resultado = 'No aprobado'
            
            # Insertar evaluación
            cursor.execute("""
                INSERT INTO evaluaciones_capacitacion 
                (capacitacion_id, participante, pre_test, post_test, resultado, fecha_evaluacion)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (capacitacion_id, participante, pre_test_num, post_test_num, resultado))
            
            connection.commit()
            flash('Evaluación agregada exitosamente', 'success')
            return redirect(url_for('capacitaciones'))
        
        else:
            # Obtener capacitaciones para el select
            cursor.execute("""
                SELECT c.id, c.fecha, e.nombre as empresa_nombre
                FROM capacitaciones c
                JOIN empresas e ON c.nit_empresa = e.nit_empresa
                ORDER BY c.fecha DESC
            """)
            capacitaciones_list = cursor.fetchall()
            
            return render_template('agregar_evaluacion.html', capacitaciones=capacitaciones_list)
            
    except mysql.connector.Error as e:
        print(f"Error en agregar_evaluacion: {e}")
        flash('Error al procesar la evaluación', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()




@bp.route('/editar_evaluacion/<int:evaluacion_id>', methods=['GET', 'POST'], endpoint="editar_evaluacion")
def editar_evaluacion(evaluacion_id):
    """Editar evaluación de capacitación"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'POST':
            # Actualizar evaluación
            participante = request.form['participante']
            pre_test = request.form['pre_test']
            post_test = request.form['post_test']
            
            # Calcular resultado
            post_test_num = float(post_test) if post_test else 0
            if post_test_num >= 70:
                resultado = 'Aprobado'
            elif post_test_num >= 60:
                resultado = 'Requiere'
            else:
                resultado = 'No aprobado'
            
            cursor.execute("""
                UPDATE evaluaciones_capacitacion 
                SET participante = %s, pre_test = %s, post_test = %s, resultado = %s
                WHERE id = %s
            """, (participante, pre_test, post_test, resultado, evaluacion_id))
            
            connection.commit()
            flash('Evaluación actualizada exitosamente', 'success')
            return redirect(url_for('capacitaciones'))
        
        else:
            # Obtener datos de la evaluación
            cursor.execute("SELECT * FROM evaluaciones_capacitacion WHERE id = %s", (evaluacion_id,))
            evaluacion = cursor.fetchone()
            
            if not evaluacion:
                flash('Evaluación no encontrada', 'error')
                return redirect(url_for('capacitaciones'))
            
            return render_template('editar_evaluacion.html', evaluacion=evaluacion)
            
    except mysql.connector.Error as e:
        print(f"Error al editar evaluación: {e}")
        flash('Error al editar la evaluación', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()




@bp.route('/reporte_capacitaciones_pdf', endpoint="reporte_capacitaciones_pdf")
def reporte_capacitaciones_pdf():
    """Generar reporte PDF de capacitaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from io import BytesIO
        import tempfile
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        # Obtener datos para el reporte
        cursor.execute("""
            SELECT c.fecha, e.nombre as empresa, c.responsable, c.estado,
                   COUNT(ec.id) as total_evaluaciones,
                   SUM(CASE WHEN ec.resultado = 'Aprobado' THEN 1 ELSE 0 END) as aprobados
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            LEFT JOIN evaluaciones_capacitacion ec ON c.id = ec.capacitacion_id
            GROUP BY c.id, c.fecha, e.nombre, c.responsable, c.estado
            ORDER BY c.fecha DESC
        """)
        datos = cursor.fetchall()
        
        # Crear PDF en memoria
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        
        # Título
        story.append(Paragraph("Reporte de Efectividad de Capacitaciones", title_style))
        story.append(Paragraph("<br/><br/>", styles['Normal']))
        
        # Crear tabla
        data = [['Fecha', 'Empresa', 'Responsable', 'Estado', 'Evaluaciones', 'Aprobados', 'Efectividad']]
        
        for row in datos:
            efectividad = f"{(row['aprobados'] / max(row['total_evaluaciones'], 1)) * 100:.1f}%" if row['total_evaluaciones'] > 0 else "N/A"
            data.append([
                str(row['fecha']),
                row['empresa'],
                row['responsable'],
                row['estado'],
                str(row['total_evaluaciones']),
                str(row['aprobados']),
                efectividad
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        doc.build(story)
        
        buffer.seek(0)
        
        return send_file(
            BytesIO(buffer.read()),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='reporte_capacitaciones.pdf'
        )
        
    except Exception as e:
        print(f"Error al generar PDF: {e}")
        flash('Error al generar el reporte PDF. Instala reportlab: pip install reportlab', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()




@bp.route('/reporte_capacitaciones_excel', endpoint="reporte_capacitaciones_excel")
def reporte_capacitaciones_excel():
    """Exportar reporte Excel de capacitaciones"""
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    try:
        import pandas as pd
        from io import BytesIO
        
        # Conectar a la base de datos
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        
        # Obtener datos
        query = """
            SELECT c.fecha, e.nombre as empresa, c.responsable, c.estado,
                   COUNT(ec.id) as total_evaluaciones,
                   SUM(CASE WHEN ec.resultado = 'Aprobado' THEN 1 ELSE 0 END) as aprobados,
                   ROUND((SUM(CASE WHEN ec.resultado = 'Aprobado' THEN 1 ELSE 0 END) / 
                         GREATEST(COUNT(ec.id), 1)) * 100, 2) as efectividad_porcentaje
            FROM capacitaciones c
            JOIN empresas e ON c.nit_empresa = e.nit_empresa
            LEFT JOIN evaluaciones_capacitacion ec ON c.id = ec.capacitacion_id
            GROUP BY c.id, c.fecha, e.nombre, c.responsable, c.estado
            ORDER BY c.fecha DESC
        """
        
        df = pd.read_sql(query, connection)
        
        # Crear archivo Excel en memoria
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Capacitaciones', index=False)
            
            # Obtener detalles de evaluaciones
            query_evaluaciones = """
                SELECT c.fecha as fecha_capacitacion, e.nombre as empresa, 
                       ec.participante, ec.pre_test, ec.post_test, ec.resultado
                FROM evaluaciones_capacitacion ec
                JOIN capacitaciones c ON ec.capacitacion_id = c.id
                JOIN empresas e ON c.nit_empresa = e.nit_empresa
                ORDER BY c.fecha DESC, ec.participante
            """
            df_evaluaciones = pd.read_sql(query_evaluaciones, connection)
            df_evaluaciones.to_excel(writer, sheet_name='Evaluaciones_Detalle', index=False)
        
        buffer.seek(0)
        
        return send_file(
            BytesIO(buffer.read()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='reporte_capacitaciones.xlsx'
        )
        
    except Exception as e:
        print(f"Error al generar Excel: {e}")
        flash('Error al generar el reporte Excel. Instala pandas y openpyxl: pip install pandas openpyxl', 'error')
        return redirect(url_for('capacitaciones'))
    finally:
        if 'connection' in locals():
            connection.close()




@bp.route('/api/capacitaciones/<int:capacitacion_id>/evaluaciones', endpoint="api_evaluaciones_capacitacion")
def api_evaluaciones_capacitacion(capacitacion_id):
    """API para obtener evaluaciones de una capacitación específica"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root", 
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM evaluaciones_capacitacion 
            WHERE capacitacion_id = %s 
            ORDER BY participante
        """, (capacitacion_id,))
        
        evaluaciones = cursor.fetchall()
        return jsonify({'evaluaciones': evaluaciones})
        
    except mysql.connector.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()



