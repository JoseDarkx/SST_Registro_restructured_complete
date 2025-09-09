# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask


from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint("epp", __name__)

@bp.route('/control_epp', endpoint="control_epp")
def control_epp():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conectar a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Consulta: Obtener todos los EPP asignados con info del personal y del EPP
    cursor.execute("""
    SELECT ea.id, ea.personal_id, ea.fecha_entrega, ea.estado, ea.observaciones, ea.firmado,
        p.nombre_completo AS nombre_personal,
        e.nombre AS nombre_epp
    FROM epp_asignados ea
    JOIN personal p ON ea.personal_id = p.id
    JOIN epp e ON ea.epp_id = e.id
    """)

    epp_asignados = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('control_epp.html', usuario_actual=usuario, epp_asignados=epp_asignados)



@bp.route('/asignar_epp', methods=['GET', 'POST'], endpoint="asignar_epp")
def asignar_epp():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener trabajadores con su información
    cursor.execute("""
        SELECT p.id, p.nombre_completo, p.cargo, e.nombre AS empresa
        FROM personal p
        JOIN empresas e ON p.nit_empresa = e.nit_empresa
        WHERE p.estado = 'Activo'
    """)
    personal = cursor.fetchall()

    # Obtener EPP con su información
    cursor.execute("""
        SELECT id, nombre, tipo_proteccion
        FROM epp
    """)
    epps = cursor.fetchall()
    

    if request.method == 'POST':
        try:
            personal_id = int(request.form['personal_id'])
            epp_id = int(request.form['epp_id'])
            fecha_entrega = request.form['fecha_entrega']
            estado = request.form['estado']
            observaciones = request.form.get('observaciones', '')
            firmado = 1 if 'firmado' in request.form else 0

            # Insertar en epp_asignados
            cursor.execute("""
                INSERT INTO epp_asignados (
                    epp_id, personal_id, fecha_entrega,
                    estado, observaciones, firmado
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                epp_id, personal_id, fecha_entrega,
                estado, observaciones, firmado
            ))

            conexion.commit()
            flash('EPP asignado correctamente.', 'success')
            return redirect(url_for('control_epp'))

        except Exception as e:
            flash("No se logró agregar la evaluación", "danger")

    cursor.close()
    conexion.close()

    return render_template('asignar_epp.html', usuario_actual=usuario, personal=personal, epps=epps)




@bp.route('/reporte_general_epp', methods=['GET', 'POST'], endpoint="reporte_general_epp")
def reporte_general_epp():
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conectar a la base de datos
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener parámetros del formulario de búsqueda
    tipo_epp = request.args.get('tipoEpp')
    nivel_riesgo = request.args.get('nivelRiesgo')  # Si tienes este campo en tu tabla
    fecha_inicio = request.args.get('fechaInicio')
    fecha_fin = request.args.get('fechaFin')

    # Construir condiciones dinámicas para los filtros
    condiciones = []
    parametros = []

    if tipo_epp and tipo_epp != "Todos":
        condiciones.append("e.nombre = %s")
        parametros.append(tipo_epp)

    if fecha_inicio:
        condiciones.append("ea.fecha_entrega >= %s")
        parametros.append(fecha_inicio)

    if fecha_fin:
        condiciones.append("ea.fecha_entrega <= %s")
        parametros.append(fecha_fin)

    where_clause = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    # Consulta principal: contar EPP asignados
    query = f"""
        SELECT COUNT(DISTINCT ea.personal_id) AS trabajadores,
               COUNT(*) AS epp_asignados,
               SUM(CASE WHEN e.fecha_vencimiento >= CURDATE() THEN 1 ELSE 0 END) AS vigentes,
               SUM(CASE WHEN e.fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END) AS proximos_vencer,
               SUM(CASE WHEN e.fecha_vencimiento < CURDATE() THEN 1 ELSE 0 END) AS vencidos
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        {where_clause}
    """

    cursor.execute(query, parametros)
    resultado = cursor.fetchone()

    # Lógica de estado general
    estado = "OK"
    if resultado["vencidos"] > 5:
        estado = "Crítico"
    elif resultado["proximos_vencer"] > 5:
        estado = "Atención"

    # Armar diccionario con los datos
    resumen = {
        "trabajadores": resultado["trabajadores"],
        "epp_asignados": resultado["epp_asignados"],
        "vigentes": resultado["vigentes"],
        "proximos_vencer": resultado["proximos_vencer"],
        "vencidos": resultado["vencidos"],
        "estado": estado
    }

    cursor.close()
    conexion.close()

    # Renderizar plantilla con los datos
    return render_template('reporte_general_epp.html', usuario_actual=usuario, resumen=resumen)





@bp.route('/ver_epp_asignado/<int:personal_id>', endpoint="ver_epp_asignado")
def ver_epp_asignado(personal_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Obtener datos del trabajador
    cursor.execute("""
        SELECT nombre_completo, cargo, estado
        FROM personal
        WHERE id = %s
    """, (personal_id,))
    trabajador = cursor.fetchone()

    # Historial de entregas de EPP
    cursor.execute("""
        SELECT ea.fecha_entrega, e.nombre AS nombre_epp, e.normativa_cumplida AS modelo,
               e.fecha_vencimiento, 'Juan López' AS responsable
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        WHERE ea.personal_id = %s
        ORDER BY ea.fecha_entrega DESC
    """, (personal_id,))
    entregas = cursor.fetchall()

    # Historial de novedades (si tienes tabla)
    # Puedes personalizar esto si tienes una tabla de novedades de EPP
    cursor.execute("""
        SELECT '2025-03-12' AS fecha, e.nombre AS tipo_epp, 'Dañado' AS motivo,
               p.nombre_completo AS entidad, 'Aprobado' AS estado
        FROM epp_asignados ea
        JOIN epp e ON ea.epp_id = e.id
        JOIN personal p ON ea.personal_id = p.id
        WHERE ea.personal_id = %s
        LIMIT 2
    """, (personal_id,))
    novedades = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template(
        'ver_epp_asignado.html',
        usuario_actual=usuario,
        trabajador=trabajador,
        entregas=entregas,
        novedades=novedades
    )




@bp.route('/editar_epp_asignado/<int:asignacion_id>', methods=['GET', 'POST'], endpoint="editar_epp_asignado")
def editar_epp_asignado(asignacion_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    if request.method == 'POST':
        epp_id = int(request.form['epp_id'])  # nuevo campo que llega desde el formulario
        fecha_entrega = request.form['fecha_entrega']
        estado = request.form['estado']
        observaciones = request.form['observaciones']
        firmado = True if request.form.get('firmado') == '1' else False

        cursor.execute("""
            UPDATE epp_asignados
            SET epp_id = %s, fecha_entrega = %s, estado = %s, observaciones = %s, firmado = %s
            WHERE id = %s
        """, (epp_id, fecha_entrega, estado, observaciones, firmado, asignacion_id))
        conexion.commit()
        cursor.close()
        conexion.close()

        flash('Asignación actualizada correctamente', 'success')
        return redirect(url_for('control_epp'))

    # Obtener datos de la asignación actual
    cursor.execute("""
        SELECT ea.*, p.nombre_completo AS nombre_personal
        FROM epp_asignados ea
        JOIN personal p ON ea.personal_id = p.id
        WHERE ea.id = %s
    """, (asignacion_id,))
    asignacion = cursor.fetchone()

    # Obtener lista de EPP para mostrar en el select
    cursor.execute("""
        SELECT id, nombre, tipo_proteccion, stock
        FROM epp
        ORDER BY nombre ASC
    """)
    lista_epp = cursor.fetchall()

    cursor.close()
    conexion.close()

    return render_template('editar_epp_asignado.html',
                           usuario_actual=usuario,
                           asignacion=asignacion,
                           lista_epp=lista_epp)



@bp.route('/agregar_epp', methods=['GET', 'POST'], endpoint="agregar_epp")
def agregar_epp():
    # Verifica si el usuario ha iniciado sesión
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))
    
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Anyi#1530',
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)  # opcional: dictionary=True para obtener dict en vez de tuplas

    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # Cerramos cursor temporal
    cursor.close()
    conexion.close()

    if request.method == 'POST':
        try:
            # Obtener los datos del formulario
            nombre = request.form['nombre']
            tipo_proteccion = request.form['tipo_proteccion']
            normativa_cumplida = request.form['normativa_cumplida']
            proveedor = request.form['proveedor']
            vida_util_dias = int(request.form['vida_util_dias'])
            fecha_vencimiento = request.form['fecha_vencimiento']
            stock = int(request.form['stock'])

            # Conexión a la base de datos
            conexion = mysql.connector.connect(
                host='localhost',
                user='root',
                password='Anyi#1530',
                database='gestusSG'
            )
            cursor = conexion.cursor()

            # Insertar nuevo EPP
            cursor.execute("""
                INSERT INTO epp (
                    nombre, tipo_proteccion, normativa_cumplida,
                    proveedor, vida_util_dias, fecha_vencimiento, stock
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                nombre, tipo_proteccion, normativa_cumplida,
                proveedor, vida_util_dias, fecha_vencimiento, stock
            ))

            conexion.commit()
            cursor.close()
            conexion.close()

            flash('Elemento de EPP agregado correctamente.', 'success')
            return redirect(url_for('inventario_epp'))

        except Exception as e:
            flash(f'Error al agregar EPP: {str(e)}', 'danger')

    # GET: Renderizar formulario vacío
    return render_template('agregar_epp.html', usuario_actual=usuario)





