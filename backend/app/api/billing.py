"""SaaS billing endpoints — Stripe checkout, subscriptions, portal, webhooks."""
from __future__ import annotations

import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.auth import get_current_user, UserInfo
from app.config import settings

router = APIRouter(prefix="/api/v1/saas/billing", tags=["saas-billing"])


def _init_stripe():
    """Initialize Stripe with the secret key."""
    stripe.api_key = settings.stripe_secret_key


# ── Request / Response models ──

class CheckoutRequest(BaseModel):
    """Create a Stripe Checkout Session for a la carte report purchase."""
    report_preview_id: str
    price_cents: int
    bbl: str
    address: Optional[str] = None
    buildable_sf: Optional[float] = None


class SubscribeRequest(BaseModel):
    """Create a Stripe Checkout Session for annual subscription."""
    pass  # No params needed — uses STRIPE_ANNUAL_PRICE_ID


class PortalRequest(BaseModel):
    """Redirect to Stripe Customer Portal."""
    pass


# ── In-memory user store (replace with DB later) ──
_user_stripe_map: dict[str, str] = {}  # clerk_user_id -> stripe_customer_id
_user_plans: dict[str, str] = {}  # clerk_user_id -> plan_type (a_la_carte | annual)


def _get_or_create_customer(user: UserInfo) -> str:
    """Get or create a Stripe customer for the user."""
    _init_stripe()

    if user.clerk_user_id in _user_stripe_map:
        return _user_stripe_map[user.clerk_user_id]

    # Search for existing customer by email
    if user.email:
        customers = stripe.Customer.list(email=user.email, limit=1)
        if customers.data:
            cust_id = customers.data[0].id
            _user_stripe_map[user.clerk_user_id] = cust_id
            return cust_id

    # Create new customer
    customer = stripe.Customer.create(
        email=user.email,
        name=f"{user.first_name or ''} {user.last_name or ''}".strip() or None,
        metadata={"clerk_user_id": user.clerk_user_id},
    )
    _user_stripe_map[user.clerk_user_id] = customer.id
    return customer.id


# ── POST /checkout — a la carte payment ──
@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, user: UserInfo = Depends(get_current_user)):
    """Create Stripe Checkout Session for a single report purchase."""
    _init_stripe()
    customer_id = _get_or_create_customer(user)

    # Check if user is on annual plan (free generation)
    if _user_plans.get(user.clerk_user_id) == "annual":
        return {
            "free": True,
            "message": "Annual subscribers get unlimited reports. Generating for free.",
        }

    frontend_url = settings.frontend_url or "http://localhost:3000"

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": req.price_cents,
                    "product_data": {
                        "name": f"Zoning Feasibility Report — {req.address or req.bbl}",
                        "description": f"BBL: {req.bbl} | {req.buildable_sf:,.0f} buildable SF" if req.buildable_sf else f"BBL: {req.bbl}",
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{frontend_url}/dashboard?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/dashboard/new-report?checkout=canceled",
            metadata={
                "clerk_user_id": user.clerk_user_id,
                "preview_id": req.report_preview_id,
                "bbl": req.bbl,
                "buildable_sf": str(req.buildable_sf or 0),
                "price_cents": str(req.price_cents),
            },
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"checkout_url": session.url, "session_id": session.id}


# ── POST /subscribe — annual subscription ──
@router.post("/subscribe")
async def create_subscription(user: UserInfo = Depends(get_current_user)):
    """Create Stripe Checkout Session for annual subscription."""
    _init_stripe()
    customer_id = _get_or_create_customer(user)

    annual_price_id = settings.stripe_annual_price_id
    if not annual_price_id:
        raise HTTPException(
            status_code=500,
            detail="Annual subscription not configured (STRIPE_ANNUAL_PRICE_ID missing)",
        )

    frontend_url = settings.frontend_url or "http://localhost:3000"

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": annual_price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{frontend_url}/dashboard/billing?subscription=success",
            cancel_url=f"{frontend_url}/dashboard/billing?subscription=canceled",
            metadata={"clerk_user_id": user.clerk_user_id},
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"checkout_url": session.url, "session_id": session.id}


# ── POST /portal — Stripe Customer Portal ──
@router.post("/portal")
async def create_portal_session(user: UserInfo = Depends(get_current_user)):
    """Create a Stripe Customer Portal session for billing management."""
    _init_stripe()
    customer_id = _get_or_create_customer(user)

    frontend_url = settings.frontend_url or "http://localhost:3000"

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{frontend_url}/dashboard/billing",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"portal_url": session.url}


# ── GET /me — user billing info ──
@router.get("/me")
async def get_billing_info(user: UserInfo = Depends(get_current_user)):
    """Get current user's billing information."""
    plan_type = _user_plans.get(user.clerk_user_id, "a_la_carte")
    has_customer = user.clerk_user_id in _user_stripe_map

    return {
        "clerk_user_id": user.clerk_user_id,
        "email": user.email,
        "plan_type": plan_type,
        "has_stripe_customer": has_customer,
    }


# ── POST /webhooks/stripe — Stripe webhook handler ──
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    _init_stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    webhook_secret = settings.stripe_webhook_secret
    if not webhook_secret:
        # In development, skip signature verification
        import json
        event = json.loads(payload)
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "") if isinstance(event, dict) else event.type
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif event_type == "customer.subscription.created":
        _handle_subscription_created(data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data)

    return {"status": "ok"}


def _handle_checkout_completed(session):
    """Process completed checkout — trigger report generation."""
    metadata = session.get("metadata", {}) if isinstance(session, dict) else session.metadata
    clerk_user_id = metadata.get("clerk_user_id")
    preview_id = metadata.get("preview_id")

    if clerk_user_id:
        # Store customer mapping
        customer_id = session.get("customer") if isinstance(session, dict) else session.customer
        if customer_id:
            _user_stripe_map[clerk_user_id] = customer_id

    # TODO: Trigger report generation via preview_id
    # This will be wired up with the reports_saas module


def _handle_subscription_created(subscription):
    """Process new subscription."""
    metadata = subscription.get("metadata", {}) if isinstance(subscription, dict) else subscription.metadata
    clerk_user_id = metadata.get("clerk_user_id")
    if clerk_user_id:
        _user_plans[clerk_user_id] = "annual"


def _handle_subscription_updated(subscription):
    """Process subscription update."""
    status = subscription.get("status") if isinstance(subscription, dict) else subscription.status
    metadata = subscription.get("metadata", {}) if isinstance(subscription, dict) else subscription.metadata
    clerk_user_id = metadata.get("clerk_user_id")
    if clerk_user_id and status in ("active", "trialing"):
        _user_plans[clerk_user_id] = "annual"


def _handle_subscription_deleted(subscription):
    """Process subscription cancellation."""
    metadata = subscription.get("metadata", {}) if isinstance(subscription, dict) else subscription.metadata
    clerk_user_id = metadata.get("clerk_user_id")
    if clerk_user_id:
        _user_plans[clerk_user_id] = "a_la_carte"


def _handle_payment_failed(invoice):
    """Handle failed payment."""
    # TODO: Mark user's subscription as past_due
    pass
