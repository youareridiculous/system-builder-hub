import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/Select';
import { DateRangePicker, DateRange } from '../components/DateRangePicker';
import { Badge } from '../components/Badge';
import { FirstRunChecklist } from '../components/FirstRunChecklist';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  Users, 
  DollarSign, 
  Calendar, 
  TrendingUp, 
  Mail, 
  Phone, 
  MessageSquare,
  Target,
  Clock,
  CheckCircle,
  Plus
} from 'lucide-react';
import { DealCreateModal } from '../components/modals/DealCreateModal';

interface DashboardData {
  quick_stats: {
    total_accounts: number;
    total_contacts: number;
    open_deals: number;
    pending_activities: number;
    pipeline_value: number;
  };
  today: {
    communications: number;
    activities: number;
  };
}

interface CommunicationsData {
  summary: {
    total_communications: number;
    total_successful: number;
    total_failed: number;
    overall_success_rate: number;
  };
  by_type: Record<string, any>;
  by_status: Record<string, any>;
  daily_volume: Array<{date: string; count: number}>;
}

interface PipelineData {
  summary: {
    total_deals: number;
    total_value: number;
    avg_deal_value: number;
    win_rate: number;
    avg_velocity_days: number;
  };
  by_stage: Record<string, any>;
  win_loss: {
    won: number;
    lost: number;
    total_closed: number;
  };
}

interface ActivitiesData {
  summary: {
    total_activities: number;
    total_completed: number;
    total_pending: number;
    overall_completion_rate: number;
    overdue_count: number;
  };
  by_type: Record<string, any>;
  daily_completion: Array<{date: string; created: number; completed: number; completion_rate: number}>;
}

