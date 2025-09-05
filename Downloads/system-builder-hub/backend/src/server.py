from flask import Flask


def create_app():
    app = Flask(__name__)
    from venture_os.http.api import bp as venture_os_bp

    # Register other blueprints
    
    # Register Venture OS API blueprint if not already registered
    if "venture_os_api" not in app.blueprints:
        app.register_blueprint(venture_os_bp)
        app.logger.info("Venture OS API mounted at /api/venture_os")

    return app
