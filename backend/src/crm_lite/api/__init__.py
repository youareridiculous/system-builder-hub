from flask import Blueprint

crm_lite_bp = Blueprint("crm_lite", __name__, url_prefix="/api/crm_lite")

@crm_lite_bp.get("/")
def root():
    return {"module": "crm_lite", "status": "ok"}

# Import and initialize contacts routes
from . import contacts_api
contacts_api.init_contacts_routes(crm_lite_bp)

# Some auto-loaders expect `bp`
bp = crm_lite_bp
