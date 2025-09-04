"""
Jobs API for background task management
"""
import logging
from flask import Blueprint, jsonify, request
from rq import Queue
from rq.job import Job
from redis_core import get_rq_queue, redis_available
from jobs.tasks import generate_build_job, send_email_mock, process_payment_webhook

logger = logging.getLogger(__name__)

bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')

@bp.route('/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    if not redis_available():
        return jsonify({
            'success': False,
            'error': 'Redis not available'
        }), 503
    
    try:
        queue = get_rq_queue()
        if queue is None:
            return jsonify({
                'success': False,
                'error': 'Queue not available'
            }), 503
        
        job = Job.fetch(job_id, connection=queue.connection)
        
        status = {
            'job_id': job_id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        }
        
        if job.is_finished:
            status['result'] = job.result
        elif job.is_failed:
            status['error'] = str(job.exc_info)
        
        return jsonify({
            'success': True,
            'job': status
        })
        
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Job not found'
        }), 404

@bp.route('/enqueue/build', methods=['POST'])
def enqueue_build():
    """Enqueue a build job"""
    if not redis_available():
        return jsonify({
            'success': False,
            'error': 'Redis not available'
        }), 503
    
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'project_id is required'
            }), 400
        
        queue = get_rq_queue()
        if queue is None:
            return jsonify({
                'success': False,
                'error': 'Queue not available'
            }), 503
        
        job = queue.enqueue(generate_build_job, project_id)
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'status': 'queued'
        }), 202
        
    except Exception as e:
        logger.error(f"Error enqueueing build job: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to enqueue job'
        }), 500

@bp.route('/enqueue/email', methods=['POST'])
def enqueue_email():
    """Enqueue an email job"""
    if not redis_available():
        return jsonify({
            'success': False,
            'error': 'Redis not available'
        }), 503
    
    try:
        data = request.get_json()
        to_email = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not all([to_email, subject, body]):
            return jsonify({
                'success': False,
                'error': 'to, subject, and body are required'
            }), 400
        
        queue = get_rq_queue()
        if queue is None:
            return jsonify({
                'success': False,
                'error': 'Queue not available'
            }), 503
        
        job = queue.enqueue(send_email_mock, to_email, subject, body)
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'status': 'queued'
        }), 202
        
    except Exception as e:
        logger.error(f"Error enqueueing email job: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to enqueue job'
        }), 500

@bp.route('/enqueue/webhook', methods=['POST'])
def enqueue_webhook():
    """Enqueue a webhook processing job"""
    if not redis_available():
        return jsonify({
            'success': False,
            'error': 'Redis not available'
        }), 503
    
    try:
        data = request.get_json()
        event = data.get('event')
        
        if not event:
            return jsonify({
                'success': False,
                'error': 'event is required'
            }), 400
        
        queue = get_rq_queue()
        if queue is None:
            return jsonify({
                'success': False,
                'error': 'Queue not available'
            }), 503
        
        job = queue.enqueue(process_payment_webhook, event)
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'status': 'queued'
        }), 202
        
    except Exception as e:
        logger.error(f"Error enqueueing webhook job: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to enqueue job'
        }), 500
