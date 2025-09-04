import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent } from '../utils/analytics';
import { canCreate } from '../utils/rbac';
import { 
  Building, 
  Users, 
  CreditCard, 
  Upload, 
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Plus,
  Trash2
} from 'lucide-react';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  component: React.ComponentType<OnboardingStepProps>;
}

interface OnboardingStepProps {
  data: any;
  onUpdate: (data: any) => void;
  onNext: () => void;
  onBack: () => void;
}

const CompanyProfileStep: React.FC<OnboardingStepProps> = ({ data, onUpdate, onNext }) => {
  const [formData, setFormData] = useState({
    company_name: data.company_name || '',
    brand_color: data.brand_color || '#3B82F6'
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdate(formData);
    onNext();
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <Building className="h-12 w-12 mx-auto text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Company Profile</h2>
        <p className="text-gray-600 mt-2">Let's start by setting up your company information</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Company Name *
          </label>
          <input
            type="text"
            required
            value={formData.company_name}
            onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter your company name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Brand Color
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="color"
              value={formData.brand_color}
              onChange={(e) => setFormData({ ...formData, brand_color: e.target.value })}
              className="h-10 w-20 border border-gray-300 rounded-md"
            />
            <span className="text-sm text-gray-600">{formData.brand_color}</span>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!formData.company_name.trim()}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue
            <ArrowRight className="h-4 w-4 ml-2" />
          </button>
        </div>
      </form>
    </div>
  );
};

