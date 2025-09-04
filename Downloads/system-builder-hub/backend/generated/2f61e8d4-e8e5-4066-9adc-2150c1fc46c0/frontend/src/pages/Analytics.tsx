import React, { useState, useEffect } from 'react';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/Select';
import { DateRangePicker, DateRange } from '../components/DateRangePicker';
import { Badge } from '../components/Badge';
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  DollarSign, 
  MessageSquare, 
  Calendar,
  Filter
} from 'lucide-react';

export default function Analytics() {
  const { showToast } = useToast();
  const { hasPermission } = useAuth();
  const [dateRange, setDateRange] = useState<DateRange>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    to: new Date()
  });
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>({});

  useEffect(() => {
    if (hasPermission('analytics.read')) {
      fetchData();
    }
  }, [dateRange]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const fromDate = dateRange.from.toISOString().split('T')[0];
      const toDate = dateRange.to.toISOString().split('T')[0];
      
      const response = await fetch(`/api/analytics/dashboard/overview?from=${fromDate}&to=${toDate}`);
      const result = await response.json();
      setData(result);
    } catch (error) {
      showToast('Failed to fetch analytics data', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!hasPermission('analytics.read')) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-gray-500">You don't have permission to view analytics.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <p className="text-gray-600">Track your CRM performance and insights</p>
        </div>
        <div className="flex items-center space-x-2">
          <DateRangePicker
            value={dateRange}
            onValueChange={setDateRange}
          />
          <Button variant="outline" onClick={fetchData}>
            <Filter className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total Contacts</p>
                <p className="text-2xl font-bold">{data.quick_stats?.total_contacts || 0}</p>
              </div>
              <div className="text-blue-600">
                <Users className="w-4 h-4" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pipeline Value</p>
                <p className="text-2xl font-bold">${(data.quick_stats?.pipeline_value || 0).toLocaleString()}</p>
              </div>
              <div className="text-purple-600">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Open Deals</p>
                <p className="text-2xl font-bold">{data.quick_stats?.open_deals || 0}</p>
              </div>
              <div className="text-green-600">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Pending Activities</p>
                <p className="text-2xl font-bold">{data.quick_stats?.pending_activities || 0}</p>
              </div>
              <div className="text-red-600">
                <Calendar className="w-4 h-4" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Placeholder for Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle>Communication Success Rate</CardTitle>
            <CardDescription>Daily success rate over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center text-gray-500">
              Chart coming soon...
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Pipeline Velocity</CardTitle>
            <CardDescription>Average days per stage</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center text-gray-500">
              Chart coming soon...
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Today's Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{data.today?.communications || 0}</p>
              <p className="text-sm text-gray-600">Communications</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{data.today?.activities || 0}</p>
              <p className="text-sm text-gray-600">Activities</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
