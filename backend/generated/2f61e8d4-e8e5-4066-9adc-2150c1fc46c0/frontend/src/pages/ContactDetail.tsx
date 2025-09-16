import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../lib/api.ts';
import { useToast } from '../contexts/ToastContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { Label } from '../components/Label';
import { Textarea } from '../components/Textarea';
import { Badge } from '../components/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/Tabs';
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
import {
  Phone,
  Mail,
  MessageSquare,
  User,
  Building,
  Calendar,
  Clock,
  Play,
  Pause,
  Plus,
  Edit,
  Trash2,
  Pin,
  FileText,
  CheckCircle,
  XCircle,
  ArrowLeft,
  Volume2
} from 'lucide-react';

interface Contact {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  title: string;
  account_id: number;
  account_name: string;
  created_at: string;
}

interface CommunicationHistory {
  id: number;
  type: string;
  direction: string;
  subject?: string;
  content?: string;
  status: string;
  provider: string;
  duration?: number;
  recording_url?: string;
  created_at: string;
}

interface Activity {
  id: number;
  type: string;
  subject: string;
  description: string;
  due_date: string;
  completed: boolean;
  created_at: string;
}

interface Note {
  id: number;
  body: string;
  pinned: boolean;
  created_at: string;
  updated_at: string;
}

