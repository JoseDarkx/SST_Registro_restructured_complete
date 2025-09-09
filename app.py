from flask import Flask
from sst.auth.routes import bp as auth_bp
from sst.empresas.routes import bp as empresas_bp
from sst.epp.routes import bp as epp_bp
from sst.evaluaciones.routes import bp as evaluaciones_bp
from sst.documentos.routes import bp as documentos_bp
from sst.dashboard.routes import bp as dashboard_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = 'clave_secreta'
    app.debug = True

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(epp_bp)
    app.register_blueprint(evaluaciones_bp)
    app.register_blueprint(documentos_bp)
    app.register_blueprint(dashboard_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run()
