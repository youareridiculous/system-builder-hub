import React, { useState, useEffect } from 'react';
import { api } from '../lib/api.ts';
import { useToast } from '../contexts/ToastContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Label } from '../components/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/Select';
import { Badge } from '../components/Badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../components/Dialog';
import {
  Plus,
  Edit,
  Trash2,
  DollarSign,
  User,
  Building,
  Calendar,
  MoreHorizontal,
  GripVertical,
  FileText
} from 'lucide-react';

interface Pipeline {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

interface Deal {
  id: number;
  title: string;
  amount: number;
  stage: string;
  account_id: number;
  contact_id: number;
  close_date: string;
  created_at: string;
  account_name: string;
  contact_name: string;
  position: number;
}

interface Stage {
  name: string;
  deals: Deal[];
  totalAmount: number;
  dealCount: number;
}

const DEFAULT_STAGES = ['prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'];

export default function Pipelines() {
  const { showToast } = useToast();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  
  // Modal states
  const [showCreatePipelineModal, setShowCreatePipelineModal] = useState(false);
  const [showCreateDealModal, setShowCreateDealModal] = useState(false);
  const [showEditDealModal, setShowEditDealModal] = useState(false);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  
  // Form states
  const [pipelineForm, setPipelineForm] = useState({ name: '', description: '' });
  const [dealForm, setDealForm] = useState({
    title: '',
    amount: '',
    stage: 'prospecting',
    account_id: '',
    contact_id: '',
    close_date: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (pipelines.length > 0 && !selectedPipeline) {
      setSelectedPipeline(pipelines[0]);
    }
  }, [pipelines]);

  const fetchData = async () => {
    try {
      const [pipelinesData, dealsData, accountsData, contactsData] = await Promise.all([
        api.get('/pipelines/'),
        api.get('/deals/'),
        api.get('/accounts/'),
        api.get('/contacts/')
      ]);
      
      setPipelines(pipelinesData);
      setDeals(dealsData);
      setAccounts(accountsData);
      setContacts(contactsData);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching data:', err);
      showToast('Failed to load pipeline data', 'error');
      setLoading(false);
    }
  };

  const handleCreatePipeline = async () => {
    try {
      await api.post('/pipelines/', pipelineForm);
      setShowCreatePipelineModal(false);
      setPipelineForm({ name: '', description: '' });
      showToast('Pipeline created successfully!', 'success');
      fetchData();
    } catch (err) {
      showToast('Failed to create pipeline', 'error');
    }
  };

  const handleCreateDeal = async () => {
    try {
      const data = {
        ...dealForm,
        amount: parseFloat(dealForm.amount) || 0,
        account_id: dealForm.account_id ? parseInt(dealForm.account_id) : null,
        contact_id: dealForm.contact_id ? parseInt(dealForm.contact_id) : null,
        position: 0
      };
      
      await api.post('/deals/', data);
      setShowCreateDealModal(false);
      setDealForm({
        title: '',
        amount: '',
        stage: 'prospecting',
        account_id: '',
        contact_id: '',
        close_date: ''
      });
      showToast('Deal created successfully!', 'success');
      fetchData();
    } catch (err) {
      showToast('Failed to create deal', 'error');
    }
  };

  const handleUpdateDealStage = async (dealId: number, newStage: string) => {
    try {
      await api.put(`/deals/${dealId}`, { stage: newStage });
      showToast('Deal stage updated!', 'success');
      fetchData();
    } catch (err) {
      showToast('Failed to update deal stage', 'error');
    }
  };

  const handleDeleteDeal = async (dealId: number) => {
    try {
      await api.del(`/deals/${dealId}`);
      showToast('Deal deleted successfully!', 'success');
      fetchData();
    } catch (err) {
      showToast('Failed to delete deal', 'error');
    }
  };

  // Group deals by stage
  const getStages = (): Stage[] => {
    const stages: Stage[] = DEFAULT_STAGES.map(stageName => ({
      name: stageName,
      deals: [],
      totalAmount: 0,
      dealCount: 0
    }));

    deals.forEach(deal => {
      const stage = stages.find(s => s.name === deal.stage);
      if (stage) {
        stage.deals.push(deal);
        stage.totalAmount += deal.amount || 0;
        stage.dealCount += 1;
      }
    });

    // Sort deals by position within each stage
    stages.forEach(stage => {
      stage.deals.sort((a, b) => (a.position || 0) - (b.position || 0));
    });

    return stages;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const getStageColor = (stage: string) => {
    const colors = {
      prospecting: 'bg-blue-100 text-blue-800',
      qualification: 'bg-yellow-100 text-yellow-800',
      proposal: 'bg-purple-100 text-purple-800',
      negotiation: 'bg-orange-100 text-orange-800',
      closed_won: 'bg-green-100 text-green-800',
      closed_lost: 'bg-red-100 text-red-800'
    };
    return colors[stage as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const handleDragStart = (e: React.DragEvent, dealId: number) => {
    e.dataTransfer.setData('dealId', dealId.toString());
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetStage: string) => {
    e.preventDefault();
    const dealId = parseInt(e.dataTransfer.getData('dealId'));
    handleUpdateDealStage(dealId, targetStage);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const stages = getStages();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Pipelines</h1>
          <p className="mt-2 text-gray-600">
            Manage your sales pipeline and track deals through stages
          </p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => setShowCreatePipelineModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            New Pipeline
          </Button>
        </div>
      </div>

      {/* Pipeline Selector */}
      {pipelines.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-4">
              <Label className="text-sm font-medium">Active Pipeline:</Label>
              <Select 
                value={selectedPipeline?.id?.toString() || ''} 
                onValueChange={(value) => {
                  const pipeline = pipelines.find(p => p.id.toString() === value);
                  setSelectedPipeline(pipeline || null);
                }}
              >
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="Select a pipeline" />
                </SelectTrigger>
                <SelectContent>
                  {pipelines.map((pipeline) => (
                    <SelectItem key={pipeline.id} value={pipeline.id.toString()}>
                      {pipeline.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Kanban Board */}
      {selectedPipeline && (
        <div className="grid grid-cols-6 gap-4">
          {stages.map((stage) => (
            <div
              key={stage.name}
              className="bg-gray-50 rounded-lg p-4 min-h-[600px]"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, stage.name)}
            >
              {/* Stage Header */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 capitalize">
                    {stage.name.replace('_', ' ')}
                  </h3>
                  <Badge className={getStageColor(stage.name)}>
                    {stage.dealCount}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 font-medium">
                  {formatCurrency(stage.totalAmount)}
                </p>
                
                {/* Add Deal Button */}
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-2"
                  onClick={() => {
                    setDealForm({ ...dealForm, stage: stage.name });
                    setShowCreateDealModal(true);
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Deal
                </Button>
              </div>

              {/* Deal Cards */}
              <div className="space-y-3">
                {stage.deals.map((deal) => (
                  <div
                    key={deal.id}
                    className="bg-white rounded-lg p-3 shadow-sm border cursor-move hover:shadow-md transition-shadow"
                    draggable
                    onDragStart={(e) => handleDragStart(e, deal.id)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-sm text-gray-900 line-clamp-2">
                        {deal.title}
                      </h4>
                      <div className="flex space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedDeal(deal);
                            setDealForm({
                              title: deal.title,
                              amount: deal.amount?.toString() || '',
                              stage: deal.stage,
                              account_id: deal.account_id?.toString() || '',
                              contact_id: deal.contact_id?.toString() || '',
                              close_date: deal.close_date || ''
                            });
                            setShowEditDealModal(true);
                          }}
                        >
                          <Edit className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteDeal(deal.id)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                    
                    <div className="space-y-1">
                      <div className="flex items-center text-sm text-gray-600">
                        <DollarSign className="w-3 h-3 mr-1" />
                        {formatCurrency(deal.amount || 0)}
                      </div>
                      
                      {deal.account_name && (
                        <div className="flex items-center text-sm text-gray-600">
                          <Building className="w-3 h-3 mr-1" />
                          <span className="truncate">{deal.account_name}</span>
                        </div>
                      )}
                      
                      {deal.contact_name && (
                        <div className="flex items-center text-sm text-gray-600">
                          <User className="w-3 h-3 mr-1" />
                          <span className="truncate">{deal.contact_name}</span>
                        </div>
                      )}
                      
                      {deal.close_date && (
                        <div className="flex items-center text-sm text-gray-600">
                          <Calendar className="w-3 h-3 mr-1" />
                          {new Date(deal.close_date).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {pipelines.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No pipelines yet</h3>
            <p className="text-gray-600 mb-4">
              Create your first pipeline to start managing deals
            </p>
            <Button onClick={() => setShowCreatePipelineModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Pipeline
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Create Pipeline Modal */}
      <Dialog open={showCreatePipelineModal} onOpenChange={setShowCreatePipelineModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Pipeline</DialogTitle>
            <DialogDescription>
              Create a new sales pipeline
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="pipeline-name">Name</Label>
              <Input
                id="pipeline-name"
                value={pipelineForm.name}
                onChange={(e) => setPipelineForm({ ...pipelineForm, name: e.target.value })}
                placeholder="Enter pipeline name"
              />
            </div>
            <div>
              <Label htmlFor="pipeline-description">Description</Label>
              <Input
                id="pipeline-description"
                value={pipelineForm.description}
                onChange={(e) => setPipelineForm({ ...pipelineForm, description: e.target.value })}
                placeholder="Enter pipeline description"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreatePipelineModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreatePipeline}>
              Create Pipeline
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Deal Modal */}
      <Dialog open={showCreateDealModal} onOpenChange={setShowCreateDealModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Deal</DialogTitle>
            <DialogDescription>
              Add a new deal to the pipeline
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="deal-title">Title</Label>
              <Input
                id="deal-title"
                value={dealForm.title}
                onChange={(e) => setDealForm({ ...dealForm, title: e.target.value })}
                placeholder="Enter deal title"
              />
            </div>
            <div>
              <Label htmlFor="deal-amount">Amount</Label>
              <Input
                id="deal-amount"
                type="number"
                value={dealForm.amount}
                onChange={(e) => setDealForm({ ...dealForm, amount: e.target.value })}
                placeholder="Enter deal amount"
              />
            </div>
            <div>
              <Label htmlFor="deal-stage">Stage</Label>
              <Select value={dealForm.stage} onValueChange={(value) => setDealForm({ ...dealForm, stage: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DEFAULT_STAGES.map((stage) => (
                    <SelectItem key={stage} value={stage}>
                      {stage.replace('_', ' ').charAt(0).toUpperCase() + stage.replace('_', ' ').slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="deal-account">Account</Label>
              <Select value={dealForm.account_id} onValueChange={(value) => setDealForm({ ...dealForm, account_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select account" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id.toString()}>
                      {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="deal-contact">Contact</Label>
              <Select value={dealForm.contact_id} onValueChange={(value) => setDealForm({ ...dealForm, contact_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select contact" />
                </SelectTrigger>
                <SelectContent>
                  {contacts.map((contact) => (
                    <SelectItem key={contact.id} value={contact.id.toString()}>
                      {contact.first_name} {contact.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="deal-close-date">Close Date</Label>
              <Input
                id="deal-close-date"
                type="date"
                value={dealForm.close_date}
                onChange={(e) => setDealForm({ ...dealForm, close_date: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDealModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateDeal}>
              Create Deal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Deal Modal */}
      <Dialog open={showEditDealModal} onOpenChange={setShowEditDealModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Deal</DialogTitle>
            <DialogDescription>
              Update deal information
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-deal-title">Title</Label>
              <Input
                id="edit-deal-title"
                value={dealForm.title}
                onChange={(e) => setDealForm({ ...dealForm, title: e.target.value })}
                placeholder="Enter deal title"
              />
            </div>
            <div>
              <Label htmlFor="edit-deal-amount">Amount</Label>
              <Input
                id="edit-deal-amount"
                type="number"
                value={dealForm.amount}
                onChange={(e) => setDealForm({ ...dealForm, amount: e.target.value })}
                placeholder="Enter deal amount"
              />
            </div>
            <div>
              <Label htmlFor="edit-deal-stage">Stage</Label>
              <Select value={dealForm.stage} onValueChange={(value) => setDealForm({ ...dealForm, stage: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DEFAULT_STAGES.map((stage) => (
                    <SelectItem key={stage} value={stage}>
                      {stage.replace('_', ' ').charAt(0).toUpperCase() + stage.replace('_', ' ').slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="edit-deal-account">Account</Label>
              <Select value={dealForm.account_id} onValueChange={(value) => setDealForm({ ...dealForm, account_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select account" />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id.toString()}>
                      {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="edit-deal-contact">Contact</Label>
              <Select value={dealForm.contact_id} onValueChange={(value) => setDealForm({ ...dealForm, contact_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select contact" />
                </SelectTrigger>
                <SelectContent>
                  {contacts.map((contact) => (
                    <SelectItem key={contact.id} value={contact.id.toString()}>
                      {contact.first_name} {contact.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="edit-deal-close-date">Close Date</Label>
              <Input
                id="edit-deal-close-date"
                type="date"
                value={dealForm.close_date}
                onChange={(e) => setDealForm({ ...dealForm, close_date: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDealModal(false)}>
              Cancel
            </Button>
            <Button onClick={async () => {
              try {
                await api.put(`/deals/${selectedDeal?.id}`, {
                  ...dealForm,
                  amount: parseFloat(dealForm.amount) || 0,
                  account_id: dealForm.account_id ? parseInt(dealForm.account_id) : null,
                  contact_id: dealForm.contact_id ? parseInt(dealForm.contact_id) : null
                });
                setShowEditDealModal(false);
                setSelectedDeal(null);
                showToast('Deal updated successfully!', 'success');
                fetchData();
              } catch (err) {
                showToast('Failed to update deal', 'error');
              }
            }}>
              Update Deal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
