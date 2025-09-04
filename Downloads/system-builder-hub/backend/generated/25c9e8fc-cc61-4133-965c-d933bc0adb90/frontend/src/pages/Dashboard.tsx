import React, { useState, useEffect } from 'react';
import { api } from '../lib/api.ts'
import { Building2, DollarSign, Calendar, TrendingUp, Users, Plus } from 'lucide-react';
import { DealCreateModal } from '../components/modals/DealCreateModal';

function Dashboard() {
  const [metrics, setMetrics] = useState({
    totalAccounts: 0,
    totalDeals: 0,
    openActivities: 0
  });
  const [openDealModal, setOpenDealModal] = useState(false);

  useEffect(() => {
    // Fetch metrics from API
    const fetchMetrics = async () => {
      try {
        const [accounts, deals, activities] = await Promise.all([
          api.get('/accounts/'),
          api.get('/deals/'),
          api.get('/activities/')
        ]);
        
        
        
        
        
        setMetrics({
          totalAccounts: accounts.length || 0,
          totalDeals: deals.length || 0,
          openActivities: activities.filter((a) => !a.completed).length || 0
        });
      } catch (error) {
        console.error('Error fetching metrics:', error);
      }
    };
    
    fetchMetrics();
  }, []);

  const metricCards = [
    {
      title: 'Total Accounts',
      value: metrics.totalAccounts,
      icon: Building2,
      color: 'bg-blue-500',
      textColor: 'text-blue-500'
    },
    {
      title: 'Total Deals',
      value: metrics.totalDeals,
      icon: DollarSign,
      color: 'bg-green-500',
      textColor: 'text-green-500'
    },
    {
      title: 'Open Activities',
      value: metrics.openActivities,
      icon: Calendar,
      color: 'bg-yellow-500',
      textColor: 'text-yellow-500'
    }
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex items-center space-x-4">
          <button 
            onClick={() => setOpenDealModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Deal
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.title} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center">
                <div className={`p-3 rounded-full ${metric.color} bg-opacity-10`}>
                  <Icon className={`w-6 h-6 ${metric.textColor}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{metric.title}</p>
                  <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Deals by Stage</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            Chart placeholder - Deals by Stage
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Activities by Type</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            Chart placeholder - Activities by Type
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-gray-600">New deal created: Enterprise Software License</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-600">Contact updated: John Smith</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
              <span className="text-sm text-gray-600">Activity scheduled: Follow-up call</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;