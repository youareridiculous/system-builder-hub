import React, { useState, useEffect } from "react";
import { useToast } from "../contexts/ToastContext";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/Card";
import { Badge } from "../components/Badge";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow,
  TableEmptyState
} from "../components/Table";
import { 
  AlertTriangle,
  CheckCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
  Eye,
  Play
} from 'lucide-react';
import { WebhooksFilters } from '../components/webhooks/WebhooksFilters';
import { PayloadModal } from '../components/webhooks/PayloadModal';

export default function Webhooks() {
  const { showToast } = useToast();
  const { hasPermission } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    provider: '',
    event_type: '',
    status: '',
    from_date: '',
    to_date: '',
    search: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedPayload, setSelectedPayload] = useState(null);
  const [payloadModalOpen, setPayloadModalOpen] = useState(false);

  useEffect(() => {
    if (hasPermission("webhooks.read")) {
      fetchEvents();
    }
  }, [filters, currentPage]);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      params.append('page', currentPage.toString());
      params.append('limit', '25');
      
      const response = await api.get(`/webhooks/events?${params.toString()}`);
      setEvents(response.events || []);
      setTotalPages(response.total_pages || 1);
    } catch (error) {
      showToast("Failed to fetch webhook events", "error");
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  const handleClearFilters = () => {
    setFilters({
      provider: '',
      event_type: '',
      status: '',
      from_date: '',
      to_date: '',
      search: ''
    });
    setCurrentPage(1);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const handleViewPayload = (event) => {
    setSelectedPayload(event);
    setPayloadModalOpen(true);
  };

  const handleReplay = async (eventId) => {
    if (!hasPermission('webhooks.replay')) {
      showToast('You don\'t have permission to replay webhooks', 'error');
      return;
    }

    try {
      await api.post(`/webhooks/events/${eventId}/replay`);
      showToast('Webhook replayed successfully', 'success');
      fetchEvents(); // Refresh the list
    } catch (error) {
      showToast('Failed to replay webhook', 'error');
    }
  };

  if (!hasPermission("webhooks.read")) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-gray-500">You don't have permission to view webhooks.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Webhooks Console</h1>
        <p className="text-gray-600">Monitor webhook events from communication providers</p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <WebhooksFilters 
            filters={filters}
            onFilterChange={handleFilterChange}
            onClearFilters={handleClearFilters}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Webhook Events</CardTitle>
          <CardDescription>Recent webhook events from communication providers</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Event Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Communication ID</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  </TableCell>
                </TableRow>
              ) : events.length === 0 ? (
                <TableEmptyState message="No webhook events found">
                  <p className="text-sm text-gray-500 mt-2">
                    Configure your communication providers to start receiving webhook events.
                  </p>
                </TableEmptyState>
              ) : (
                events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>
                      <div className="text-sm">
                        {new Date(event.created_at).toLocaleString()}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{event.provider}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">{event.event_type}</div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(event.status)}
                        <Badge className={
                          event.status === 'success' ? 'bg-green-100 text-green-800' :
                          event.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }>
                          {event.status}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-600">
                        {event.communication_id || '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewPayload(event)}
                        >
                          <Eye className="w-3 h-3 mr-1" />
                          View
                        </Button>
                        {hasPermission('webhooks.replay') && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReplay(event.id)}
                          >
                            <Play className="w-3 h-3 mr-1" />
                            Replay
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          
          {/* Pagination */}
          {events.length > 0 && (
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-gray-500">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payload Modal */}
      <PayloadModal
        isOpen={payloadModalOpen}
        onClose={() => setPayloadModalOpen(false)}
        payload={selectedPayload?.raw_payload}
        eventId={selectedPayload?.id}
      />
    </div>
  );
}