export default function Dashboard() {
  const { accountId } = useParams();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<DateRange>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    to: new Date()
  });
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [communicationsData, setCommunicationsData] = useState<CommunicationsData | null>(null);
  const [pipelineData, setPipelineData] = useState<PipelineData | null>(null);
  const [activitiesData, setActivitiesData] = useState<ActivitiesData | null>(null);
  const [openDealModal, setOpenDealModal] = useState(false);
  const [showChecklist, setShowChecklist] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, [dateRange]);

  const fetchDashboardData = async () => {
    try {
      const [overview, comms, pipeline, activities] = await Promise.all([
        api.get('/api/analytics/dashboard/overview'),
        api.get(`/api/analytics/communications/summary?from=${getDateFromRange()}&to=${getDateToRange()}`),
        api.get(`/api/analytics/pipeline/summary?from=${getDateFromRange()}&to=${getDateToRange()}`),
        api.get(`/api/analytics/activities/summary?from=${getDateFromRange()}&to=${getDateToRange()}`)
      ]);
      
      setDashboardData(overview);
      setCommunicationsData(comms);
      setPipelineData(pipeline);
      setActivitiesData(activities);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setLoading(false);
    }
  };

  const getDateFromRange = () => {
    return dateRange.from.toISOString().split('T')[0];
  };

  const getDateToRange = () => {
    return dateRange.to.toISOString().split('T')[0];
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-full">
      {showChecklist && (
        <FirstRunChecklist onDismiss={() => setShowChecklist(false)} />
      )}
      <div className="flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            {accountId ? 'Account overview and analytics' : 'CRM overview and analytics'}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <DateRangePicker
            value={dateRange}
            onValueChange={setDateRange}
          />
          <Button onClick={() => setOpenDealModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            New Deal
          </Button>
        </div>
      </div>

      {/* Quick Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Accounts</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.quick_stats.total_accounts || 0}</div>
            <p className="text-xs text-muted-foreground">
              Active accounts in system
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pipeline Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(dashboardData?.quick_stats.pipeline_value || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Total deal value
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Deals</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.quick_stats.open_deals || 0}</div>
            <p className="text-xs text-muted-foreground">
              Active deals in pipeline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Activities</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.quick_stats.pending_activities || 0}</div>
            <p className="text-xs text-muted-foreground">
              Tasks to complete
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Communications Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Communications Overview</CardTitle>
            <CardDescription>
              Email, SMS, and call activity over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            {communicationsData?.daily_volume && communicationsData.daily_volume.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={communicationsData.daily_volume}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#8884d8" name="Communications" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No communication data available
              </div>
            )}
            
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {communicationsData?.summary.total_communications || 0}
                </div>
                <div className="text-sm text-gray-600">Total</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {communicationsData?.summary.overall_success_rate || 0}%
                </div>
                <div className="text-sm text-gray-600">Success Rate</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {communicationsData?.summary.total_failed || 0}
                </div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Pipeline Performance</CardTitle>
            <CardDescription>
              Deal stages and conversion rates
            </CardDescription>
          </CardHeader>
          <CardContent>
            {pipelineData?.by_stage && Object.keys(pipelineData.by_stage).length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={Object.entries(pipelineData.by_stage).map(([stage, data]) => ({
                  stage,
                  count: data.count,
                  value: data.total_amount
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="stage" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Bar yAxisId="left" dataKey="count" fill="#8884d8" name="Deals" />
                  <Bar yAxisId="right" dataKey="value" fill="#82ca9d" name="Value" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No pipeline data available
              </div>
            )}
            
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {pipelineData?.summary.win_rate || 0}%
                </div>
                <div className="text-sm text-gray-600">Win Rate</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {pipelineData?.summary.avg_velocity_days || 0}
                </div>
                <div className="text-sm text-gray-600">Avg Days</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {formatCurrency(pipelineData?.summary.avg_deal_value || 0)}
                </div>
                <div className="text-sm text-gray-600">Avg Deal</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Activities Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Activities Completion</CardTitle>
            <CardDescription>
              Task completion rates and trends
            </CardDescription>
          </CardHeader>
          <CardContent>
            {activitiesData?.daily_completion && activitiesData.daily_completion.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={activitiesData.daily_completion}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="created" stroke="#8884d8" name="Created" />
                  <Line type="monotone" dataKey="completed" stroke="#82ca9d" name="Completed" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No activity data available
              </div>
            )}
            
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {activitiesData?.summary.total_activities || 0}
                </div>
                <div className="text-sm text-gray-600">Total</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {activitiesData?.summary.overall_completion_rate || 0}%
                </div>
                <div className="text-sm text-gray-600">Completion</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {activitiesData?.summary.overdue_count || 0}
                </div>
                <div className="text-sm text-gray-600">Overdue</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Communication Types</CardTitle>
            <CardDescription>
              Breakdown by communication method
            </CardDescription>
          </CardHeader>
          <CardContent>
            {communicationsData?.by_type && Object.keys(communicationsData.by_type).length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={Object.entries(communicationsData.by_type).map(([type, data]) => ({
                      name: type,
                      value: data.count
                    }))}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {Object.entries(communicationsData.by_type).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No communication type data available
              </div>
            )}
            
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <Mail className="w-4 h-4 text-blue-600 mr-1" />
                  <span className="text-sm font-medium">Email</span>
                </div>
                <div className="text-lg font-bold">
                  {communicationsData?.by_type?.email?.count || 0}
                </div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <MessageSquare className="w-4 h-4 text-green-600 mr-1" />
                  <span className="text-sm font-medium">SMS</span>
                </div>
                <div className="text-lg font-bold">
                  {communicationsData?.by_type?.sms?.count || 0}
                </div>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center mb-1">
                  <Phone className="w-4 h-4 text-purple-600 mr-1" />
                  <span className="text-sm font-medium">Call</span>
                </div>
                <div className="text-lg font-bold">
                  {communicationsData?.by_type?.call?.count || 0}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Today's Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Today's Activity</CardTitle>
          <CardDescription>
            Real-time activity summary
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {dashboardData?.today.communications || 0}
              </div>
              <div className="text-sm text-gray-600">Communications</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {dashboardData?.today.activities || 0}
              </div>
              <div className="text-sm text-gray-600">Activities</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {dashboardData?.quick_stats.total_contacts || 0}
              </div>
              <div className="text-sm text-gray-600">Contacts</div>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">
                {dashboardData?.quick_stats.open_deals || 0}
              </div>
              <div className="text-sm text-gray-600">Open Deals</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Deal Create Modal */}
      <DealCreateModal 
        open={openDealModal} 
        onOpenChange={setOpenDealModal} 
        onCreated={() => {
          setOpenDealModal(false);
          fetchDashboardData();
        }}
        accountId={accountId}
      />
    </div>
  );
}