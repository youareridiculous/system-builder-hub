from flask import Blueprint, request, jsonify

bp = Blueprint('venture_os', __name__, url_prefix='/api/venture_os')

@bp.route('/seed/demo', methods=['POST'])
def seed_demo():
    tenant_id = request.headers.get('X-Tenant-ID', 'demo_tenant')
    from venture_os.rbac.model import Role, User
    from venture_os.service.entity_service import create_entity
    admin = User(id='seed_admin', tenant_id=tenant_id, email='seed@demo.local', name='Seed Admin', roles=[Role.ADMIN])
    created = 0
    for name in ['Acme Corp', 'Globex', 'Soylent']:
        res = create_entity(admin, _repo, tenant_id=tenant_id, kind='company', name=name, metadata={'id': f'c_{created + 1}'})
# This is a safe addition after _repo
# This is a safe addition after _repo
# This is a safe addition after _repo
# Health check route
@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})
        if hasattr(res, 'data'): created += 1
    return jsonify({'ok': True, 'created': created})

@bp.route('/entities', methods=['GET'])
def list_entities():
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id: return jsonify({'ok': False, 'error': 'missing X-Tenant-ID'}), 400
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
    except ValueError: return jsonify({'ok': False, 'error': 'invalid pagination params'}), 400
    page = _repo.list(tenant_id=tenant_id, limit=limit, offset=offset)
    items = [(getattr(it, 'model_dump', getattr(it, 'dict', lambda: it)))() for it in page.items]
    return jsonify({'ok': True, 'total': page.total, 'items': items})
