# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask


from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint("auth", __name__)

@bp.route('/registrarse', methods=['GET', 'POST'], endpoint="registrarse")
def registrarse():
    if request.method == 'POST':
        nombre_completo = request.form['nombre_completo']
        correo = request.form['correo']
        usuario = request.form['usuario']
        contraseña = generate_password_hash(request.form['contraseña'])
        nit_empresa = request.form['nit_empresa']
        rol_id = request.form['rol_id']

        # Verificar si ya existe el usuario o el correo
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s OR usuario = %s", (correo, usuario))
        existente = cursor.fetchone()

        if existente:
            flash("Este usuario ya fue registrado anteriormente.", "error")  # Categoría 'error'
            return redirect(url_for('registrarse'))

        # Si no existe, lo insertamos
        cursor.execute("""
            INSERT INTO usuarios (nombre_completo, correo, usuario, contraseña, estado, nit_empresa, rol_id)
            VALUES (%s, %s, %s, %s, 'Activo', %s, %s)
        """, (nombre_completo, correo, usuario, contraseña, nit_empresa, rol_id))
        conexion.commit()

        flash("Usuario registrado exitosamente.", "success")  # Categoría 'success'
        return redirect(url_for('registrarse'))

    # Si es GET, cargamos roles y empresas para mostrar en el formulario
    cursor.execute("SELECT id, nombre FROM roles")
    roles = cursor.fetchall()
    cursor.execute("SELECT nit_empresa, nombre FROM empresas")
    empresas = cursor.fetchall()
    return render_template('register.html', roles=roles, empresas=empresas)




@bp.route('/iniciar-sesion', methods=['GET', 'POST'], endpoint="iniciar_sesion")
def iniciar_sesion():
    if request.method == 'POST':
        # Capturar credenciales
        nit_empresa = request.form['nit_empresa']
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']

        # Conexión y cursor
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Anyi#1530",
            database="gestussg"
        )
        cursor = conexion.cursor(dictionary=True)

        # Buscar el usuario
        cursor.execute("""
            SELECT * FROM usuarios 
            WHERE usuario = %s AND nit_empresa = %s
        """, (usuario, nit_empresa))
        user = cursor.fetchone()

        # Validar usuario y contraseña
        if user and user['contraseña'] == contraseña:
            session['usuario_id'] = user['id']
            session['usuario'] = user['usuario']
            session['nit_empresa'] = user['nit_empresa']
            flash("Inicio de sesión exitoso.")
            cursor.close()
            conexion.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales incorrectas o usuario inactivo', 'error')

        cursor.close()
        conexion.close()

    return render_template('login.html')



@bp.route('/ver_inventario', endpoint="ver_inventario")
def ver_inventario():
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

    # Obtener todos los EPP
    cursor.execute("SELECT * FROM epp")
    epps = cursor.fetchall()

    # Indicador: Total de EPP
    total_epp = len(epps)

    # Indicador: Stock bajo (vida útil < 120 días)
    cursor.execute("""
        SELECT COUNT(*) AS stock_bajo
        FROM epp
        WHERE DATEDIFF(fecha_vencimiento, CURDATE()) <= 120
    """)
    stock_bajo = cursor.fetchone()['stock_bajo']

    # Indicador: EPP Agotados (vida útil vencida)
    cursor.execute("""
        SELECT COUNT(*) AS agotados
        FROM epp
        WHERE fecha_vencimiento < CURDATE()
    """)
    agotados = cursor.fetchone()['agotados']

    # Indicador: EPP entregados este mes
    cursor.execute("""
        SELECT COUNT(*) AS entregados_mes
        FROM epp_asignados
        WHERE MONTH(fecha_entrega) = MONTH(CURDATE())
          AND YEAR(fecha_entrega) = YEAR(CURDATE())
    """)
    entregados_mes = cursor.fetchone()['entregados_mes']

    cursor.close()
    conexion.close()

    return render_template('ver_inventario.html',
        usuario_actual=usuario,
        epps=epps,
        total_epp=total_epp,
        stock_bajo=stock_bajo,
        agotados=agotados,
        entregados_mes=entregados_mes)


@bp.route('/solicitudes_contrasena', methods=['GET', 'POST'], endpoint="solicitudes_contrasena")
def solicitudes_contrasena():
    # Redirigir si el usuario no ha iniciado sesión
    if 'usuario_id' not in session:
        return redirect(url_for('iniciar_sesion'))

    # Conexión a la base de datos
    conexion = mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="Anyi#1530",
        database="gestussg"
    )
    cursor = conexion.cursor(dictionary=True)

    # ============================
    # Obtener datos del usuario actual
    # ============================
    cursor.execute("""
        SELECT u.nombre_completo, r.nombre AS rol
        FROM usuarios u
        JOIN roles r ON u.rol_id = r.id
        WHERE u.id = %s
    """, (session['usuario_id'],))
    usuario = cursor.fetchone()

    # ============================
    # Verificar si es administrador
    # ============================
    if usuario['rol'] != 'Administrador':
        cursor.close()
        conexion.close()
        return "Acceso denegado", 403

    # ============================
    # Procesar formulario POST
    # ============================
    if request.method == 'POST':
        solicitud_id = request.form.get('solicitud_id')
        nueva_contrasena = request.form.get('nueva_contrasena')

        # Buscar el correo de la solicitud
        cursor.execute("SELECT correo FROM recuperacion_contraseña WHERE id = %s", (solicitud_id,))
        solicitud = cursor.fetchone()

        if solicitud:
            correo = solicitud['correo']

            # Generar hash de la nueva contraseña
            hashed_password = generate_password_hash(nueva_contrasena)

            # Actualizar la contraseña del usuario
            cursor.execute("UPDATE usuarios SET contraseña = %s WHERE correo = %s", (hashed_password, correo))

            # Marcar la solicitud como 'Atendida'
            cursor.execute("UPDATE recuperacion_contraseña SET estado = 'Atendida' WHERE id = %s", (solicitud_id,))

            # Guardar cambios
            conexion.commit()

    # ============================
    # Obtener todas las solicitudes pendientes
    # ============================
    cursor.execute("SELECT * FROM recuperacion_contraseña WHERE estado = 'Pendiente'")
    solicitudes = cursor.fetchall()

    # Cerrar conexión
    cursor.close()
    conexion.close()

    # Renderizar plantilla HTML con las solicitudes y datos del usuario
    return render_template('solicitudes_contrasena.html', solicitudes=solicitudes, usuario_actual=usuario)





@bp.route('/certificados/<nombre_archivo>', endpoint="ver_certificado")
def ver_certificado(nombre_archivo):
    carpeta = os.path.join(os.getcwd(), 'uploads', 'certificados')
    ruta = os.path.join(carpeta, nombre_archivo)

    if not os.path.exists(ruta):
        abort(404, description="Archivo no encontrado.")

    extension = nombre_archivo.rsplit('.', 1)[-1].lower()

    if extension == 'pdf':
        return send_from_directory(carpeta, nombre_archivo)
    else:
        return send_from_directory(carpeta, nombre_archivo, as_attachment=True)
    



@bp.route('/registro-empresa', methods=['GET', 'POST'], endpoint="registro_empresa")
def registro_empresa():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('registerEmpresa.html')



@bp.route('/registro-usuario', methods=['GET', 'POST'], endpoint="registro_usuario")
def registro_usuario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('registerUsu.html')



@bp.route('/cerrar-sesion', endpoint="cerrar_sesion")
def cerrar_sesion():
    session.clear()  # Eliminar variables de sesión
    flash("Has cerrado sesión correctamente.")
    return redirect(url_for('iniciar_sesion'))


