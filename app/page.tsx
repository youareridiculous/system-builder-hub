'use client';

import { useState } from 'react';
import { useAuth } from '@/components/SimpleAuthProvider';
import LoginForm from '@/components/LoginForm';
import { ModelSelector } from '@/components/ModelSelector';
import SystemBuilder from '@/components/SystemBuilder';
import { ChatInterface } from '@/components/ChatInterface';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'builder'>('chat');
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const { isAuthenticated, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sbh-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sbh-50 to-blue-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-sbh-600 rounded-lg flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-white">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">System Builder Hub</h1>
                <p className="text-sm text-gray-500">AI-powered system generation</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <ModelSelector selectedModel={selectedModel} onModelChange={setSelectedModel} />
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'chat'
                      ? 'bg-white text-sbh-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 inline mr-1">
                    <path d="M12 8V4H8"></path>
                    <rect width="16" height="12" x="4" y="8" rx="2"></rect>
                    <path d="M2 14h2"></path>
                    <path d="M20 14h2"></path>
                    <path d="M15 13v2"></path>
                    <path d="M9 13v2"></path>
                  </svg>
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
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 inline mr-1">
                    <polyline points="16 18 22 12 16 6"></polyline>
                    <polyline points="8 6 2 12 8 18"></polyline>
                  </svg>
                  Builder
                </button>
              </div>
              <button
                onClick={logout}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'chat' ? (
          <ChatInterface selectedModel={selectedModel} />
        ) : (
          <SystemBuilder />
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 text-sm">
            <p>System Builder Hub - Better than Cursor for complete system generation</p>
            <p className="mt-2">Powered by AI • Deployed on AWS • Ready for production</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
