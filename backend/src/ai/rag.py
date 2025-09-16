"""
RAG (Retrieval-Augmented Generation) service for CRM/Ops Template
"""
import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import db_session
from src.ai.models import AIEmbedding
from src.ai.schemas import RAGSearchRequest, RAGSearchResponse, RAGIndexRequest, RAGIndexResponse
from src.llm.orchestration import LLMOrchestration
import redis

logger = logging.getLogger(__name__)

class RAGService:
    """Service for RAG operations"""
    
    def __init__(self):
        self.llm_orchestration = LLMOrchestration()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def search_rag(self, request: RAGSearchRequest) -> RAGSearchResponse:
        """Search RAG index"""
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(request.query)
            
            # Search for similar chunks
            matches = self._search_similar_chunks(
                query_embedding, request.tenant_id, request.filters, request.limit
            )
            
            # Generate answer if requested
            answer = None
            if matches:
                answer = self._generate_answer(request.query, matches)
            
            # Extract sources
            sources = self._extract_sources(matches)
            
            return RAGSearchResponse(
                matches=matches,
                answer=answer,
                sources=sources,
                metrics={
                    'query_length': len(request.query),
                    'matches_found': len(matches),
                    'search_time_ms': 0  # Would be calculated in real implementation
                }
            )
            
        except Exception as e:
            logger.error(f"Error in RAG search: {e}")
            raise
    
    def index_rag(self, request: RAGIndexRequest) -> RAGIndexResponse:
        """Index content for RAG"""
        try:
            # Create indexing job
            job_id = f"rag_index_{request.tenant_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Start indexing process
            self._start_indexing_job(job_id, request)
            
            return RAGIndexResponse(
                job_id=job_id,
                status='started',
                scopes=request.scopes,
                estimated_duration=self._estimate_indexing_duration(request.scopes)
            )
            
        except Exception as e:
            logger.error(f"Error in RAG indexing: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        # In production, this would use an embedding model
        # For now, return a placeholder embedding
        
        # This is a stub implementation
        # In real implementation, you would:
        # 1. Use a service like OpenAI embeddings, Cohere, or local models
        # 2. Handle different text lengths and chunking
        # 3. Cache embeddings for performance
        # 4. Handle rate limits and quotas
        
        # Placeholder embedding (512-dimensional)
        import random
        random.seed(hash(text) % 2**32)
        embedding = [random.uniform(-1, 1) for _ in range(512)]
        
        return embedding
    
    def _search_similar_chunks(self, query_embedding: List[float], tenant_id: str, 
                              filters: Optional[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity"""
        try:
            with db_session() as session:
                # Build query
                query = session.query(AIEmbedding).filter(
                    AIEmbedding.tenant_id == tenant_id
                )
                
                # Apply filters
                if filters:
                    if 'source_type' in filters:
                        query = query.filter(AIEmbedding.source_type == filters['source_type'])
                    
                    if 'date_range' in filters:
                        start_date = filters['date_range'].get('start')
                        end_date = filters['date_range'].get('end')
                        if start_date:
                            query = query.filter(AIEmbedding.created_at >= start_date)
                        if end_date:
                            query = query.filter(AIEmbedding.created_at <= end_date)
                
                # Get embeddings
                embeddings = query.limit(limit * 2).all()  # Get more for similarity calculation
                
                # Calculate similarities (cosine similarity)
                similarities = []
                for embedding in embeddings:
                    similarity = self._cosine_similarity(query_embedding, embedding.vector or [])
                    similarities.append((similarity, embedding))
                
                # Sort by similarity and return top matches
                similarities.sort(key=lambda x: x[0], reverse=True)
                top_matches = similarities[:limit]
                
                return [
                    {
                        'chunk_id': match[1].chunk_id,
                        'content': match[1].content,
                        'source_type': match[1].source_type,
                        'source_id': match[1].source_id,
                        'similarity': match[0],
                        'metadata': match[1].meta or {}
                    }
                    for match in top_matches
                ]
                
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _generate_answer(self, query: str, matches: List[Dict[str, Any]]) -> str:
        """Generate answer using retrieved chunks"""
        # Build context from matches
        context = "\n\n".join([match['content'] for match in matches])
        
        prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {query}

Answer:"""

        answer = self.llm_orchestration.generate(prompt)
        return answer
    
    def _extract_sources(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information from matches"""
        sources = []
        seen_sources = set()
        
        for match in matches:
            source_key = f"{match['source_type']}:{match['source_id']}"
            
            if source_key not in seen_sources:
                sources.append({
                    'source_type': match['source_type'],
                    'source_id': match['source_id'],
                    'title': match['metadata'].get('title', ''),
                    'url': match['metadata'].get('url', ''),
                    'created_at': match['metadata'].get('created_at', ''),
                    'relevance_score': match['similarity']
                })
                seen_sources.add(source_key)
        
        return sources
    
    def _start_indexing_job(self, job_id: str, request: RAGIndexRequest):
        """Start indexing job"""
        # This would use Redis/RQ to start a background job
        # For now, just log the job start
        
        logger.info(f"Starting RAG indexing job {job_id} for tenant {request.tenant_id}")
        
        # In production, this would:
        # 1. Enqueue a background job
        # 2. Process each scope (contacts, deals, tasks, files)
        # 3. Chunk content and generate embeddings
        # 4. Store in database with metadata
        # 5. Update job status
    
    def _estimate_indexing_duration(self, scopes: List[str]) -> int:
        """Estimate indexing duration in seconds"""
        # Rough estimation based on scope count
        base_duration = 30  # seconds per scope
        return len(scopes) * base_duration
    
    def index_contacts(self, tenant_id: str):
        """Index contacts for RAG"""
        try:
            from src.crm_ops.models import Contact
            
            with db_session() as session:
                contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).all()
                
                for contact in contacts:
                    # Create chunks from contact data
                    chunks = self._chunk_contact_data(contact)
                    
                    # Generate embeddings and store
                    for i, chunk in enumerate(chunks):
                        embedding = self._generate_embedding(chunk['content'])
                        
                        ai_embedding = AIEmbedding(
                            tenant_id=tenant_id,
                            source_type='contact',
                            source_id=str(contact.id),
                            chunk_id=f"{contact.id}_chunk_{i}",
                            content=chunk['content'],
                            vector=embedding,
                            meta={
                                'title': f"{contact.first_name} {contact.last_name}",
                                'email': contact.email,
                                'company': contact.company,
                                'created_at': contact.created_at.isoformat() if contact.created_at else None
                            }
                        )
                        
                        session.add(ai_embedding)
                
                session.commit()
                logger.info(f"Indexed {len(contacts)} contacts for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error indexing contacts: {e}")
    
    def index_deals(self, tenant_id: str):
        """Index deals for RAG"""
        try:
            from src.crm_ops.models import Deal
            
            with db_session() as session:
                deals = session.query(Deal).filter(Deal.tenant_id == tenant_id).all()
                
                for deal in deals:
                    # Create chunks from deal data
                    chunks = self._chunk_deal_data(deal)
                    
                    # Generate embeddings and store
                    for i, chunk in enumerate(chunks):
                        embedding = self._generate_embedding(chunk['content'])
                        
                        ai_embedding = AIEmbedding(
                            tenant_id=tenant_id,
                            source_type='deal',
                            source_id=str(deal.id),
                            chunk_id=f"{deal.id}_chunk_{i}",
                            content=chunk['content'],
                            vector=embedding,
                            meta={
                                'title': deal.title,
                                'value': deal.value,
                                'pipeline_stage': deal.pipeline_stage,
                                'status': deal.status,
                                'created_at': deal.created_at.isoformat() if deal.created_at else None
                            }
                        )
                        
                        session.add(ai_embedding)
                
                session.commit()
                logger.info(f"Indexed {len(deals)} deals for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error indexing deals: {e}")
    
    def index_tasks(self, tenant_id: str):
        """Index tasks for RAG"""
        try:
            from src.crm_ops.models import Task
            
            with db_session() as session:
                tasks = session.query(Task).filter(Task.tenant_id == tenant_id).all()
                
                for task in tasks:
                    # Create chunks from task data
                    chunks = self._chunk_task_data(task)
                    
                    # Generate embeddings and store
                    for i, chunk in enumerate(chunks):
                        embedding = self._generate_embedding(chunk['content'])
                        
                        ai_embedding = AIEmbedding(
                            tenant_id=tenant_id,
                            source_type='task',
                            source_id=str(task.id),
                            chunk_id=f"{task.id}_chunk_{i}",
                            content=chunk['content'],
                            vector=embedding,
                            meta={
                                'title': task.title,
                                'status': task.status,
                                'priority': task.priority,
                                'assignee_id': task.assignee_id,
                                'created_at': task.created_at.isoformat() if task.created_at else None
                            }
                        )
                        
                        session.add(ai_embedding)
                
                session.commit()
                logger.info(f"Indexed {len(tasks)} tasks for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Error indexing tasks: {e}")
    
    def _chunk_contact_data(self, contact) -> List[Dict[str, str]]:
        """Chunk contact data for indexing"""
        chunks = []
        
        # Basic info chunk
        basic_info = f"Contact: {contact.first_name} {contact.last_name}"
        if contact.email:
            basic_info += f", Email: {contact.email}"
        if contact.phone:
            basic_info += f", Phone: {contact.phone}"
        if contact.company:
            basic_info += f", Company: {contact.company}"
        
        chunks.append({'content': basic_info})
        
        # Tags chunk
        if contact.tags:
            tags_text = f"Tags: {', '.join(contact.tags)}"
            chunks.append({'content': tags_text})
        
        # Custom fields chunk
        if contact.custom_fields:
            custom_fields_text = f"Additional information: {json.dumps(contact.custom_fields)}"
            chunks.append({'content': custom_fields_text})
        
        return chunks
    
    def _chunk_deal_data(self, deal) -> List[Dict[str, str]]:
        """Chunk deal data for indexing"""
        chunks = []
        
        # Basic info chunk
        basic_info = f"Deal: {deal.title}"
        if deal.value:
            basic_info += f", Value: ${deal.value:,.0f}"
        basic_info += f", Stage: {deal.pipeline_stage}, Status: {deal.status}"
        
        chunks.append({'content': basic_info})
        
        # Notes chunk
        if deal.notes:
            chunks.append({'content': f"Notes: {deal.notes}"})
        
        # Custom fields chunk
        if deal.custom_fields:
            custom_fields_text = f"Additional information: {json.dumps(deal.custom_fields)}"
            chunks.append({'content': custom_fields_text})
        
        return chunks
    
    def _chunk_task_data(self, task) -> List[Dict[str, str]]:
        """Chunk task data for indexing"""
        chunks = []
        
        # Basic info chunk
        basic_info = f"Task: {task.title}"
        basic_info += f", Status: {task.status}, Priority: {task.priority}"
        if task.assignee_id:
            basic_info += f", Assigned to: {task.assignee_id}"
        
        chunks.append({'content': basic_info})
        
        # Description chunk
        if task.description:
            chunks.append({'content': f"Description: {task.description}"})
        
        return chunks
    
    def get_indexing_status(self, tenant_id: str) -> Dict[str, Any]:
        """Get indexing status for tenant"""
        try:
            with db_session() as session:
                # Count embeddings by source type
                stats = session.query(
                    AIEmbedding.source_type,
                    func.count(AIEmbedding.id).label('count')
                ).filter(
                    AIEmbedding.tenant_id == tenant_id
                ).group_by(AIEmbedding.source_type).all()
                
                return {
                    'tenant_id': tenant_id,
                    'total_chunks': sum(stat.count for stat in stats),
                    'by_source_type': {stat.source_type: stat.count for stat in stats},
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting indexing status: {e}")
            return {
                'tenant_id': tenant_id,
                'total_chunks': 0,
                'by_source_type': {},
                'error': str(e)
            }
