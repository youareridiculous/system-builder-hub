'use client'

import { useState } from 'react'
import { Code, Database, Cloud, Zap, Settings, Play, Download, Eye } from 'lucide-react'

interface SystemSpec {
  name: string
  description: string
  type: 'web-app' | 'api' | 'data-pipeline' | 'ml-service' | 'microservice'
  techStack: string[]
  features: string[]
  infrastructure: string[]
}

const systemTypes = [
  { id: 'web-app', name: 'Web Application', icon: Code, description: 'Full-stack web app with frontend and backend' },
  { id: 'api', name: 'REST API', icon: Database, description: 'Backend API service with database' },
  { id: 'data-pipeline', name: 'Data Pipeline', icon: Cloud, description: 'ETL pipeline for data processing' },
  { id: 'ml-service', name: 'ML Service', icon: Zap, description: 'Machine learning model serving' },
  { id: 'microservice', name: 'Microservice', icon: Settings, description: 'Containerized microservice' }
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

  const updateSpec = (updates: Partial<SystemSpec>) => {
    setSpec(prev => ({ ...prev, ...updates }))
  }

  const toggleArrayItem = (array: string[], item: string, setter: (items: string[]) => void) => {
    if (array.includes(item)) {
      setter(array.filter(i => i !== item))
    } else {
      setter([...array, item])
    }
  }

  const generateSystem = async () => {
    setIsGenerating(true)
    // TODO: Implement system generation logic
    setTimeout(() => {
      setIsGenerating(false)
      alert('System generation will be implemented in the next phase!')
    }, 2000)
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
                  <Icon className="w-5 h-5" />
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
                System Name
              </label>
              <input
                type="text"
                value={spec.name}
                onChange={(e) => updateSpec({ name: e.target.value })}
                placeholder="e.g., E-commerce Platform"
                className="input-field"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={spec.description}
                onChange={(e) => updateSpec({ description: e.target.value })}
                placeholder="Describe what your system should do..."
                className="input-field"
                rows={4}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                System Type
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
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between pt-6 border-t border-gray-200">
          <button
            onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
            disabled={currentStep === 1}
            className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          {currentStep < 5 ? (
            <button
              onClick={() => setCurrentStep(Math.min(5, currentStep + 1))}
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
