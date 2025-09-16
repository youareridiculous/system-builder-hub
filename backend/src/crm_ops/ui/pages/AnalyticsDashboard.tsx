import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent, AnalyticsEvents } from '../utils/analytics';
import { 
  TrendingUp, 
  TrendingDown,
  Users,
  DollarSign,
  Target,
  Calendar,
  Activity,
  BarChart3,
  PieChart,
  Download
} from 'lucide-react';

interface AnalyticsData {
  contacts_added: number;
  deals_open: number;
  deals_won: number;
  deals_lost: number;
  pipeline_summary: Record<string, number>;
  tasks_completed: number;
  total_deal_value: number;
  average_deal_value: number;
  win_rate: number;
  period_days: number;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: React.ReactNode;
  color: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  change, 
  changeType = 'neutral',
  icon, 
  color 
}) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {change && (
          <div className="flex items-center mt-1">
            {changeType === 'positive' ? (
              <TrendingUp className="h-4 w-4 text-green-600 mr-1" />
            ) : changeType === 'negative' ? (
              <TrendingDown className="h-4 w-4 text-red-600 mr-1" />
            ) : null}
            <span className={`text-sm ${
              changeType === 'positive' ? 'text-green-600' : 
              changeType === 'negative' ? 'text-red-600' : 'text-gray-600'
            }`}>
              {change}
            </span>
          </div>
        )}
      </div>
      <div className={`p-3 rounded-full ${color}`}>
        {icon}
      </div>
    </div>
  </div>
);

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
  icon?: React.ReactNode;
}

const ChartCard: React.FC<ChartCardProps> = ({ title, children, icon }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {icon && (
        <div className="p-2 bg-gray-100 rounded-lg">
          {icon}
        </div>
      )}
    </div>
    {children}
  </div>
);

