'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Send, Download, Eye, Edit, RefreshCw, Upload, Link, Globe, Settings, FileText, Image, Code, Database, Server, Cloud, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

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

interface FileUpload {
  file: File;
  type: 'image' | 'document' | 'code' | 'other';
  preview?: string;
}

interface ReferenceUrl {
  url: string;
  title?: string;
  description?: string;
}

export default function SystemBuilder() {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; timestamp: Date }>>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [generatedSystem, setGeneratedSystem] = useState<GeneratedSystem | null>(null);
  const [systemSpec, setSystemSpec] = useState<SystemSpec>({
    name: '',
    description: '',
    type: 'web_app',
    techStack: [],
    features: [],
    infrastructure: []
  });
  const [uploadedFiles, setUploadedFiles] = useState<FileUpload[]>([]);
  const [referenceUrls, setReferenceUrls] = useState<ReferenceUrl[]>([]);
  const [deploymentDomain, setDeploymentDomain] = useState('');
  const [deploymentStatus, setDeploymentStatus] = useState<'idle' | 'deploying' | 'success' | 'error'>('idle');
  const [deploymentUrl, setDeploymentUrl] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [editHistory, setEditHistory] = useState<any[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    setMessages(prev => [...prev, { role, content, timestamp: new Date() }]);
    setTimeout(scrollToBottom, 100);
  }, []);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    files.forEach(file => {
      const fileType = getFileType(file);
      const fileUpload: FileUpload = {
        file,
        type: fileType,
        preview: fileType === 'image' ? URL.createObjectURL(file) : undefined
      };
      setUploadedFiles(prev => [...prev, fileUpload]);
    });
  };

  const getFileType = (file: File): 'image' | 'document' | 'code' | 'other' => {
    const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const documentTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    const codeTypes = ['text/javascript', 'text/typescript', 'text/html', 'text/css', 'application/json'];
    
    if (imageTypes.includes(file.type)) return 'image';
    if (documentTypes.includes(file.type)) return 'document';
    if (codeTypes.includes(file.type)) return 'code';
    return 'other';
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const addReferenceUrl = () => {
    if (deploymentDomain.trim()) {
      setReferenceUrls(prev => [...prev, { url: deploymentDomain.trim() }]);
      setDeploymentDomain('');
    }
  };

  const removeReferenceUrl = (index: number) => {
    setReferenceUrls(prev => prev.filter((_, i) => i !== index));
  };

  const analyzeUrl = async (url: string) => {
    try {
      const response = await fetch('/api/system/analyze-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await response.json();
      if (data.success) {
        return data.analysis;
      }
    } catch (error) {
      console.error('Error analyzing URL:', error);
    }
    return null;
  };

  const generateSystem = async () => {
    if (!systemSpec.name || !systemSpec.description) {
      addMessage('assistant', 'Please provide a system name and description to generate a system.');
      return;
    }

    setIsLoading(true);
    addMessage('user', `Generate a ${systemSpec.name}: ${systemSpec.description}`);

    try {
      // Upload files first if any
      let uploadedFileIds: string[] = [];
      if (uploadedFiles.length > 0 && generatedSystem) {
        const formData = new FormData();
        uploadedFiles.forEach((fileUpload, index) => {
          formData.append(`files`, fileUpload.file);
        });
        
        const uploadResponse = await fetch(`/api/system/upload-reference/${generatedSystem.id}`, {
          method: 'POST',
          body: formData
        });
        const uploadData = await uploadResponse.json();
        if (uploadData.success) {
          uploadedFileIds = uploadData.file_ids;
        }
      }

      // Analyze reference URLs
      let urlInsights: any[] = [];
      for (const refUrl of referenceUrls) {
        const analysis = await analyzeUrl(refUrl.url);
        if (analysis) {
          urlInsights.push(analysis);
        }
      }

      const response = await fetch('/api/system/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...systemSpec,
          reference_urls: referenceUrls.map(r => r.url),
          uploaded_files: uploadedFileIds,
          url_insights: urlInsights
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setGeneratedSystem(data.system);
        addMessage('assistant', `🎉 System "${data.system.specification.name}" generated successfully! I've created a complete, deployable application with ${data.system.preview.fileCount} files including frontend, backend, infrastructure, and deployment configurations.`);
      } else {
        addMessage('assistant', `❌ Error generating system: ${data.error}`);
      }
    } catch (error) {
      addMessage('assistant', `❌ Error generating system: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const previewSystem = async () => {
    if (!generatedSystem) return;

    try {
      const response = await fetch(`/api/system/preview/${generatedSystem.id}`);
      const data = await response.json();
      
      if (data.success) {
        setGeneratedSystem(data.system);
        addMessage('assistant', `📋 System preview updated. The system includes ${data.system.preview.components} components and ${data.system.preview.fileCount} files.`);
      }
    } catch (error) {
      addMessage('assistant', `❌ Error previewing system: ${error}`);
    }
  };

  const downloadSystem = async () => {
    if (!generatedSystem) return;

    try {
      const response = await fetch(`/api/system/download/${generatedSystem.id}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${generatedSystem.specification.name.toLowerCase().replace(/\s+/g, '-')}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        addMessage('assistant', `📦 System downloaded successfully! You can now deploy it to your own infrastructure.`);
      }
    } catch (error) {
      addMessage('assistant', `❌ Error downloading system: ${error}`);
    }
  };

  const deploySystem = async () => {
    if (!generatedSystem) return;

    setDeploymentStatus('deploying');
    addMessage('assistant', '🚀 Starting live deployment...');

    try {
      const response = await fetch(`/api/system/deploy/${generatedSystem.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: deploymentDomain || undefined,
          domain_type: deploymentDomain ? 'custom' : 'sbh_managed'
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setDeploymentStatus('success');
        setDeploymentUrl(data.deployment_url);
        addMessage('assistant', `🎉 System deployed successfully! Your application is now live at: ${data.deployment_url}`);
      } else {
        setDeploymentStatus('error');
        addMessage('assistant', `❌ Deployment failed: ${data.error}`);
      }
    } catch (error) {
      setDeploymentStatus('error');
      addMessage('assistant', `❌ Deployment error: ${error}`);
    }
  };

  const editSystem = async (newSpec: Partial<SystemSpec>) => {
    if (!generatedSystem) return;

    setIsLoading(true);
    addMessage('user', `Edit system: ${JSON.stringify(newSpec)}`);

    try {
      const response = await fetch(`/api/system/edit/${generatedSystem.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSpec)
      });

      const data = await response.json();
      
      if (data.success) {
        setGeneratedSystem(data.system);
        setEditHistory(prev => [...prev, { timestamp: new Date(), changes: newSpec }]);
        addMessage('assistant', `✏️ System updated successfully! Changes have been applied and the system has been regenerated.`);
      } else {
        addMessage('assistant', `❌ Error editing system: ${data.error}`);
      }
    } catch (error) {
      addMessage('assistant', `❌ Error editing system: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const regenerateSystem = async (components: string[] = []) => {
    if (!generatedSystem) return;

    setIsLoading(true);
    addMessage('user', `Regenerate system components: ${components.join(', ')}`);

    try {
      const response = await fetch(`/api/system/regenerate/${generatedSystem.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ components })
      });

      const data = await response.json();
      
      if (data.success) {
        setGeneratedSystem(data.system);
        addMessage('assistant', `🔄 System components regenerated successfully!`);
      } else {
        addMessage('assistant', `❌ Error regenerating system: ${data.error}`);
      }
    } catch (error) {
      addMessage('assistant', `❌ Error regenerating system: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const validateDomain = async (domain: string) => {
    try {
      const response = await fetch('/api/system/domain/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      return { success: false, error: 'Domain validation failed' };
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Panel - Chat Interface */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <h1 className="text-2xl font-bold text-gray-900">System Builder Hub</h1>
          <p className="text-gray-600">AI-powered system generation and deployment</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-3xl p-4 rounded-lg ${
                message.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-white border border-gray-200'
              }`}>
                <div className="whitespace-pre-wrap">{message.content}</div>
                <div className={`text-xs mt-2 ${
                  message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 p-4 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Generating system...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your system or ask questions..."
              className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), addMessage('user', input), setInput(''))}
            />
            <button
              onClick={() => {
                addMessage('user', input);
                setInput('');
              }}
              className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel - System Builder */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
        {/* System Specification */}
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">System Specification</h2>
          
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">System Name</label>
              <input
                type="text"
                value={systemSpec.name}
                onChange={(e) => setSystemSpec(prev => ({ ...prev, name: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="e.g., E-commerce Platform"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={systemSpec.description}
                onChange={(e) => setSystemSpec(prev => ({ ...prev, description: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
                placeholder="Describe what your system should do..."
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">System Type</label>
              <select
                value={systemSpec.type}
                onChange={(e) => setSystemSpec(prev => ({ ...prev, type: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="web_app">Web Application</option>
                <option value="api">API Service</option>
                <option value="mobile_app">Mobile App</option>
                <option value="desktop_app">Desktop App</option>
                <option value="microservice">Microservice</option>
              </select>
            </div>
          </div>
        </div>

        {/* File Upload & References */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-md font-semibold text-gray-900 mb-3">References & Files</h3>
          
          {/* File Upload */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Upload Files</label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
              <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600 mb-2">Drag & drop files or click to browse</p>
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
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Choose Files
              </button>
            </div>
            
            {/* Uploaded Files */}
            {uploadedFiles.length > 0 && (
              <div className="mt-2 space-y-2">
                {uploadedFiles.map((fileUpload, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                    <div className="flex items-center space-x-2">
                      {fileUpload.type === 'image' && <Image className="h-4 w-4 text-gray-500" />}
                      {fileUpload.type === 'document' && <FileText className="h-4 w-4 text-gray-500" />}
                      {fileUpload.type === 'code' && <Code className="h-4 w-4 text-gray-500" />}
                      <span className="text-sm text-gray-700">{fileUpload.file.name}</span>
                    </div>
                    <button
                      onClick={() => removeFile(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Reference URLs */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Reference URLs</label>
            <div className="flex space-x-2">
              <input
                type="url"
                value={deploymentDomain}
                onChange={(e) => setDeploymentDomain(e.target.value)}
                placeholder="https://example.com"
                className="flex-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={addReferenceUrl}
                className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
              >
                <Link className="h-4 w-4" />
              </button>
            </div>
            
            {/* Reference URLs List */}
            {referenceUrls.length > 0 && (
              <div className="mt-2 space-y-2">
                {referenceUrls.map((refUrl, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                    <span className="text-sm text-gray-700 truncate">{refUrl.url}</span>
                    <button
                      onClick={() => removeReferenceUrl(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-md font-semibold text-gray-900 mb-3">Actions</h3>
          
          <div className="space-y-2">
            <button
              onClick={generateSystem}
              disabled={isLoading || !systemSpec.name || !systemSpec.description}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Code className="h-4 w-4" />
              <span>Generate System</span>
            </button>
            
            {generatedSystem && (
              <>
                <button
                  onClick={previewSystem}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                >
                  <Eye className="h-4 w-4" />
                  <span>Preview</span>
                </button>
                
                <button
                  onClick={downloadSystem}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                >
                  <Download className="h-4 w-4" />
                  <span>Download</span>
                </button>
                
                <button
                  onClick={() => setEditMode(!editMode)}
                  className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
                >
                  <Edit className="h-4 w-4" />
                  <span>{editMode ? 'Exit Edit' : 'Edit System'}</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Deployment */}
        {generatedSystem && (
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-md font-semibold text-gray-900 mb-3">Live Deployment</h3>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Custom Domain (Optional)</label>
                <input
                  type="text"
                  value={deploymentDomain}
                  onChange={(e) => setDeploymentDomain(e.target.value)}
                  placeholder="myapp.com or leave blank for SBH subdomain"
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <button
                onClick={deploySystem}
                disabled={deploymentStatus === 'deploying'}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
              >
                {deploymentStatus === 'deploying' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Globe className="h-4 w-4" />
                )}
                <span>
                  {deploymentStatus === 'deploying' ? 'Deploying...' : 'Deploy Live'}
                </span>
              </button>
              
              {deploymentStatus === 'success' && deploymentUrl && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                  <div className="flex items-center space-x-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-800">Deployed Successfully!</span>
                  </div>
                  <a
                    href={deploymentUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-green-600 hover:text-green-700 underline"
                  >
                    {deploymentUrl}
                  </a>
                </div>
              )}
              
              {deploymentStatus === 'error' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <div className="flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm text-red-800">Deployment Failed</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* System Status */}
        {generatedSystem && (
          <div className="p-4">
            <h3 className="text-md font-semibold text-gray-900 mb-3">System Status</h3>
            
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Status:</span>
                <span className={`font-medium ${
                  generatedSystem.status === 'generated' ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  {generatedSystem.status}
                </span>
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Files:</span>
                <span className="font-medium">{generatedSystem.preview?.fileCount || 0}</span>
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Components:</span>
                <span className="font-medium">{generatedSystem.preview?.components || 0}</span>
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Created:</span>
                <span className="font-medium">
                  {new Date(generatedSystem.createdAt).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
