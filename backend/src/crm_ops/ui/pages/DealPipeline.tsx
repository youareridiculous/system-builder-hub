import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent, AnalyticsEvents } from '../utils/analytics';
import { canCreate, canUpdate } from '../utils/rbac';
import { 
  Plus, 
  DollarSign, 
  Calendar,
  User,
  ChevronRight,
  MoreVertical
} from 'lucide-react';

interface Deal {
  id: string;
  type: string;
  attributes: {
    title: string;
    value: number;
    pipeline_stage: string;
    status: string;
    expected_close_date: string;
    contact_id: string;
    created_at: string;
  };
}

interface DealCardProps {
  deal: Deal;
  onEdit: (deal: Deal) => void;
  onMove: (dealId: string, newStage: string) => void;
}

const DealCard: React.FC<DealCardProps> = ({ deal, onEdit, onMove }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'prospecting': return 'bg-gray-100 text-gray-800';
      case 'qualification': return 'bg-blue-100 text-blue-800';
      case 'proposal': return 'bg-yellow-100 text-yellow-800';
      case 'negotiation': return 'bg-purple-100 text-purple-800';
      case 'closed_won': return 'bg-green-100 text-green-800';
      case 'closed_lost': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'bg-blue-100 text-blue-800';
      case 'won': return 'bg-green-100 text-green-800';
      case 'lost': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-3 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-medium text-gray-900 text-sm line-clamp-2">
          {deal.attributes.title}
        </h3>
        <div className="relative">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="text-gray-400 hover:text-gray-600"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          {isMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border border-gray-200">
              <div className="py-1">
                <button
                  onClick={() => {
                    onEdit(deal);
                    setIsMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Edit Deal
                </button>
                <button
                  onClick={() => {
                    onMove(deal.id, 'closed_won');
                    setIsMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-green-700 hover:bg-gray-100"
                >
                  Mark as Won
                </button>
                <button
                  onClick={() => {
                    onMove(deal.id, 'closed_lost');
                    setIsMenuOpen(false);
                  }}
                  className="block w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-gray-100"
                >
                  Mark as Lost
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center text-sm text-gray-600">
            <DollarSign className="h-4 w-4 mr-1" />
            ${deal.attributes.value?.toLocaleString() || 0}
          </div>
          <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(deal.attributes.status)}`}>
            {deal.attributes.status}
          </span>
        </div>

        {deal.attributes.expected_close_date && (
          <div className="flex items-center text-sm text-gray-600">
            <Calendar className="h-4 w-4 mr-1" />
            {new Date(deal.attributes.expected_close_date).toLocaleDateString()}
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <span className={`px-2 py-1 text-xs rounded-full ${getStageColor(deal.attributes.pipeline_stage)}`}>
            {deal.attributes.pipeline_stage.replace('_', ' ')}
          </span>
          <div className="flex items-center text-xs text-gray-500">
            <User className="h-3 w-3 mr-1" />
            Contact
          </div>
        </div>
      </div>
    </div>
  );
};

interface PipelineColumnProps {
  title: string;
  stage: string;
  deals: Deal[];
  onEdit: (deal: Deal) => void;
  onMove: (dealId: string, newStage: string) => void;
  onAddDeal: (stage: string) => void;
}

const PipelineColumn: React.FC<PipelineColumnProps> = ({
  title,
  stage,
  deals,
  onEdit,
  onMove,
  onAddDeal
}) => {
  const getColumnColor = (stage: string) => {
    switch (stage) {
      case 'prospecting': return 'border-gray-300';
      case 'qualification': return 'border-blue-300';
      case 'proposal': return 'border-yellow-300';
      case 'negotiation': return 'border-purple-300';
      case 'closed_won': return 'border-green-300';
      case 'closed_lost': return 'border-red-300';
      default: return 'border-gray-300';
    }
  };

  return (
    <div className={`flex-shrink-0 w-80 bg-gray-50 rounded-lg p-4 border-2 ${getColumnColor(stage)}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <span className="bg-white px-2 py-1 rounded-full text-xs font-medium text-gray-600">
          {deals.length}
        </span>
      </div>
      
      <div className="space-y-3">
        {deals.map((deal) => (
          <DealCard
            key={deal.id}
            deal={deal}
            onEdit={onEdit}
            onMove={onMove}
          />
        ))}
        
        {canCreate('deals') && (
          <button
            onClick={() => onAddDeal(stage)}
            className="w-full p-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
          >
            <Plus className="h-5 w-5 mx-auto mb-1" />
            <span className="text-sm">Add Deal</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default function DealPipeline() {
  const { data, error, isLoading, refetch } = useApi('/deals');
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);

  const handleEditDeal = (deal: Deal) => {
    setSelectedDeal(deal);
    trackEvent(AnalyticsEvents.DEAL_UPDATED, { dealId: deal.id });
    // Open edit modal or guided prompt
    console.log('Opening edit deal guided prompt');
  };

  const handleMoveDeal = (dealId: string, newStage: string) => {
    trackEvent(AnalyticsEvents.DEAL_STAGE_CHANGED, { dealId, newStage });
    // Update deal stage via API
    console.log('Moving deal', dealId, 'to stage', newStage);
  };

  const handleAddDeal = (stage: string) => {
    trackEvent(AnalyticsEvents.DEAL_CREATED, { stage });
    // Open add deal guided prompt
    console.log('Opening add deal guided prompt for stage:', stage);
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  const deals = data?.data || [];
  
  const pipelineStages = [
    { key: 'prospecting', title: 'Prospecting' },
    { key: 'qualification', title: 'Qualification' },
    { key: 'proposal', title: 'Proposal' },
    { key: 'negotiation', title: 'Negotiation' },
    { key: 'closed_won', title: 'Closed Won' },
    { key: 'closed_lost', title: 'Closed Lost' }
  ];

  const dealsByStage = pipelineStages.reduce((acc, stage) => {
    acc[stage.key] = deals.filter((deal: Deal) => 
      deal.attributes.pipeline_stage === stage.key
    );
    return acc;
  }, {} as Record<string, Deal[]>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Deal Pipeline</h1>
          <p className="text-gray-600">Track your sales opportunities through the pipeline</p>
        </div>
        {canCreate('deals') && (
          <button
            onClick={() => handleAddDeal('prospecting')}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Deal
          </button>
        )}
      </div>

      {/* Pipeline Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Summary</h2>
        <div className="grid grid-cols-6 gap-4">
          {pipelineStages.map((stage) => (
            <div key={stage.key} className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {dealsByStage[stage.key]?.length || 0}
              </div>
              <div className="text-sm text-gray-600">{stage.title}</div>
              {dealsByStage[stage.key]?.length > 0 && (
                <div className="text-xs text-gray-500">
                  ${dealsByStage[stage.key].reduce((sum, deal) => sum + (deal.attributes.value || 0), 0).toLocaleString()}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Kanban Board */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex space-x-6 overflow-x-auto pb-4">
          {pipelineStages.map((stage) => (
            <PipelineColumn
              key={stage.key}
              title={stage.title}
              stage={stage.key}
              deals={dealsByStage[stage.key] || []}
              onEdit={handleEditDeal}
              onMove={handleMoveDeal}
              onAddDeal={handleAddDeal}
            />
          ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <DollarSign className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Pipeline Value</p>
              <p className="text-2xl font-bold text-gray-900">
                ${deals.reduce((sum, deal) => sum + (deal.attributes.value || 0), 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Calendar className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Deals Closing This Month</p>
              <p className="text-2xl font-bold text-gray-900">
                {deals.filter((deal: Deal) => {
                  const closeDate = new Date(deal.attributes.expected_close_date);
                  const now = new Date();
                  return closeDate.getMonth() === now.getMonth() && 
                         closeDate.getFullYear() === now.getFullYear();
                }).length}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <User className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Active Deals</p>
              <p className="text-2xl font-bold text-gray-900">
                {deals.filter((deal: Deal) => deal.attributes.status === 'open').length}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
