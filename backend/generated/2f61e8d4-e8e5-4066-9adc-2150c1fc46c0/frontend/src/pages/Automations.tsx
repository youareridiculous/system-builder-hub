import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { useToast } from '../contexts/ToastContext';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Label } from '../components/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/Select';
import { Badge } from '../components/Badge';
import { Switch } from '../components/Switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/Tabs';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '../components/Dialog';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow,
  TableEmptyState
} from '../components/Table';
import { 
  Plus, 
  Edit, 
  Trash2, 
  Copy, 
  Play, 
  Eye, 
  Zap,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronRight,
  Filter,
  Search,
  Calendar,
  Mail,
  MessageSquare,
  User,
  DollarSign,
  FileText,
  ArrowRight
} from 'lucide-react';

// TypeScript interfaces
interface AutomationRule {
  id: number;
  name: string;
  trigger: string; // Backend uses 'trigger' not 'trigger_type'
  conditions: string; // JSON string from backend
  actions: string; // JSON string from backend
  is_enabled: boolean; // Backend uses 'is_enabled' not 'is_active'
  tenant_id: string;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  // Optional fields that might not be in all responses
  debounce_minutes?: number;
  dry_run_default?: boolean;
  run_count?: number;
  success_count?: number;
}

interface AutomationConditions {
  pipeline_id?: string;
  stage?: string;
  stage_operator?: 'equals' | 'in';
  contact_has_email?: boolean;
  contact_has_phone?: boolean;
  account_id?: string;
  business_hours_only?: boolean;
  minimum_amount?: string;
  tags_include?: string;
  communication_type?: string;
  communication_status?: string;
}

interface AutomationAction {
  type: 'send_email' | 'send_sms' | 'create_activity' | 'move_deal_stage' | 'add_note' | 'wait';
  template_id?: string;
  delay_minutes?: number;
  activity_type?: string;
  activity_subject?: string;
  activity_description?: string;
  due_date_offset?: number;
  target_stage?: string;
  note_body?: string;
  note_pinned?: boolean;
  wait_duration?: number;
  wait_unit?: 'minutes' | 'hours';
}

interface AutomationRun {
  id: number;
  rule_id: number;
  trigger_payload: any;
  actions_attempted: any[];
  result: 'success' | 'error' | 'skipped';
  error_message?: string;
  elapsed_ms: number;
  created_at: string;
  is_dry_run: boolean;
  conditions_matched: boolean;
}

interface TestResult {
  conditions_matched: boolean;
  actions: Array<{
    type: string;
    template_name?: string;
    rendered_subject?: string;
    rendered_body?: string;
    target_entities?: string[];
    delay_minutes?: number;
  }>;
}

