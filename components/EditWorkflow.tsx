'use client';

import React, { useState, useRef } from 'react';
import { 
  Edit, 
  Save, 
  RotateCcw, 
  Upload, 
  MessageSquare, 
  Code, 
  Database, 
  Server, 
  Globe,
  CheckCircle,
  AlertCircle,
  Loader2,
  History,
  X,
  Plus
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
}

interface EditHistory {
  id: string;
  timestamp: Date;
  changes: Partial<SystemSpec>;
  feedback?: string;
  files?: string[];
  status: 'pending' | 'applied' | 'failed';
}

interface EditWorkflowProps {
  system: GeneratedSystem;
  onSystemUpdate: (updatedSystem: GeneratedSystem) => void;
  onClose: () => void;
}

export default function EditWorkflow({ system, onSystemUpdate, onClose }: EditWorkflowProps) {
  const [editMode, setEditMode] = useState<'spec' | 'feedback' | 'regenerate'>('spec');
  const [editedSpec, setEditedSpec] = useState<SystemSpec>(system.specification);
  const [feedback, setFeedback] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [selectedComponents, setSelectedComponents] = useState<string[]>([]);
  const [editHistory, setEditHistory] = useState<EditHistory[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const componentOptions = [
    { id: 'frontend', name: 'Frontend', icon: <Code className="h-4 w-4" /> },
    { id: 'backend', name: 'Backend', icon: <Server className="h-4 w-4" /> },
    { id: 'database', name: 'Database', icon: <Database className="h-4 w-4" /> },
    { id: 'infrastructure', name: 'Infrastructure', icon: <Globe className="h-4 w-4" /> },
    { id: 'deployment', name: 'Deployment', icon: <Globe className="h-4 w-4" /> }
  ];

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setUploadedFiles(prev => [...prev, ...files]);
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const applySpecificationChanges = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/system/edit/${system.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editedSpec)
      });

      const data = await response.json();
      
      if (data.success) {
        const editRecord: EditHistory = {
          id: Date.now().toString(),
          timestamp: new Date(),
          changes: editedSpec,
          status: 'applied'
        };
        
        setEditHistory(prev => [editRecord, ...prev]);
        onSystemUpdate(data.system);
        setEditMode('spec');
      } else {
        setError(data.error || 'Failed to apply changes');
      }
    } catch (error) {
      setError('Error applying changes');
    } finally {
      setIsLoading(false);
    }
  };

  const applyFeedbackChanges = async () => {
    if (!feedback.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      // Upload files if any
      let uploadedFileIds: string[] = [];
      if (uploadedFiles.length > 0) {
        const formData = new FormData();
        uploadedFiles.forEach(file => {
          formData.append('files', file);
        });
        
        const uploadResponse = await fetch(`/api/system/upload-reference/${system.id}`, {
          method: 'POST',
          body: formData
        });
        const uploadData = await uploadResponse.json();
        if (uploadData.success) {
          uploadedFileIds = uploadData.file_ids;
        }
      }

      const response = await fetch(`/api/system/edit/${system.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedback,
          uploaded_files: uploadedFileIds
        })
      });

      const data = await response.json();
      
      if (data.success) {
        const editRecord: EditHistory = {
          id: Date.now().toString(),
          timestamp: new Date(),
          changes: {},
          feedback,
          files: uploadedFileIds,
          status: 'applied'
        };
        
        setEditHistory(prev => [editRecord, ...prev]);
        onSystemUpdate(data.system);
        setFeedback('');
        setUploadedFiles([]);
        setEditMode('spec');
      } else {
        setError(data.error || 'Failed to apply feedback');
      }
    } catch (error) {
      setError('Error applying feedback');
    } finally {
      setIsLoading(false);
    }
  };

  const regenerateComponents = async () => {
    if (selectedComponents.length === 0) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/system/regenerate/${system.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ components: selectedComponents })
      });

      const data = await response.json();
      
      if (data.success) {
        const editRecord: EditHistory = {
          id: Date.now().toString(),
          timestamp: new Date(),
          changes: {},
          status: 'applied'
        };
        
        setEditHistory(prev => [editRecord, ...prev]);
        onSystemUpdate(data.system);
        setSelectedComponents([]);
        setEditMode('spec');
      } else {
        setError(data.error || 'Failed to regenerate components');
      }
    } catch (error) {
      setError('Error regenerating components');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleComponent = (componentId: string) => {
    setSelectedComponents(prev => 
      prev.includes(componentId) 
        ? prev.filter(id => id !== componentId)
        : [...prev, componentId]
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Edit System</h2>
            <p className="text-gray-600">{system.specification.name}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setEditMode('spec')}
            className={`px-6 py-3 text-sm font-medium ${
              editMode === 'spec'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Edit className="h-4 w-4 inline mr-2" />
            Edit Specification
          </button>
          <button
            onClick={() => setEditMode('feedback')}
            className={`px-6 py-3 text-sm font-medium ${
              editMode === 'feedback'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <MessageSquare className="h-4 w-4 inline mr-2" />
            Provide Feedback
          </button>
          <button
            onClick={() => setEditMode('regenerate')}
            className={`px-6 py-3 text-sm font-medium ${
              editMode === 'regenerate'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <RotateCcw className="h-4 w-4 inline mr-2" />
            Regenerate Components
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <span className="text-red-800">{error}</span>
              </div>
            </div>
          )}

          {/* Edit Specification Mode */}
          {editMode === 'spec' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">System Name</label>
                <input
                  type="text"
                  value={editedSpec.name}
                  onChange={(e) => setEditedSpec(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={editedSpec.description}
                  onChange={(e) => setEditedSpec(prev => ({ ...prev, description: e.target.value }))}
                  rows={4}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">System Type</label>
                <select
                  value={editedSpec.type}
                  onChange={(e) => setEditedSpec(prev => ({ ...prev, type: e.target.value }))}
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="web_app">Web Application</option>
                  <option value="api">API Service</option>
                  <option value="mobile_app">Mobile App</option>
                  <option value="desktop_app">Desktop App</option>
                  <option value="microservice">Microservice</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tech Stack</label>
                <div className="flex flex-wrap gap-2">
                  {editedSpec.techStack.map((tech, index) => (
                    <div key={index} className="flex items-center space-x-2 bg-blue-100 text-blue-800 px-3 py-1 rounded-full">
                      <span className="text-sm">{tech}</span>
                      <button
                        onClick={() => setEditedSpec(prev => ({
                          ...prev,
                          techStack: prev.techStack.filter((_, i) => i !== index)
                        }))}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => {
                      const newTech = prompt('Enter new technology:');
                      if (newTech) {
                        setEditedSpec(prev => ({
                          ...prev,
                          techStack: [...prev.techStack, newTech]
                        }));
                      }
                    }}
                    className="flex items-center space-x-1 text-blue-600 hover:text-blue-800"
                  >
                    <Plus className="h-4 w-4" />
                    <span className="text-sm">Add Tech</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Features</label>
                <div className="flex flex-wrap gap-2">
                  {editedSpec.features.map((feature, index) => (
                    <div key={index} className="flex items-center space-x-2 bg-green-100 text-green-800 px-3 py-1 rounded-full">
                      <span className="text-sm">{feature}</span>
                      <button
                        onClick={() => setEditedSpec(prev => ({
                          ...prev,
                          features: prev.features.filter((_, i) => i !== index)
                        }))}
                        className="text-green-600 hover:text-green-800"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => {
                      const newFeature = prompt('Enter new feature:');
                      if (newFeature) {
                        setEditedSpec(prev => ({
                          ...prev,
                          features: [...prev.features, newFeature]
                        }));
                      }
                    }}
                    className="flex items-center space-x-1 text-green-600 hover:text-green-800"
                  >
                    <Plus className="h-4 w-4" />
                    <span className="text-sm">Add Feature</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Feedback Mode */}
          {editMode === 'feedback' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Feedback & Requirements</label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  rows={6}
                  placeholder="Describe what you'd like to change, add, or improve. Be as specific as possible..."
                  className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Upload Reference Files</label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600 mb-2">Upload screenshots, documents, or code examples</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="image/*,.pdf,.doc,.docx,.txt,.js,.ts,.tsx,.jsx,.html,.css,.json"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
                  >
                    Choose Files
                  </button>
                </div>

                {uploadedFiles.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {uploadedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                        <span className="text-sm text-gray-700">{file.name}</span>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Regenerate Components Mode */}
          {editMode === 'regenerate' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Select Components to Regenerate</label>
                <div className="grid grid-cols-2 gap-4">
                  {componentOptions.map((component) => (
                    <button
                      key={component.id}
                      onClick={() => toggleComponent(component.id)}
                      className={`p-4 border-2 rounded-lg text-left transition-colors ${
                        selectedComponents.includes(component.id)
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        {component.icon}
                        <span className="font-medium">{component.name}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {selectedComponents.length > 0 && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-800">
                    Selected components: {selectedComponents.join(', ')}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-4">
            <History className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-600">
              {editHistory.length} edit{editHistory.length !== 1 ? 's' : ''} applied
            </span>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            
            {editMode === 'spec' && (
              <button
                onClick={applySpecificationChanges}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                <span>Apply Changes</span>
              </button>
            )}
            
            {editMode === 'feedback' && (
              <button
                onClick={applyFeedbackChanges}
                disabled={isLoading || !feedback.trim()}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <MessageSquare className="h-4 w-4" />
                )}
                <span>Apply Feedback</span>
              </button>
            )}
            
            {editMode === 'regenerate' && (
              <button
                onClick={regenerateComponents}
                disabled={isLoading || selectedComponents.length === 0}
                className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4" />
                )}
                <span>Regenerate</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
