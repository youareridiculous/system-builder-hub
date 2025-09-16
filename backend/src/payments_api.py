"""
Payments API - Stripe integration for subscriptions
"""
import logging
import os
import hmac
import hashlib
from functools import wraps
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify, current_app
from .auth_api import require_auth, get_current_user
from .db import get_db, get_user_subscription, is_subscription_active, update_subscription_from_webhook

logger = logging.getLogger(__name__)

bp = Blueprint("payments", __name__, url_prefix="/api/payments")

# Mock Stripe for development (replace with real Stripe in production)
class MockStripe:
    """Mock Stripe client for development"""
    
    @staticmethod
    def create_checkout_session(price_id: str, success_url: str, cancel_url: str, customer_email: str = None):
        """Mock checkout session creation"""
        return {
            'id': 'cs_mock_' + os.urandom(8).hex(),
            'url': success_url + '?session_id=cs_mock_' + os.urandom(8).hex(),
            'status': 'open'
        }
    
    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str, secret: str):
        """Mock webhook event construction"""
        # In real implementation, this would verify the signature
        return {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_mock_' + os.urandom(8).hex(),
                    'customer_email': 'test@example.com',
                    'metadata': {
                        'user_id': '1',
                        'plan': 'pro'
                    }
                }
            }
        }

# Use mock Stripe in development
stripe = MockStripe()

def require_subscription(plan: Optional[str] = None):
    """Decorator to require active subscription and optionally specific plan"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Check subscription status
            db = get_db(current_app.config.get('DATABASE', 'system_builder_hub.db'))
            if not is_subscription_active(db, user['id'], plan):
                return jsonify({
                    'error': 'Subscription required',
                    'message': f'Active subscription{" to " + plan if plan else ""} required'
                }), 403
            
            # Add user to request context
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_available_plans() -> List[Dict[str, Any]]:
    """Get available subscription plans"""
    return [
        {
            'id': 'basic',
            'name': 'Basic',
            'price': 9.99,
            'interval': 'month',
            'features': ['Basic features', 'Email support']
        },
        {
            'id': 'pro',
            'name': 'Pro',
            'price': 29.99,
            'interval': 'month',
            'features': ['All Basic features', 'Priority support', 'Advanced analytics']
        },
        {
            'id': 'enterprise',
            'name': 'Enterprise',
            'price': 99.99,
            'interval': 'month',
            'features': ['All Pro features', 'Dedicated support', 'Custom integrations']
        }
    ]

@bp.route("/plans", methods=["GET"])
def get_plans():
    """Get available subscription plans"""
    try:
        plans = get_available_plans()
        return jsonify({
            'success': True,
            'plans': plans
        }), 200
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        return jsonify({'error': 'Failed to get plans'}), 500

@bp.route("/create-checkout", methods=["POST"])
@require_auth
def create_checkout():
    """Create Stripe checkout session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        plan_id = data.get('plan_id')
        if not plan_id:
            return jsonify({'error': 'plan_id is required'}), 400
        
        # Get plan details
        plans = get_available_plans()
        plan = next((p for p in plans if p['id'] == plan_id), None)
        if not plan:
            return jsonify({'error': 'Invalid plan_id'}), 400
        
        user = request.current_user
        
        # Create checkout session
        success_url = current_app.config.get('PUBLIC_BASE_URL', 'http://localhost:5001') + '/ui/subscription?success=true'
        cancel_url = current_app.config.get('PUBLIC_BASE_URL', 'http://localhost:5001') + '/ui/subscription?canceled=true'
        
        session = stripe.create_checkout_session(
            price_id=f"price_{plan_id}",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user['email']
        )
        
        return jsonify({
            'success': True,
            'checkout_url': session['url'],
            'session_id': session['id']
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@bp.route("/webhook", methods=["POST"])
def webhook():
    """Handle Stripe webhooks"""
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Verify webhook signature (in production, use real Stripe secret)
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET', 'whsec_test')
        
        try:
            event = stripe.construct_webhook_event(payload, sig_header, webhook_secret)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Enqueue webhook processing for background handling
        try:
            from .redis_core import redis_available, get_rq_queue
            from .jobs.tasks import process_payment_webhook
            
            if redis_available():
                queue = get_rq_queue()
                if queue:
                    # Enqueue the webhook processing
                    job = queue.enqueue(process_payment_webhook, event)
                    logger.info(f"Webhook processing queued: {event['type']} (job_id: {job.id})")
                    
                    # Return immediately - webhook will be processed in background
                    return jsonify({
                        'success': True,
                        'status': 'queued',
                        'job_id': job.id,
                        'message': 'Webhook queued for background processing'
                    }), 202
                else:
                    logger.warning("Queue not available, processing webhook synchronously")
            else:
                logger.warning("Redis not available, processing webhook synchronously")
        except Exception as e:
            logger.warning(f"Background processing failed, falling back to sync: {e}")
        
        # Fallback to synchronous processing
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = int(session['metadata']['user_id'])
            plan = session['metadata']['plan']
            
            # Update user subscription
            db = get_db(current_app.config.get('DATABASE', 'system_builder_hub.db'))
            update_subscription_from_webhook(db, user_id, plan, 'active')
            
            logger.info(f"Subscription activated for user {user_id}: {plan}")
            
        elif event['type'] == 'customer.subscription.deleted':
            # Handle subscription cancellation
            subscription = event['data']['object']
            user_id = int(subscription['metadata']['user_id'])
            
            db = get_db(current_app.config.get('DATABASE', 'system_builder_hub.db'))
            update_subscription_from_webhook(db, user_id, 'free', 'canceled')
            
            logger.info(f"Subscription canceled for user {user_id}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@bp.route("/status", methods=["GET"])
@require_auth
def subscription_status():
    """Get current user's subscription status"""
    try:
        user = request.current_user
        db = get_db(current_app.config.get('DATABASE', 'system_builder_hub.db'))
        
        subscription = get_user_subscription(db, user['id'])
        if not subscription:
            return jsonify({'error': 'Subscription not found'}), 404
        
        # Check if subscription is active
        is_active = is_subscription_active(db, user['id'])
        
        return jsonify({
            'success': True,
            'subscription': {
                'plan': subscription['subscription_plan'],
                'status': subscription['subscription_status'],
                'trial_end': subscription['trial_end'],
                'is_active': is_active
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        return jsonify({'error': 'Failed to get subscription status'}), 500

@bp.route("/cancel", methods=["POST"])
@require_auth
def cancel_subscription():
    """Cancel user's subscription"""
    try:
        user = request.current_user
        db = get_db(current_app.config.get('DATABASE', 'system_builder_hub.db'))
        
        # Update subscription status to canceled
        update_subscription_from_webhook(db, user['id'], 'free', 'canceled')
        
        return jsonify({
            'success': True,
            'message': 'Subscription canceled successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500