export default function Automations() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [automations, setAutomations] = useState<AutomationRule[]>([]);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [triggerFilter, setTriggerFilter] = useState<string>('all');
  const [enabledFilter, setEnabledFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Modal states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [selectedAutomation, setSelectedAutomation] = useState<AutomationRule | null>(null);
  
  // Form states
  const [formData, setFormData] = useState<Partial<AutomationRule>>({
    name: '',
    trigger: 'deal.stage_changed',
    conditions: '{}',
    actions: '[{"type": "send_email"}]',
    debounce_minutes: 1,
    dry_run_default: false,
    is_enabled: true
  });
  
  // Test states
  const [testData, setTestData] = useState({
    entity_type: 'deal',
    entity_id: '',
    from_stage: '',
    to_stage: '',
    communication_status: ''
  });
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  
  const { showToast } = useToast();
  const { hasPermission } = useAuth();

  useEffect(() => {
    if (id) {
      fetchAutomationDetail();
      fetchAutomationRuns();
    } else {
      fetchAutomations();
    }
    fetchTemplates();
  }, [id, searchTerm, triggerFilter, enabledFilter, currentPage]);

  const fetchAutomations = async () => {
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('q', searchTerm);
      if (triggerFilter && triggerFilter !== 'all') params.append('trigger', triggerFilter);
      if (enabledFilter && enabledFilter !== 'all') params.append('enabled', enabledFilter);
      params.append('page', currentPage.toString());
      params.append('per_page', '25');
      
      const response = await api.get(`/api/automations/?${params.toString()}`);
      setAutomations(response.items || response);
      setTotalPages(response.total_pages || 1);
    } catch (error) {
      showToast('Failed to fetch automations', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchAutomationDetail = async () => {
    try {
      const response = await api.get(`/api/automations/${id}`);
      setSelectedAutomation(response);
      setFormData(response);
    } catch (error) {
      showToast('Failed to fetch automation details', 'error');
    }
  };

  const fetchAutomationRuns = async () => {
    if (!id) return;
    
    try {
      const response = await api.get(`/api/automations/${id}/runs`);
      setRuns(response.items || response);
    } catch (error) {
      showToast('Failed to fetch automation runs', 'error');
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/api/templates/');
      setTemplates(response);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/automations/', formData);
      showToast('Automation created successfully', 'success');
      setCreateModalOpen(false);
      resetForm();
      fetchAutomations();
    } catch (error) {
      showToast('Failed to create automation', 'error');
    }
  };

  const handleUpdate = async () => {
    if (!selectedAutomation) return;
    
    try {
      await api.put(`/api/automations/${selectedAutomation.id}`, formData);
      showToast('Automation updated successfully', 'success');
      setEditModalOpen(false);
      resetForm();
      fetchAutomations();
    } catch (error) {
      showToast('Failed to update automation', 'error');
    }
  };

  const handleDelete = async (automationId: number) => {
    try {
      await api.del(`/api/automations/${automationId}`);
      showToast('Automation deleted successfully', 'success');
      fetchAutomations();
    } catch (error) {
      showToast('Failed to delete automation', 'error');
    }
  };

  const handleToggle = async (automation: AutomationRule) => {
    try {
      await api.patch(`/api/automations/${automation.id}/enabled`, {
        enabled: !automation.is_active
      });
      showToast(`Automation ${automation.is_enabled ? 'disabled' : 'enabled'} successfully`, 'success');
      // Optimistic update
      setAutomations(prev => prev.map(a => 
        a.id === automation.id ? { ...a, is_enabled: !a.is_enabled } : a
      ));
    } catch (error) {
      showToast('Failed to toggle automation', 'error');
    }
  };

  const handleDuplicate = async (automation: AutomationRule) => {
    try {
      await api.post('/api/automations/', {
        ...automation,
        name: `${automation.name} (Copy)`,
        is_enabled: false
      });
      showToast('Automation duplicated successfully', 'success');
      fetchAutomations();
    } catch (error) {
      showToast('Failed to duplicate automation', 'error');
    }
  };

  const handleTest = async () => {
    try {
      const payload = {
        rule_id: selectedAutomation?.id,
        trigger_payload: {
          entity_type: testData.entity_type,
          entity_id: parseInt(testData.entity_id),
          from_stage: testData.from_stage,
          to_stage: testData.to_stage,
          communication_status: testData.communication_status
        }
      };
      
      const response = await api.post('/api/automations/test', payload);
      setTestResult(response);
      setTestModalOpen(true);
    } catch (error) {
      showToast('Failed to test automation', 'error');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      trigger: 'deal.stage_changed',
      conditions: '{}',
      actions: '[{"type": "send_email"}]',
      debounce_minutes: 1,
      dry_run_default: false,
      is_enabled: true
    });
    setSelectedAutomation(null);
  };

  const addAction = () => {
    setFormData(prev => {
      const actions = prev.actions ? JSON.parse(prev.actions) : [];
      actions.push({ type: 'send_email' });
      return {
        ...prev,
        actions: JSON.stringify(actions)
      };
    });
  };

  const removeAction = (index: number) => {
    setFormData(prev => {
      const actions = prev.actions ? JSON.parse(prev.actions) : [];
      actions.splice(index, 1);
      return {
        ...prev,
        actions: JSON.stringify(actions)
      };
    });
  };

  const updateAction = (index: number, field: string, value: any) => {
    setFormData(prev => {
      const actions = prev.actions ? JSON.parse(prev.actions) : [];
      actions[index] = { ...actions[index], [field]: value };
      return {
        ...prev,
        actions: JSON.stringify(actions)
      };
    });
  };

  const getTriggerIcon = (triggerType: string) => {
    switch (triggerType) {
      case 'deal.stage_changed': return <DollarSign className="w-4 h-4" />;
      case 'contact.created': return <User className="w-4 h-4" />;
      case 'communication.status_updated': return <MessageSquare className="w-4 h-4" />;
      default: return <Zap className="w-4 h-4" />;
    }
  };

  const getTriggerLabel = (triggerType: string) => {
    switch (triggerType) {
      case 'deal.stage_changed': return 'Deal Stage Changed';
      case 'contact.created': return 'Contact Created';
      case 'communication.status_updated': return 'Communication Status Updated';
      default: return triggerType;
    }
  };

  const getResultIcon = (result: string) => {
    switch (result) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'skipped': return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default: return <AlertCircle className="w-4 h-4 text-gray-500" />;
    }
  };

  const getResultColor = (result: string) => {
    switch (result) {
      case 'success': return 'bg-green-100 text-green-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'skipped': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getConditionsSummary = (conditions: AutomationConditions | string) => {
    // Handle case where conditions is a JSON string
    let conditionsObj: AutomationConditions;
    if (typeof conditions === 'string') {
      try {
        conditionsObj = JSON.parse(conditions);
      } catch {
        return 'Invalid conditions format';
      }
    } else {
      conditionsObj = conditions || {};
    }
    
    const parts = [];
    if (conditionsObj.pipeline_id) parts.push(`Pipeline=${conditionsObj.pipeline_id}`);
    if (conditionsObj.stage) parts.push(`Stage=${conditionsObj.stage}`);
    if (conditionsObj.minimum_amount) parts.push(`Amount≥${conditionsObj.minimum_amount}`);
    if (conditionsObj.business_hours_only) parts.push('BH');
    return parts.join(' • ') || 'Any';
  };

  const getActionsSummary = (actions: AutomationAction[] | string) => {
    // Handle case where actions is a JSON string
    let actionsArray: AutomationAction[];
    if (typeof actions === 'string') {
      try {
        actionsArray = JSON.parse(actions);
      } catch {
        return 'Invalid actions format';
      }
    } else {
      actionsArray = actions || [];
    }
    
    if (!Array.isArray(actionsArray)) {
      return 'Invalid actions format';
    }
    
    return actionsArray.map(action => {
      switch (action.type) {
        case 'send_email': return `Email: ${templates.find(t => t.id === action.template_id)?.name || 'Template'}`;
        case 'send_sms': return `SMS: ${templates.find(t => t.id === action.template_id)?.name || 'Template'}`;
        case 'create_activity': return `Activity: ${action.activity_subject || action.activity_type}`;
        case 'move_deal_stage': return `Move Stage: ${action.target_stage}`;
        case 'add_note': return 'Add Note';
        case 'wait': return `Wait: ${action.wait_duration}${action.wait_unit}`;
        default: return action.type;
      }
    }).join(' • ');
  };

  if (!hasPermission('automations.read')) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-gray-500">You don't have permission to view automations.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Detail view
  if (id && selectedAutomation) {
    return (
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <button 
              onClick={() => navigate('/automations')}
              className="flex items-center text-gray-600 hover:text-gray-900 mb-2"
            >
              <ChevronRight className="w-4 h-4 rotate-180 mr-2" />
              Back to Automations
            </button>
            <h1 className="text-2xl font-bold">{selectedAutomation.name}</h1>
            <p className="text-gray-600">Automation details and execution history</p>
          </div>
          <div className="flex space-x-2">
            {hasPermission('automations.run_test') && (
              <Button variant="outline" onClick={() => setTestModalOpen(true)}>
                <Play className="w-4 h-4 mr-2" />
                Test
              </Button>
            )}
            {hasPermission('automations.write') && (
              <Button onClick={() => setEditModalOpen(true)}>
                <Edit className="w-4 h-4 mr-2" />
                Edit
              </Button>
            )}
          </div>
        </div>

        <Tabs defaultValue="definition" className="space-y-6">
          <TabsList>
            <TabsTrigger value="definition">Definition</TabsTrigger>
            <TabsTrigger value="runs">Runs ({runs.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="definition">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Trigger</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center space-x-2">
                    {getTriggerIcon(selectedAutomation.trigger_type)}
                    <span className="font-medium">{getTriggerLabel(selectedAutomation.trigger_type)}</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span>Active:</span>
                      <Badge className={selectedAutomation.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {selectedAutomation.is_active ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Debounce:</span>
                      <span>{selectedAutomation.debounce_minutes} minutes</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Total Runs:</span>
                      <span>{selectedAutomation.run_count}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Success Rate:</span>
                      <span>{selectedAutomation.run_count > 0 ? Math.round((selectedAutomation.success_count / selectedAutomation.run_count) * 100) : 0}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Conditions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(selectedAutomation.conditions).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="font-medium">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {selectedAutomation.actions.map((action, index) => (
                      <div key={index} className="flex items-center space-x-3 p-3 border rounded">
                        <div className="flex items-center space-x-2">
                          {action.type === 'send_email' && <Mail className="w-4 h-4" />}
                          {action.type === 'send_sms' && <MessageSquare className="w-4 h-4" />}
                          {action.type === 'create_activity' && <Calendar className="w-4 h-4" />}
                          {action.type === 'move_deal_stage' && <ArrowRight className="w-4 h-4" />}
                          {action.type === 'add_note' && <FileText className="w-4 h-4" />}
                          <span className="capitalize">{action.type.replace(/_/g, ' ')}</span>
                        </div>
                        {action.delay_minutes && action.delay_minutes > 0 && (
                          <Badge variant="outline">
                            <Clock className="w-3 h-3 mr-1" />
                            {action.delay_minutes}m delay
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="runs">
            <Card>
              <CardHeader>
                <CardTitle>Execution History</CardTitle>
                <CardDescription>Recent automation runs and their results</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Trigger</TableHead>
                      <TableHead>Matched</TableHead>
                      <TableHead>Actions</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs.length === 0 ? (
                      <TableEmptyState message="No runs found" />
                    ) : (
                      runs.map((run) => (
                        <TableRow key={run.id}>
                          <TableCell>
                            <div className="text-sm">
                              {new Date(run.created_at).toLocaleString()}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="text-sm max-w-xs truncate">
                              {JSON.stringify(run.trigger_payload).substring(0, 50)}...
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={run.conditions_matched ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                              {run.conditions_matched ? 'Yes' : 'No'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="text-sm">
                              {run.actions_attempted.length} actions
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center space-x-2">
                              {getResultIcon(run.result)}
                              <Badge className={getResultColor(run.result)}>
                                {run.result}
                              </Badge>
                              {run.is_dry_run && (
                                <Badge variant="outline" className="text-xs">Dry Run</Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="text-sm">
                              {run.elapsed_ms}ms
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  // List view
  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Automations</h1>
          <p className="text-gray-600">Manage automated workflows and rules</p>
        </div>
        {hasPermission('automations.write') && (
          <Button onClick={() => setCreateModalOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create Rule
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search automations..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div>
              <Label>Trigger</Label>
              <Select value={triggerFilter} onValueChange={setTriggerFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All triggers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All triggers</SelectItem>
                  <SelectItem value="deal.stage_changed">Deal Stage Changed</SelectItem>
                  <SelectItem value="contact.created">Contact Created</SelectItem>
                  <SelectItem value="communication.status_updated">Communication Status Updated</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Status</Label>
              <Select value={enabledFilter} onValueChange={setEnabledFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="true">Enabled</SelectItem>
                  <SelectItem value="false">Disabled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button variant="outline" className="w-full">
                <Filter className="w-4 h-4 mr-2" />
                More Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Automations Table */}
      <Card>
        <CardHeader>
          <CardTitle>Automations ({automations.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Trigger</TableHead>
                <TableHead>Conditions</TableHead>
                <TableHead>Actions</TableHead>
                <TableHead>Enabled</TableHead>
                <TableHead>Last Run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  </TableCell>
                </TableRow>
              ) : automations.length === 0 ? (
                <TableEmptyState message="No automations found">
                  {hasPermission('automations.write') && (
                    <Button onClick={() => setCreateModalOpen(true)} className="mt-4">
                      <Plus className="w-4 h-4 mr-2" />
                      Create Rule
                    </Button>
                  )}
                </TableEmptyState>
              ) : (
                automations.map((automation) => (
                  <TableRow key={automation.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{automation.name}</div>
                        <div className="text-sm text-gray-500">
                          {automation.actions.length} actions
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        {getTriggerIcon(automation.trigger)}
                        <span className="text-sm">{getTriggerLabel(automation.trigger)}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-600 max-w-xs truncate">
                        {getConditionsSummary(automation.conditions)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-600 max-w-xs truncate">
                        {getActionsSummary(automation.actions)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Switch
                          checked={automation.is_enabled}
                          onCheckedChange={() => handleToggle(automation)}
                          disabled={!hasPermission('automations.write')}
                        />
                        <Badge className={automation.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                          {automation.is_enabled ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-500">
                        {automation.last_run_at 
                          ? new Date(automation.last_run_at).toLocaleDateString()
                          : 'Never'
                        }
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {automation.run_count > 0 
                          ? `${Math.round((automation.success_count / automation.run_count) * 100)}%`
                          : '-'
                        }
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/automations/${automation.id}`)}
                        >
                          <Eye className="w-3 h-3" />
                        </Button>
                        {hasPermission('automations.run_test') && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedAutomation(automation);
                              setTestModalOpen(true);
                            }}
                          >
                            <Play className="w-3 h-3" />
                          </Button>
                        )}
                        {hasPermission('automations.write') && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDuplicate(automation)}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedAutomation(automation);
                                setFormData(automation);
                                setEditModalOpen(true);
                              }}
                            >
                              <Edit className="w-3 h-3" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDelete(automation.id)}
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create/Edit Modal */}
      <Dialog open={createModalOpen || editModalOpen} onOpenChange={setCreateModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {createModalOpen ? 'Create Automation Rule' : 'Edit Automation Rule'}
            </DialogTitle>
            <DialogDescription>
              Configure automated workflows that trigger based on events
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="automation-name">Name *</Label>
                <Input
                  id="automation-name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Automation name"
                />
              </div>
              <div>
                <Label htmlFor="automation-trigger">Trigger *</Label>
                <Select value={formData.trigger} onValueChange={(value) => setFormData(prev => ({ ...prev, trigger: value }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="deal.stage_changed">Deal Stage Changed</SelectItem>
                    <SelectItem value="contact.created">Contact Created</SelectItem>
                    <SelectItem value="communication.status_updated">Communication Status Updated</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Actions *</CardTitle>
                <CardDescription>What should happen when conditions are met?</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {(formData.actions ? JSON.parse(formData.actions) : []).map((action: any, index: number) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium">Action {index + 1}</span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => removeAction(index)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <Label>Type</Label>
                          <Select value={action.type} onValueChange={(value) => updateAction(index, 'type', value)}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="send_email">Send Email</SelectItem>
                              <SelectItem value="send_sms">Send SMS</SelectItem>
                              <SelectItem value="create_activity">Create Activity</SelectItem>
                              <SelectItem value="move_deal_stage">Move Deal Stage</SelectItem>
                              <SelectItem value="add_note">Add Note</SelectItem>
                              <SelectItem value="wait">Wait</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        
                        {(action.type === 'send_email' || action.type === 'send_sms') && (
                          <div>
                            <Label>Template</Label>
                            <Select value={action.template_id || ''} onValueChange={(value) => updateAction(index, 'template_id', value)}>
                              <SelectTrigger>
                                <SelectValue placeholder="Select template" />
                              </SelectTrigger>
                              <SelectContent>
                                {templates
                                  .filter(t => t.type === (action.type === 'send_email' ? 'email' : 'sms'))
                                  .map(template => (
                                    <SelectItem key={template.id} value={template.id.toString()}>
                                      {template.name}
                                    </SelectItem>
                                  ))
                                }
                              </SelectContent>
                            </Select>
                          </div>
                        )}
                        
                        <div>
                          <Label>Delay (minutes)</Label>
                          <Input
                            type="number"
                            value={action.delay_minutes || 0}
                            onChange={(e) => updateAction(index, 'delay_minutes', parseInt(e.target.value) || 0)}
                            placeholder="0"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  <Button variant="outline" onClick={addAction}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Action
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Settings */}
            <Card>
              <CardHeader>
                <CardTitle>Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Debounce Window (minutes)</Label>
                    <Input
                      type="number"
                      value={formData.debounce_minutes || 1}
                      onChange={(e) => setFormData(prev => ({ ...prev, debounce_minutes: parseInt(e.target.value) || 1 }))}
                      placeholder="1"
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={formData.dry_run_default || false}
                      onCheckedChange={(checked) => setFormData(prev => ({ ...prev, dry_run_default: checked }))}
                    />
                    <Label>Dry-run by default</Label>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={createModalOpen ? handleCreate : handleUpdate}>
              {createModalOpen ? 'Create Rule' : 'Update Rule'}
            </Button>
            {editModalOpen && (
              <Button onClick={() => {
                setFormData(prev => ({ ...prev, is_active: true }));
                handleUpdate();
              }}>
                Save & Enable
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Modal */}
      <Dialog open={testModalOpen} onOpenChange={setTestModalOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Test Automation Rule</DialogTitle>
            <DialogDescription>
              Test this automation with sample data (dry-run only)
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <Label>Entity Type</Label>
                <Select value={testData.entity_type} onValueChange={(value) => setTestData(prev => ({ ...prev, entity_type: value }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="deal">Deal</SelectItem>
                    <SelectItem value="contact">Contact</SelectItem>
                    <SelectItem value="communication">Communication</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label>Entity ID</Label>
                <Input
                  value={testData.entity_id}
                  onChange={(e) => setTestData(prev => ({ ...prev, entity_id: e.target.value }))}
                  placeholder="Enter entity ID"
                />
              </div>
              
              {testData.entity_type === 'deal' && (
                <>
                  <div>
                    <Label>From Stage</Label>
                    <Input
                      value={testData.from_stage}
                      onChange={(e) => setTestData(prev => ({ ...prev, from_stage: e.target.value }))}
                      placeholder="e.g., prospecting"
                    />
                  </div>
                  <div>
                    <Label>To Stage</Label>
                    <Input
                      value={testData.to_stage}
                      onChange={(e) => setTestData(prev => ({ ...prev, to_stage: e.target.value }))}
                      placeholder="e.g., qualification"
                    />
                  </div>
                </>
              )}
              
              {testData.entity_type === 'communication' && (
                <div>
                  <Label>New Status</Label>
                  <Input
                    value={testData.communication_status}
                    onChange={(e) => setTestData(prev => ({ ...prev, communication_status: e.target.value }))}
                    placeholder="e.g., delivered"
                  />
                </div>
              )}
              
              <Button onClick={handleTest} className="w-full">
                <Play className="w-4 h-4 mr-2" />
                Run Test
              </Button>
            </div>
            
            {testResult && (
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Test Results</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center space-x-2">
                        {testResult.conditions_matched ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-500" />
                        )}
                        <span className={testResult.conditions_matched ? 'text-green-700' : 'text-red-700'}>
                          {testResult.conditions_matched ? 'Conditions matched' : 'Conditions not matched'}
                        </span>
                      </div>
                      
                      <div>
                        <h4 className="font-medium mb-2">Actions that would execute:</h4>
                        <div className="space-y-2">
                          {testResult.actions.map((action, index) => (
                            <div key={index} className="p-3 border rounded">
                              <div className="flex items-center space-x-2 mb-2">
                                <span className="font-medium capitalize">{action.type.replace(/_/g, ' ')}</span>
                                {action.delay_minutes && action.delay_minutes > 0 && (
                                  <Badge variant="outline">
                                    <Clock className="w-3 h-3 mr-1" />
                                    {action.delay_minutes}m delay
                                  </Badge>
                                )}
                              </div>
                              {action.template_name && (
                                <div className="text-sm text-gray-600">Template: {action.template_name}</div>
                              )}
                              {action.rendered_subject && (
                                <div className="text-sm text-gray-600">Subject: {action.rendered_subject}</div>
                              )}
                              {action.rendered_body && (
                                <div className="text-sm text-gray-600">Body: {action.rendered_body.substring(0, 100)}...</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setTestModalOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
