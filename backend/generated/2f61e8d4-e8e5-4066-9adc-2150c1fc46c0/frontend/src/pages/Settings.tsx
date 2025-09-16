import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';

export default function Settings() {
  const { showToast } = useToast();
  const { hasPermission } = useAuth();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('account');
  
  // Simple state
  const [environment, setEnvironment] = useState({
    backend_version: 'v1.0.1',
    build_id: 'N/A',
    tenant_id: 'N/A',
    secrets_configured: false
  });
  const [users, setUsers] = useState([]);
  const [branding, setBranding] = useState({
    tenant_name: '',
    logo_url: '',
    primary_color: '#3b82f6'
  });

  // Load basic data once on mount
  useEffect(() => {
    const loadData = async () => {
      if (!hasPermission('settings.read')) {
        setLoading(false);
        return;
      }

      try {
        const [environmentRes, usersRes, brandingRes] = await Promise.all([
          api.get('/api/settings/environment'),
          api.get('/api/settings/users'),
          api.get('/api/settings/branding')
        ]);
        
        setEnvironment(environmentRes);
        setUsers(usersRes);
        setBranding(brandingRes);
      } catch (error) {
        console.error('Error loading settings data:', error);
        showToast('Failed to load settings data', 'error');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [hasPermission, showToast]);

  const handleSaveBranding = async () => {
    if (!hasPermission('settings.write')) {
      showToast('You don\'t have permission to save settings', 'error');
      return;
    }

    try {
      await api.post('/api/settings/branding', branding);
      showToast('Branding settings saved successfully', 'success');
    } catch (error) {
      showToast('Failed to save branding settings', 'error');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const tabs = [
    { id: 'account', label: 'Account' },
    { id: 'providers', label: 'Providers' },
    { id: 'users', label: 'Users & Roles' },
    { id: 'branding', label: 'Branding' },
    { id: 'environment', label: 'Environment' }
  ];

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">Settings</h1>
      <p className="text-gray-600 mb-6">Configure communication providers and system settings</p>
      
      {/* Simple Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white border rounded-lg p-6">
        {activeTab === 'account' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Account Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Account Name</label>
                <input 
                  type="text" 
                  value={environment?.tenant_id || 'N/A'} 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
                <p className="text-xs text-gray-500 mt-1">Your unique account identifier</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Account Type</label>
                <input 
                  type="text" 
                  value="Standard" 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
                <p className="text-xs text-gray-500 mt-1">Your current subscription plan</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">System Version</label>
                <input 
                  type="text" 
                  value={environment?.backend_version || 'v1.0.1'} 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
                <p className="text-xs text-gray-500 mt-1">Current system version</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'providers' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Provider Status</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded">
                <span className="font-medium">Email Provider</span>
                <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">Mock</span>
              </div>
              <div className="flex items-center justify-between p-3 border rounded">
                <span className="font-medium">SMS Provider</span>
                <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">Mock</span>
              </div>
              <div className="flex items-center justify-between p-3 border rounded">
                <span className="font-medium">Voice Provider</span>
                <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">Mock</span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Users & Roles</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Total Users: {users?.length || 0}</span>
                {hasPermission('users.manage') && (
                  <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
                    Invite User
                  </button>
                )}
              </div>
              
              {users && users.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Roles</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {users.map((user) => (
                        <tr key={user.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {user.first_name} {user.last_name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {user.email}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div className="flex flex-wrap gap-1">
                              {user.roles?.map((role) => (
                                <span key={role} className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">
                                  {role}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {hasPermission('users.manage') && (
                              <button className="text-blue-600 hover:text-blue-900">Edit</button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  No users found
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'branding' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Branding & Appearance</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Company Name</label>
                <input 
                  type="text" 
                  value={branding?.tenant_name || ''} 
                  onChange={(e) => setBranding({ ...branding, tenant_name: e.target.value })}
                  placeholder="Your Company Name"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">This name will appear in the sidebar and login page</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Logo URL</label>
                <input 
                  type="text" 
                  value={branding?.logo_url || ''} 
                  onChange={(e) => setBranding({ ...branding, logo_url: e.target.value })}
                  placeholder="https://example.com/logo.png"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">URL to your company logo (PNG, JPG, or SVG recommended)</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">Primary Color</label>
                <div className="flex items-center space-x-2 mt-1">
                  <input 
                    type="text" 
                    value={branding?.primary_color || '#3b82f6'} 
                    onChange={(e) => setBranding({ ...branding, primary_color: e.target.value })}
                    placeholder="#3b82f6"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <div
                    className="w-10 h-10 rounded border"
                    style={{ backgroundColor: branding?.primary_color || '#3b82f6' }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Primary color for buttons, links, and accents (hex format)</p>
              </div>
              
              <div className="flex justify-end pt-4">
                <button
                  onClick={handleSaveBranding}
                  disabled={!hasPermission('settings.write')}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  Save Branding
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'environment' && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Environment Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Backend Version</label>
                <input 
                  type="text" 
                  value={environment?.backend_version || 'v1.0.1'} 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Build ID</label>
                <input 
                  type="text" 
                  value={environment?.build_id || 'N/A'} 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Tenant ID</label>
                <input 
                  type="text" 
                  value={environment?.tenant_id || 'N/A'} 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Secrets Configured</label>
                <input 
                  type="text" 
                  value={environment?.secrets_configured ? 'Yes' : 'No'} 
                  disabled 
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

