"""
CSV Import/Export API for CRM/Ops Template
"""
import logging
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Tuple
from flask import Blueprint, request, jsonify, g, send_file
from sqlalchemy.orm import Session
from src.database import db_session
from src.security.decorators import require_tenant_context, require_role
from src.security.policy import Role
from src.tenancy.context import get_current_tenant_id
from src.crm_ops.models import Contact
from src.crm_ops.api.base import (
    CRMOpsAPIBase, CRMOpsAPIError, ValidationError, handle_api_errors
)
from src.crm_ops.import_export.service import ImportExportService

logger = logging.getLogger(__name__)

bp = Blueprint('import_export', __name__, url_prefix='/api')

class ImportExportAPI(CRMOpsAPIBase):
    """Import/Export API implementation"""
    
    def __init__(self):
        super().__init__(None, 'import_export')
    
    @handle_api_errors
    def import_contacts_csv(self) -> tuple:
        """Import contacts from CSV"""
        tenant_id = get_current_tenant_id()
        user_id = getattr(g, 'user_id', None)
        
        # Check file size limit (10MB)
        if 'file' not in request.files:
            raise ValidationError("No file provided", "file")
        
        file = request.files['file']
        if file.filename == '':
            raise ValidationError("No file selected", "file")
        
        if not file.filename.lower().endswith('.csv'):
            raise ValidationError("File must be a CSV", "file")
        
        # Read file content
        try:
            content = file.read()
            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise ValidationError("File size exceeds 10MB limit", "file")
            
            # Parse CSV
            text_content = content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text_content))
            
            # Process rows
            service = ImportExportService()
            result = service.import_contacts_csv(tenant_id, user_id, reader)
            
            # Log audit event
            self.log_audit_event('create', 'csv_import', new_values={
                'contacts_inserted': result['inserted'],
                'contacts_updated': result['updated'],
                'contacts_skipped': result['skipped'],
                'errors_count': len(result['errors'])
            })
            
            return jsonify({
                'data': {
                    'type': 'import_result',
                    'attributes': result
                }
            }), 200
            
        except UnicodeDecodeError:
            raise ValidationError("Invalid file encoding. Please use UTF-8", "file")
        except Exception as e:
            logger.error(f"Error importing CSV for tenant {tenant_id}: {e}")
            raise CRMOpsAPIError("Failed to import CSV", 500, "IMPORT_ERROR")
    
    @handle_api_errors
    def export_contacts_csv(self) -> tuple:
        """Export contacts to CSV"""
        tenant_id = get_current_tenant_id()
        
        # Get filters from query params
        filters = {}
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('tags'):
            filters['tags'] = request.args.get('tags').split(',')
        
        try:
            service = ImportExportService()
            csv_content = service.export_contacts_csv(tenant_id, filters)
            
            # Create file response
            output = io.StringIO()
            output.write(csv_content)
            output.seek(0)
            
            # Log audit event
            self.log_audit_event('read', 'csv_export', new_values={
                'filters': filters
            })
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'contacts_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
            )
            
        except Exception as e:
            logger.error(f"Error exporting CSV for tenant {tenant_id}: {e}")
            raise CRMOpsAPIError("Failed to export CSV", 500, "EXPORT_ERROR")
    
    @handle_api_errors
    def export_deals_csv(self) -> tuple:
        """Export deals to CSV"""
        tenant_id = get_current_tenant_id()
        
        # Get filters from query params
        filters = {}
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('pipeline_stage'):
            filters['pipeline_stage'] = request.args.get('pipeline_stage')
        
        try:
            service = ImportExportService()
            csv_content = service.export_deals_csv(tenant_id, filters)
            
            # Create file response
            output = io.StringIO()
            output.write(csv_content)
            output.seek(0)
            
            # Log audit event
            self.log_audit_event('read', 'deals_csv_export', new_values={
                'filters': filters
            })
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'deals_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
            )
            
        except Exception as e:
            logger.error(f"Error exporting deals CSV for tenant {tenant_id}: {e}")
            raise CRMOpsAPIError("Failed to export deals CSV", 500, "EXPORT_ERROR")

# Initialize API
import_export_api = ImportExportAPI()

# Route handlers
@bp.route('/contacts/import', methods=['POST'])
@require_tenant_context
@require_role(Role.MEMBER)
def import_contacts_csv():
    """Import contacts from CSV"""
    return import_export_api.import_contacts_csv()

@bp.route('/contacts/export.csv', methods=['GET'])
@require_tenant_context
def export_contacts_csv():
    """Export contacts to CSV"""
    return import_export_api.export_contacts_csv()

@bp.route('/deals/export.csv', methods=['GET'])
@require_tenant_context
def export_deals_csv():
    """Export deals to CSV"""
    return import_export_api.export_deals_csv()
