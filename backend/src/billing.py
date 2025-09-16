#!/usr/bin/env python3
"""
Billing System for System Builder Hub
Handles plans, subscriptions, usage counters, invoices, and webhook processing.
"""

import os
import json
import time
import logging
import sqlite3
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from flask import request, current_app, g
from config import config

logger = logging.getLogger(__name__)

class PlanType(Enum):
    """Plan types"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    TRIAL = "trial"

class InvoiceStatus(Enum):
    """Invoice status"""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"

@dataclass
class Plan:
    """Billing plan"""
    id: str
    name: str
    type: PlanType
    price_monthly: float
    price_yearly: float
    currency: str
    features: Dict[str, Any]
    limits: Dict[str, int]
    active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Subscription:
    """User subscription"""
    id: str
    user_id: str
    tenant_id: str
    plan_id: str
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    trial_start: Optional[datetime]
    trial_end: Optional[datetime]
    created_at: datetime
    updated_at: datetime

@dataclass
class UsageCounter:
    """Usage counter for billing"""
    id: str
    user_id: str
    tenant_id: str
    counter_type: str
    current_usage: int
    limit: int
    reset_date: datetime
    created_at: datetime
    updated_at: datetime

@dataclass
class Invoice:
    """Billing invoice"""
    id: str
    user_id: str
    tenant_id: str
    subscription_id: str
    amount: float
    currency: str
    status: InvoiceStatus
    due_date: datetime
    paid_at: Optional[datetime]
    metadata: Dict[str, Any]
    created_at: datetime

class BillingManager:
    """Manages billing operations"""
    
    def __init__(self):
        self._init_database()
        self._ensure_default_plans()
    
    def _init_database(self):
        """Initialize billing database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create plans table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS plans (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        price_monthly REAL NOT NULL,
                        price_yearly REAL NOT NULL,
                        currency TEXT NOT NULL,
                        features TEXT,
                        limits TEXT,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create subscriptions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        plan_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        current_period_start TIMESTAMP NOT NULL,
                        current_period_end TIMESTAMP NOT NULL,
                        cancel_at_period_end BOOLEAN DEFAULT FALSE,
                        trial_start TIMESTAMP,
                        trial_end TIMESTAMP,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (plan_id) REFERENCES plans (id)
                    )
                ''')
                
                # Create usage_counters table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_counters (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        counter_type TEXT NOT NULL,
                        current_usage INTEGER DEFAULT 0,
                        limit_value INTEGER NOT NULL,
                        reset_date TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create invoices table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS invoices (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        subscription_id TEXT NOT NULL,
                        amount REAL NOT NULL,
                        currency TEXT NOT NULL,
                        status TEXT NOT NULL,
                        due_date TIMESTAMP NOT NULL,
                        paid_at TIMESTAMP,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Billing database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize billing database: {e}")
    
    def _ensure_default_plans(self):
        """Ensure default billing plans exist"""
        plans = self.list_plans()
        if not plans:
            # Create default plans
            self.create_plan(
                name="Free",
                type=PlanType.FREE,
                price_monthly=0.0,
                price_yearly=0.0,
                currency="USD",
                features={
                    "previews": True,
                    "basic_export": True,
                    "community_support": True
                },
                limits={
                    "active_previews": 2,
                    "exports_per_month": 5,
                    "storage_gb": 1
                }
            )
            
            self.create_plan(
                name="Basic",
                type=PlanType.BASIC,
                price_monthly=29.0,
                price_yearly=290.0,
                currency="USD",
                features={
                    "previews": True,
                    "advanced_export": True,
                    "priority_support": True,
                    "custom_branding": True
                },
                limits={
                    "active_previews": 10,
                    "exports_per_month": 50,
                    "storage_gb": 10
                }
            )
            
            self.create_plan(
                name="Pro",
                type=PlanType.PRO,
                price_monthly=99.0,
                price_yearly=990.0,
                currency="USD",
                features={
                    "previews": True,
                    "advanced_export": True,
                    "priority_support": True,
                    "custom_branding": True,
                    "api_access": True,
                    "advanced_analytics": True
                },
                limits={
                    "active_previews": 50,
                    "exports_per_month": 200,
                    "storage_gb": 100
                }
            )
            
            self.create_plan(
                name="Enterprise",
                type=PlanType.ENTERPRISE,
                price_monthly=299.0,
                price_yearly=2990.0,
                currency="USD",
                features={
                    "previews": True,
                    "advanced_export": True,
                    "dedicated_support": True,
                    "custom_branding": True,
                    "api_access": True,
                    "advanced_analytics": True,
                    "sso": True,
                    "custom_integrations": True
                },
                limits={
                    "active_previews": 200,
                    "exports_per_month": 1000,
                    "storage_gb": 1000
                }
            )
            
            logger.info("Created default billing plans")
    
    def create_plan(self, name: str, type: PlanType, price_monthly: float, price_yearly: float,
                   currency: str, features: Dict[str, Any], limits: Dict[str, int]) -> Plan:
        """Create a new billing plan"""
        plan_id = f"plan_{int(time.time())}"
        now = datetime.now()
        
        plan = Plan(
            id=plan_id,
            name=name,
            type=type,
            price_monthly=price_monthly,
            price_yearly=price_yearly,
            currency=currency,
            features=features,
            limits=limits,
            active=True,
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO plans 
                    (id, name, type, price_monthly, price_yearly, currency, features, limits, 
                     active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    plan.id,
                    plan.name,
                    plan.type.value,
                    plan.price_monthly,
                    plan.price_yearly,
                    plan.currency,
                    json.dumps(plan.features),
                    json.dumps(plan.limits),
                    plan.active,
                    plan.created_at.isoformat(),
                    plan.updated_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created billing plan: {plan_id}")
                return plan
                
        except Exception as e:
            logger.error(f"Failed to create billing plan: {e}")
            raise
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get billing plan by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM plans WHERE id = ?', (plan_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Plan(
                    id=row[0],
                    name=row[1],
                    type=PlanType(row[2]),
                    price_monthly=row[3],
                    price_yearly=row[4],
                    currency=row[5],
                    features=json.loads(row[6]) if row[6] else {},
                    limits=json.loads(row[7]) if row[7] else {},
                    active=bool(row[8]),
                    created_at=datetime.fromisoformat(row[9]),
                    updated_at=datetime.fromisoformat(row[10])
                )
                
        except Exception as e:
            logger.error(f"Failed to get billing plan: {e}")
            return None
    
    def list_plans(self) -> List[Plan]:
        """List all billing plans"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM plans WHERE active = TRUE ORDER BY price_monthly ASC')
                rows = cursor.fetchall()
                
                return [Plan(
                    id=row[0],
                    name=row[1],
                    type=PlanType(row[2]),
                    price_monthly=row[3],
                    price_yearly=row[4],
                    currency=row[5],
                    features=json.loads(row[6]) if row[6] else {},
                    limits=json.loads(row[7]) if row[7] else {},
                    active=bool(row[8]),
                    created_at=datetime.fromisoformat(row[9]),
                    updated_at=datetime.fromisoformat(row[10])
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list billing plans: {e}")
            return []
    
    def create_subscription(self, user_id: str, tenant_id: str, plan_id: str, 
                           trial_days: int = 0) -> Subscription:
        """Create a new subscription"""
        subscription_id = f"sub_{int(time.time())}"
        now = datetime.now()
        
        # Get plan details
        plan = self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        # Calculate period dates
        current_period_start = now
        current_period_end = now + timedelta(days=30)  # Monthly billing
        
        # Set trial period if specified
        trial_start = None
        trial_end = None
        if trial_days > 0:
            trial_start = now
            trial_end = now + timedelta(days=trial_days)
            status = SubscriptionStatus.TRIAL
        else:
            status = SubscriptionStatus.ACTIVE
        
        subscription = Subscription(
            id=subscription_id,
            user_id=user_id,
            tenant_id=tenant_id,
            plan_id=plan_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=False,
            trial_start=trial_start,
            trial_end=trial_end,
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO subscriptions 
                    (id, user_id, tenant_id, plan_id, status, current_period_start, 
                     current_period_end, cancel_at_period_end, trial_start, trial_end, 
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    subscription.id,
                    subscription.user_id,
                    subscription.tenant_id,
                    subscription.plan_id,
                    subscription.status.value,
                    subscription.current_period_start.isoformat(),
                    subscription.current_period_end.isoformat(),
                    subscription.cancel_at_period_end,
                    subscription.trial_start.isoformat() if subscription.trial_start else None,
                    subscription.trial_end.isoformat() if subscription.trial_end else None,
                    subscription.created_at.isoformat(),
                    subscription.updated_at.isoformat()
                ))
                conn.commit()
                
                # Initialize usage counters
                self._initialize_usage_counters(user_id, tenant_id, plan)
                
                logger.info(f"Created subscription: {subscription_id}")
                return subscription
                
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            raise
    
    def _initialize_usage_counters(self, user_id: str, tenant_id: str, plan: Plan):
        """Initialize usage counters for a subscription"""
        try:
            now = datetime.now()
            reset_date = now + timedelta(days=30)  # Monthly reset
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                for counter_type, limit_value in plan.limits.items():
                    counter_id = f"counter_{int(time.time())}_{counter_type}"
                    cursor.execute('''
                        INSERT INTO usage_counters 
                        (id, user_id, tenant_id, counter_type, current_usage, limit_value, 
                         reset_date, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        counter_id,
                        user_id,
                        tenant_id,
                        counter_type,
                        0,
                        limit_value,
                        reset_date.isoformat(),
                        now.isoformat(),
                        now.isoformat()
                    ))
                
                conn.commit()
                logger.info(f"Initialized usage counters for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to initialize usage counters: {e}")
    
    def get_subscription(self, user_id: str, tenant_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM subscriptions 
                    WHERE user_id = ? AND tenant_id = ? AND status IN (?, ?, ?)
                    ORDER BY created_at DESC LIMIT 1
                ''', (
                    user_id, tenant_id,
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.TRIAL.value,
                    SubscriptionStatus.PAST_DUE.value
                ))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Subscription(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    plan_id=row[3],
                    status=SubscriptionStatus(row[4]),
                    current_period_start=datetime.fromisoformat(row[5]),
                    current_period_end=datetime.fromisoformat(row[6]),
                    cancel_at_period_end=bool(row[7]),
                    trial_start=datetime.fromisoformat(row[8]) if row[8] else None,
                    trial_end=datetime.fromisoformat(row[9]) if row[9] else None,
                    created_at=datetime.fromisoformat(row[10]),
                    updated_at=datetime.fromisoformat(row[11])
                )
                
        except Exception as e:
            logger.error(f"Failed to get subscription: {e}")
            return None
    
    def increment_usage(self, user_id: str, tenant_id: str, counter_type: str, amount: int = 1) -> bool:
        """Increment usage counter"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Get current usage
                cursor.execute('''
                    SELECT current_usage, limit_value, reset_date FROM usage_counters 
                    WHERE user_id = ? AND tenant_id = ? AND counter_type = ?
                ''', (user_id, tenant_id, counter_type))
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Usage counter not found: {counter_type}")
                    return False
                
                current_usage, limit_value, reset_date = row
                reset_date = datetime.fromisoformat(reset_date)
                
                # Check if counter needs reset
                if datetime.now() > reset_date:
                    current_usage = 0
                    reset_date = datetime.now() + timedelta(days=30)
                
                # Check if limit exceeded
                if current_usage + amount > limit_value:
                    logger.warning(f"Usage limit exceeded: {counter_type}")
                    return False
                
                # Update usage
                cursor.execute('''
                    UPDATE usage_counters 
                    SET current_usage = ?, reset_date = ?, updated_at = ?
                    WHERE user_id = ? AND tenant_id = ? AND counter_type = ?
                ''', (
                    current_usage + amount,
                    reset_date.isoformat(),
                    datetime.now().isoformat(),
                    user_id, tenant_id, counter_type
                ))
                conn.commit()
                
                logger.info(f"Incremented usage counter: {counter_type} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to increment usage: {e}")
            return False
    
    def get_usage(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Get current usage for user"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT counter_type, current_usage, limit_value, reset_date 
                    FROM usage_counters 
                    WHERE user_id = ? AND tenant_id = ?
                ''', (user_id, tenant_id))
                rows = cursor.fetchall()
                
                usage = {}
                for row in rows:
                    counter_type, current_usage, limit_value, reset_date = row
                    usage[counter_type] = {
                        'current': current_usage,
                        'limit': limit_value,
                        'reset_date': reset_date,
                        'percentage': (current_usage / limit_value * 100) if limit_value > 0 else 0
                    }
                
                return usage
                
        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return {}
    
    def create_invoice(self, user_id: str, tenant_id: str, subscription_id: str, 
                      amount: float, currency: str = "USD") -> Invoice:
        """Create a new invoice"""
        invoice_id = f"inv_{int(time.time())}"
        now = datetime.now()
        
        invoice = Invoice(
            id=invoice_id,
            user_id=user_id,
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            amount=amount,
            currency=currency,
            status=InvoiceStatus.OPEN,
            due_date=now + timedelta(days=30),
            paid_at=None,
            metadata={},
            created_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO invoices 
                    (id, user_id, tenant_id, subscription_id, amount, currency, status, 
                     due_date, paid_at, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice.id,
                    invoice.user_id,
                    invoice.tenant_id,
                    invoice.subscription_id,
                    invoice.amount,
                    invoice.currency,
                    invoice.status.value,
                    invoice.due_date.isoformat(),
                    invoice.paid_at.isoformat() if invoice.paid_at else None,
                    json.dumps(invoice.metadata),
                    invoice.created_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created invoice: {invoice_id}")
                return invoice
                
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise
    
    def process_webhook(self, payload: str, signature: str) -> bool:
        """Process webhook from payment provider"""
        try:
            # Verify webhook signature (Stripe-style)
            webhook_secret = os.getenv('BILLING_WEBHOOK_SECRET')
            if webhook_secret:
                expected_signature = hmac.new(
                    webhook_secret.encode(),
                    payload.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(f"sha256={expected_signature}", signature):
                    logger.error("Invalid webhook signature")
                    return False
            
            # Parse webhook data
            data = json.loads(payload)
            event_type = data.get('type')
            
            if event_type == 'invoice.payment_succeeded':
                return self._handle_payment_succeeded(data)
            elif event_type == 'invoice.payment_failed':
                return self._handle_payment_failed(data)
            elif event_type == 'customer.subscription.updated':
                return self._handle_subscription_updated(data)
            elif event_type == 'customer.subscription.deleted':
                return self._handle_subscription_deleted(data)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            return False
    
    def _handle_payment_succeeded(self, data: Dict[str, Any]) -> bool:
        """Handle successful payment webhook"""
        try:
            invoice_id = data.get('data', {}).get('object', {}).get('id')
            if invoice_id:
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE invoices 
                        SET status = ?, paid_at = ?
                        WHERE id = ?
                    ''', (
                        InvoiceStatus.PAID.value,
                        datetime.now().isoformat(),
                        invoice_id
                    ))
                    conn.commit()
                
                logger.info(f"Payment succeeded for invoice: {invoice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment succeeded: {e}")
            return False
    
    def _handle_payment_failed(self, data: Dict[str, Any]) -> bool:
        """Handle failed payment webhook"""
        try:
            invoice_id = data.get('data', {}).get('object', {}).get('id')
            if invoice_id:
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE invoices 
                        SET status = ?
                        WHERE id = ?
                    ''', (InvoiceStatus.UNCOLLECTIBLE.value, invoice_id))
                    conn.commit()
                
                logger.info(f"Payment failed for invoice: {invoice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle payment failed: {e}")
            return False
    
    def _handle_subscription_updated(self, data: Dict[str, Any]) -> bool:
        """Handle subscription update webhook"""
        try:
            subscription_id = data.get('data', {}).get('object', {}).get('id')
            status = data.get('data', {}).get('object', {}).get('status')
            
            if subscription_id and status:
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE subscriptions 
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                    ''', (status, datetime.now().isoformat(), subscription_id))
                    conn.commit()
                
                logger.info(f"Subscription updated: {subscription_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle subscription updated: {e}")
            return False
    
    def _handle_subscription_deleted(self, data: Dict[str, Any]) -> bool:
        """Handle subscription deletion webhook"""
        try:
            subscription_id = data.get('data', {}).get('object', {}).get('id')
            
            if subscription_id:
                with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE subscriptions 
                        SET status = ?, updated_at = ?
                        WHERE id = ?
                    ''', (SubscriptionStatus.CANCELED.value, datetime.now().isoformat(), subscription_id))
                    conn.commit()
                
                logger.info(f"Subscription canceled: {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle subscription deleted: {e}")
            return False
    
    def get_invoices(self, user_id: str, tenant_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's invoices"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM invoices 
                    WHERE user_id = ? AND tenant_id = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (user_id, tenant_id, limit))
                rows = cursor.fetchall()
                
                invoices = []
                for row in rows:
                    invoice = {
                        'id': row[0],
                        'user_id': row[1],
                        'tenant_id': row[2],
                        'subscription_id': row[3],
                        'amount': row[4],
                        'currency': row[5],
                        'status': row[6],
                        'due_date': row[7],
                        'paid_at': row[8],
                        'metadata': json.loads(row[9]) if row[9] else {},
                        'created_at': row[10]
                    }
                    invoices.append(invoice)
                
                return invoices
                
        except Exception as e:
            logger.error(f"Failed to get invoices: {e}")
            return []

# Global instance
billing_manager = BillingManager()