// Simple chart components (in a real app, you'd use a charting library like Chart.js or Recharts)
const SimpleBarChart: React.FC<{ data: Record<string, number>; title: string }> = ({ data, title }) => {
  const maxValue = Math.max(...Object.values(data));
  
  return (
    <div className="space-y-3">
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600 capitalize">{key.replace('_', ' ')}</span>
            <span className="text-gray-900 font-medium">{value}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(value / maxValue) * 100}%` }}
            ></div>
          </div>
        </div>
      ))}
    </div>
  );
};

const SimplePieChart: React.FC<{ data: Record<string, number>; title: string }> = ({ data, title }) => {
  const total = Object.values(data).reduce((sum, value) => sum + value, 0);
  
  return (
    <div className="space-y-3">
      {Object.entries(data).map(([key, value]) => {
        const percentage = total > 0 ? (value / total) * 100 : 0;
        return (
          <div key={key} className="flex items-center justify-between">
            <div className="flex items-center">
              <div 
                className="w-3 h-3 rounded-full mr-2"
                style={{ backgroundColor: `hsl(${Math.random() * 360}, 70%, 50%)` }}
              ></div>
              <span className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</span>
            </div>
            <span className="text-sm font-medium text-gray-900">
              {value} ({percentage.toFixed(1)}%)
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default function AnalyticsDashboard() {
  const [selectedPeriod, setSelectedPeriod] = useState('30');
  const [selectedView, setSelectedView] = useState<'crm' | 'ops' | 'activities'>('crm');

  const { data: crmAnalytics, error: crmError, isLoading: crmLoading } = useApi(`/analytics/crm?days=${selectedPeriod}`);
  const { data: opsAnalytics, error: opsError, isLoading: opsLoading } = useApi(`/analytics/ops?days=${selectedPeriod}`);
  const { data: activityAnalytics, error: activityError, isLoading: activityLoading } = useApi(`/analytics/activities?days=${selectedPeriod}`);

  const isLoading = crmLoading || opsLoading || activityLoading;
  const error = crmError || opsError || activityError;

  React.useEffect(() => {
    trackEvent(AnalyticsEvents.ANALYTICS_VIEWED, { 
      period: selectedPeriod, 
      view: selectedView 
    });
  }, [selectedPeriod, selectedView]);

  const handleExportData = () => {
    trackEvent('ui.analytics.export', { period: selectedPeriod, view: selectedView });
    // Export analytics data
    console.log('Exporting analytics data');
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage error={error} />;
  }

  const crmData = crmAnalytics?.data?.attributes as AnalyticsData;
  const opsData = opsAnalytics?.data?.attributes;
  const activityData = activityAnalytics?.data?.attributes;

  const renderCRMView = () => (
    <div className="space-y-6">
      {/* CRM Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Contacts Added"
          value={crmData?.contacts_added || 0}
          change="+12%"
          changeType="positive"
          icon={<Users className="h-6 w-6 text-blue-600" />}
          color="bg-blue-100"
        />
        <MetricCard
          title="Deals Won"
          value={crmData?.deals_won || 0}
          change="+8%"
          changeType="positive"
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          color="bg-green-100"
        />
        <MetricCard
          title="Win Rate"
          value={`${crmData?.win_rate?.toFixed(1) || 0}%`}
          change="+2.5%"
          changeType="positive"
          icon={<Target className="h-6 w-6 text-purple-600" />}
          color="bg-purple-100"
        />
        <MetricCard
          title="Total Value"
          value={`$${(crmData?.total_deal_value || 0).toLocaleString()}`}
          change="+15%"
          changeType="positive"
          icon={<DollarSign className="h-6 w-6 text-yellow-600" />}
          color="bg-yellow-100"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Pipeline Summary" icon={<BarChart3 className="h-5 w-5 text-gray-600" />}>
          <SimpleBarChart 
            data={crmData?.pipeline_summary || {}} 
            title="Pipeline Stages" 
          />
        </ChartCard>
        
        <ChartCard title="Deal Status Distribution" icon={<PieChart className="h-5 w-5 text-gray-600" />}>
          <SimplePieChart 
            data={{
              'Open': crmData?.deals_open || 0,
              'Won': crmData?.deals_won || 0,
              'Lost': crmData?.deals_lost || 0
            }} 
            title="Deal Status" 
          />
        </ChartCard>
      </div>
    </div>
  );

  const renderOpsView = () => (
    <div className="space-y-6">
      {/* Ops Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Active Projects"
          value={opsData?.projects_active || 0}
          change="+3"
          changeType="positive"
          icon={<Users className="h-6 w-6 text-blue-600" />}
          color="bg-blue-100"
        />
        <MetricCard
          title="Tasks Completed"
          value={opsData?.tasks_done || 0}
          change="+18%"
          changeType="positive"
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          color="bg-green-100"
        />
        <MetricCard
          title="Completion Rate"
          value={`${opsData?.completion_rate?.toFixed(1) || 0}%`}
          change="+5.2%"
          changeType="positive"
          icon={<Target className="h-6 w-6 text-purple-600" />}
          color="bg-purple-100"
        />
        <MetricCard
          title="Total Hours"
          value={`${(opsData?.total_actual_hours || 0).toFixed(0)}h`}
          change="+12%"
          changeType="positive"
          icon={<Calendar className="h-6 w-6 text-yellow-600" />}
          color="bg-yellow-100"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Task Status Distribution" icon={<BarChart3 className="h-5 w-5 text-gray-600" />}>
          <SimpleBarChart 
            data={{
              'To Do': opsData?.tasks_todo || 0,
              'In Progress': opsData?.tasks_in_progress || 0,
              'Review': opsData?.tasks_review || 0,
              'Done': opsData?.tasks_done || 0
            }} 
            title="Task Status" 
          />
        </ChartCard>
        
        <ChartCard title="Task Priority Distribution" icon={<PieChart className="h-5 w-5 text-gray-600" />}>
          <SimplePieChart 
            data={{
              'Urgent': opsData?.tasks_urgent || 0,
              'High': opsData?.tasks_high || 0,
              'Medium': opsData?.tasks_medium || 0,
              'Low': opsData?.tasks_low || 0
            }} 
            title="Task Priority" 
          />
        </ChartCard>
      </div>
    </div>
  );

  const renderActivityView = () => (
    <div className="space-y-6">
      {/* Activity Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Activities"
          value={(activityData?.activities_call || 0) + (activityData?.activities_email || 0) + (activityData?.activities_meeting || 0) + (activityData?.activities_task || 0)}
          change="+25%"
          changeType="positive"
          icon={<Activity className="h-6 w-6 text-blue-600" />}
          color="bg-blue-100"
        />
        <MetricCard
          title="Completed Activities"
          value={activityData?.activities_completed || 0}
          change="+15%"
          changeType="positive"
          icon={<TrendingUp className="h-6 w-6 text-green-600" />}
          color="bg-green-100"
        />
        <MetricCard
          title="Completion Rate"
          value={`${activityData?.completion_rate?.toFixed(1) || 0}%`}
          change="+3.2%"
          changeType="positive"
          icon={<Target className="h-6 w-6 text-purple-600" />}
          color="bg-purple-100"
        />
        <MetricCard
          title="High Priority"
          value={activityData?.activities_high || 0}
          change="-5%"
          changeType="negative"
          icon={<Calendar className="h-6 w-6 text-red-600" />}
          color="bg-red-100"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Activity Types" icon={<BarChart3 className="h-5 w-5 text-gray-600" />}>
          <SimpleBarChart 
            data={{
              'Calls': activityData?.activities_call || 0,
              'Emails': activityData?.activities_email || 0,
              'Meetings': activityData?.activities_meeting || 0,
              'Tasks': activityData?.activities_task || 0
            }} 
            title="Activity Types" 
          />
        </ChartCard>
        
        <ChartCard title="Activity Status" icon={<PieChart className="h-5 w-5 text-gray-600" />}>
          <SimplePieChart 
            data={{
              'Completed': activityData?.activities_completed || 0,
              'Pending': activityData?.activities_pending || 0,
              'Cancelled': activityData?.activities_cancelled || 0
            }} 
            title="Activity Status" 
          />
        </ChartCard>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-gray-600">Comprehensive insights into your CRM and operations performance</p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <button
            onClick={handleExportData}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
        </div>
      </div>

      {/* View Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { key: 'crm', label: 'CRM Analytics', icon: <Users className="h-4 w-4" /> },
              { key: 'ops', label: 'Operations', icon: <Activity className="h-4 w-4" /> },
              { key: 'activities', label: 'Activities', icon: <Calendar className="h-4 w-4" /> }
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSelectedView(tab.key as any)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                  selectedView === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {selectedView === 'crm' && renderCRMView()}
        {selectedView === 'ops' && renderOpsView()}
        {selectedView === 'activities' && renderActivityView()}
      </div>
    </div>
  );
}
