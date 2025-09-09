# Importación de librerías necesarias
from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import mysql.connector  # Para conectar con MySQL
from werkzeug.security import generate_password_hash  # Para encriptar contraseñas

# Inicialización de la app Flask


from flask import Blueprint, render_template, request, redirect, url_for, session, flash

bp = Blueprint("dashboard", __name__)

@bp.route("/dashboard", endpoint="dashboard")
def dashboard():
    
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

    # ==============================
    # Obtener solo las empresas activas para el selector
    # ==============================
    cursor.execute("SELECT nit_empresa, nombre FROM empresas WHERE estado = 'Activa'")
    empresas = cursor.fetchall()

    # ==============================
    # Leer el NIT seleccionado desde el formulario (GET)
    # ==============================
    nit_seleccionado = request.args.get('nit_empresa')

    # ==============================
    # Contar solo  empresas activas (no depende de filtro)
    # ==============================
    cursor.execute("SELECT COUNT(*) AS total_empresas FROM empresas WHERE estado = 'Activa'")
    total_empresas = cursor.fetchone()['total_empresas']

    # ==============================
    # Contar evaluaciones activas (se cuentan todas porque no tienen nit_empresa)
    # ==============================
    cursor.execute("SELECT COUNT(*) AS total_evaluaciones FROM evaluaciones")
    total_evaluaciones = cursor.fetchone()['total_evaluaciones']

    # ==============================
    # Contar capacitaciones (con o sin filtro por empresa)
    # ==============================
    if nit_seleccionado:
        cursor.execute("SELECT COUNT(*) AS total_capacitaciones FROM capacitaciones WHERE nit_empresa = %s", (nit_seleccionado,))
    else:
        cursor.execute("SELECT COUNT(*) AS total_capacitaciones FROM capacitaciones")
    total_capacitaciones = cursor.fetchone()['total_capacitaciones']

    # ==============================
    # Gráfico: Incidentes por tipo (con filtro si hay nit_empresa)
    # ==============================
    if nit_seleccionado:
        cursor.execute("""
            SELECT i.tipo, COUNT(*) AS cantidad
            FROM incidentes i
            JOIN empresas e ON i.nit_empresa = e.nit_empresa
            WHERE e.estado = 'Activa'
            GROUP BY i.tipo
                """)
    else:
        cursor.execute("""
            SELECT tipo, COUNT(*) AS cantidad
            FROM incidentes
            GROUP BY tipo
        """)
    incidentes_por_tipo = cursor.fetchall()

    # ==============================
    # Gráfico: Estado de documentos (con filtro si hay nit_empresa)
    # ==============================
    if nit_seleccionado:
        cursor.execute("""
            SELECT d.estado, COUNT(*) AS cantidad
            FROM documentos_empresa d
            JOIN empresas e ON d.nit_empresa = e.nit_empresa
            WHERE e.estado = 'Activa'
            GROUP BY d.estado
        """)
    else:
        cursor.execute("""
            SELECT estado, COUNT(*) AS cantidad
            FROM documentos_empresa
            GROUP BY estado
        """)
    documentos_por_estado = cursor.fetchall()

    # ==============================
    # Cerrar conexión
    # ==============================
    cursor.close()
    conexion.close()

    # ==============================
    # Renderizar la plantilla con todos los datos
    # ==============================
    return render_template(
        'dashboard.html',
        usuario_actual=usuario,
        total_empresas=total_empresas,
        total_evaluaciones=total_evaluaciones,
        total_capacitaciones=total_capacitaciones,
        incidentes_por_tipo=incidentes_por_tipo,
        documentos_por_estado=documentos_por_estado,
        empresas=empresas,
        nit_seleccionado=nit_seleccionado
    )


   # ====================================


@bp.route('/', endpoint="index")
def index():
    return render_template('index.html')


