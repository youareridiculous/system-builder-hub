import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api.ts';
import { useToast } from '../contexts/ToastContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Label } from '../components/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/Select';
import { Textarea } from '../components/Textarea';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '../components/Dialog';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '../components/Table';
import { Badge } from '../components/Badge';
import { 
  Phone, 
  Mail, 
  MessageSquare, 
  Plus, 
  Play,
  Pause,
  Clock,
  User,
  Building,
  Volume2
} from 'lucide-react';

interface CommunicationHistory {
  id: number;
  contact_id: number;
  account_id?: number;
  type: string;
  direction: string;
  provider: string;
  provider_message_id?: string;
  subject?: string;
  content?: string;
  duration?: number;
  status: string;
  recording_url?: string;
  created_at: string;
  first_name?: string;
  last_name?: string;
  account_name?: string;
}

interface Contact {
  id: number;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  title?: string;
}

export default function Communications() {
  const { accountId } = useParams();
  const { showToast } = useToast();
  const [communications, setCommunications] = useState<CommunicationHistory[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [showCallModal, setShowCallModal] = useState(false);
  const [showSMSModal, setShowSMSModal] = useState(false);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [filters, setFilters] = useState({
    type: 'all',
    status: 'all',
    contact_id: 'all',
    date_from: '',
    date_to: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(25);
  const [playingRecording, setPlayingRecording] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  // Email form state
  const [emailForm, setEmailForm] = useState({
    to: '',
    subject: '',
    body: '',
    contact_id: ''
  });
  
  // Call form state
  const [callForm, setCallForm] = useState({
    phone_number: '',
    contact_id: ''
  });
  
  // SMS form state
  const [smsForm, setSMSForm] = useState({
    phone_number: '',
    message: '',
    contact_id: ''
  });

  useEffect(() => {
    fetchData();
  }, [accountId, currentPage, filters.type, filters.status, filters.contact_id, filters.date_from, filters.date_to]);

  const fetchData = async () => {
    try {
      // Filter out "all" values and empty strings
      const cleanFilters = Object.fromEntries(
        Object.entries(filters).filter(([key, value]) => value && value !== 'all')
      );
      
      const params = {
        account_id: accountId,
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        ...cleanFilters
      };
      
      console.log('Fetching communications with params:', params);
      
      const [communicationsData, contactsData, accountsData] = await Promise.all([
        api.get('/communications/history', { params }),
        api.get('/contacts/'),
        api.get('/accounts/')
      ]);
      
      setCommunications(communicationsData);
      setContacts(contactsData);
      setAccounts(accountsData);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching data:', err);
      setLoading(false);
    }
  };

  const handleSendEmail = async () => {
    try {
      await api.post('/communications/send-email', {
        to: emailForm.to,
        subject: emailForm.subject,
        body: emailForm.body,
        contact_id: parseInt(emailForm.contact_id)
      });
      
      setShowEmailModal(false);
      setEmailForm({ to: '', subject: '', body: '', contact_id: '' });
      showToast('Email sent successfully!', 'success');
      fetchData(); // Refresh communications
    } catch (err) {
      console.error('Error sending email:', err);
      showToast('Failed to send email. Please try again.', 'error');
    }
  };

  const handleInitiateCall = async () => {
    try {
      await api.post('/communications/initiate-call', {
        phone_number: callForm.phone_number,
        contact_id: parseInt(callForm.contact_id)
      });
      
      setShowCallModal(false);
      setCallForm({ phone_number: '', contact_id: '' });
      showToast('Call initiated successfully!', 'success');
      fetchData(); // Refresh communications
    } catch (err) {
      console.error('Error initiating call:', err);
      showToast('Failed to initiate call. Please try again.', 'error');
    }
  };

  const handleSendSMS = async () => {
    try {
      await api.post('/communications/send-sms', {
        phone_number: smsForm.phone_number,
        message: smsForm.message,
        contact_id: parseInt(smsForm.contact_id)
      });
      
      setShowSMSModal(false);
      setSMSForm({ phone_number: '', message: '', contact_id: '' });
      showToast('SMS sent successfully!', 'success');
      fetchData(); // Refresh communications
    } catch (err) {
      console.error('Error sending SMS:', err);
      showToast('Failed to send SMS. Please try again.', 'error');
    }
  };

  const getStatusBadge = (status: string) => {
    const statusColors = {
      'sent': 'bg-green-100 text-green-800',
      'delivered': 'bg-blue-100 text-blue-800',
      'failed': 'bg-red-100 text-red-800',
      'answered': 'bg-green-100 text-green-800',
      'missed': 'bg-yellow-100 text-yellow-800',
      'initiated': 'bg-gray-100 text-gray-800'
    };
    
    return (
      <Badge className={statusColors[status as keyof typeof statusColors] || 'bg-gray-100 text-gray-800'}>
        {status}
      </Badge>
    );
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'call':
        return <Phone className="w-4 h-4" />;
      case 'email':
        return <Mail className="w-4 h-4" />;
      case 'sms':
        return <MessageSquare className="w-4 h-4" />;
      default:
        return <MessageSquare className="w-4 h-4" />;
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const handlePlayRecording = (recordingUrl: string) => {
    if (playingRecording === recordingUrl) {
      // Stop current recording
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setPlayingRecording(null);
    } else {
      // Play new recording
      if (audioRef.current) {
        audioRef.current.src = recordingUrl;
        audioRef.current.play();
        setPlayingRecording(recordingUrl);
      }
    }
  };

  const handleAudioEnded = () => {
    setPlayingRecording(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {accountId ? `Communications - ${accounts.find(a => a.id === parseInt(accountId))?.name || 'Account'}` : 'Communications'}
          </h1>
          <p className="mt-2 text-gray-600">
            {accountId ? 'All communications for this account' : 'All communications across all accounts'}
          </p>
          <div className="mt-2">
            <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
              Mode: Mock (Simulated Communications)
            </Badge>
          </div>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => setShowEmailModal(true)}>
            <Mail className="w-4 h-4 mr-2" />
            Send Email
          </Button>
          <Button onClick={() => setShowCallModal(true)}>
            <Phone className="w-4 h-4 mr-2" />
            Make Call
          </Button>
          <Button onClick={() => setShowSMSModal(true)}>
            <MessageSquare className="w-4 h-4 mr-2" />
            Send SMS
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Communication History</CardTitle>
          <CardDescription>
            Recent communications with contacts
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-6 p-4 border rounded-lg bg-gray-50">
            <h3 className="text-sm font-medium mb-3">Filters</h3>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div>
                <Label htmlFor="filter-type">Type</Label>
                <Select value={filters.type || 'all'} onValueChange={(value) => setFilters({ ...filters, type: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="All types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All types</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="call">Call</SelectItem>
                    <SelectItem value="sms">SMS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="filter-status">Status</Label>
                <Select value={filters.status || 'all'} onValueChange={(value) => setFilters({ ...filters, status: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All statuses</SelectItem>
                    <SelectItem value="sent">Sent</SelectItem>
                    <SelectItem value="delivered">Delivered</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="initiated">Initiated</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="filter-contact">Contact</Label>
                <Select value={filters.contact_id || 'all'} onValueChange={(value) => setFilters({ ...filters, contact_id: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="All contacts" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All contacts</SelectItem>
                    {contacts.map((contact) => (
                      <SelectItem key={contact.id} value={contact.id.toString()}>
                        {contact.first_name} {contact.last_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="filter-date-from">From Date</Label>
                <Input
                  type="date"
                  value={filters.date_from}
                  onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="filter-date-to">To Date</Label>
                <Input
                  type="date"
                  value={filters.date_to}
                  onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
                />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setFilters({ type: 'all', status: 'all', contact_id: 'all', date_from: '', date_to: '' })}
              >
                Clear Filters
              </Button>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Direction</TableHead>
                <TableHead>Subject/Content</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Recording</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {communications.map((comm) => (
                <TableRow key={comm.id}>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      {getTypeIcon(comm.type)}
                      <span className="capitalize">{comm.type}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <User className="w-4 h-4 text-gray-400" />
                      <Link 
                        to={`/contacts/${comm.contact_id}`}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        {comm.first_name} {comm.last_name}
                      </Link>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={comm.direction === 'outbound' ? 'default' : 'secondary'}>
                      {comm.direction}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="max-w-xs truncate">
                      {comm.subject || comm.content || '-'}
                    </div>
                  </TableCell>
                  <TableCell>
                    {comm.type === 'call' ? formatDuration(comm.duration) : '-'}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(comm.status)}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-600 capitalize">{comm.provider}</span>
                  </TableCell>
                  <TableCell>
                    {comm.recording_url ? (
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                          <Volume2 className="w-3 h-3 mr-1" />
                          Available
                        </Badge>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => handlePlayRecording(comm.recording_url!)}
                          className="h-6 px-2"
                        >
                          {playingRecording === comm.recording_url ? (
                            <Pause className="w-3 h-3" />
                          ) : (
                            <Play className="w-3 h-3" />
                          )}
                        </Button>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600">
                        {new Date(comm.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {communications.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No communications found. Start by sending an email, making a call, or sending an SMS.
            </div>
          )}
          
          {/* Pagination */}
          {communications.length > 0 && (
            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, communications.length)} of {communications.length} communications
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <span className="text-sm text-gray-500">
                  Page {currentPage}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={communications.length < pageSize}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Hidden audio element for recordings */}
      <audio
        ref={audioRef}
        onEnded={handleAudioEnded}
        className="hidden"
      />

      {/* Email Modal */}
      <Dialog open={showEmailModal} onOpenChange={setShowEmailModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Email</DialogTitle>
            <DialogDescription>
              Send an email to a contact
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="email-contact">Contact</Label>
              <Select value={emailForm.contact_id} onValueChange={(value) => {
                const contact = contacts.find(c => c.id.toString() === value);
                setEmailForm({ ...emailForm, contact_id: value, to: contact?.email || '' });
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a contact" />
                </SelectTrigger>
                <SelectContent>
                  {contacts.map((contact) => (
                    <SelectItem key={contact.id} value={contact.id.toString()}>
                      {contact.first_name} {contact.last_name} ({contact.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email-to">To</Label>
              <Input
                id="email-to"
                value={emailForm.to}
                onChange={(e) => setEmailForm({ ...emailForm, to: e.target.value })}
                placeholder="recipient@example.com"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email-subject">Subject</Label>
              <Input
                id="email-subject"
                value={emailForm.subject}
                onChange={(e) => setEmailForm({ ...emailForm, subject: e.target.value })}
                placeholder="Email subject"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email-body">Message</Label>
              <Textarea
                id="email-body"
                value={emailForm.body}
                onChange={(e) => setEmailForm({ ...emailForm, body: e.target.value })}
                placeholder="Your message..."
                rows={5}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEmailModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleSendEmail}>
              Send Email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Call Modal */}
      <Dialog open={showCallModal} onOpenChange={setShowCallModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Make Call</DialogTitle>
            <DialogDescription>
              Initiate a phone call to a contact
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="call-contact">Contact</Label>
              <Select value={callForm.contact_id} onValueChange={(value) => {
                const contact = contacts.find(c => c.id.toString() === value);
                setCallForm({ ...callForm, contact_id: value, phone_number: contact?.phone || '' });
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a contact" />
                </SelectTrigger>
                <SelectContent>
                  {contacts.map((contact) => (
                    <SelectItem key={contact.id} value={contact.id.toString()}>
                      {contact.first_name} {contact.last_name} ({contact.phone})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="call-phone">Phone Number</Label>
              <Input
                id="call-phone"
                value={callForm.phone_number}
                onChange={(e) => setCallForm({ ...callForm, phone_number: e.target.value })}
                placeholder="+1 (555) 123-4567"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCallModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleInitiateCall}>
              Make Call
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* SMS Modal */}
      <Dialog open={showSMSModal} onOpenChange={setShowSMSModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send SMS</DialogTitle>
            <DialogDescription>
              Send a text message to a contact
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="sms-contact">Contact</Label>
              <Select value={smsForm.contact_id} onValueChange={(value) => {
                const contact = contacts.find(c => c.id.toString() === value);
                setSMSForm({ ...smsForm, contact_id: value, phone_number: contact?.phone || '' });
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a contact" />
                </SelectTrigger>
                <SelectContent>
                  {contacts.map((contact) => (
                    <SelectItem key={contact.id} value={contact.id.toString()}>
                      {contact.first_name} {contact.last_name} ({contact.phone})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="sms-phone">Phone Number</Label>
              <Input
                id="sms-phone"
                value={smsForm.phone_number}
                onChange={(e) => setSMSForm({ ...smsForm, phone_number: e.target.value })}
                placeholder="+1 (555) 123-4567"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="sms-message">Message</Label>
              <Textarea
                id="sms-message"
                value={smsForm.message}
                onChange={(e) => setSMSForm({ ...smsForm, message: e.target.value })}
                placeholder="Your message..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSMSModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleSendSMS}>
              Send SMS
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
