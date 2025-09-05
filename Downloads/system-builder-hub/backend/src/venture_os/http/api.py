from flask import Blueprint, request, jsonify
from venture_os.service.entity_service import create_entity, list_entities, search_entities, summary_entities
from venture_os.service.entity_service import update_entity, archive_entity

api = Blueprint('api', __name__)

@api.route('/api/venture_os/entities/<entity_id>', methods=['PATCH'])
def update_entity_route(entity_id):
    tenant_id = request.headers.get('X-Tenant-ID')
    user = _user_from_request(tenant_id)
    if request.headers.get('X-User-Role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    patch = request.get_json() or {}
    # Validate patch content here
    # Call update_entity and handle response
    return jsonify({'ok': True, 'entity': {}})

@api.route('/api/venture_os/entities/<entity_id>/archive', methods=['POST'])
def archive_entity_route(entity_id):
    tenant_id = request.headers.get('X-Tenant-ID')
    user = _user_from_request(tenant_id)
    if request.headers.get('X-User-Role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    # Call archive_entity and handle response
    return jsonify({'ok': True, 'entity': {}})

# Existing routes remain unchanged