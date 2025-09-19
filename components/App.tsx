'use client';

import React, { useState } from 'react';
import { 
  Home, 
  Code, 
  Database, 
  Settings, 
  LogOut, 
  Menu, 
  X,
  User,
  Bell,
  Search
} from 'lucide-react';
import SystemBuilder from './SystemBuilder';
import SystemDashboard from './SystemDashboard';
import EditWorkflow from './EditWorkflow';
import DomainManagement from './DomainManagement';

interface GeneratedSystem {
  id: string;
  specification: any;
  preview: any;
  templates: any;
  architecture: any;
  deployment: any;
  status: string;
  createdAt: string;
  updatedAt: string;
}

type ViewMode = 'dashboard' | 'builder' | 'edit' | 'domain';

export default function App() {
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');
  const [selectedSystem, setSelectedSystem] = useState<GeneratedSystem | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState({
    name: 'Admin User',
    email: 'admin@sbh.com',
    avatar: null
  });

  const handleSystemSelect = (system: GeneratedSystem) => {
    setSelectedSystem(system);
    setCurrentView('edit');
  };

  const handleCreateNew = () => {
    setSelectedSystem(null);
    setCurrentView('builder');
  };

  const handleSystemUpdate = (updatedSystem: GeneratedSystem) => {
    setSelectedSystem(updatedSystem);
  };

  const handleDomainConfigured = (config: any) => {
    // Handle domain configuration
    console.log('Domain configured:', config);
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <SystemDashboard
            onSystemSelect={handleSystemSelect}
            onCreateNew={handleCreateNew}
          />
        );
      case 'builder':
        return <SystemBuilder />;
      case 'edit':
        return selectedSystem ? (
          <EditWorkflow
            system={selectedSystem}
            onSystemUpdate={handleSystemUpdate}
            onClose={() => setCurrentView('dashboard')}
          />
        ) : (
          <SystemDashboard
            onSystemSelect={handleSystemSelect}
            onCreateNew={handleCreateNew}
          />
        );
      case 'domain':
        return selectedSystem ? (
          <DomainManagement
            systemId={selectedSystem.id}
            onDomainConfigured={handleDomainConfigured}
          />
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-600">Please select a system first</p>
          </div>
        );
      default:
        return (
          <SystemDashboard
            onSystemSelect={handleSystemSelect}
            onCreateNew={handleCreateNew}
          />
        );
    }
  };

  const navigation = [
    { name: 'Dashboard', icon: Home, view: 'dashboard' as ViewMode },
    { name: 'System Builder', icon: Code, view: 'builder' as ViewMode },
    { name: 'Edit System', icon: Database, view: 'edit' as ViewMode, disabled: !selectedSystem },
    { name: 'Domain Management', icon: Settings, view: 'domain' as ViewMode, disabled: !selectedSystem },
  ];

  return (
    <div className="h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      } lg:translate-x-0 lg:static lg:inset-0`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <Code className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">SBH</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="mt-6 px-3">
          <div className="space-y-1">
            {navigation.map((item) => (
              <button
                key={item.name}
                onClick={() => {
                  setCurrentView(item.view);
                  setSidebarOpen(false);
                }}
                disabled={item.disabled}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  currentView === item.view
                    ? 'bg-blue-100 text-blue-700'
                    : item.disabled
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </button>
            ))}
          </div>
        </nav>

        {/* User Section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user.name}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {user.email}
              </p>
            </div>
            <button className="text-gray-400 hover:text-gray-600">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:ml-0">
        {/* Top Navigation */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden text-gray-400 hover:text-gray-600"
              >
                <Menu className="h-6 w-6" />
              </button>
              
              <div className="ml-4 lg:ml-0">
                <h1 className="text-xl font-semibold text-gray-900">
                  {currentView === 'dashboard' && 'System Dashboard'}
                  {currentView === 'builder' && 'System Builder'}
                  {currentView === 'edit' && 'Edit System'}
                  {currentView === 'domain' && 'Domain Management'}
                </h1>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Search */}
              <div className="hidden md:block">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search systems..."
                    className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Notifications */}
              <button className="text-gray-400 hover:text-gray-600">
                <Bell className="h-5 w-5" />
              </button>

              {/* User Menu */}
              <div className="flex items-center space-x-2">
                <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center">
                  <User className="h-4 w-4 text-white" />
                </div>
                <span className="hidden md:block text-sm font-medium text-gray-700">
                  {user.name}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 sm:p-6 lg:p-8">
            {renderCurrentView()}
          </div>
        </main>
      </div>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
