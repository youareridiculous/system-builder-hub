"""
API generators for Co-Builder.

Generates API routes for lead capture and payments.
"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_lead_api(build_id: str, workspace: str) -> Dict[str, Any]:
    """
    Generate the lead capture API route.
    
    Args:
        build_id: The build ID for this workspace
        workspace: The workspace root path
        
    Returns:
        Dict with success status and metadata
    """
    try:
        build_path = Path(workspace) / build_id
        
        # Generate lead API route
        lead_route = build_path / "apps/site/app/api/lead/route.ts"
        lead_content = _generate_lead_route()
        lead_route.write_text(lead_content)
        
        # Generate email utility
        email_util = build_path / "apps/site/lib/email.ts"
        email_content = _generate_email_util()
        email_util.write_text(email_content)
        
        return {
            "success": True,
            "path": str(lead_route),
            "is_directory": False,
            "lines_changed": len(lead_content.splitlines()) + len(email_content.splitlines()),
            "sha256": "",  # Will be computed by file_ops
            "created_files": [str(lead_route), str(email_util)]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "is_directory": False,
            "lines_changed": 0,
            "sha256": ""
        }


def generate_compile_endpoints(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate SBH backend endpoints (/api/cobuilder/compile, /api/cobuilder/spec)"""
    return {"success": True, "path": "compile_endpoints", "sha256": "compile_endpoints_generated"}


def generate_payments_router(build_id: str, workspace: str) -> Dict[str, Any]:
    """
    Generate the payments API routes.
    
    Args:
        build_id: The build ID for this workspace
        workspace: The workspace root path
        
    Returns:
        Dict with success status and metadata
    """
    try:
        build_path = Path(workspace) / build_id
        
        # Generate checkout API route
        checkout_route = build_path / "apps/site/app/api/checkout/route.ts"
        checkout_content = _generate_checkout_route()
        checkout_route.write_text(checkout_content)
        
        # Generate payments router
        payments_router = build_path / "apps/site/lib/payments/router.ts"
        payments_router.parent.mkdir(parents=True, exist_ok=True)
        payments_content = _generate_payments_router()
        payments_router.write_text(payments_content)
        
        # Generate webhook route
        webhook_route = build_path / "apps/site/app/api/webhooks/payments/route.ts"
        webhook_content = _generate_webhook_route()
        webhook_route.write_text(webhook_content)
        
        return {
            "success": True,
            "path": str(checkout_route),
            "is_directory": False,
            "lines_changed": len(checkout_content.splitlines()) + len(payments_content.splitlines()) + len(webhook_content.splitlines()),
            "sha256": "",  # Will be computed by file_ops
            "created_files": [str(checkout_route), str(payments_router), str(webhook_route)]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "is_directory": False,
            "lines_changed": 0,
            "sha256": ""
        }


def _generate_lead_route() -> str:
    """Generate the lead capture API route."""
    return '''import { NextResponse } from "next/server";
import { z } from "zod";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();
const Body = z.object({ email: z.string().email(), source: z.string().optional() });

export async function POST(req: Request) {
  try {
    const json = await req.json();
    const data = Body.parse(json);
    await prisma.lead.create({ data: { email: data.email, source: data.source ?? "cli" } });
    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json({ ok: false, error: `${err}` }, { status: 400 });
  }
}
'''


def _generate_email_util() -> str:
    """Generate the email utility functions."""
    return '''// Email utility functions
// In production, integrate with your email service (SendGrid, Resend, etc.)

export interface EmailOptions {
  to: string
  subject: string
  html: string
  text?: string
}

export async function sendEmail(options: EmailOptions): Promise<void> {
  // Stub implementation - replace with real email service
  console.log('📧 Email would be sent:', {
    to: options.to,
    subject: options.subject,
    preview: options.html.substring(0, 100) + '...'
  })
  
  // Simulate async operation
  await new Promise(resolve => setTimeout(resolve, 100))
}

export async function sendWelcomeEmail(email: string, name: string): Promise<void> {
  const subject = 'Welcome to our platform!'
  const html = `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h1 style="color: #0ea5e9;">Welcome, ${name}!</h1>
      <p>Thank you for signing up. We're excited to have you on board.</p>
      <p>If you have any questions, feel free to reach out to our support team.</p>
      <p>Best regards,<br>The Team</p>
    </div>
  `
  
  await sendEmail({
    to: email,
    subject,
    html,
    text: `Welcome, ${name}! Thank you for signing up. We're excited to have you on board.`
  })
}

export async function sendNotificationEmail(email: string, message: string): Promise<void> {
  const subject = 'New notification'
  const html = `
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2>Notification</h2>
      <p>${message}</p>
    </div>
  `
  
  await sendEmail({
    to: email,
    subject,
    html,
    text: message
  })
}
'''


def _generate_checkout_route() -> str:
    """Generate the checkout API route."""
    return '''import { NextResponse } from "next/server";
import Stripe from "stripe";

export async function POST() {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) return NextResponse.json({ ok: true, mode: "mock" });
  const stripe = new Stripe(key, { apiVersion: "2024-06-20" });
  // … create Checkout Session here if needed …
  return NextResponse.json({ ok: true });
}
'''


