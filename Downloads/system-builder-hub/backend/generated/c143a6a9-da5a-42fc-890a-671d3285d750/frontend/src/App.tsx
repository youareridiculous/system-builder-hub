import React, { useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  Home, 
  Building2, 
  Users, 
  DollarSign, 
  GitBranch, 
  Calendar,
  Plus
} from 'lucide-react';

// Import pages
import Dashboard from './pages/Dashboard.tsx';
import Accounts from './pages/Accounts.tsx';
import Contacts from './pages/Contacts';
import Deals from './pages/Deals';
import Pipelines from './pages/Pipelines';
import Activities from './pages/Activities';

// Import modals
import { AccountCreateModal } from './components/modals/AccountCreateModal';
import { DealCreateModal } from './components/modals/DealCreateModal';

function Sidebar() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/accounts', label: 'Accounts', icon: Building2 },
    { path: '/contacts', label: 'Contacts', icon: Users },
    { path: '/deals', label: 'Deals', icon: DollarSign },
    { path: '/pipelines', label: 'Pipelines', icon: GitBranch },
    { path: '/activities', label: 'Activities', icon: Calendar },
  ];

  return (
    <div className="w-64 bg-gray-900 text-white h-screen fixed left-0 top-0 overflow-y-auto">
      <div className="p-6">
        <h1 className="text-xl font-bold mb-8">CRM Flagship</h1>
        
        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
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
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        
        <div className="mt-8 pt-6 border-t border-gray-700">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Quick Actions
          </h3>
          <div className="space-y-2">
            <button 
              onClick={() => window.dispatchEvent(new CustomEvent('open-account-modal'))}
              className="flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors w-full"
            >
              <Plus className="w-5 h-5" />
              <span>New Account</span>
            </button>
            <button 
              onClick={() => window.dispatchEvent(new CustomEvent('open-deal-modal'))}
              className="flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white transition-colors w-full"
            >
              <Plus className="w-5 h-5" />
              <span>New Deal</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [accountModalOpen, setAccountModalOpen] = useState(false);
  const [dealModalOpen, setDealModalOpen] = useState(false);

  React.useEffect(() => {
    const handleAccountModal = () => setAccountModalOpen(true);
    const handleDealModal = () => setDealModalOpen(true);
    
    window.addEventListener('open-account-modal', handleAccountModal);
    window.addEventListener('open-deal-modal', handleDealModal);
    
    return () => {
      window.removeEventListener('open-account-modal', handleAccountModal);
      window.removeEventListener('open-deal-modal', handleDealModal);
    };
  }, []);

  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-64 p-6 bg-gray-50 min-h-screen w-full">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/deals" element={<Deals />} />
          <Route path="/pipelines" element={<Pipelines />} />
          <Route path="/activities" element={<Activities />} />
        </Routes>
      </main>
      
      {/* Global modals */}
      <AccountCreateModal 
        open={accountModalOpen} 
        onOpenChange={setAccountModalOpen} 
        onCreated={() => {
          window.dispatchEvent(new Event('reload-accounts'));
        }} 
      />
      <DealCreateModal 
        open={dealModalOpen} 
        onOpenChange={setDealModalOpen} 
        onCreated={() => {
          window.dispatchEvent(new Event('reload-deals'));
        }} 
      />
    </div>
  );
}

export default App;
