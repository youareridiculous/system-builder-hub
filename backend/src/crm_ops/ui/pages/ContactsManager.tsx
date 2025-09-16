import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner, SkeletonTable } from '../components/LoadingStates';
import { ErrorMessage, EmptyState } from '../components/ErrorStates';
import { trackEvent, AnalyticsEvents } from '../utils/analytics';
import { canCreate, canUpdate, canDelete } from '../utils/rbac';
import { 
  Search, 
  Filter, 
  Plus, 
  Edit, 
  Trash2, 
  Eye,
  Download,
  Upload,
  Mail,
  Phone
} from 'lucide-react';

interface Contact {
  id: string;
  type: string;
  attributes: {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    company: string;
    tags: string[];
    custom_fields: Record<string, any>;
    created_at: string;
  };
}

interface ContactDetailProps {
  contact: Contact | null;
  isOpen: boolean;
  onClose: () => void;
}

const ContactDetail: React.FC<ContactDetailProps> = ({ contact, isOpen, onClose }) => {
  if (!contact || !isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              {contact.attributes.first_name} {contact.attributes.last_name}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-6">
            {/* Contact Info */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Contact Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <div className="flex items-center mt-1">
                    <Mail className="h-4 w-4 text-gray-400 mr-2" />
                    <span className="text-gray-900">{contact.attributes.email || 'Not provided'}</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Phone</label>
                  <div className="flex items-center mt-1">
                    <Phone className="h-4 w-4 text-gray-400 mr-2" />
                    <span className="text-gray-900">{contact.attributes.phone || 'Not provided'}</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Company</label>
                  <span className="text-gray-900">{contact.attributes.company || 'Not provided'}</span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Created</label>
                  <span className="text-gray-900">
                    {new Date(contact.attributes.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Tags */}
            {contact.attributes.tags && contact.attributes.tags.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {contact.attributes.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Custom Fields */}
            {contact.attributes.custom_fields && Object.keys(contact.attributes.custom_fields).length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Custom Fields</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(contact.attributes.custom_fields).map(([key, value]) => (
                    <div key={key}>
                      <label className="block text-sm font-medium text-gray-700 capitalize">
                        {key.replace('_', ' ')}
                      </label>
                      <span className="text-gray-900">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end space-x-3 pt-6 border-t">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Close
              </button>
              {canUpdate('contacts') && (
                <button
                  onClick={() => {
                    trackEvent(AnalyticsEvents.CONTACT_VIEWED, { contactId: contact.id });
                    onClose();
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Edit Contact
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function ContactsManager() {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const { data, error, isLoading, refetch } = useApi('/contacts');

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    trackEvent('ui.contacts.search', { term: value });
  };

  const handleViewContact = (contact: Contact) => {
    setSelectedContact(contact);
    setIsDetailOpen(true);
    trackEvent(AnalyticsEvents.CONTACT_VIEWED, { contactId: contact.id });
  };

  const handleEditContact = (contact: Contact) => {
    trackEvent(AnalyticsEvents.CONTACT_UPDATED, { contactId: contact.id });
    // Open edit modal or guided prompt
    console.log('Opening edit contact guided prompt');
  };

  const handleDeleteContact = (contact: Contact) => {
    if (window.confirm('Are you sure you want to delete this contact?')) {
      trackEvent(AnalyticsEvents.CONTACT_DELETED, { contactId: contact.id });
      // Delete contact via API
      console.log('Deleting contact:', contact.id);
    }
  };

  const handleAddContact = () => {
    trackEvent(AnalyticsEvents.CONTACT_CREATED);
    // Open add contact guided prompt
    console.log('Opening add contact guided prompt');
  };

  const handleImportContacts = () => {
    trackEvent('ui.contacts.import');
    // Open import modal
    console.log('Opening import contacts modal');
  };

  const handleExportContacts = () => {
    trackEvent('ui.contacts.export');
    // Export contacts to CSV
    console.log('Exporting contacts to CSV');
  };

  if (isLoading) {
    return <SkeletonTable />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  const contacts = data?.data || [];
  const filteredContacts = contacts.filter((contact: Contact) => {
    const matchesSearch = 
      contact.attributes.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.attributes.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.attributes.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      contact.attributes.company.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || 
      (statusFilter === 'active' && contact.attributes.tags?.includes('active')) ||
      (statusFilter === 'lead' && contact.attributes.tags?.includes('lead'));

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contacts</h1>
          <p className="text-gray-600">Manage your customer contacts and leads</p>
        </div>
        <div className="flex space-x-3">
          {canCreate('contacts') && (
            <button
              onClick={handleAddContact}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Contact
            </button>
          )}
          <button
            onClick={handleImportContacts}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <Upload className="h-4 w-4 mr-2" />
            Import
          </button>
          <button
            onClick={handleExportContacts}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
          <div className="flex-1 max-w-md">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search contacts..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="lead">Lead</option>
            </select>
          </div>
        </div>
      </div>

      {/* Contacts Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredContacts.length === 0 ? (
          <EmptyState
            title="No contacts found"
            description="Get started by adding your first contact."
            action={
              canCreate('contacts') ? (
                <button
                  onClick={handleAddContact}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Contact
                </button>
              ) : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tags
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredContacts.map((contact: Contact) => (
                  <tr key={contact.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10">
                          <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-sm font-medium text-blue-600">
                              {contact.attributes.first_name[0]}{contact.attributes.last_name[0]}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {contact.attributes.first_name} {contact.attributes.last_name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {contact.attributes.phone || 'No phone'}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {contact.attributes.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {contact.attributes.company || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-wrap gap-1">
                        {contact.attributes.tags?.slice(0, 2).map((tag, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                          >
                            {tag}
                          </span>
                        ))}
                        {contact.attributes.tags && contact.attributes.tags.length > 2 && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            +{contact.attributes.tags.length - 2}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(contact.attributes.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <button
                          onClick={() => handleViewContact(contact)}
                          className="text-blue-600 hover:text-blue-900"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {canUpdate('contacts') && (
                          <button
                            onClick={() => handleEditContact(contact)}
                            className="text-gray-600 hover:text-gray-900"
                            title="Edit contact"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                        )}
                        {canDelete('contacts') && (
                          <button
                            onClick={() => handleDeleteContact(contact)}
                            className="text-red-600 hover:text-red-900"
                            title="Delete contact"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Contact Detail Modal */}
      <ContactDetail
        contact={selectedContact}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedContact(null);
        }}
      />
    </div>
  );
}
