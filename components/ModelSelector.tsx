'use client'

import { useState } from 'react'
import { ChevronDown, Zap, Clock, Star } from 'lucide-react'

interface ModelSelectorProps {
  selectedModel: string
  onModelChange: (model: string) => void
}

const models = [
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    description: 'Fast & Cost-effective',
    icon: Clock,
    color: 'text-green-600'
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    description: 'Best Quality (Default)',
    icon: Star,
    color: 'text-blue-600'
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    description: 'Balanced Performance',
    icon: Zap,
    color: 'text-purple-600'
  }
]

export function ModelSelector({ selectedModel, onModelChange }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  
  const selectedModelData = models.find(m => m.id === selectedModel) || models[1]

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
      >
        <selectedModelData.icon className={`w-4 h-4 ${selectedModelData.color}`} />
        <span className="text-sm font-medium text-gray-700">{selectedModelData.name}</span>
        <ChevronDown className="w-4 h-4 text-gray-400" />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                AI Model Selection
              </div>
              {models.map((model) => {
                const Icon = model.icon
                return (
                  <button
                    key={model.id}
                    onClick={() => {
                      onModelChange(model.id)
                      setIsOpen(false)
                    }}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-left transition-colors ${
                      selectedModel === model.id
                        ? 'bg-sbh-50 text-sbh-700'
                        : 'hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${model.color}`} />
                    <div>
                      <div className="text-sm font-medium">{model.name}</div>
                      <div className="text-xs text-gray-500">{model.description}</div>
                    </div>
                    {selectedModel === model.id && (
                      <div className="ml-auto w-2 h-2 bg-sbh-600 rounded-full" />
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
