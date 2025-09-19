'use client';

import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  Download, 
  Eye, 
  Edit, 
  Trash2, 
  Globe, 
  Clock, 
  Code, 
  Database, 
  Server, 
  Cloud,
  CheckCircle,
  AlertCircle,
  Loader2,
  Plus,
  RefreshCw
} from 'lucide-react';

interface SystemSpec {
  name: string;
  description: string;
  type: string;
  techStack: string[];
  features: string[];
  infrastructure: string[];
}

interface GeneratedSystem {
  id: string;
  specification: SystemSpec;
  preview: any;
  templates: any;
  architecture: any;
  deployment: any;
  status: string;
  createdAt: string;
  updatedAt: string;
  deploymentUrl?: string;
  deploymentStatus?: 'idle' | 'deploying' | 'success' | 'error';
}

interface SystemDashboardProps {
  onSystemSelect: (system: GeneratedSystem) => void;
  onCreateNew: () => void;
}

export default function SystemDashboard({ onSystemSelect, onCreateNew }: SystemDashboardProps) {
  const [systems, setSystems] = useState<GeneratedSystem[]>([]);
  const [filteredSystems, setFilteredSystems] = useState<GeneratedSystem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSystems, setSelectedSystems] = useState<string[]>([]);

  useEffect(() => {
    loadSystems();
  }, []);

  useEffect(() => {
    filterSystems();
  }, [systems, searchTerm, statusFilter, typeFilter]);

  const loadSystems = async () => {
    setIsLoading(true);
    try {
      // This would typically fetch from a systems list endpoint
      // For now, we'll simulate with localStorage or a mock API
      const response = await fetch('/api/systems/list');
      if (response.ok) {
        const data = await response.json();
        setSystems(data.systems || []);
      } else {
        // Fallback to localStorage for demo
        const storedSystems = localStorage.getItem('sbh-systems');
        if (storedSystems) {
          setSystems(JSON.parse(storedSystems));
        }
      }
    } catch (error) {
      console.error('Error loading systems:', error);
      // Fallback to localStorage for demo
      const storedSystems = localStorage.getItem('sbh-systems');
      if (storedSystems) {
        setSystems(JSON.parse(storedSystems));
      }
    } finally {
      setIsLoading(false);
    }
  };

  const filterSystems = () => {
    let filtered = systems;

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(system =>
        system.specification.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        system.specification.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        system.specification.techStack.some(tech => 
          tech.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(system => system.status === statusFilter);
    }

    // Type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter(system => system.specification.type === typeFilter);
    }

    setFilteredSystems(filtered);
  };

  const deleteSystem = async (systemId: string) => {
    if (!confirm('Are you sure you want to delete this system?')) return;

    try {
      const response = await fetch(`/api/systems/${systemId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setSystems(prev => prev.filter(s => s.id !== systemId));
        setSelectedSystems(prev => prev.filter(id => id !== systemId));
      } else {
        alert('Failed to delete system');
      }
    } catch (error) {
      console.error('Error deleting system:', error);
      alert('Error deleting system');
    }
  };

  const downloadSystem = async (systemId: string) => {
    try {
      const response = await fetch(`/api/system/download/${systemId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `system-${systemId}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Error downloading system:', error);
    }
  };

  const deploySystem = async (systemId: string) => {
    try {
      const response = await fetch(`/api/system/deploy/${systemId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain_type: 'sbh_managed' })
      });

      const data = await response.json();
      
      if (data.success) {
        setSystems(prev => prev.map(s => 
          s.id === systemId 
            ? { ...s, deploymentUrl: data.deployment_url, deploymentStatus: 'success' }
            : s
        ));
      }
    } catch (error) {
      console.error('Error deploying system:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'generated':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'generating':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'web_app':
        return <Code className="h-4 w-4 text-blue-500" />;
      case 'api':
        return <Server className="h-4 w-4 text-green-500" />;
      case 'mobile_app':
        return <Database className="h-4 w-4 text-purple-500" />;
      default:
        return <Cloud className="h-4 w-4 text-gray-500" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Loading systems...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Dashboard</h1>
          <p className="text-gray-600">Manage your generated systems</p>
        </div>
        <button
          onClick={onCreateNew}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          <span>New System</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search systems..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Status</option>
            <option value="generated">Generated</option>
            <option value="generating">Generating</option>
            <option value="error">Error</option>
          </select>
          
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Types</option>
            <option value="web_app">Web App</option>
            <option value="api">API</option>
            <option value="mobile_app">Mobile App</option>
            <option value="desktop_app">Desktop App</option>
            <option value="microservice">Microservice</option>
          </select>
          
          <button
            onClick={loadSystems}
            className="px-3 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Systems Grid */}
      {filteredSystems.length === 0 ? (
        <div className="text-center py-12">
          <Code className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No systems found</h3>
          <p className="text-gray-600 mb-4">
            {systems.length === 0 
              ? "Get started by creating your first system"
              : "Try adjusting your search or filters"
            }
          </p>
          {systems.length === 0 && (
            <button
              onClick={onCreateNew}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Create Your First System
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSystems.map((system) => (
            <div key={system.id} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
              {/* System Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-2">
                  {getTypeIcon(system.specification.type)}
                  <h3 className="text-lg font-semibold text-gray-900 truncate">
                    {system.specification.name}
                  </h3>
                </div>
                <div className="flex items-center space-x-1">
                  {getStatusIcon(system.status)}
                </div>
              </div>

              {/* System Description */}
              <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                {system.specification.description}
              </p>

              {/* System Stats */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-900">
                    {system.preview?.fileCount || 0}
                  </div>
                  <div className="text-xs text-gray-500">Files</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-900">
                    {system.preview?.components || 0}
                  </div>
                  <div className="text-xs text-gray-500">Components</div>
                </div>
              </div>

              {/* Tech Stack */}
              <div className="mb-4">
                <div className="flex flex-wrap gap-1">
                  {system.specification.techStack.slice(0, 3).map((tech, index) => (
                    <span key={index} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                      {tech}
                    </span>
                  ))}
                  {system.specification.techStack.length > 3 && (
                    <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                      +{system.specification.techStack.length - 3}
                    </span>
                  )}
                </div>
              </div>

              {/* Deployment Status */}
              {system.deploymentUrl && (
                <div className="mb-4 p-2 bg-green-50 border border-green-200 rounded-md">
                  <div className="flex items-center space-x-2">
                    <Globe className="h-3 w-3 text-green-600" />
                    <span className="text-xs text-green-800">Live</span>
                  </div>
                  <a
                    href={system.deploymentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-green-600 hover:text-green-700 underline truncate block"
                  >
                    {system.deploymentUrl}
                  </a>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => onSystemSelect(system)}
                    className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                    title="View Details"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                  
                  <button
                    onClick={() => downloadSystem(system.id)}
                    className="p-2 text-gray-400 hover:text-green-600 transition-colors"
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                  
                  {!system.deploymentUrl && (
                    <button
                      onClick={() => deploySystem(system.id)}
                      className="p-2 text-gray-400 hover:text-purple-600 transition-colors"
                      title="Deploy"
                    >
                      <Globe className="h-4 w-4" />
                    </button>
                  )}
                </div>
                
                <div className="text-xs text-gray-500">
                  {formatDate(system.createdAt)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Bulk Actions */}
      {selectedSystems.length > 0 && (
        <div className="fixed bottom-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              {selectedSystems.length} selected
            </span>
            <div className="flex space-x-2">
              <button className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200">
                Download All
              </button>
              <button className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200">
                Delete All
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