const InviteTeamStep: React.FC<OnboardingStepProps> = ({ data, onUpdate, onNext, onBack }) => {
  const [invitedUsers, setInvitedUsers] = useState(data.invited_users || []);

  const addUser = () => {
    setInvitedUsers([...invitedUsers, { email: '', role: 'member' }]);
  };

  const removeUser = (index: number) => {
    setInvitedUsers(invitedUsers.filter((_, i) => i !== index));
  };

  const updateUser = (index: number, field: string, value: string) => {
    const updated = [...invitedUsers];
    updated[index] = { ...updated[index], [field]: value };
    setInvitedUsers(updated);
  };

  const handleNext = () => {
    onUpdate({ invited_users: invitedUsers });
    onNext();
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <Users className="h-12 w-12 mx-auto text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Invite Your Team</h2>
        <p className="text-gray-600 mt-2">Invite team members to collaborate on your CRM</p>
      </div>

      <div className="space-y-6">
        {invitedUsers.map((user, index) => (
          <div key={index} className="flex items-center space-x-4 p-4 border border-gray-200 rounded-lg">
            <div className="flex-1 space-y-3">
              <input
                type="email"
                placeholder="Email address"
                value={user.email}
                onChange={(e) => updateUser(index, 'email', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <select
                value={user.role}
                onChange={(e) => updateUser(index, 'role', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <button
              onClick={() => removeUser(index)}
              className="p-2 text-red-600 hover:text-red-800"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}

        <button
          onClick={addUser}
          className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-gray-400 hover:text-gray-800"
        >
          <Plus className="h-4 w-4 mx-auto mb-1" />
          Add Team Member
        </button>

        <div className="flex justify-between">
          <button
            onClick={onBack}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </button>
          <button
            onClick={handleNext}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Continue
            <ArrowRight className="h-4 w-4 ml-2" />
          </button>
        </div>
      </div>
    </div>
  );
};

const PlanSelectionStep: React.FC<OnboardingStepProps> = ({ data, onUpdate, onNext, onBack }) => {
  const [selectedPlan, setSelectedPlan] = useState(data.selected_plan || 'starter');

  const plans = [
    {
      id: 'starter',
      name: 'Starter',
      price: '$29',
      features: ['Up to 1,000 contacts', 'Basic analytics', 'Email support']
    },
    {
      id: 'professional',
      name: 'Professional',
      price: '$99',
      features: ['Up to 10,000 contacts', 'Advanced analytics', 'Priority support', 'Custom integrations']
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 'Custom',
      features: ['Unlimited contacts', 'Full analytics suite', 'Dedicated support', 'Custom development']
    }
  ];

  const handleNext = () => {
    onUpdate({ selected_plan: selectedPlan });
    onNext();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <CreditCard className="h-12 w-12 mx-auto text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Choose Your Plan</h2>
        <p className="text-gray-600 mt-2">Select the plan that best fits your needs</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {plans.map((plan) => (
          <div
            key={plan.id}
            onClick={() => setSelectedPlan(plan.id)}
            className={`p-6 border rounded-lg cursor-pointer transition-colors ${
              selectedPlan === plan.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
            <p className="text-2xl font-bold text-blue-600 mt-2">{plan.price}</p>
            <ul className="mt-4 space-y-2">
              {plan.features.map((feature, index) => (
                <li key={index} className="text-sm text-gray-600 flex items-center">
                  <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </button>
        <button
          onClick={handleNext}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Continue
          <ArrowRight className="h-4 w-4 ml-2" />
        </button>
      </div>
    </div>
  );
};

const ImportDataStep: React.FC<OnboardingStepProps> = ({ data, onUpdate, onNext, onBack }) => {
  const [importType, setImportType] = useState(data.import_data_type || 'demo');

  const handleNext = () => {
    onUpdate({ import_data_type: importType });
    onNext();
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <Upload className="h-12 w-12 mx-auto text-blue-600 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900">Import Your Data</h2>
        <p className="text-gray-600 mt-2">Choose how you'd like to get started</p>
      </div>

      <div className="space-y-4 mb-8">
        <div
          onClick={() => setImportType('demo')}
          className={`p-6 border rounded-lg cursor-pointer transition-colors ${
            importType === 'demo'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <h3 className="text-lg font-semibold text-gray-900">Load Demo Data</h3>
          <p className="text-gray-600 mt-2">
            Get started with sample contacts, deals, and projects to explore the platform
          </p>
        </div>

        <div
          onClick={() => setImportType('csv')}
          className={`p-6 border rounded-lg cursor-pointer transition-colors ${
            importType === 'csv'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <h3 className="text-lg font-semibold text-gray-900">Import CSV</h3>
          <p className="text-gray-600 mt-2">
            Upload a CSV file with your existing contacts and data
          </p>
        </div>

        <div
          onClick={() => setImportType('skip')}
          className={`p-6 border rounded-lg cursor-pointer transition-colors ${
            importType === 'skip'
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <h3 className="text-lg font-semibold text-gray-900">Start Fresh</h3>
          <p className="text-gray-600 mt-2">
            Begin with an empty workspace and add data as you go
          </p>
        </div>
      </div>

      <div className="flex justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </button>
        <button
          onClick={handleNext}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Continue
          <ArrowRight className="h-4 w-4 ml-2" />
        </button>
      </div>
    </div>
  );
};

const FinishStep: React.FC<OnboardingStepProps> = ({ data, onComplete }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleComplete = async () => {
    setIsLoading(true);
    try {
      // Complete onboarding
      await fetch('/api/onboarding/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'X-Tenant-Slug': localStorage.getItem('tenant_slug') || ''
        }
      });

      // Load demo data if selected
      if (data.import_data_type === 'demo') {
        await fetch('/api/admin/demo-seed', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'X-Tenant-Slug': localStorage.getItem('tenant_slug') || ''
          },
          body: JSON.stringify({
            contacts: 20,
            deals: 5,
            projects: 2,
            tasks_per_project: 8
          })
        });
      }

      trackEvent('onboarding.completed', {
        import_type: data.import_data_type,
        selected_plan: data.selected_plan
      });

      onComplete();
    } catch (error) {
      console.error('Error completing onboarding:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto text-center">
      <CheckCircle className="h-16 w-16 mx-auto text-green-600 mb-6" />
      <h2 className="text-2xl font-bold text-gray-900 mb-4">You're All Set!</h2>
      <p className="text-gray-600 mb-8">
        Your CRM/Ops workspace is ready. You can now start managing your contacts, deals, and projects.
      </p>

      <div className="bg-gray-50 rounded-lg p-6 mb-8">
        <h3 className="font-semibold text-gray-900 mb-4">What's Next?</h3>
        <ul className="text-left space-y-2 text-sm text-gray-600">
          <li>• Explore your dashboard to see key metrics</li>
          <li>• Add your first contact or deal</li>
          <li>• Invite team members to collaborate</li>
          <li>• Customize your workspace settings</li>
        </ul>
      </div>

      <button
        onClick={handleComplete}
        disabled={isLoading}
        className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Setting up...' : 'Get Started'}
      </button>
    </div>
  );
};

const steps: OnboardingStep[] = [
  {
    id: 'company_profile',
    title: 'Company Profile',
    description: 'Set up your company information',
    component: CompanyProfileStep
  },
  {
    id: 'invite_team',
    title: 'Invite Team',
    description: 'Invite team members',
    component: InviteTeamStep
  },
  {
    id: 'plan_selection',
    title: 'Choose Plan',
    description: 'Select your subscription plan',
    component: PlanSelectionStep
  },
  {
    id: 'import_data',
    title: 'Import Data',
    description: 'Import your existing data',
    component: ImportDataStep
  },
  {
    id: 'finish',
    title: 'Complete',
    description: 'Finish setup',
    component: FinishStep
  }
];

export default function OnboardingWizard() {
  const [currentStep, setCurrentStep] = useState(0);
  const [onboardingData, setOnboardingData] = useState({});
  const [isCompleted, setIsCompleted] = useState(false);

  const { data: status, error, isLoading } = useApi('/onboarding/status');

  useEffect(() => {
    if (status?.data?.attributes?.completed) {
      setIsCompleted(true);
    }
  }, [status]);

  const handleStepUpdate = (stepData: any) => {
    setOnboardingData({ ...onboardingData, ...stepData });
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    setIsCompleted(true);
    // Redirect to dashboard
    window.location.href = '/ui/dashboard';
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage error={error} />;
  }

  if (isCompleted) {
    return null; // Will redirect to dashboard
  }

  const currentStepData = steps[currentStep];
  const StepComponent = currentStepData.component;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Progress bar */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      index <= currentStep
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    {index + 1}
                  </div>
                  {index < steps.length - 1 && (
                    <div
                      className={`w-16 h-1 mx-2 ${
                        index < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="text-sm text-gray-600">
              Step {currentStep + 1} of {steps.length}
            </div>
          </div>
        </div>
      </div>

      {/* Step content */}
      <div className="max-w-4xl mx-auto px-4 py-12">
        <StepComponent
          data={onboardingData}
          onUpdate={handleStepUpdate}
          onNext={handleNext}
          onBack={handleBack}
          onComplete={handleComplete}
        />
      </div>
    </div>
  );
}
