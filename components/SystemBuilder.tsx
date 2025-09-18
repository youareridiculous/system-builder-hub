'use client'

import { useState } from 'react'
import { Code, Database, Cloud, Zap, Settings, Play, Download, Eye, ShoppingCart, FileText, BarChart3, Globe, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'

interface SystemSpec {
  name: string
  description: string
  type: 'web-app' | 'api' | 'data-pipeline' | 'ml-service' | 'microservice' | 'ecommerce-platform' | 'cms' | 'dashboard'
  techStack: string[]
  features: string[]
  infrastructure: string[]
}

interface DomainValidation {
  success: boolean
  domain: string
  domain_type: string
  strategy: any
  setup_instructions: any
  error?: string
}

interface DeploymentResult {
  success: boolean
  system_id: string
  live_url: string
  deployment_id: string
  deployment_type: string
  domain_type: string
  dns_setup: any
  ssl_setup: any
  strategy: any
  status: string
  message: string
  error?: string
}

const systemTypes = [
  { id: 'web-app', name: 'Web Application', icon: Code, description: 'Full-stack web app with frontend and backend' },
  { id: 'api', name: 'REST API', icon: Database, description: 'Backend API service with database' },
  { id: 'data-pipeline', name: 'Data Pipeline', icon: Cloud, description: 'ETL pipeline for data processing' },
  { id: 'ml-service', name: 'ML Service', icon: Zap, description: 'Machine learning model serving' },
  { id: 'microservice', name: 'Microservice', icon: Settings, description: 'Containerized microservice' },
  { id: 'ecommerce-platform', name: 'E-commerce Platform', icon: ShoppingCart, description: 'Complete e-commerce solution with payment processing' },
  { id: 'cms', name: 'Content Management System', icon: FileText, description: 'CMS for content creation and management' },
  { id: 'dashboard', name: 'Analytics Dashboard', icon: BarChart3, description: 'Real-time analytics and reporting dashboard' }
]

const techStacks = [
  'React + Node.js', 'Vue.js + Python', 'Angular + Java', 'Next.js + TypeScript',
  'Python + FastAPI', 'Go + Gin', 'Rust + Actix', 'PHP + Laravel',
  'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch'
]

const commonFeatures = [
  'User Authentication', 'REST API', 'Database Integration', 'File Upload',
  'Real-time Updates', 'Search Functionality', 'Admin Dashboard', 'Email Notifications',
  'Payment Processing', 'Analytics', 'Caching', 'Logging'
]

const infrastructureOptions = [
  'AWS ECS Fargate', 'AWS Lambda', 'AWS RDS', 'AWS S3', 'AWS ALB',
  'Docker Containers', 'Auto Scaling', 'Load Balancing', 'SSL/TLS',
  'CloudWatch Monitoring', 'GitHub Actions CI/CD'
]

export function SystemBuilder() {
  const [spec, setSpec] = useState<SystemSpec>({
    name: '',
    description: '',
    type: 'web-app',
    techStack: [],
    features: [],
    infrastructure: []
  })
  const [currentStep, setCurrentStep] = useState(1)
  const [isGenerating, setIsGenerating] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [generatedSystem, setGeneratedSystem] = useState<any>(null)
  
  // Domain management state
  const [deploymentDomain, setDeploymentDomain] = useState('')
  const [deploymentType, setDeploymentType] = useState('production')
  const [domainValidation, setDomainValidation] = useState<DomainValidation | null>(null)
  const [isValidatingDomain, setIsValidatingDomain] = useState(false)
  const [isDeploying, setIsDeploying] = useState(false)
  const [deploymentResult, setDeploymentResult] = useState<DeploymentResult | null>(null)

  const updateSpec = (updates: Partial<SystemSpec>) => {
    setSpec(prev => ({ ...prev, ...updates }))
    // Clear errors when user makes changes
    setErrors({})
  }

  const toggleArrayItem = (array: string[], item: string, setter: (items: string[]) => void) => {
    if (array.includes(item)) {
      setter(array.filter(i => i !== item))
    } else {
      setter([...array, item])
    }
  }

  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {}
    
    if (step === 1) {
      if (!spec.name.trim()) newErrors.name = 'System name is required'
      if (!spec.description.trim()) newErrors.description = 'Description is required'
      if (!spec.type) newErrors.type = 'System type is required'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, 5))
    }
  }

  const handlePrevious = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1))
  }

  const validateDomain = async (domain: string) => {
    if (!domain.trim()) return
    
    setIsValidatingDomain(true)
    try {
      const response = await fetch('/api/system/domain/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain })
      })
      const result = await response.json()
      setDomainValidation(result)
    } catch (error) {
      console.error('Error validating domain:', error)
      setDomainValidation({
        success: false,
        domain,
        domain_type: 'unknown',
        strategy: {},
        setup_instructions: {},
        error: 'Failed to validate domain'
      })
    } finally {
      setIsValidatingDomain(false)
    }
  }

  const deployToCloud = async (systemId: string) => {
    if (!deploymentDomain.trim()) {
      alert('Please enter a domain for deployment')
      return
    }

    setIsDeploying(true)
    try {
      const response = await fetch(`/api/system/deploy/${systemId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: deploymentDomain,
          type: deploymentType
        })
      })
      const result = await response.json()
      setDeploymentResult(result)
      
      if (result.success) {
        alert(`�� System deployed successfully!\n\nLive URL: ${result.live_url}\n\n${result.message}`)
      } else {
        alert(`❌ Deployment failed: ${result.error}`)
      }
    } catch (error) {
      console.error('Error deploying system:', error)
      alert('Failed to deploy system. Please try again.')
    } finally {
      setIsDeploying(false)
    }
  }

  const generateSystem = async () => {
    if (validateStep(currentStep)) {
      setIsGenerating(true)
      
      try {
        const response = await fetch('/api/system/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(spec)
        })
        
        const result = await response.json()
        
        if (result.success) {
          // System generated successfully
          setGeneratedSystem(result.system)
          console.log('Generated system:', result.system)
          
          // Show success message with system details
          const systemDetails = `
System "${spec.name}" generated successfully!

System ID: ${result.system.systemId}
Type: ${result.system.specification.type}
Components: ${result.system.architecture.components.length}
Templates: ${Object.keys(result.system.templates).length}
Infrastructure: ${result.system.deployment.services.length} services

Check the console for full system details.
          `.trim()
          
          alert(systemDetails)
        } else {
          alert(`Error generating system: ${result.error}`)
        }
      } catch (error) {
        console.error('Error generating system:', error)
        alert('Failed to generate system. Please try again.')
      } finally {
        setIsGenerating(false)
      }
    }
  }

  const downloadSystem = () => {
    if (generatedSystem) {
      const dataStr = JSON.stringify(generatedSystem, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${spec.name.toLowerCase().replace(/\s+/g, '-')}-system.json`
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  const steps = [
    { id: 1, name: 'Basic Info', icon: Settings },
    { id: 2, name: 'Tech Stack', icon: Code },
    { id: 3, name: 'Features', icon: Zap },
    { id: 4, name: 'Infrastructure', icon: Cloud },
    { id: 5, name: 'Review', icon: Eye }
  ]

  return (
    <div className="max-w-6xl mx-auto">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const Icon = step.icon
            const isActive = currentStep === step.id
            const isCompleted = currentStep > step.id
            
            return (
              <div key={step.id} className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                    isActive
                      ? 'border-sbh-600 bg-sbh-600 text-white'
                      : isCompleted
                      ? 'border-green-500 bg-green-500 text-white'
                      : 'border-gray-300 bg-white text-gray-400'
                  }`}
                >
                  {isCompleted ? '✓' : <Icon className="w-5 h-5" />}
                </div>
                <div className="ml-3">
                  <p className={`text-sm font-medium ${isActive ? 'text-sbh-600' : 'text-gray-500'}`}>
                    {step.name}
                  </p>
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-16 h-0.5 mx-4 ${isCompleted ? 'bg-green-500' : 'bg-gray-300'}`} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="card">
        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Basic Information</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                System Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={spec.name}
                onChange={(e) => updateSpec({ name: e.target.value })}
                placeholder="e.g., E-commerce Platform"
                className={`input-field ${errors.name ? 'border-red-500' : ''}`}
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600">{errors.name}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                value={spec.description}
                onChange={(e) => updateSpec({ description: e.target.value })}
                placeholder="Describe what your system should do..."
                className={`input-field ${errors.description ? 'border-red-500' : ''}`}
                rows={4}
              />
              {errors.description && (
                <p className="mt-1 text-sm text-red-600">{errors.description}</p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                System Type <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {systemTypes.map((type) => {
                  const Icon = type.icon
                  return (
                    <button
                      key={type.id}
                      onClick={() => updateSpec({ type: type.id as any })}
                      className={`p-4 border-2 rounded-lg text-left transition-colors ${
                        spec.type === type.id
                          ? 'border-sbh-600 bg-sbh-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <Icon className="w-6 h-6 text-sbh-600 mb-2" />
                      <h3 className="font-medium text-gray-900">{type.name}</h3>
                      <p className="text-sm text-gray-500 mt-1">{type.description}</p>
                    </button>
                  )
                })}
              </div>
              {errors.type && (
                <p className="mt-2 text-sm text-red-600">{errors.type}</p>
              )}
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Technology Stack</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Technologies
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {techStacks.map((tech) => (
                  <button
                    key={tech}
                    onClick={() => toggleArrayItem(spec.techStack, tech, (items) => updateSpec({ techStack: items }))}
                    className={`px-3 py-2 rounded-lg border text-sm transition-colors ${
                      spec.techStack.includes(tech)
                        ? 'border-sbh-600 bg-sbh-600 text-white'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {tech}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Features</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Features
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {commonFeatures.map((feature) => (
                  <button
                    key={feature}
                    onClick={() => toggleArrayItem(spec.features, feature, (items) => updateSpec({ features: items }))}
                    className={`px-4 py-3 rounded-lg border text-left transition-colors ${
                      spec.features.includes(feature)
                        ? 'border-sbh-600 bg-sbh-50 text-sbh-700'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {feature}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Infrastructure</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Infrastructure Components
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {infrastructureOptions.map((infra) => (
                  <button
                    key={infra}
                    onClick={() => toggleArrayItem(spec.infrastructure, infra, (items) => updateSpec({ infrastructure: items }))}
                    className={`px-4 py-3 rounded-lg border text-left transition-colors ${
                      spec.infrastructure.includes(infra)
                        ? 'border-sbh-600 bg-sbh-50 text-sbh-700'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {infra}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {currentStep === 5 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Review & Generate</h2>
            
            {/* System Specification Review */}
            <div className="bg-gray-50 rounded-lg p-6 space-y-4">
              <div>
                <h3 className="font-medium text-gray-900">System Name</h3>
                <p className="text-gray-600">{spec.name || 'Not specified'}</p>
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Description</h3>
                <p className="text-gray-600">{spec.description || 'Not specified'}</p>
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Type</h3>
                <p className="text-gray-600">{systemTypes.find(t => t.id === spec.type)?.name}</p>
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Tech Stack</h3>
                <div className="flex flex-wrap gap-2 mt-1">
                  {spec.techStack.map((tech) => (
                    <span key={tech} className="px-2 py-1 bg-sbh-100 text-sbh-700 rounded text-sm">
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Features</h3>
                <div className="flex flex-wrap gap-2 mt-1">
                  {spec.features.map((feature) => (
                    <span key={feature} className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Infrastructure</h3>
                <div className="flex flex-wrap gap-2 mt-1">
                  {spec.infrastructure.map((infra) => (
                    <span key={infra} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm">
                      {infra}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Generated System Display */}
            {generatedSystem && (
              <div className="space-y-6">
                <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                  <h3 className="font-medium text-green-900 mb-4 flex items-center">
                    <CheckCircle className="w-5 h-5 mr-2" />
                    System Generated Successfully!
                  </h3>
                  <div className="space-y-2 text-sm">
                    <p><strong>System ID:</strong> {generatedSystem.systemId}</p>
                    <p><strong>Components:</strong> {generatedSystem.architecture.components.length}</p>
                    <p><strong>Templates:</strong> {Object.keys(generatedSystem.templates).length}</p>
                    <p><strong>Infrastructure Services:</strong> {generatedSystem.deployment.services.length}</p>
                  </div>
                  <div className="flex space-x-3 mt-4">
                    <button
                      onClick={downloadSystem}
                      className="btn-secondary flex items-center space-x-2"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download System</span>
                    </button>
                  </div>
                </div>

                {/* Deployment Section */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                  <h3 className="font-medium text-blue-900 mb-4 flex items-center">
                    <Globe className="w-5 h-5 mr-2" />
                    Deploy to Cloud
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Domain Name
                      </label>
                      <div className="flex space-x-3">
                        <input
                          type="text"
                          value={deploymentDomain}
                          onChange={(e) => setDeploymentDomain(e.target.value)}
                          onBlur={() => deploymentDomain && validateDomain(deploymentDomain)}
                          placeholder="e.g., myapp.com or myapp.sbh.umbervale.com"
                          className="input-field flex-1"
                        />
                        {isValidatingDomain && (
                          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mt-2" />
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Deployment Type
                      </label>
                      <select
                        value={deploymentType}
                        onChange={(e) => setDeploymentType(e.target.value)}
                        className="input-field"
                      >
                        <option value="preview">Preview (for testing)</option>
                        <option value="production">Production (live system)</option>
                      </select>
                    </div>

                    {/* Domain Validation Results */}
                    {domainValidation && (
                      <div className={`p-4 rounded-lg border ${
                        domainValidation.success 
                          ? 'bg-green-50 border-green-200' 
                          : 'bg-red-50 border-red-200'
                      }`}>
                        <div className="flex items-start">
                          {domainValidation.success ? (
                            <CheckCircle className="w-5 h-5 text-green-600 mr-2 mt-0.5" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-600 mr-2 mt-0.5" />
                          )}
                          <div className="flex-1">
                            <h4 className={`font-medium ${
                              domainValidation.success ? 'text-green-900' : 'text-red-900'
                            }`}>
                              {domainValidation.success ? 'Domain Valid' : 'Domain Invalid'}
                            </h4>
                            {domainValidation.success ? (
                              <div className="mt-2">
                                <p className="text-sm text-green-700">
                                  <strong>Type:</strong> {domainValidation.domain_type}
                                </p>
                                <p className="text-sm text-green-700">
                                  <strong>Strategy:</strong> {domainValidation.strategy.setup_instructions}
                                </p>
                                {domainValidation.setup_instructions.steps && domainValidation.setup_instructions.steps.length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-sm font-medium text-green-800">Setup Steps:</p>
                                    <ul className="text-sm text-green-700 mt-1 space-y-1">
                                      {domainValidation.setup_instructions.steps.map((step: string, index: number) => (
                                        <li key={index}>{step}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <p className="text-sm text-red-700 mt-1">
                                {domainValidation.error}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Deployment Button */}
                    <button
                      onClick={() => deployToCloud(generatedSystem.systemId)}
                      disabled={isDeploying || !deploymentDomain.trim() || !domainValidation?.success}
                      className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isDeploying ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          <span>Deploying...</span>
                        </>
                      ) : (
                        <>
                          <Cloud className="w-4 h-4" />
                          <span>Deploy to Cloud</span>
                        </>
                      )}
                    </button>

                    {/* Deployment Result */}
                    {deploymentResult && (
                      <div className={`p-4 rounded-lg border ${
                        deploymentResult.success 
                          ? 'bg-green-50 border-green-200' 
                          : 'bg-red-50 border-red-200'
                      }`}>
                        <div className="flex items-start">
                          {deploymentResult.success ? (
                            <CheckCircle className="w-5 h-5 text-green-600 mr-2 mt-0.5" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-600 mr-2 mt-0.5" />
                          )}
                          <div className="flex-1">
                            <h4 className={`font-medium ${
                              deploymentResult.success ? 'text-green-900' : 'text-red-900'
                            }`}>
                              {deploymentResult.success ? 'Deployment Successful!' : 'Deployment Failed'}
                            </h4>
                            {deploymentResult.success ? (
                              <div className="mt-2 space-y-2">
                                <p className="text-sm text-green-700">
                                  <strong>Live URL:</strong> 
                                  <a 
                                    href={deploymentResult.live_url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="ml-1 text-green-600 hover:text-green-800 underline flex items-center"
                                  >
                                    {deploymentResult.live_url}
                                    <ExternalLink className="w-3 h-3 ml-1" />
                                  </a>
                                </p>
                                <p className="text-sm text-green-700">
                                  <strong>Deployment ID:</strong> {deploymentResult.deployment_id}
                                </p>
                                <p className="text-sm text-green-700">
                                  <strong>Domain Type:</strong> {deploymentResult.domain_type}
                                </p>
                                <p className="text-sm text-green-700">
                                  <strong>Status:</strong> {deploymentResult.status}
                                </p>
                              </div>
                            ) : (
                              <p className="text-sm text-red-700 mt-1">
                                {deploymentResult.error}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between pt-6 border-t border-gray-200">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 1}
            className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          {currentStep < 5 ? (
            <button
              onClick={handleNext}
              className="btn-primary"
            >
              Next
            </button>
          ) : (
            <button
              onClick={generateSystem}
              disabled={isGenerating}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Generate System</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
