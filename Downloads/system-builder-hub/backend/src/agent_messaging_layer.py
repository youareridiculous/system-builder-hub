"""
Priority 24: Agent-to-Agent Communication Layer (A2A Layer)

This module implements a secure, modular, and intelligent Agent-to-Agent Communication Layer
that allows agents within a system (and optionally across systems) to send, receive, interpret,
and respond to messages, goals, data, and coordination signals.
"""

import sqlite3
import json
import uuid
import time
import threading
import queue
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import asyncio
import websockets
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages that can be sent between agents"""
    INSTRUCTION = "instruction"
    QUESTION = "question"
    STATUS_UPDATE = "status_update"
    ALERT = "alert"
    HANDOFF = "handoff"
    GOAL_DELEGATION = "goal_delegation"
    DATA_BLOB = "data_blob"
    MEMORY_REFERENCE = "memory_reference"
    COORDINATION = "coordination"
    RETRAIN_REQUEST = "retrain_request"
    HEALING_REQUEST = "healing_request"
    MARKETPLACE_UPDATE = "marketplace_update"

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

class MessageStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    RESPONDED = "responded"
    FAILED = "failed"
    EXPIRED = "expired"

class IntentClassification(Enum):
    """Intent classification for message validation"""
    BENIGN = "benign"
    COORDINATION = "coordination"
    REQUEST = "request"
    ALERT = "alert"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"

@dataclass
class AgentMessage:
    """Represents a message between agents"""
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    priority: MessagePriority
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    ttl: int  # Time to live in seconds
    trust_level: float  # 0.0 to 1.0
    thread_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    status: MessageStatus = MessageStatus.PENDING
    delivery_attempts: int = 0
    max_retries: int = 3

@dataclass
class MessageThread:
    """Represents a conversation thread between agents"""
    thread_id: str
    topic: str
    goal_id: Optional[str]
    participants: List[str]
    created_at: datetime
    last_activity: datetime
    message_count: int
    status: str  # active, completed, archived

@dataclass
class AgentCapability:
    """Represents an agent's messaging capabilities"""
    agent_id: str
    supported_message_types: List[MessageType]
    supported_intents: List[str]
    max_message_size: int
    processing_speed: float  # messages per second
    is_online: bool
    last_seen: datetime

