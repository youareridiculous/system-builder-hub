import React, { useState, useEffect } from 'react'
import { api } from '../lib/api.ts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card'
import { Button } from '../components/Button'
import { Input } from '../components/Input'
import { Label } from '../components/Label'
import { Textarea } from '../components/Textarea'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '../components/Dialog'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '../components/Table'
import { Plus, Edit, Trash2, FileText } from 'lucide-react'
import { Badge } from '../components/Badge'

function Pipelines() {
  const [pipelines, setPipelines] = useState([])
  const [deals, setDeals] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [selectedPipeline, setSelectedPipeline] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  })

  const fetchPipelines = async () => {
    try {
      const data = await api.get('/pipelines/')
      setPipelines(data)
      setLoading(false)
    } catch (err) {
      console.error('Error fetching pipelines:', err)
      setLoading(false)
    }
  }

  const fetchDeals = async () => {
    try {
      const data = await api.get('/deals/')
      setDeals(data)
    } catch (err) {
      console.error('Error fetching deals:', err)
    }
  }

  useEffect(() => {
    fetchPipelines()
    fetchDeals()
  }, [])

  const handleCreate = async () => {
    try {
      await api.post('/pipelines/', formData)
      setShowCreateDialog(false)
      setFormData({ name: '', description: '' })
      fetchPipelines()
    } catch (err) {
      console.error('Error creating pipeline:', err)
      alert('Failed to create pipeline')
    }
  }

  const handleEdit = async () => {
    try {
      await api.put(`/pipelines/${selectedPipeline.id}`, formData)
      setShowEditDialog(false)
      setSelectedPipeline(null)
      setFormData({ name: '', description: '' })
      fetchPipelines()
    } catch (err) {
      console.error('Error updating pipeline:', err)
      alert('Failed to update pipeline')
    }
  }

  const handleDelete = async () => {
    try {
      await api.del(`/pipelines/${selectedPipeline.id}`)
      setShowDeleteDialog(false)
      setSelectedPipeline(null)
      fetchPipelines()
    } catch (err) {
      console.error('Error deleting pipeline:', err)
      alert('Failed to delete pipeline')
    }
  }

  const openEditDialog = (pipeline) => {
    setSelectedPipeline(pipeline)
    setFormData({
      name: pipeline.name || '',
      description: pipeline.description || ''
    })
    setShowEditDialog(true)
  }

  const openDeleteDialog = (pipeline) => {
    setSelectedPipeline(pipeline)
    setShowDeleteDialog(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Pipelines</h1>
          <p className="mt-2 text-gray-600">Manage your sales pipelines</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Pipeline
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="w-5 h-5 mr-2" />
            All Pipelines
          </CardTitle>
          <CardDescription>
            A list of all your sales pipelines and their details
          </CardDescription>
        </CardHeader>
        <CardContent>
                {/* Kanban Board View */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {/* Prospecting Column */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Prospecting</h3>
            <Badge variant="secondary" className="bg-blue-100 text-blue-800">
              {deals.filter(deal => deal.stage === 'prospecting').length}
            </Badge>
          </div>
          <div className="space-y-3">
            {deals.filter(deal => deal.stage === 'prospecting').map((deal) => (
              <div key={deal.id} className="bg-white rounded-lg p-3 shadow-sm border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900">{deal.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {deal.amount ? `$${deal.amount.toLocaleString()}` : 'No amount'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {deal.account ? deal.account.name : 'No account'}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => openDeleteDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Qualification Column */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Qualification</h3>
            <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
              {deals.filter(deal => deal.stage === 'qualification').length}
            </Badge>
          </div>
          <div className="space-y-3">
            {deals.filter(deal => deal.stage === 'qualification').map((deal) => (
              <div key={deal.id} className="bg-white rounded-lg p-3 shadow-sm border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900">{deal.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {deal.amount ? `$${deal.amount.toLocaleString()}` : 'No amount'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {deal.account ? deal.account.name : 'No account'}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => openDeleteDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Proposal Column */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Proposal</h3>
            <Badge variant="secondary" className="bg-purple-100 text-purple-800">
              {deals.filter(deal => deal.stage === 'proposal').length}
            </Badge>
          </div>
          <div className="space-y-3">
            {deals.filter(deal => deal.stage === 'proposal').map((deal) => (
              <div key={deal.id} className="bg-white rounded-lg p-3 shadow-sm border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900">{deal.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {deal.amount ? `$${deal.amount.toLocaleString()}` : 'No amount'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {deal.account ? deal.account.name : 'No account'}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => openDeleteDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Negotiation Column */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Negotiation</h3>
            <Badge variant="secondary" className="bg-orange-100 text-orange-800">
              {deals.filter(deal => deal.stage === 'negotiation').length}
            </Badge>
          </div>
          <div className="space-y-3">
            {deals.filter(deal => deal.stage === 'negotiation').map((deal) => (
              <div key={deal.id} className="bg-white rounded-lg p-3 shadow-sm border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900">{deal.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {deal.amount ? `$${deal.amount.toLocaleString()}` : 'No amount'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {deal.account ? deal.account.name : 'No account'}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => openDeleteDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Closed Won Column */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Closed Won</h3>
            <Badge variant="secondary" className="bg-green-100 text-green-800">
              {deals.filter(deal => deal.stage === 'closed_won').length}
            </Badge>
          </div>
          <div className="space-y-3">
            {deals.filter(deal => deal.stage === 'closed_won').map((deal) => (
              <div key={deal.id} className="bg-white rounded-lg p-3 shadow-sm border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900">{deal.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {deal.amount ? `$${deal.amount.toLocaleString()}` : 'No amount'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {deal.account ? deal.account.name : 'No account'}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => openDeleteDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Closed Lost Column */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-700">Closed Lost</h3>
            <Badge variant="secondary" className="bg-red-100 text-red-800">
              {deals.filter(deal => deal.stage === 'closed_lost').length}
            </Badge>
          </div>
          <div className="space-y-3">
            {deals.filter(deal => deal.stage === 'closed_lost').map((deal) => (
              <div key={deal.id} className="bg-white rounded-lg p-3 shadow-sm border">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900">{deal.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      {deal.amount ? `$${deal.amount.toLocaleString()}` : 'No amount'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {deal.account ? deal.account.name : 'No account'}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openEditDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Edit className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => openDeleteDialog(deal)}
                      className="h-6 w-6 p-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Pipeline</DialogTitle>
            <DialogDescription>
              Add a new sales pipeline to your CRM system
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Pipeline Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter pipeline name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Enter pipeline description"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate}>Create Pipeline</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Pipeline</DialogTitle>
            <DialogDescription>
              Update the pipeline information
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Pipeline Name</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter pipeline name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Enter pipeline description"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleEdit}>Update Pipeline</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Pipeline</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedPipeline?.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete Pipeline
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Pipelines