@bp.route('/editar_epp/<int:epp_id>', methods=['GET', 'POST'], endpoint="editar_epp")
def editar_epp(epp_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor(dictionary=True)
    # ==============================
    # Obtener datos del usuario actual
    # ==============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    if request.method == 'POST':
        # Obtener datos del formulario y actualizar
        nombre = request.form['nombre']
        tipo_proteccion = request.form['tipo_proteccion']
        normativa_cumplida = request.form['normativa_cumplida']
        proveedor = request.form['proveedor']
        vida_util_dias = request.form['vida_util_dias']
        fecha_vencimiento = request.form['fecha_vencimiento']

        cursor.execute("""
            UPDATE epp
            SET nombre=%s, tipo_proteccion=%s, normativa_cumplida=%s, proveedor=%s,
                vida_util_dias=%s, fecha_vencimiento=%s
            WHERE id=%s
        """, (nombre, tipo_proteccion, normativa_cumplida, proveedor, vida_util_dias, fecha_vencimiento, epp_id))
        conexion.commit()
        flash("EPP actualizado correctamente", "success")
        return redirect(url_for('inventario_epp'))

    # Mostrar formulario con datos existentes
    cursor.execute("SELECT * FROM epp WHERE id = %s", (epp_id,))
    epp = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not epp:
        flash("Elemento EPP no encontrado", "warning")
        return redirect(url_for('inventario_epp'))

    return render_template('editar_epp.html', usuario_actual=usuario, epp=epp)


@bp.route('/eliminar_epp/<int:epp_id>', endpoint="eliminar_epp")
def eliminar_epp(epp_id):
    if 'usuario' not in session:
        return redirect(url_for('iniciar_sesion'))

    conexion = mysql.connector.connect(
        host='localhost',
        user='root',
        password="Anyi#1530",
        database='gestusSG'
    )
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM epp WHERE id = %s", (epp_id,))
    conexion.commit()

    cursor.close()
    conexion.close()

    flash("EPP eliminado correctamente", "success")
    return redirect(url_for('inventario_epp'))





