'use client'

import { useState } from 'react'
import { ChatInterface } from '@/components/ChatInterface'
import { SystemBuilder } from '@/components/SystemBuilder'
import { ModelSelector } from '@/components/ModelSelector'
import { Bot, Zap, Cloud, Code } from 'lucide-react'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'builder'>('chat')
  const [selectedModel, setSelectedModel] = useState('gpt-4o')

  return (
    <div className="min-h-screen bg-gradient-to-br from-sbh-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-sbh-600 rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">System Builder Hub</h1>
                <p className="text-sm text-gray-500">AI-powered system generation</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <ModelSelector 
                selectedModel={selectedModel} 
                onModelChange={setSelectedModel} 
              />
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'chat'
                      ? 'bg-white text-sbh-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Bot className="w-4 h-4 inline mr-1" />
                  Chat
                </button>
                <button
                  onClick={() => setActiveTab('builder')}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'builder'
                      ? 'bg-white text-sbh-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Code className="w-4 h-4 inline mr-1" />
                  Builder
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'chat' ? (
          <ChatInterface selectedModel={selectedModel} />
        ) : (
          <SystemBuilder />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 text-sm">
            <p>System Builder Hub - Better than Cursor for complete system generation</p>
            <p className="mt-2">Powered by AI • Deployed on AWS • Ready for production</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