class AgentMessagingLayer:
    """
    Core Agent-to-Agent Communication Layer
    
    Provides secure, intelligent messaging between agents with:
    - Real-time and asynchronous message delivery
    - Permission and intent validation
    - Message history and threading
    - Integration with existing system components
    """
    
    def __init__(self, base_dir: Path, memory_system, agent_orchestrator, 
                 access_control, llm_factory, black_box_inspector=None):
        self.base_dir = base_dir
        self.memory_system = memory_system
        self.agent_orchestrator = agent_orchestrator
        self.access_control = access_control
        self.llm_factory = llm_factory
        self.black_box_inspector = black_box_inspector
        
        # Database setup
        self.db_path = base_dir / "data" / "agent_messaging.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Message queues and delivery
        self.message_queue = queue.Queue()
        self.delivery_queue = queue.Queue()
        self.retry_queue = queue.Queue()
        
        # Agent registry and capabilities
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.agent_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Threading and real-time support
        self.websocket_connections: Dict[str, Any] = {}
        self.message_history: Dict[str, List[AgentMessage]] = defaultdict(list)
        self.active_threads: Dict[str, MessageThread] = {}
        
        # Background processing
        self.running = True
        self.delivery_thread = threading.Thread(target=self._delivery_worker, daemon=True)
        self.retry_thread = threading.Thread(target=self._retry_worker, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        
        # Start background threads
        self.delivery_thread.start()
        self.retry_thread.start()
        self.cleanup_thread.start()
        
        logger.info("Agent Messaging Layer initialized")
    
    def _init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_messages (
                    message_id TEXT PRIMARY KEY,
                    sender_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ttl INTEGER NOT NULL,
                    trust_level REAL NOT NULL,
                    thread_id TEXT,
                    parent_message_id TEXT,
                    status TEXT NOT NULL,
                    delivery_attempts INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    FOREIGN KEY (parent_message_id) REFERENCES agent_messages (message_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_threads (
                    thread_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    goal_id TEXT,
                    participants TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    status TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_capabilities (
                    agent_id TEXT PRIMARY KEY,
                    supported_message_types TEXT NOT NULL,
                    supported_intents TEXT NOT NULL,
                    max_message_size INTEGER NOT NULL,
                    processing_speed REAL NOT NULL,
                    is_online BOOLEAN NOT NULL,
                    last_seen TEXT NOT NULL
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON agent_messages(sender_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON agent_messages(receiver_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread ON agent_messages(thread_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON agent_messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_status ON agent_messages(status)")
            
            conn.commit()
    
    def register_agent(self, agent_id: str, capabilities: AgentCapability):
        """Register an agent and its messaging capabilities"""
        self.agent_capabilities[agent_id] = capabilities
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_capabilities 
                (agent_id, supported_message_types, supported_intents, max_message_size, 
                 processing_speed, is_online, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_id,
                json.dumps([mt.value for mt in capabilities.supported_message_types]),
                json.dumps(capabilities.supported_intents),
                capabilities.max_message_size,
                capabilities.processing_speed,
                capabilities.is_online,
                capabilities.last_seen.isoformat()
            ))
            conn.commit()
        
        logger.info(f"Registered agent {agent_id} with {len(capabilities.supported_message_types)} message types")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agent_capabilities:
            del self.agent_capabilities[agent_id]
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM agent_capabilities WHERE agent_id = ?", (agent_id,))
                conn.commit()
            
            logger.info(f"Unregistered agent {agent_id}")
    
    def send_message(self, sender_id: str, receiver_id: str, message_type: MessageType,
                    content: str, priority: MessagePriority = MessagePriority.NORMAL,
                    metadata: Optional[Dict[str, Any]] = None, ttl: int = 3600,
                    thread_id: Optional[str] = None, parent_message_id: Optional[str] = None) -> str:
        """
        Send a message from one agent to another
        
        Returns the message ID
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Default metadata
        if metadata is None:
            metadata = {}
        
        # Create message
        message = AgentMessage(
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            priority=priority,
            content=content,
            metadata=metadata,
            timestamp=timestamp,
            ttl=ttl,
            trust_level=1.0,  # Will be calculated during validation
            thread_id=thread_id,
            parent_message_id=parent_message_id
        )
        
        # Validate message before sending
        validation_result = self._validate_message(message)
        if not validation_result['valid']:
            raise ValueError(f"Message validation failed: {validation_result['reason']}")
        
        # Update trust level
        message.trust_level = validation_result['trust_level']
        
        # Store message in database
        self._store_message(message)
        
        # Add to delivery queue
        self.delivery_queue.put(message)
        
        # Log to black box inspector if available
        if self.black_box_inspector:
            self.black_box_inspector.log_trace_event(
                trace_type="agent_messaging",
                component_id=f"{sender_id}->{receiver_id}",
                payload={
                    "message_id": message_id,
                    "message_type": message_type.value,
                    "priority": priority.value,
                    "content_length": len(content),
                    "trust_level": message.trust_level
                },
                metadata={
                    "sender_id": sender_id,
                    "receiver_id": receiver_id,
                    "thread_id": thread_id,
                    "validation_result": validation_result
                }
            )
        
        logger.info(f"Message {message_id} sent from {sender_id} to {receiver_id}")
        return message_id
    
    def _validate_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Validate a message for permissions, intent, and compatibility"""
        validation_result = {
            'valid': True,
            'reason': None,
            'trust_level': 1.0,
            'intent_classification': IntentClassification.BENIGN
        }
        
        try:
            # Check if sender and receiver exist
            if message.sender_id not in self.agent_capabilities:
                validation_result['valid'] = False
                validation_result['reason'] = f"Sender agent {message.sender_id} not registered"
                return validation_result
            
            if message.receiver_id not in self.agent_capabilities:
                validation_result['valid'] = False
                validation_result['reason'] = f"Receiver agent {message.receiver_id} not registered"
                return validation_result
            
            sender_cap = self.agent_capabilities[message.sender_id]
            receiver_cap = self.agent_capabilities[message.receiver_id]
            
            # Check message size
            if len(message.content) > receiver_cap.max_message_size:
                validation_result['valid'] = False
                validation_result['reason'] = f"Message too large for receiver (max: {receiver_cap.max_message_size})"
                return validation_result
            
            # Check if receiver supports this message type
            if message.message_type not in receiver_cap.supported_message_types:
                validation_result['valid'] = False
                validation_result['reason'] = f"Receiver does not support message type {message.message_type.value}"
                return validation_result
            
            # Check permissions using access control
            if self.access_control:
                permission_result = self.access_control.check_agent_permission(
                    message.sender_id, message.receiver_id, "send_message"
                )
                if not permission_result['allowed']:
                    validation_result['valid'] = False
                    validation_result['reason'] = f"Permission denied: {permission_result['reason']}"
                    return validation_result
                
                # Adjust trust level based on permissions
                validation_result['trust_level'] *= permission_result.get('trust_level', 1.0)
            
            # Intent classification using LLM if available
            if self.llm_factory:
                intent_result = self._classify_intent(message)
                validation_result['intent_classification'] = intent_result['classification']
                
                if intent_result['classification'] == IntentClassification.MALICIOUS:
                    validation_result['valid'] = False
                    validation_result['reason'] = "Message classified as malicious"
                    return validation_result
                elif intent_result['classification'] == IntentClassification.SUSPICIOUS:
                    validation_result['trust_level'] *= 0.5
                elif intent_result['classification'] == IntentClassification.BENIGN:
                    validation_result['trust_level'] *= 1.0
                else:
                    validation_result['trust_level'] *= 0.8
            
            # Check if receiver is online
            if not receiver_cap.is_online:
                validation_result['trust_level'] *= 0.7  # Reduce trust for offline agents
            
            return validation_result
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['reason'] = f"Validation error: {str(e)}"
            return validation_result
    
    def _classify_intent(self, message: AgentMessage) -> Dict[str, Any]:
        """Classify the intent of a message using LLM"""
        try:
            # Create prompt for intent classification
            prompt = f"""
            Classify the intent of this agent message:
            
            Sender: {message.sender_id}
            Receiver: {message.receiver_id}
            Type: {message.message_type.value}
            Content: {message.content}
            
            Classify as one of: benign, coordination, request, alert, suspicious, malicious
            
            Respond with only the classification.
            """
            
            # Use LLM for classification
            response = self.llm_factory.generate_response(prompt, temperature=0.1)
            classification_text = response.strip().lower()
            
            # Map to enum
            classification_map = {
                'benign': IntentClassification.BENIGN,
                'coordination': IntentClassification.COORDINATION,
                'request': IntentClassification.REQUEST,
                'alert': IntentClassification.ALERT,
                'suspicious': IntentClassification.SUSPICIOUS,
                'malicious': IntentClassification.MALICIOUS
            }
            
            classification = classification_map.get(classification_text, IntentClassification.BENIGN)
            
            return {
                'classification': classification,
                'confidence': 0.8  # Could be enhanced with confidence scoring
            }
            
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return {
                'classification': IntentClassification.BENIGN,
                'confidence': 0.5
            }
    
    def _store_message(self, message: AgentMessage):
        """Store a message in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agent_messages 
                (message_id, sender_id, receiver_id, message_type, priority, content, 
                 metadata, timestamp, ttl, trust_level, thread_id, parent_message_id, 
                 status, delivery_attempts, max_retries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.sender_id,
                message.receiver_id,
                message.message_type.value,
                message.priority.value,
                message.content,
                json.dumps(message.metadata),
                message.timestamp.isoformat(),
                message.ttl,
                message.trust_level,
                message.thread_id,
                message.parent_message_id,
                message.status.value,
                message.delivery_attempts,
                message.max_retries
            ))
            conn.commit()
    
    def _delivery_worker(self):
        """Background worker for message delivery"""
        while self.running:
            try:
                message = self.delivery_queue.get(timeout=1)
                
                # Check if message has expired
                if datetime.now() - message.timestamp > timedelta(seconds=message.ttl):
                    self._update_message_status(message.message_id, MessageStatus.EXPIRED)
                    continue
                
                # Attempt delivery
                delivery_success = self._deliver_message(message)
                
                if delivery_success:
                    self._update_message_status(message.message_id, MessageStatus.DELIVERED)
                else:
                    # Add to retry queue if attempts remain
                    if message.delivery_attempts < message.max_retries:
                        message.delivery_attempts += 1
                        self.retry_queue.put((message, time.time() + 60))  # Retry in 1 minute
                    else:
                        self._update_message_status(message.message_id, MessageStatus.FAILED)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Delivery worker error: {e}")
    
    def _retry_worker(self):
        """Background worker for retrying failed messages"""
        while self.running:
            try:
                # Check retry queue
                current_time = time.time()
                retry_items = []
                
                while not self.retry_queue.empty():
                    message, retry_time = self.retry_queue.get()
                    if current_time >= retry_time:
                        retry_items.append(message)
                    else:
                        self.retry_queue.put((message, retry_time))
                        break
                
                # Process retry items
                for message in retry_items:
                    delivery_success = self._deliver_message(message)
                    if delivery_success:
                        self._update_message_status(message.message_id, MessageStatus.DELIVERED)
                    elif message.delivery_attempts < message.max_retries:
                        message.delivery_attempts += 1
                        self.retry_queue.put((message, current_time + 60))
                    else:
                        self._update_message_status(message.message_id, MessageStatus.FAILED)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Retry worker error: {e}")
    
    def _deliver_message(self, message: AgentMessage) -> bool:
        """Attempt to deliver a message to its recipient"""
        try:
            # Check if receiver is online
            receiver_cap = self.agent_capabilities.get(message.receiver_id)
            if not receiver_cap or not receiver_cap.is_online:
                return False
            
            # Notify subscribers
            if message.receiver_id in self.agent_subscribers:
                for callback in self.agent_subscribers[message.receiver_id]:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Subscriber callback error: {e}")
            
            # Add to message history
            self.message_history[message.receiver_id].append(message)
            
            # Update last seen
            receiver_cap.last_seen = datetime.now()
            
            logger.info(f"Message {message.message_id} delivered to {message.receiver_id}")
            return True
            
        except Exception as e:
            logger.error(f"Message delivery failed: {e}")
            return False
    
    def _update_message_status(self, message_id: str, status: MessageStatus):
        """Update the status of a message in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE agent_messages SET status = ? WHERE message_id = ?",
                (status.value, message_id)
            )
            conn.commit()
    
    def subscribe_to_messages(self, agent_id: str, callback: Callable[[AgentMessage], None]):
        """Subscribe to receive messages for a specific agent"""
        self.agent_subscribers[agent_id].append(callback)
        logger.info(f"Added subscriber for agent {agent_id}")
    
    def unsubscribe_from_messages(self, agent_id: str, callback: Callable[[AgentMessage], None]):
        """Unsubscribe from messages for a specific agent"""
        if agent_id in self.agent_subscribers:
            try:
                self.agent_subscribers[agent_id].remove(callback)
                logger.info(f"Removed subscriber for agent {agent_id}")
            except ValueError:
                pass
    
    def get_messages_for_agent(self, agent_id: str, limit: int = 100, 
                              message_type: Optional[MessageType] = None,
                              status: Optional[MessageStatus] = None) -> List[AgentMessage]:
        """Get messages for a specific agent"""
        query = """
            SELECT * FROM agent_messages 
            WHERE receiver_id = ?
        """
        params = [agent_id]
        
        if message_type:
            query += " AND message_type = ?"
            params.append(message_type.value)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            message = AgentMessage(
                message_id=row['message_id'],
                sender_id=row['sender_id'],
                receiver_id=row['receiver_id'],
                message_type=MessageType(row['message_type']),
                priority=MessagePriority(row['priority']),
                content=row['content'],
                metadata=json.loads(row['metadata']),
                timestamp=datetime.fromisoformat(row['timestamp']),
                ttl=row['ttl'],
                trust_level=row['trust_level'],
                thread_id=row['thread_id'],
                parent_message_id=row['parent_message_id'],
                status=MessageStatus(row['status']),
                delivery_attempts=row['delivery_attempts'],
                max_retries=row['max_retries']
            )
            messages.append(message)
        
        return messages
    
    def get_message_threads(self, agent_id: Optional[str] = None, 
                           status: Optional[str] = None) -> List[MessageThread]:
        """Get message threads"""
        query = "SELECT * FROM message_threads"
        params = []
        
        if agent_id:
            query += " WHERE participants LIKE ?"
            params.append(f"%{agent_id}%")
        
        if status:
            if agent_id:
                query += " AND status = ?"
            else:
                query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY last_activity DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
        
        threads = []
        for row in rows:
            thread = MessageThread(
                thread_id=row['thread_id'],
                topic=row['topic'],
                goal_id=row['goal_id'],
                participants=json.loads(row['participants']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_activity=datetime.fromisoformat(row['last_activity']),
                message_count=row['message_count'],
                status=row['status']
            )
            threads.append(thread)
        
        return threads
    
    def create_message_thread(self, topic: str, participants: List[str], 
                             goal_id: Optional[str] = None) -> str:
        """Create a new message thread"""
        thread_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO message_threads 
                (thread_id, topic, goal_id, participants, created_at, last_activity, message_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                topic,
                goal_id,
                json.dumps(participants),
                timestamp.isoformat(),
                timestamp.isoformat(),
                0,
                "active"
            ))
            conn.commit()
        
        return thread_id
    
    def _cleanup_worker(self):
        """Background worker for cleaning up expired messages and old data"""
        while self.running:
            try:
                # Clean up expired messages
                cutoff_time = datetime.now() - timedelta(days=30)
                
                with sqlite3.connect(self.db_path) as conn:
                    # Delete expired messages
                    conn.execute("""
                        DELETE FROM agent_messages 
                        WHERE timestamp < ? AND status IN ('delivered', 'read', 'responded')
                    """, (cutoff_time.isoformat(),))
                    
                    # Archive old threads
                    conn.execute("""
                        UPDATE message_threads 
                        SET status = 'archived' 
                        WHERE last_activity < ? AND status = 'active'
                    """, (cutoff_time.isoformat(),))
                    
                    conn.commit()
                
                # Clean up in-memory data
                for agent_id in list(self.message_history.keys()):
                    self.message_history[agent_id] = [
                        msg for msg in self.message_history[agent_id]
                        if msg.timestamp > cutoff_time
                    ]
                
                time.sleep(3600)  # Run cleanup every hour
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Message counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM agent_messages 
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Message counts by type
            cursor = conn.execute("""
                SELECT message_type, COUNT(*) as count 
                FROM agent_messages 
                GROUP BY message_type
            """)
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Active agents
            cursor = conn.execute("""
                SELECT COUNT(*) as count 
                FROM agent_capabilities 
                WHERE is_online = 1
            """)
            active_agents = cursor.fetchone()[0]
            
            # Thread counts
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM message_threads 
                GROUP BY status
            """)
            thread_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            'total_messages': sum(status_counts.values()),
            'status_counts': status_counts,
            'type_counts': type_counts,
            'active_agents': active_agents,
            'registered_agents': len(self.agent_capabilities),
            'thread_counts': thread_counts,
            'queue_sizes': {
                'delivery_queue': self.delivery_queue.qsize(),
                'retry_queue': self.retry_queue.qsize()
            }
        }
    
    def shutdown(self):
        """Shutdown the messaging layer"""
        self.running = False
        
        # Wait for background threads to finish
        if self.delivery_thread.is_alive():
            self.delivery_thread.join(timeout=5)
        if self.retry_thread.is_alive():
            self.retry_thread.join(timeout=5)
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        logger.info("Agent Messaging Layer shutdown complete")
