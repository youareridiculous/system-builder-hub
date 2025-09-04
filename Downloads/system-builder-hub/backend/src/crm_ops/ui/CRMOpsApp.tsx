import React, { useState } from 'react';
import { 
  Home, 
  Users, 
  DollarSign, 
  Activity, 
  FolderOpen, 
  CheckSquare, 
  MessageSquare, 
  BarChart3, 
  Settings,
  Menu,
  X
} from 'lucide-react';
import CRMDashboard from './pages/CRMDashboard';
import ContactsManager from './pages/ContactsManager';
import DealPipeline from './pages/DealPipeline';
import ProjectKanban from './pages/ProjectKanban';
import AnalyticsDashboard from './pages/AnalyticsDashboard';
import TeamChat from './pages/TeamChat';
import AdminPanel from './pages/AdminPanel';

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  component: React.ComponentType;
  requiresAuth?: boolean;
}

const navigationItems: NavigationItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <Home className="h-5 w-5" />, component: CRMDashboard },
  { id: 'contacts', label: 'Contacts', icon: <Users className="h-5 w-5" />, component: ContactsManager },
  { id: 'deals', label: 'Deals', icon: <DollarSign className="h-5 w-5" />, component: DealPipeline },
  { id: 'activities', label: 'Activities', icon: <Activity className="h-5 w-5" />, component: CRMDashboard },
  { id: 'projects', label: 'Projects', icon: <FolderOpen className="h-5 w-5" />, component: ProjectKanban },
  { id: 'tasks', label: 'Tasks', icon: <CheckSquare className="h-5 w-5" />, component: ProjectKanban },
  { id: 'messages', label: 'Messages', icon: <MessageSquare className="h-5 w-5" />, component: TeamChat },
  { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="h-5 w-5" />, component: AnalyticsDashboard },
  { id: 'admin', label: 'Admin', icon: <Settings className="h-5 w-5" />, component: AdminPanel },
];

export default function CRMOpsApp() {
  const [activePage, setActivePage] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const currentUser = {
    name: 'John Doe',
    email: 'john@example.com',
    role: 'admin'
  };

  const ActiveComponent = navigationItems.find(item => item.id === activePage)?.component || CRMDashboard;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">CRM/Ops</h1>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* User info */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
              <span className="text-sm font-medium text-blue-600">
                {currentUser.name.split(' ').map(n => n[0]).join('')}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{currentUser.name}</p>
              <p className="text-xs text-gray-500">{currentUser.role}</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navigationItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                setActivePage(item.id);
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center space-x-3 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activePage === item.id
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-30 bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-gray-400 hover:text-gray-600"
            >
              <Menu className="h-6 w-6" />
            </button>
            
            <div className="flex items-center space-x-4">
              <div className="hidden sm:block">
                <h2 className="text-lg font-medium text-gray-900">
                  {navigationItems.find(item => item.id === activePage)?.label}
                </h2>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <button className="text-gray-400 hover:text-gray-600">
                <div className="relative">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full"></span>
                </div>
              </button>

              {/* User menu */}
              <div className="relative">
                <button className="flex items-center space-x-2 text-gray-400 hover:text-gray-600">
                  <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-600">
                      {currentUser.name.split(' ').map(n => n[0]).join('')}
                    </span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <ActiveComponent />
        </main>
      </div>
    </div>
  );
}
