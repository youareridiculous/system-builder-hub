import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation, useParams } from 'react-router-dom';
import { ToastProviderWrapper } from './contexts/ToastContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import { 
  Home, 
  Building2, 
  Users, 
  DollarSign, 
  GitBranch, 
  Calendar,
  MessageSquare,
  Plus,
  ChevronDown,
  ChevronRight,
  Mail,
  Phone,
  FileText,
  Webhook,
  Settings as SettingsIcon,
  Zap,
  LogOut,
  User,
  TrendingUp
} from 'lucide-react';

// Import pages
import Dashboard from './pages/Dashboard.tsx';
import Accounts from './pages/Accounts.tsx';
import Contacts from './pages/Contacts';
import Deals from './pages/Deals';
import Pipelines from './pages/Pipelines';
import Activities from './pages/Activities';
import Communications from './pages/Communications';
import ContactDetail from './pages/ContactDetail';
import Templates from './pages/Templates';
import Automations from './pages/Automations';
import Analytics from './pages/Analytics';
import Webhooks from './pages/Webhooks';
import Settings from './pages/Settings';
import Login from './pages/Login';

// Import modals
import { AccountCreateModal } from './components/modals/AccountCreateModal';
import { DealCreateModal } from './components/modals/DealCreateModal';

function Sidebar() {
  const location = useLocation();
  const { user, logout, hasPermission } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [accountsExpanded, setAccountsExpanded] = useState(false);
  
  // Fetch accounts on component mount (only if user is authenticated)
  useEffect(() => {
    const fetchAccounts = async () => {
      if (!user) return; // Don't fetch if user is not logged in
      
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;
        
        const response = await fetch('http://localhost:8000/api/accounts/', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setAccounts(data);
        }
      } catch (error) {
        console.error('Error fetching accounts:', error);
      }
    };
    fetchAccounts();
  }, [user]); // Re-run when user changes

  const accountNavItems = [
    { path: `/account/${selectedAccount?.id}/dashboard`, label: 'Dashboard', icon: Home, permission: 'analytics.read' },
    { path: `/account/${selectedAccount?.id}/contacts`, label: 'Contacts', icon: Users, permission: 'contacts.read' },
    { path: `/account/${selectedAccount?.id}/deals`, label: 'Deals', icon: DollarSign, permission: 'deals.read' },
    { path: `/account/${selectedAccount?.id}/pipelines`, label: 'Pipelines', icon: GitBranch, permission: 'pipelines.read' },
    { path: `/account/${selectedAccount?.id}/activities`, label: 'Activities', icon: Calendar, permission: 'activities.read' },
    { path: `/account/${selectedAccount?.id}/communications`, label: 'Communications', icon: MessageSquare, permission: 'communications.read' },
    { path: `/templates`, label: 'Templates', icon: FileText, permission: 'templates.read' },
    { path: `/automations`, label: 'Automations', icon: Zap, permission: 'automations.read' },
    { path: `/analytics`, label: 'Analytics', icon: TrendingUp, permission: 'analytics.read' },
    { path: `/webhooks`, label: 'Webhooks', icon: Webhook, permission: 'webhooks.read' },
    { path: `/settings`, label: 'Settings', icon: SettingsIcon, permission: 'settings.read' },
  ];

  return (
    <div className="w-64 bg-gray-900 text-white h-screen fixed left-0 top-0 overflow-y-auto">
      <div className="p-6">
        <h1 className="text-xl font-bold mb-8">CRM Flagship</h1>
        
        {/* User Info */}
        {user && (
          <div className="mb-6 p-3 bg-gray-800 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <User className="w-4 h-4" />
              <span className="text-sm font-medium">{user.name}</span>
            </div>
            <div className="text-xs text-gray-400 mb-2">{user.email}</div>
            <div className="flex flex-wrap gap-1">
              {user.roles.map((role) => (
                <span key={role} className="text-xs bg-blue-600 px-2 py-1 rounded">
                  {role}
                </span>
              ))}
            </div>
            <button
              onClick={logout}
              className="mt-2 w-full flex items-center justify-center space-x-2 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <LogOut className="w-3 h-3" />
              <span>Logout</span>
            </button>
          </div>
        )}
        
        <nav className="space-y-2">
          {/* Accounts Dropdown */}
          <div className="space-y-1">
            {!selectedAccount ? (
              // Show dropdown when no account is selected
              <>
                <button
                  onClick={() => setAccountsExpanded(!accountsExpanded)}
                  className="flex items-center justify-between w-full px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <Building2 className="w-5 h-5" />
                    <span>Accounts</span>
                  </div>
                  {accountsExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
                
                {accountsExpanded && (
                  <div className="ml-6 space-y-1">
                    {accounts.map((account) => (
                      <button
                        key={account.id}
                        onClick={() => {
                          setSelectedAccount(account);
                          setAccountsExpanded(false); // Collapse dropdown after selection
                        }}
                        className="w-full text-left px-3 py-2 rounded-md text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                      >
                        {account.name}
                      </button>
                    ))}
                  </div>
                )}
              </>
            ) : (
              // Show selected account with navigation
              <>
                {/* Account Info Card */}
                <div className="mb-4 p-3 bg-gray-800 rounded-lg">
                  <div className="flex items-center space-x-2 mb-1">
                    <Building2 className="w-4 h-4" />
                    <span className="text-sm font-medium text-white">Current Account</span>
                  </div>
                  <div className="text-sm text-gray-300 font-semibold">{selectedAccount.name}</div>
                </div>
                
                {accountNavItems.map((item) => {
                  // Check if user has permission for this item
                  if (item.permission && !hasPermission(item.permission)) {
                    return null;
                  }
                  
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                      }`}
                    >
                      <item.icon className="w-5 h-5" />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </>
            )}
          </div>
          
          {/* Quick Actions */}
          {selectedAccount && (
            <div className="pt-4 border-t border-gray-700">
              <h3 className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Quick Actions
              </h3>
              <div className="space-y-1">
                {hasPermission('contacts.write') && (
                  <button
                    onClick={() => window.dispatchEvent(new CustomEvent('open-contact-modal'))}
                    className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>New Contact</span>
                  </button>
                )}
                {hasPermission('deals.write') && (
                  <button
                    onClick={() => window.dispatchEvent(new CustomEvent('open-deal-modal'))}
                    className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>New Deal</span>
                  </button>
                )}
                {hasPermission('communications.send') && (
                  <>
                    <button
                      onClick={() => window.dispatchEvent(new CustomEvent('open-email-modal'))}
                      className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                    >
                      <Mail className="w-4 h-4" />
                      <span>Send Email</span>
                    </button>
                    <button
                      onClick={() => window.dispatchEvent(new CustomEvent('open-sms-modal'))}
                      className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />
                      <span>Send SMS</span>
                    </button>
                    <button
                      onClick={() => window.dispatchEvent(new CustomEvent('open-call-modal'))}
                      className="w-full flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
                    >
                      <Phone className="w-4 h-4" />
                      <span>Make Call</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </nav>
      </div>
    </div>
  );
}

function AppContent() {
  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <div className="flex-1 ml-64 p-6 overflow-y-auto max-w-full bg-white">
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/accounts" element={
            <ProtectedRoute requiredPermission="accounts.read">
              <Accounts />
            </ProtectedRoute>
          } />
          
          <Route path="/contacts" element={
            <ProtectedRoute requiredPermission="contacts.read">
              <Contacts />
            </ProtectedRoute>
          } />
          
          <Route path="/contacts/:id" element={
            <ProtectedRoute requiredPermission="contacts.read">
              <ContactDetail />
            </ProtectedRoute>
          } />
          
          <Route path="/deals" element={
            <ProtectedRoute requiredPermission="deals.read">
              <Deals />
            </ProtectedRoute>
          } />
          
          <Route path="/pipelines" element={
            <ProtectedRoute requiredPermission="pipelines.read">
              <Pipelines />
            </ProtectedRoute>
          } />
          
          <Route path="/activities" element={
            <ProtectedRoute requiredPermission="activities.read">
              <Activities />
            </ProtectedRoute>
          } />
          
          <Route path="/communications" element={
            <ProtectedRoute requiredPermission="communications.read">
              <Communications />
            </ProtectedRoute>
          } />
          
          <Route path="/templates" element={
            <ProtectedRoute requiredPermission="templates.read">
              <Templates />
            </ProtectedRoute>
          } />
          
          <Route path="/automations" element={
            <ProtectedRoute requiredPermission="automations.read">
              <Automations />
            </ProtectedRoute>
          } />
          
          <Route path="/analytics" element={
            <ProtectedRoute requiredPermission="analytics.read">
              <Analytics />
            </ProtectedRoute>
          } />
          
          <Route path="/webhooks" element={
            <ProtectedRoute requiredPermission="webhooks.read">
              <Webhooks />
            </ProtectedRoute>
          } />
          
          <Route path="/settings" element={
            <ProtectedRoute requiredPermission="settings.read">
              <Settings />
            </ProtectedRoute>
          } />
          
          {/* Account-specific routes */}
          <Route path="/account/:accountId/dashboard" element={
            <ProtectedRoute requiredPermission="analytics.read">
              <Dashboard />
            </ProtectedRoute>
          } />
          
          <Route path="/account/:accountId/contacts" element={
            <ProtectedRoute requiredPermission="contacts.read">
              <Contacts />
            </ProtectedRoute>
          } />
          
          <Route path="/account/:accountId/deals" element={
            <ProtectedRoute requiredPermission="deals.read">
              <Deals />
            </ProtectedRoute>
          } />
          
          <Route path="/account/:accountId/pipelines" element={
            <ProtectedRoute requiredPermission="pipelines.read">
              <Pipelines />
            </ProtectedRoute>
          } />
          
          <Route path="/account/:accountId/activities" element={
            <ProtectedRoute requiredPermission="activities.read">
              <Activities />
            </ProtectedRoute>
          } />
          
          <Route path="/account/:accountId/communications" element={
            <ProtectedRoute requiredPermission="communications.read">
              <Communications />
            </ProtectedRoute>
          } />
        </Routes>
      </div>
      
      {/* Modals */}
      <AccountCreateModal />
      <DealCreateModal />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProviderWrapper>
        <AppContent />
      </ToastProviderWrapper>
    </AuthProvider>
  );
}