export default function ContactDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [contact, setContact] = useState<Contact | null>(null);
  const [communications, setCommunications] = useState<CommunicationHistory[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modal states
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [showSMSModal, setShowSMSModal] = useState(false);
  const [showCallModal, setShowCallModal] = useState(false);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showEditNoteModal, setShowEditNoteModal] = useState(false);
  const [showActivityModal, setShowActivityModal] = useState(false);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [playingRecording, setPlayingRecording] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  // Form states
  const [emailForm, setEmailForm] = useState({ subject: '', body: '' });
  const [smsForm, setSMSForm] = useState({ message: '' });
  const [callForm, setCallForm] = useState({ phone_number: '' });
  const [noteForm, setNoteForm] = useState({ body: '' });
  const [activityForm, setActivityForm] = useState({
    type: 'call',
    subject: '',
    description: '',
    due_date: ''
  });

  useEffect(() => {
    if (id) {
      fetchContactData();
    }
  }, [id]);

  const fetchContactData = async () => {
    try {
      const [contactData, commsData, activitiesData, notesData] = await Promise.all([
        api.get(`/contacts/${id}`),
        api.get('/communications/history', { params: { contact_id: id } }),
        api.get('/activities/', { params: { contact_id: id } }),
        api.get(`/contacts/${id}/notes`)
      ]);
      
      setContact(contactData);
      setCommunications(commsData);
      setActivities(activitiesData);
      setNotes(notesData);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching contact data:', err);
      showToast('Failed to load contact data', 'error');
      setLoading(false);
    }
  };

  const handleSendEmail = async () => {
    try {
      await api.post('/communications/send-email', {
        to: contact?.email,
        subject: emailForm.subject,
        body: emailForm.body,
        contact_id: parseInt(id!)
      });
      
      setShowEmailModal(false);
      setEmailForm({ subject: '', body: '' });
      showToast('Email sent successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to send email', 'error');
    }
  };

  const handleSendSMS = async () => {
    try {
      await api.post('/communications/send-sms', {
        phone_number: contact?.phone,
        message: smsForm.message,
        contact_id: parseInt(id!)
      });
      
      setShowSMSModal(false);
      setSMSForm({ message: '' });
      showToast('SMS sent successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to send SMS', 'error');
    }
  };

  const handleInitiateCall = async () => {
    try {
      await api.post('/communications/initiate-call', {
        phone_number: contact?.phone,
        contact_id: parseInt(id!)
      });
      
      setShowCallModal(false);
      setCallForm({ phone_number: '' });
      showToast('Call initiated successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to initiate call', 'error');
    }
  };

  const handleAddNote = async () => {
    try {
      await api.post(`/contacts/${id}/notes`, {
        body: noteForm.body,
        pinned: false
      });
      
      setShowNoteModal(false);
      setNoteForm({ body: '' });
      showToast('Note added successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to add note', 'error');
    }
  };

  const handleEditNote = async () => {
    if (!selectedNote) return;
    
    try {
      await api.put(`/notes/${selectedNote.id}`, {
        body: noteForm.body
      });
      
      setShowEditNoteModal(false);
      setSelectedNote(null);
      setNoteForm({ body: '' });
      showToast('Note updated successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to update note', 'error');
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    try {
      await api.del(`/notes/${noteId}`);
      showToast('Note deleted successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to delete note', 'error');
    }
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

  const handleAddActivity = async () => {
    try {
      await api.post('/activities/', {
        ...activityForm,
        contact_id: parseInt(id!),
        completed: false
      });
      
      setShowActivityModal(false);
      setActivityForm({ type: 'call', subject: '', description: '', due_date: '' });
      showToast('Activity added successfully!', 'success');
      fetchContactData();
    } catch (err) {
      showToast('Failed to add activity', 'error');
    }
  };

  const getStatusBadge = (status: string) => {
    const statusColors = {
      sent: 'bg-blue-100 text-blue-800',
      delivered: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      initiated: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      missed: 'bg-red-100 text-red-800'
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
        return <Calendar className="w-4 h-4" />;
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Combine and sort timeline items
  const timelineItems = [
    ...communications.map(comm => ({ ...comm, itemType: 'communication' as const })),
    ...activities.map(activity => ({ ...activity, itemType: 'activity' as const }))
  ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">Contact not found</p>
        <Button onClick={() => navigate('/contacts')} className="mt-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Contacts
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" onClick={() => navigate('/contacts')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {contact.first_name} {contact.last_name}
            </h1>
            <p className="text-gray-600">{contact.title}</p>
          </div>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => setShowEmailModal(true)}>
            <Mail className="w-4 h-4 mr-2" />
            Send Email
          </Button>
          <Button onClick={() => setShowSMSModal(true)}>
            <MessageSquare className="w-4 h-4 mr-2" />
            Send SMS
          </Button>
          <Button onClick={() => setShowCallModal(true)}>
            <Phone className="w-4 h-4 mr-2" />
            Call
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contact Info */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-sm font-medium text-gray-500">Email</Label>
                <div className="flex items-center space-x-2 mt-1">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <a href={`mailto:${contact.email}`} className="text-blue-600 hover:underline">
                    {contact.email}
                  </a>
                </div>
              </div>
              
              <div>
                <Label className="text-sm font-medium text-gray-500">Phone</Label>
                <div className="flex items-center space-x-2 mt-1">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <a href={`tel:${contact.phone}`} className="text-blue-600 hover:underline">
                    {contact.phone}
                  </a>
                </div>
              </div>
              
              <div>
                <Label className="text-sm font-medium text-gray-500">Account</Label>
                <div className="flex items-center space-x-2 mt-1">
                  <Building className="w-4 h-4 text-gray-400" />
                  <span>{contact.account_name}</span>
                </div>
              </div>
              
              <div>
                <Label className="text-sm font-medium text-gray-500">Created</Label>
                <div className="flex items-center space-x-2 mt-1">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <span>{new Date(contact.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button 
                variant="outline" 
                className="w-full justify-start"
                onClick={() => setShowNoteModal(true)}
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Note
              </Button>
              <Button 
                variant="outline" 
                className="w-full justify-start"
                onClick={() => setShowActivityModal(true)}
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Activity
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Timeline */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
              <CardDescription>
                All communications and activities with {contact.first_name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {timelineItems.map((item) => (
                  <div key={`${item.itemType}-${item.id}`} className="flex space-x-4 p-4 border rounded-lg">
                    <div className="flex-shrink-0">
                      {getTypeIcon(item.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium capitalize">
                            {item.itemType === 'communication' ? item.type : item.type}
                          </span>
                          {item.itemType === 'communication' && getStatusBadge(item.status)}
                        </div>
                        <span className="text-sm text-gray-500">
                          {new Date(item.created_at).toLocaleString()}
                        </span>
                      </div>
                      
                      {item.itemType === 'communication' && (
                        <div className="mt-2">
                          {item.subject && (
                            <p className="font-medium">{item.subject}</p>
                          )}
                          {item.content && (
                            <p className="text-gray-600 mt-1">{item.content}</p>
                          )}
                          {item.duration && (
                            <p className="text-sm text-gray-500 mt-1">
                              Duration: {formatDuration(item.duration)}
                            </p>
                          )}
                          {item.recording_url && (
                            <div className="mt-2 space-y-2">
                              <div className="flex items-center space-x-2">
                                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                  <Volume2 className="w-3 h-3 mr-1" />
                                  Recording Available
                                </Badge>
                                {item.duration && (
                                  <span className="text-xs text-gray-500">
                                    {formatDuration(item.duration)}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center space-x-2">
                                <Button 
                                  variant="outline" 
                                  size="sm" 
                                  onClick={() => handlePlayRecording(item.recording_url!)}
                                  className="flex items-center space-x-1"
                                >
                                  {playingRecording === item.recording_url ? (
                                    <>
                                      <Pause className="w-3 h-3" />
                                      <span>Pause</span>
                                    </>
                                  ) : (
                                    <>
                                      <Play className="w-3 h-3" />
                                      <span>Play</span>
                                    </>
                                  )}
                                </Button>
                                <audio
                                  ref={audioRef}
                                  onEnded={handleAudioEnded}
                                  className="hidden"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                      
                      {item.itemType === 'activity' && (
                        <div className="mt-2">
                          <p className="font-medium">{item.subject}</p>
                          <p className="text-gray-600 mt-1">{item.description}</p>
                          <div className="flex items-center space-x-4 mt-2">
                            <span className="text-sm text-gray-500">
                              Due: {new Date(item.due_date).toLocaleDateString()}
                            </span>
                            <Badge variant={item.completed ? 'default' : 'secondary'}>
                              {item.completed ? 'Completed' : 'Pending'}
                            </Badge>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                
                {timelineItems.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    No communications or activities yet. Start by sending an email or adding a note.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Tabs for Notes, Files, Tasks */}
      <Card>
        <Tabs defaultValue="notes" className="w-full">
          <CardHeader>
            <TabsList>
              <TabsTrigger value="notes">Notes</TabsTrigger>
              <TabsTrigger value="files">Files</TabsTrigger>
              <TabsTrigger value="tasks">Tasks</TabsTrigger>
            </TabsList>
          </CardHeader>
          <CardContent>
            <TabsContent value="notes" className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium">Notes</h3>
                <Button onClick={() => setShowNoteModal(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Note
                </Button>
              </div>
              
              <div className="space-y-4">
                {notes.map((note) => (
                  <div key={note.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {note.pinned && <Pin className="w-4 h-4 text-yellow-500" />}
                        <span className="text-sm text-gray-500">
                          {new Date(note.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setSelectedNote(note);
                            setNoteForm({ body: note.body });
                            setShowEditNoteModal(true);
                          }}
                        >
                          <Edit className="w-3 h-3" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleDeleteNote(note.id)}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                    <p className="text-gray-700">{note.body}</p>
                  </div>
                ))}
                
                {notes.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    No notes yet. Add your first note to get started.
                  </div>
                )}
              </div>
            </TabsContent>
            
            <TabsContent value="files" className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium">Files & Attachments</h3>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Upload File
                </Button>
              </div>
              
              <div className="text-center py-8 text-gray-500">
                File upload functionality coming soon...
              </div>
            </TabsContent>
            
            <TabsContent value="tasks" className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium">Tasks</h3>
                <Button onClick={() => setShowActivityModal(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Task
                </Button>
              </div>
              
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Due Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activities.map((activity) => (
                    <TableRow key={activity.id}>
                      <TableCell className="capitalize">{activity.type}</TableCell>
                      <TableCell>{activity.subject}</TableCell>
                      <TableCell>{new Date(activity.due_date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Badge variant={activity.completed ? 'default' : 'secondary'}>
                          {activity.completed ? 'Completed' : 'Pending'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-2">
                          <Button variant="outline" size="sm">
                            <Edit className="w-3 h-3" />
                          </Button>
                          <Button variant="outline" size="sm">
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              {activities.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No tasks yet. Add your first task to get started.
                </div>
              )}
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>

      {/* Modals */}
      {/* Email Modal */}
      <Dialog open={showEmailModal} onOpenChange={setShowEmailModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Email</DialogTitle>
            <DialogDescription>
              Send an email to {contact.first_name} {contact.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="email-subject">Subject</Label>
              <Input
                id="email-subject"
                value={emailForm.subject}
                onChange={(e) => setEmailForm({ ...emailForm, subject: e.target.value })}
                placeholder="Email subject"
              />
            </div>
            <div>
              <Label htmlFor="email-body">Message</Label>
              <Textarea
                id="email-body"
                value={emailForm.body}
                onChange={(e) => setEmailForm({ ...emailForm, body: e.target.value })}
                placeholder="Your message"
                rows={6}
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

      {/* SMS Modal */}
      <Dialog open={showSMSModal} onOpenChange={setShowSMSModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send SMS</DialogTitle>
            <DialogDescription>
              Send an SMS to {contact.first_name} {contact.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="sms-message">Message</Label>
              <Textarea
                id="sms-message"
                value={smsForm.message}
                onChange={(e) => setSMSForm({ message: e.target.value })}
                placeholder="Your message"
                rows={4}
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

      {/* Call Modal */}
      <Dialog open={showCallModal} onOpenChange={setShowCallModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Make Call</DialogTitle>
            <DialogDescription>
              Initiate a call to {contact.first_name} {contact.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="call-phone">Phone Number</Label>
              <Input
                id="call-phone"
                value={callForm.phone_number}
                onChange={(e) => setCallForm({ phone_number: e.target.value })}
                placeholder={contact.phone}
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

      {/* Note Modal */}
      <Dialog open={showNoteModal} onOpenChange={setShowNoteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Note</DialogTitle>
            <DialogDescription>
              Add a note about {contact.first_name} {contact.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="note-body">Note</Label>
              <Textarea
                id="note-body"
                value={noteForm.body}
                onChange={(e) => setNoteForm({ body: e.target.value })}
                placeholder="Your note"
                rows={6}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNoteModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddNote}>
              Add Note
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Note Modal */}
      <Dialog open={showEditNoteModal} onOpenChange={setShowEditNoteModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Note</DialogTitle>
            <DialogDescription>
              Update the note about {contact.first_name} {contact.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-note-body">Note</Label>
              <Textarea
                id="edit-note-body"
                value={noteForm.body}
                onChange={(e) => setNoteForm({ body: e.target.value })}
                placeholder="Your note"
                rows={6}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditNoteModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleEditNote}>
              Update Note
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Activity Modal */}
      <Dialog open={showActivityModal} onOpenChange={setShowActivityModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Activity</DialogTitle>
            <DialogDescription>
              Add an activity for {contact.first_name} {contact.last_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="activity-type">Type</Label>
              <select
                id="activity-type"
                value={activityForm.type}
                onChange={(e) => setActivityForm({ ...activityForm, type: e.target.value })}
                className="w-full p-2 border rounded-md"
              >
                <option value="call">Call</option>
                <option value="email">Email</option>
                <option value="meeting">Meeting</option>
                <option value="task">Task</option>
              </select>
            </div>
            <div>
              <Label htmlFor="activity-subject">Subject</Label>
              <Input
                id="activity-subject"
                value={activityForm.subject}
                onChange={(e) => setActivityForm({ ...activityForm, subject: e.target.value })}
                placeholder="Activity subject"
              />
            </div>
            <div>
              <Label htmlFor="activity-description">Description</Label>
              <Textarea
                id="activity-description"
                value={activityForm.description}
                onChange={(e) => setActivityForm({ ...activityForm, description: e.target.value })}
                placeholder="Activity description"
                rows={4}
              />
            </div>
            <div>
              <Label htmlFor="activity-due-date">Due Date</Label>
              <Input
                id="activity-due-date"
                type="datetime-local"
                value={activityForm.due_date}
                onChange={(e) => setActivityForm({ ...activityForm, due_date: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowActivityModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddActivity}>
              Add Activity
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