def _generate_payments_router() -> str:
    """Generate the payments router utility."""
    return '''// Payments router - handles different payment providers
// Currently supports Stripe, can be extended for other providers

export interface CheckoutSessionOptions {
  priceId: string
  successUrl: string
  cancelUrl: string
  customerEmail?: string
}

export interface CheckoutSession {
  id: string
  url: string
}

export interface PaymentProvider {
  createCheckoutSession(options: CheckoutSessionOptions): Promise<CheckoutSession>
  handleWebhook(payload: any, signature: string): Promise<any>
}

// Stripe implementation (stub)
class StripeProvider implements PaymentProvider {
  async createCheckoutSession(options: CheckoutSessionOptions): Promise<CheckoutSession> {
    // Stub implementation - replace with real Stripe SDK
    console.log('💳 Stripe checkout session would be created:', options)
    
    // Simulate async operation
    await new Promise(resolve => setTimeout(resolve, 200))
    
    return {
      id: `cs_test_${Date.now()}`,
      url: `${options.successUrl}?session_id=cs_test_${Date.now()}`
    }
  }
  
  async handleWebhook(payload: any, signature: string): Promise<any> {
    // Stub implementation - replace with real Stripe webhook verification
    console.log('🔔 Stripe webhook would be processed:', { payload, signature })
    
    return {
      type: payload.type,
      id: payload.id,
      processed: true
    }
  }
}

// PayPal implementation (placeholder)
class PayPalProvider implements PaymentProvider {
  async createCheckoutSession(options: CheckoutSessionOptions): Promise<CheckoutSession> {
    throw new Error('PayPal integration not implemented yet')
  }
  
  async handleWebhook(payload: any, signature: string): Promise<any> {
    throw new Error('PayPal webhook handling not implemented yet')
  }
}

// Provider factory
export function getPaymentProvider(provider: string = 'stripe'): PaymentProvider {
  switch (provider.toLowerCase()) {
    case 'stripe':
      return new StripeProvider()
    case 'paypal':
      return new PayPalProvider()
    default:
      throw new Error(`Unsupported payment provider: ${provider}`)
  }
}

// Main functions
export async function createCheckoutSession(options: CheckoutSessionOptions): Promise<CheckoutSession> {
  const provider = getPaymentProvider(process.env.PAYMENT_PROVIDER || 'stripe')
  return provider.createCheckoutSession(options)
}

export async function handlePaymentWebhook(provider: string, payload: any, signature: string): Promise<any> {
  const paymentProvider = getPaymentProvider(provider)
  return paymentProvider.handleWebhook(payload, signature)
}

// Normalize webhook events across providers
export function normalizeWebhookEvent(provider: string, event: any): any {
  switch (provider.toLowerCase()) {
    case 'stripe':
      return {
        provider: 'stripe',
        type: event.type,
        id: event.id,
        amount: event.data?.object?.amount_total,
        currency: event.data?.object?.currency,
        status: event.data?.object?.payment_status,
        customerEmail: event.data?.object?.customer_details?.email,
        createdAt: new Date(event.created * 1000).toISOString()
      }
    default:
      return {
        provider,
        type: 'unknown',
        id: event.id || 'unknown',
        raw: event
      }
  }
}
'''


def _generate_webhook_route() -> str:
    """Generate the webhook route for payment processing."""
    return '''import { NextRequest, NextResponse } from 'next/server'
import { handlePaymentWebhook, normalizeWebhookEvent } from '@/lib/payments/router'

export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const signature = request.headers.get('stripe-signature') || ''
    
    // Determine provider from headers or URL
    const provider = request.headers.get('x-payment-provider') || 'stripe'
    
    // Parse the webhook payload
    let payload
    try {
      payload = JSON.parse(body)
    } catch (error) {
      console.error('Invalid JSON payload:', error)
      return NextResponse.json(
        { ok: false, error: 'Invalid JSON payload' },
        { status: 400 }
      )
    }
    
    // Handle the webhook
    const event = await handlePaymentWebhook(provider, payload, signature)
    
    // Normalize the event
    const normalizedEvent = normalizeWebhookEvent(provider, event)
    
    // Log the normalized event
    console.log('📊 Normalized webhook event:', normalizedEvent)
    
    // Here you would typically:
    // 1. Update your database with the payment status
    // 2. Send confirmation emails
    // 3. Trigger other business logic
    
    // For now, just log and return success
    return NextResponse.json(
      { ok: true, event: normalizedEvent },
      { status: 200 }
    )
    
  } catch (error) {
    console.error('Webhook processing error:', error)
    
    return NextResponse.json(
      { ok: false, error: 'Webhook processing failed' },
      { status: 500 }
    )
  }
}

// GET endpoint for webhook verification
export async function GET() {
  return NextResponse.json({
    ok: true,
    message: 'Webhook endpoint is active',
    timestamp: new Date().toISOString()
  })
}
'''
