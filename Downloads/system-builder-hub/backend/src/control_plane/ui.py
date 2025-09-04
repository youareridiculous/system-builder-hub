"""
Control Plane UI for SBH

Provides multi-tenant administration interface for tenant management, provisioning, and operations.
"""

from flask import Blueprint, render_template_string, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

# Create control plane UI blueprint
control_plane_ui_bp = Blueprint('control_plane_ui', __name__, url_prefix='/ui/control-plane')

# HTML template for control plane
CONTROL_PLANE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SBH Control Plane - Multi-Tenant Admin</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .search-bar {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .search-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .search-input:focus {
            border-color: #667eea;
        }
        
        .tenants-table {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .table-header {
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #e1e5e9;
        }
        
        .table-header h2 {
            color: #333;
            font-size: 1.5rem;
        }
        
        .table-container {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 16px 20px;
            text-align: left;
            border-bottom: 1px solid #e1e5e9;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .tenant-slug {
            font-family: 'Monaco', 'Menlo', monospace;
            background: #e3f2fd;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .status-active {
            background: #e8f5e8;
            color: #2e7d32;
        }
        
        .status-trial {
            background: #fff3e0;
            color: #f57c00;
        }
        
        .status-inactive {
            background: #ffebee;
            color: #c62828;
        }
        
        .action-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5a6fd8;
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
            transform: translateY(-1px);
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
            transform: translateY(-1px);
        }
        
        .btn-warning {
            background: #ffc107;
            color: #212529;
        }
        
        .btn-warning:hover {
            background: #e0a800;
            transform: translateY(-1px);
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
            transform: translateY(-1px);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 8px;
        }
        
        .stat-label {
            color: #666;
            font-size: 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 16px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .success {
            background: #e8f5e8;
            color: #2e7d32;
            padding: 16px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .action-buttons {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ SBH Control Plane</h1>
            <p>Multi-Tenant SaaS Administration & Management</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-tenants">-</div>
                <div class="stat-label">Total Tenants</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="active-tenants">-</div>
                <div class="stat-label">Active Tenants</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="trial-tenants">-</div>
                <div class="stat-label">Trial Tenants</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="total-modules">-</div>
                <div class="stat-label">Total Modules</div>
            </div>
        </div>
        
        <div class="search-bar">
            <input type="text" class="search-input" id="searchInput" placeholder="Search tenants by name or slug...">
        </div>
        
        <div class="tenants-table">
            <div class="table-header">
                <h2>Tenant Management</h2>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Tenant</th>
                            <th>Plan</th>
                            <th>Modules</th>
                            <th>Status</th>
                            <th>Last Active</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="tenantsTableBody">
                        <tr>
                            <td colspan="6" class="loading">Loading tenants...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div id="messageContainer"></div>
    </div>
    
    <script>
        // Control Plane JavaScript
        class ControlPlane {
            constructor() {
                this.adminToken = 'admin-dev-token'; // In production, get from secure source
                this.baseUrl = '/api/controlplane';
                this.init();
            }
            
            init() {
                this.loadTenants();
                this.setupEventListeners();
            }
            
            setupEventListeners() {
                const searchInput = document.getElementById('searchInput');
                searchInput.addEventListener('input', (e) => {
                    this.searchTenants(e.target.value);
                });
            }
            
            async loadTenants() {
                try {
                    const response = await fetch(`${this.baseUrl}/tenants`, {
                        headers: {
                            'X-Admin-Token': this.adminToken
                        }
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        this.displayTenants(data.data.tenants);
                        this.updateStats(data.data.tenants);
                    } else {
                        this.showError(data.error || 'Failed to load tenants');
                    }
                } catch (error) {
                    this.showError(`Failed to load tenants: ${error.message}`);
                }
            }
            
            async searchTenants(query) {
                if (!query.trim()) {
                    this.loadTenants();
                    return;
                }
                
                try {
                    const response = await fetch(`${this.baseUrl}/tenants?q=${encodeURIComponent(query)}`, {
                        headers: {
                            'X-Admin-Token': this.adminToken
                        }
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        this.displayTenants(data.data.tenants);
                    } else {
                        this.showError(data.error || 'Failed to search tenants');
                    }
                } catch (error) {
                    this.showError(`Failed to search tenants: ${error.message}`);
                }
            }
            
            displayTenants(tenants) {
                const tbody = document.getElementById('tenantsTableBody');
                
                if (tenants.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="loading">No tenants found</td></tr>';
                    return;
                }
                
                tbody.innerHTML = tenants.map(tenant => `
                    <tr>
                        <td>
                            <div>
                                <strong>${tenant.name}</strong><br>
                                <span class="tenant-slug">${tenant.slug}</span>
                            </div>
                        </td>
                        <td>${tenant.plan || 'trial'}</td>
                        <td>${this.getModuleCount(tenant)}</td>
                        <td>
                            <span class="status-badge status-${tenant.status || 'active'}">
                                ${tenant.status || 'active'}
                            </span>
                        </td>
                        <td>${this.formatDate(tenant.updated_at || tenant.created_at)}</td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn btn-primary" onclick="controlPlane.viewTenant('${tenant.slug}')">
                                    View
                                </button>
                                <button class="btn btn-success" onclick="controlPlane.provisionTenant('${tenant.slug}')">
                                    Provision
                                </button>
                                <button class="btn btn-warning" onclick="controlPlane.startTrial('${tenant.slug}')">
                                    Trial
                                </button>
                                <button class="btn btn-secondary" onclick="controlPlane.runOps('${tenant.slug}')">
                                    Ops
                                </button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
            
            getModuleCount(tenant) {
                // This would be populated from actual tenant data
                return '0'; // Placeholder
            }
            
            formatDate(dateString) {
                if (!dateString) return 'N/A';
                const date = new Date(dateString);
                return date.toLocaleDateString();
            }
            
            updateStats(tenants) {
                const totalTenants = tenants.length;
                const activeTenants = tenants.filter(t => t.status === 'active').length;
                const trialTenants = tenants.filter(t => t.plan === 'trial').length;
                
                document.getElementById('total-tenants').textContent = totalTenants;
                document.getElementById('active-tenants').textContent = activeTenants;
                document.getElementById('trial-tenants').textContent = trialTenants;
                document.getElementById('total-modules').textContent = '0'; // Placeholder
            }
            
            async viewTenant(slug) {
                try {
                    const response = await fetch(`${this.baseUrl}/tenants/${slug}`, {
                        headers: {
                            'X-Admin-Token': this.adminToken
                        }
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        this.showSuccess(`Tenant ${slug} details loaded successfully`);
                        // In a real implementation, this would open a modal or navigate to detail view
                    } else {
                        this.showError(data.error || 'Failed to load tenant details');
                    }
                } catch (error) {
                    this.showError(`Failed to load tenant details: ${error.message}`);
                }
            }
            
            async provisionTenant(slug) {
                try {
                    const response = await fetch(`${this.baseUrl}/tenants/${slug}/provision`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Admin-Token': this.adminToken
                        },
                        body: JSON.stringify({
                            system: 'revops_suite',
                            dry_run: false
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        this.showSuccess(`Successfully provisioned ${slug} with revops_suite`);
                        this.loadTenants(); // Refresh the list
                    } else {
                        this.showError(data.error || 'Failed to provision tenant');
                    }
                } catch (error) {
                    this.showError(`Failed to provision tenant: ${error.message}`);
                }
            }
            
            async startTrial(slug) {
                try {
                    const response = await fetch(`${this.baseUrl}/tenants/${slug}/trial`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Admin-Token': this.adminToken
                        },
                        body: JSON.stringify({
                            module: 'crm',
                            days: 14
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        this.showSuccess(`Started 14-day trial of CRM for ${slug}`);
                        this.loadTenants(); // Refresh the list
                    } else {
                        this.showError(data.error || 'Failed to start trial');
                    }
                } catch (error) {
                    this.showError(`Failed to start trial: ${error.message}`);
                }
            }
            
            async runOps(slug) {
                try {
                    const response = await fetch(`${this.baseUrl}/tenants/${slug}/ops`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Admin-Token': this.adminToken
                        },
                        body: JSON.stringify({
                            action: 'migrate',
                            module: 'crm',
                            dry_run: true
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        this.showSuccess(`Dry-run migration completed for ${slug}`);
                    } else {
                        this.showError(data.error || 'Failed to run migration');
                    }
                } catch (error) {
                    this.showError(`Failed to run migration: ${error.message}`);
                }
            }
            
            showSuccess(message) {
                this.showMessage(message, 'success');
            }
            
            showError(message) {
                this.showMessage(message, 'error');
            }
            
            showMessage(message, type) {
                const container = document.getElementById('messageContainer');
                const messageDiv = document.createElement('div');
                messageDiv.className = type;
                messageDiv.textContent = message;
                
                container.appendChild(messageDiv);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {
                    messageDiv.remove();
                }, 5000);
            }
        }
        
        // Initialize control plane when page loads
        let controlPlane;
        document.addEventListener('DOMContentLoaded', () => {
            controlPlane = new ControlPlane();
        });
    </script>
</body>
</html>
"""

@control_plane_ui_bp.route('/')
def control_plane_dashboard():
    """Control plane dashboard"""
    try:
        return CONTROL_PLANE_HTML
    except Exception as e:
        logger.error(f"Failed to render control plane dashboard: {e}")
        return f"Error loading control plane: {str(e)}", 500
