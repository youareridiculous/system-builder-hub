import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent } from '../utils/analytics';
import { canManageUsers, canManageSubscriptions } from '../utils/rbac';
import { 
  CreditCard, 
  Globe, 
  Users, 
  Settings,
  Download,
  Upload,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Plus,
  Edit,
  Trash2
} from 'lucide-react';

interface Subscription {
  subscription_id: string;
  status: string;
  plan: string;
  current_period_start: string;
  current_period_end: string;
  amount: number;
  currency: string;
  features: Record<string, any>;
}

interface Domain {
  domain: string;
  status: string;
  ssl_certificate: string;
  dns_configured: boolean;
  created_at: string;
  verified_at: string;
}

interface User {
  id: string;
  type: string;
  attributes: {
    user_id: string;
    role: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
}

interface TabProps {
  id: string;
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}

const Tab: React.FC<TabProps> = ({ id, label, icon, active, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
      active
        ? 'bg-blue-100 text-blue-700'
        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
    }`}
  >
    {icon}
    <span>{label}</span>
  </button>
);

interface SubscriptionCardProps {
  subscription: Subscription;
  onUpgrade: () => void;
  onDowngrade: () => void;
  onCancel: () => void;
}

const SubscriptionCard: React.FC<SubscriptionCardProps> = ({
  subscription,
  onUpgrade,
  onDowngrade,
  onCancel
}) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between mb-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Current Plan</h3>
        <p className="text-sm text-gray-600">{subscription.plan}</p>
      </div>
      <span className={`px-3 py-1 text-sm font-medium rounded-full ${
        subscription.status === 'active' 
          ? 'bg-green-100 text-green-800' 
          : 'bg-red-100 text-red-800'
      }`}>
        {subscription.status}
      </span>
    </div>

    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-600">Billing Amount</p>
          <p className="text-lg font-semibold text-gray-900">
            ${(subscription.amount / 100).toFixed(2)}/{subscription.currency}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Next Billing</p>
          <p className="text-sm text-gray-900">
            {new Date(subscription.current_period_end).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-900 mb-2">Plan Features</p>
        <div className="space-y-2">
          {Object.entries(subscription.features).map(([feature, limit]) => (
            <div key={feature} className="flex justify-between text-sm">
              <span className="text-gray-600 capitalize">
                {feature.replace('_', ' ')}
              </span>
              <span className="text-gray-900">{limit}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex space-x-3 pt-4 border-t">
        <button
          onClick={onUpgrade}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Upgrade
        </button>
        <button
          onClick={onDowngrade}
          className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          Downgrade
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
);

interface DomainCardProps {
  domain: Domain;
  onRemove: (domain: string) => void;
}

const DomainCard: React.FC<DomainCardProps> = ({ domain, onRemove }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center space-x-3">
        <Globe className="h-5 w-5 text-gray-400" />
        <div>
          <h3 className="font-medium text-gray-900">{domain.domain}</h3>
          <p className="text-sm text-gray-600">Custom Domain</p>
        </div>
      </div>
      <div className="flex items-center space-x-2">
        {domain.status === 'active' ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : (
          <XCircle className="h-5 w-5 text-red-500" />
        )}
      </div>
    </div>

    <div className="space-y-3">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">Status</span>
        <span className={`font-medium ${
          domain.status === 'active' ? 'text-green-600' : 'text-red-600'
        }`}>
          {domain.status}
        </span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">SSL Certificate</span>
        <span className={`font-medium ${
          domain.ssl_certificate === 'valid' ? 'text-green-600' : 'text-red-600'
        }`}>
          {domain.ssl_certificate}
        </span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">DNS Configured</span>
        <span className={`font-medium ${
          domain.dns_configured ? 'text-green-600' : 'text-red-600'
        }`}>
          {domain.dns_configured ? 'Yes' : 'No'}
        </span>
      </div>
    </div>

    <div className="flex justify-end mt-4 pt-4 border-t">
      <button
        onClick={() => onRemove(domain.domain)}
        className="text-red-600 hover:text-red-800 text-sm font-medium"
      >
        Remove Domain
      </button>
    </div>
  </div>
);

interface UserCardProps {
  user: User;
  onUpdateRole: (userId: string, newRole: string) => void;
}

const UserCard: React.FC<UserCardProps> = ({ user, onUpdateRole }) => {
  const getRoleColor = (role: string) => {
    switch (role) {
      case 'owner': return 'bg-purple-100 text-purple-800';
      case 'admin': return 'bg-red-100 text-red-800';
      case 'member': return 'bg-blue-100 text-blue-800';
      case 'viewer': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
            <Users className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <p className="font-medium text-gray-900">User {user.attributes.user_id}</p>
            <p className="text-sm text-gray-600">
              Joined {new Date(user.attributes.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <span className={`px-2 py-1 text-xs rounded-full ${getRoleColor(user.attributes.role)}`}>
          {user.attributes.role}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className={`w-2 h-2 rounded-full ${
            user.attributes.is_active ? 'bg-green-500' : 'bg-red-500'
          }`}></span>
          <span className="text-sm text-gray-600">
            {user.attributes.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <select
          value={user.attributes.role}
          onChange={(e) => onUpdateRole(user.attributes.user_id, e.target.value)}
          className="text-sm border border-gray-300 rounded px-2 py-1"
        >
          <option value="viewer">Viewer</option>
          <option value="member">Member</option>
          <option value="admin">Admin</option>
          <option value="owner">Owner</option>
        </select>
      </div>
    </div>
  );
};

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('subscription');
  const [newDomain, setNewDomain] = useState('');

  const { data: subscription, error: subscriptionError, isLoading: subscriptionLoading } = useApi('/admin/subscriptions');
  const { data: domains, error: domainsError, isLoading: domainsLoading } = useApi('/admin/domains');
  const { data: users, error: usersError, isLoading: usersLoading } = useApi('/admin/users');

  const handleUpgradeSubscription = () => {
    trackEvent('ui.subscription.upgrade');
    console.log('Opening upgrade subscription modal');
  };

  const handleDowngradeSubscription = () => {
    trackEvent('ui.subscription.downgrade');
    console.log('Opening downgrade subscription modal');
  };

  const handleCancelSubscription = () => {
    trackEvent('ui.subscription.cancel');
    if (window.confirm('Are you sure you want to cancel your subscription?')) {
      console.log('Cancelling subscription');
    }
  };

  const handleAddDomain = () => {
    if (!newDomain.trim()) return;
    trackEvent('ui.domain.add', { domain: newDomain });
    console.log('Adding domain:', newDomain);
    setNewDomain('');
  };

  const handleRemoveDomain = (domain: string) => {
    trackEvent('ui.domain.remove', { domain });
    if (window.confirm(`Are you sure you want to remove ${domain}?`)) {
      console.log('Removing domain:', domain);
    }
  };

  const handleUpdateUserRole = (userId: string, newRole: string) => {
    trackEvent('ui.user.role_update', { userId, newRole });
    console.log('Updating user role:', userId, 'to', newRole);
  };

  const handleBackupData = () => {
    trackEvent('ui.backup.create');
    console.log('Creating backup');
  };

  const handleRestoreData = () => {
    trackEvent('ui.backup.restore');
    console.log('Opening restore backup modal');
  };

  const handleExportData = () => {
    trackEvent('ui.gdpr.export');
    console.log('Exporting user data');
  };

  const handleDeleteData = () => {
    trackEvent('ui.gdpr.delete');
    if (window.confirm('Are you sure you want to delete all user data? This action cannot be undone.')) {
      console.log('Deleting user data');
    }
  };

  const isLoading = subscriptionLoading || domainsLoading || usersLoading;
  const error = subscriptionError || domainsError || usersError;

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage error={error} />;
  }

  const subscriptionData = subscription?.data?.attributes as Subscription;
  const domainsData = domains?.data?.attributes as Domain;
  const usersData = users?.data || [];

  const tabs = [
    { id: 'subscription', label: 'Subscription', icon: <CreditCard className="h-4 w-4" /> },
    { id: 'domains', label: 'Domains', icon: <Globe className="h-4 w-4" /> },
    { id: 'users', label: 'Users', icon: <Users className="h-4 w-4" /> },
    { id: 'backup', label: 'Backup & GDPR', icon: <Shield className="h-4 w-4" /> }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
        <p className="text-gray-600">Manage your account settings and team</p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {tabs.map((tab) => (
              <Tab
                key={tab.id}
                id={tab.id}
                label={tab.label}
                icon={tab.icon}
                active={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
              />
            ))}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {activeTab === 'subscription' && canManageSubscriptions() && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscription Management</h2>
              {subscriptionData && (
                <SubscriptionCard
                  subscription={subscriptionData}
                  onUpgrade={handleUpgradeSubscription}
                  onDowngrade={handleDowngradeSubscription}
                  onCancel={handleCancelSubscription}
                />
              )}
            </div>
          </div>
        )}

        {activeTab === 'domains' && canManageSubscriptions() && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Domain Management</h2>
              
              {/* Add Domain */}
              <div className="mb-6">
                <div className="flex space-x-3">
                  <input
                    type="text"
                    placeholder="Enter domain (e.g., app.example.com)"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={handleAddDomain}
                    disabled={!newDomain.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Domains List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {domainsData && (
                  <DomainCard
                    domain={domainsData}
                    onRemove={handleRemoveDomain}
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'users' && canManageUsers() && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">User Management</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {usersData.map((user: User) => (
                  <UserCard
                    key={user.id}
                    user={user}
                    onUpdateRole={handleUpdateUserRole}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'backup' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Backup & GDPR</h2>
              
              {/* Backup Section */}
              <div className="mb-8">
                <h3 className="text-md font-medium text-gray-900 mb-4">Data Backup</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={handleBackupData}
                    className="flex items-center justify-center space-x-2 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    <Download className="h-5 w-5 text-gray-600" />
                    <span>Create Backup</span>
                  </button>
                  <button
                    onClick={handleRestoreData}
                    className="flex items-center justify-center space-x-2 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    <Upload className="h-5 w-5 text-gray-600" />
                    <span>Restore Backup</span>
                  </button>
                </div>
              </div>

              {/* GDPR Section */}
              <div>
                <h3 className="text-md font-medium text-gray-900 mb-4">GDPR Compliance</h3>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-5 w-5 text-yellow-600" />
                    <span className="text-sm font-medium text-yellow-800">
                      Data Protection Notice
                    </span>
                  </div>
                  <p className="text-sm text-yellow-700 mt-2">
                    These actions are irreversible and will affect all user data in your account.
                  </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <button
                    onClick={handleExportData}
                    className="flex items-center justify-center space-x-2 px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    <Download className="h-5 w-5 text-gray-600" />
                    <span>Export User Data</span>
                  </button>
                  <button
                    onClick={handleDeleteData}
                    className="flex items-center justify-center space-x-2 px-4 py-3 border border-red-300 text-red-700 rounded-lg hover:bg-red-50"
                  >
                    <Trash2 className="h-5 w-5" />
                    <span>Delete All Data</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {!canManageSubscriptions() && (activeTab === 'subscription' || activeTab === 'domains') && (
          <div className="text-center py-8">
            <Shield className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Access Restricted</h3>
            <p className="text-gray-600">You don't have permission to manage subscription and domain settings.</p>
          </div>
        )}

        {!canManageUsers() && activeTab === 'users' && (
          <div className="text-center py-8">
            <Shield className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Access Restricted</h3>
            <p className="text-gray-600">You don't have permission to manage users.</p>
          </div>
        )}
      </div>
    </div>
  );
}
