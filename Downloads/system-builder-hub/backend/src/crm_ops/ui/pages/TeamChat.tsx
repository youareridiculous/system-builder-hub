import React, { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { LoadingSpinner } from '../components/LoadingStates';
import { ErrorMessage } from '../components/ErrorStates';
import { trackEvent, AnalyticsEvents } from '../utils/analytics';
import { canCreate } from '../utils/rbac';
import { 
  Send, 
  Paperclip, 
  MoreVertical,
  Search,
  Plus,
  Users,
  Clock
} from 'lucide-react';

interface Message {
  id: string;
  type: string;
  attributes: {
    body: string;
    sender_id: string;
    created_at: string;
    is_edited: boolean;
    attachments: string[];
  };
}

interface Thread {
  id: string;
  type: string;
  attributes: {
    title: string;
    participants: string[];
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
}

interface MessageBubbleProps {
  message: Message;
  isOwnMessage: boolean;
  onEdit?: (message: Message) => void;
  onDelete?: (message: Message) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ 
  message, 
  isOwnMessage, 
  onEdit, 
  onDelete 
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-xs lg:max-w-md ${isOwnMessage ? 'order-2' : 'order-1'}`}>
        <div className={`rounded-lg px-4 py-2 ${
          isOwnMessage 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-100 text-gray-900'
        }`}>
          <div className="flex items-start justify-between">
            <p className="text-sm break-words">{message.attributes.body}</p>
            {isOwnMessage && (
              <div className="relative ml-2">
                <button
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="text-gray-300 hover:text-white"
                >
                  <MoreVertical className="h-3 w-3" />
                </button>
                {isMenuOpen && (
                  <div className="absolute right-0 mt-1 w-32 bg-white rounded-md shadow-lg z-10 border border-gray-200">
                    <div className="py-1">
                      <button
                        onClick={() => {
                          onEdit?.(message);
                          setIsMenuOpen(false);
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          onDelete?.(message);
                          setIsMenuOpen(false);
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-gray-100"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          {message.attributes.is_edited && (
            <p className="text-xs opacity-75 mt-1">(edited)</p>
          )}
        </div>
        <div className={`text-xs text-gray-500 mt-1 ${isOwnMessage ? 'text-right' : 'text-left'}`}>
          {new Date(message.attributes.created_at).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  );
};

interface ThreadItemProps {
  thread: Thread;
  isActive: boolean;
  onClick: () => void;
}

const ThreadItem: React.FC<ThreadItemProps> = ({ thread, isActive, onClick }) => {
  const currentUserId = localStorage.getItem('user_id');
  const otherParticipants = thread.attributes.participants.filter(id => id !== currentUserId);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 border-b border-gray-200 hover:bg-gray-50 transition-colors ${
        isActive ? 'bg-blue-50 border-blue-200' : ''
      }`}
    >
      <div className="flex items-center space-x-3">
        <div className="flex-shrink-0">
          <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
            <Users className="h-5 w-5 text-blue-600" />
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {thread.attributes.title}
          </p>
          <p className="text-xs text-gray-500 truncate">
            {otherParticipants.length} participant{otherParticipants.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex-shrink-0">
          <Clock className="h-4 w-4 text-gray-400" />
        </div>
      </div>
    </button>
  );
};

export default function TeamChat() {
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [messageText, setMessageText] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: threads, error: threadsError, isLoading: threadsLoading } = useApi('/messages/threads');
  const { data: messages, error: messagesError, isLoading: messagesLoading } = useApi(
    selectedThread ? `/messages/threads/${selectedThread.id}/messages` : null
  );

  const currentUserId = localStorage.getItem('user_id');

  useEffect(() => {
    if (selectedThread) {
      trackEvent(AnalyticsEvents.THREAD_CREATED, { threadId: selectedThread.id });
    }
  }, [selectedThread]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = () => {
    if (!messageText.trim() || !selectedThread) return;

    trackEvent(AnalyticsEvents.MESSAGE_SENT, { 
      threadId: selectedThread.id,
      messageLength: messageText.length 
    });

    // Send message via API
    console.log('Sending message:', messageText);
    setMessageText('');
  };

  const handleCreateThread = () => {
    trackEvent('ui.thread.create');
    // Open create thread modal
    console.log('Opening create thread modal');
  };

  const handleEditMessage = (message: Message) => {
    trackEvent('ui.message.edit', { messageId: message.id });
    // Open edit message modal
    console.log('Editing message:', message.id);
  };

  const handleDeleteMessage = (message: Message) => {
    if (window.confirm('Are you sure you want to delete this message?')) {
      trackEvent('ui.message.delete', { messageId: message.id });
      // Delete message via API
      console.log('Deleting message:', message.id);
    }
  };

  const handleAttachFile = () => {
    trackEvent('ui.message.attach');
    // Open file picker
    console.log('Opening file picker');
  };

  if (threadsLoading) {
    return <LoadingSpinner />;
  }

  if (threadsError) {
    return <ErrorMessage error={threadsError} />;
  }

  const allThreads = threads?.data || [];
  const filteredThreads = allThreads.filter((thread: Thread) =>
    thread.attributes.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const currentMessages = messages?.data || [];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Messages</h2>
            {canCreate('messages') && (
              <button
                onClick={handleCreateThread}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
                <Plus className="h-5 w-5" />
              </button>
            )}
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search threads..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Threads List */}
        <div className="flex-1 overflow-y-auto">
          {filteredThreads.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <Users className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>No threads found</p>
            </div>
          ) : (
            filteredThreads.map((thread: Thread) => (
              <ThreadItem
                key={thread.id}
                thread={thread}
                isActive={selectedThread?.id === thread.id}
                onClick={() => setSelectedThread(thread)}
              />
            ))
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedThread ? (
          <>
            {/* Chat Header */}
            <div className="bg-white border-b border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {selectedThread.attributes.title}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {selectedThread.attributes.participants.length} participants
                  </p>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
              {messagesLoading ? (
                <LoadingSpinner />
              ) : messagesError ? (
                <ErrorMessage error={messagesError} />
              ) : currentMessages.length === 0 ? (
                <div className="text-center text-gray-500 mt-8">
                  <p>No messages yet. Start the conversation!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {currentMessages.map((message: Message) => (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      isOwnMessage={message.attributes.sender_id === currentUserId}
                      onEdit={handleEditMessage}
                      onDelete={handleDeleteMessage}
                    />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Message Input */}
            {canCreate('messages') && (
              <div className="bg-white border-t border-gray-200 p-4">
                <div className="flex items-end space-x-3">
                  <div className="flex-1">
                    <textarea
                      value={messageText}
                      onChange={(e) => setMessageText(e.target.value)}
                      placeholder="Type your message..."
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                      rows={3}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handleAttachFile}
                      className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                    >
                      <Paperclip className="h-5 w-5" />
                    </button>
                    <button
                      onClick={handleSendMessage}
                      disabled={!messageText.trim()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Users className="h-16 w-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Select a thread</h3>
              <p className="text-gray-500">Choose a conversation from the sidebar to start messaging</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
