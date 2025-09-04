import React from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { 
  BarChart3, 
  Building2, 
  Users, 
  DollarSign, 
  FileText, 
  Calendar,
  Plus
} from 'lucide-react'
import Dashboard from './pages/Dashboard.jsx'
import Accounts from './pages/Accounts.jsx'
import Contacts from './pages/Contacts.jsx'
import Deals from './pages/Deals.jsx'
import Pipelines from './pages/Pipelines.jsx'
import Activities from './pages/Activities.jsx'

function App() {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/accounts', label: 'Accounts', icon: Building2 },
    { path: '/contacts', label: 'Contacts', icon: Users },
    { path: '/deals', label: 'Deals', icon: DollarSign },
    { path: '/pipelines', label: 'Pipelines', icon: FileText },
    { path: '/activities', label: 'Activities', icon: Calendar }
  ]

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">CRM System</h1>
          <p className="text-sm text-gray-500">Professional CRM</p>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path
            const Icon = item.icon
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.label}
              </Link>
            )
          })}
        </nav>
        
        {/* Quick Actions */}
        <div className="p-4 border-t border-gray-200">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Quick Actions
          </h3>
          <div className="space-y-2">
            <button className="w-full flex items-center px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-md transition-colors">
              <Plus className="w-4 h-4 mr-2" />
              New Account
            </button>
            <button className="w-full flex items-center px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-md transition-colors">
              <Plus className="w-4 h-4 mr-2" />
              New Deal
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <div className="p-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/deals" element={<Deals />} />
            <Route path="/pipelines" element={<Pipelines />} />
            <Route path="/activities" element={<Activities />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}

export default App
