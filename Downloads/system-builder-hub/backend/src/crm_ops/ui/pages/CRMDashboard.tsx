import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner, SkeletonCard } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent, AnalyticsEvents } from '../utils/analytics';
import { canCreate } from '../utils/rbac';
import { 
  Users, 
  TrendingUp, 
  Target, 
  Calendar,
  Plus,
  Activity,
  DollarSign
} from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: string;
  icon: React.ReactNode;
  color: string;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, change, icon, color }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {change && (
          <p className={`text-sm ${change.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
            {change} from last month
          </p>
        )}
      </div>
      <div className={`p-3 rounded-full ${color}`}>
        {icon}
      </div>
    </div>
  </div>
);

interface QuickActionProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
}

const QuickAction: React.FC<QuickActionProps> = ({ title, description, icon, onClick, disabled }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className="bg-white rounded-lg shadow p-4 text-left hover:shadow-md transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
  >
    <div className="flex items-center space-x-3">
      <div className="p-2 bg-blue-100 rounded-lg">
        {icon}
      </div>
      <div>
        <h3 className="font-medium text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </div>
  </button>
);

export default function CRMDashboard() {
  const [selectedPeriod, setSelectedPeriod] = useState('30');

  const { data: analytics, error, isLoading, refetch } = useApi('/analytics/crm');
  const { data: recentDeals } = useApi('/deals?per_page=5');
  const { data: recentActivities } = useApi('/activities?per_page=5');

  React.useEffect(() => {
    trackEvent(AnalyticsEvents.DASHBOARD_VIEWED, { period: selectedPeriod });
  }, [selectedPeriod]);

  const handleQuickAction = (action: string) => {
    trackEvent('ui.quick_action.clicked', { action });
    // Trigger guided prompt or open modal
    console.log(`Opening ${action} guided prompt`);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  const analyticsData = analytics?.data?.attributes || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CRM Dashboard</h1>
          <p className="text-gray-600">Overview of your customer relationships and sales pipeline</p>
        </div>
        <select
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Total Contacts"
          value={analyticsData.contacts_added || 0}
          change="+12%"
          icon={<Users className="h-6 w-6 text-blue-600" />}
          color="bg-blue-100"
        />
        <KPICard
          title="Deals Won"
          value={analyticsData.deals_won || 0}
          change="+8%"
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          color="bg-green-100"
        />
        <KPICard
          title="Win Rate"
          value={`${analyticsData.win_rate?.toFixed(1) || 0}%`}
          change="+2.5%"
          icon={<Target className="h-6 w-6 text-purple-600" />}
          color="bg-purple-100"
        />
        <KPICard
          title="Total Value"
          value={`$${(analyticsData.total_deal_value || 0).toLocaleString()}`}
          change="+15%"
          icon={<DollarSign className="h-6 w-6 text-yellow-600" />}
          color="bg-yellow-100"
        />
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickAction
            title="Add Contact"
            description="Create a new contact"
            icon={<Plus className="h-5 w-5 text-blue-600" />}
            onClick={() => handleQuickAction('add_contact')}
            disabled={!canCreate('contacts')}
          />
          <QuickAction
            title="Create Deal"
            description="Start a new deal"
            icon={<DollarSign className="h-5 w-5 text-green-600" />}
            onClick={() => handleQuickAction('create_deal')}
            disabled={!canCreate('deals')}
          />
          <QuickAction
            title="Log Activity"
            description="Record a call, meeting, or task"
            icon={<Activity className="h-5 w-5 text-purple-600" />}
            onClick={() => handleQuickAction('log_activity')}
            disabled={!canCreate('activities')}
          />
        </div>
      </div>

      {/* Pipeline Summary */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Summary</h2>
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="grid grid-cols-5 divide-x divide-gray-200">
            {Object.entries(analyticsData.pipeline_summary || {}).map(([stage, count]) => (
              <div key={stage} className="p-4 text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-sm text-gray-600 capitalize">
                  {stage.replace('_', ' ')}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Deals</h3>
          <div className="space-y-3">
            {recentDeals?.data?.slice(0, 5).map((deal: any) => (
              <div key={deal.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <div>
                  <p className="font-medium text-gray-900">{deal.attributes.title}</p>
                  <p className="text-sm text-gray-600">
                    ${deal.attributes.value?.toLocaleString() || 0}
                  </p>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  deal.attributes.status === 'won' ? 'bg-green-100 text-green-800' :
                  deal.attributes.status === 'lost' ? 'bg-red-100 text-red-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {deal.attributes.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activities</h3>
          <div className="space-y-3">
            {recentActivities?.data?.slice(0, 5).map((activity: any) => (
              <div key={activity.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                <div>
                  <p className="font-medium text-gray-900">{activity.attributes.title}</p>
                  <p className="text-sm text-gray-600 capitalize">
                    {activity.attributes.type}
                  </p>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  activity.attributes.status === 'completed' ? 'bg-green-100 text-green-800' :
                  activity.attributes.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {activity.attributes.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
