import React, { useState, useEffect } from 'react'
import { getData, postData, putData, deleteData } from '../lib/api'
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

function Pipelines() {
  const [pipelines, setPipelines] = useState([])
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
      const data = await getData('/api/pipelines/')
      setPipelines(data)
      setLoading(false)
    } catch (err) {
      console.error('Error fetching pipelines:', err)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPipelines()
  }, [])

  const handleCreate = async () => {
    try {
      await postData('/api/pipelines/', formData)
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
      await putData(`/api/pipelines/${selectedPipeline.id}`, formData)
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
      await deleteData(`/api/pipelines/${selectedPipeline.id}`)
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
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pipelines.map((pipeline) => (
                <TableRow key={pipeline.id}>
                  <TableCell className="font-medium">{pipeline.name}</TableCell>
                  <TableCell className="max-w-md">
                    {pipeline.description ? (
                      <p className="text-sm text-gray-600 truncate">
                        {pipeline.description}
                      </p>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {new Date(pipeline.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(pipeline)}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => openDeleteDialog(pipeline)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
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
