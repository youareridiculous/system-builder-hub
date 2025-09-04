import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './Card';
import { Button } from './Button';
import { Badge } from './Badge';
import { CheckCircle, X, Settings, Users, Mail, Target, Zap } from 'lucide-react';
import { api } from '../lib/api';

interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  icon: React.ReactNode;
  action?: () => void;
}

interface FirstRunChecklistProps {
  onDismiss: () => void;
}

export function FirstRunChecklist({ onDismiss }: FirstRunChecklistProps) {
  const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([
    {
      id: 'branding',
      title: 'Set Branding',
      description: 'Customize your company name, logo, and colors',
      completed: false,
      icon: <Settings className="w-4 h-4" />
    },
    {
      id: 'providers',
      title: 'Configure Providers',
      description: 'Set up email and SMS providers (or keep Mock mode)',
      completed: false,
      icon: <Mail className="w-4 h-4" />
    },
    {
      id: 'users',
      title: 'Invite Users',
      description: 'Add team members and assign roles',
      completed: false,
      icon: <Users className="w-4 h-4" />
    },
    {
      id: 'contacts',
      title: 'Create First Contact',
      description: 'Add your first contact to get started',
      completed: false,
      icon: <Users className="w-4 h-4" />
    },
    {
      id: 'communications',
      title: 'Send First Communication',
      description: 'Test your communication setup',
      completed: false,
      icon: <Mail className="w-4 h-4" />
    },
    {
      id: 'automations',
      title: 'Set Up Automations',
      description: 'Create automation rules to streamline workflows',
      completed: false,
      icon: <Zap className="w-4 h-4" />
    }
  ]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkCompletionStatus();
  }, []);

  const checkCompletionStatus = async () => {
    try {
      // Check if contacts exist
      const contactsResponse = await api.get('/api/contacts/?limit=1');
      if (contactsResponse && contactsResponse.length > 0) {
        updateItemStatus('contacts', true);
      }

      // Check if communications exist
      const commsResponse = await api.get('/api/communications/history?limit=1');
      if (commsResponse && commsResponse.length > 0) {
        updateItemStatus('communications', true);
      }

      // Check if automations exist
      const automationsResponse = await api.get('/api/automations/');
      if (automationsResponse && automationsResponse.length > 0) {
        updateItemStatus('automations', true);
      }

      // Check branding (tenant configs)
      const brandingResponse = await api.get('/api/settings/branding');
      if (brandingResponse.tenant_name && brandingResponse.tenant_name !== 'Demo CRM') {
        updateItemStatus('branding', true);
      }

      // Check providers
      const providersResponse = await api.get('/api/settings/provider-status');
      if (providersResponse.email?.configured || providersResponse.sms?.configured) {
        updateItemStatus('providers', true);
      }

      setLoading(false);
    } catch (error) {
      console.error('Error checking completion status:', error);
      setLoading(false);
    }
  };

  const updateItemStatus = (itemId: string, completed: boolean) => {
    setChecklistItems(prev => 
      prev.map(item => 
        item.id === itemId ? { ...item, completed } : item
      )
    );
  };

  const markItemComplete = async (itemId: string) => {
    updateItemStatus(itemId, true);
    
    // Save completion status to backend
    try {
      await api.post('/api/settings/checklist-complete', {
        item_id: itemId,
        completed: true
      });
    } catch (error) {
      console.error('Error saving checklist status:', error);
    }
  };

  const completedCount = checklistItems.filter(item => item.completed).length;
  const totalCount = checklistItems.length;

  if (loading) {
    return (
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-3 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mb-6 border-blue-200 bg-blue-50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Welcome to CRM Flagship! 🎉</CardTitle>
            <CardDescription>
              Complete these steps to get your CRM up and running
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="secondary">
              {completedCount}/{totalCount} Complete
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDismiss}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {checklistItems.map((item) => (
            <div
              key={item.id}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                item.completed 
                  ? 'bg-green-50 border-green-200' 
                  : 'bg-white border-gray-200'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-full ${
                  item.completed ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'
                }`}>
                  {item.completed ? <CheckCircle className="w-4 h-4" /> : item.icon}
                </div>
                <div>
                  <h4 className={`font-medium ${
                    item.completed ? 'text-green-800 line-through' : 'text-gray-900'
                  }`}>
                    {item.title}
                  </h4>
                  <p className={`text-sm ${
                    item.completed ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {item.description}
                  </p>
                </div>
              </div>
              {!item.completed && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markItemComplete(item.id)}
                >
                  Mark Complete
                </Button>
              )}
            </div>
          ))}
        </div>
        
        {completedCount === totalCount && (
          <div className="mt-4 p-4 bg-green-100 border border-green-200 rounded-lg">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="font-medium text-green-800">
                All setup steps completed! Your CRM is ready to go.
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
