# Payments (Stripe)

Stripe integration for subscriptions, plans, and payments. The stack wires Stripe through better-auth (`@better-auth/stripe`) plus a custom **`stripe-plans`** plugin that stores plans in the DB.

## Locations

```
packages/payments/         → Stripe client singleton + helpers
packages/auth/src/plugins/stripe-plans/  → DB-backed plan management (BETTER-AUTH-PLUGIN.md)
packages/api/src/routers/  → billing/payments procedures
```

## Client & Env

```ts
// packages/payments — Stripe client singleton
import Stripe from "stripe";
import { env } from "@condomin-ia/env/server";

export const stripe = new Stripe(env.STRIPE_SECRET_KEY);
```

- `STRIPE_SECRET_KEY` (server env only, ENV.md). Never ship it to the client.
- Test mode: `sk_test_*` in dev/CI; webhook events via Stripe CLI (`stripe listen --forward-to localhost:3000/api/auth/stripe/webhook` or your webhook route).

## Subscriptions via @better-auth/stripe

`@better-auth/stripe` handles the subscription ↔ session ↔ user model: checkout session creation, subscription lifecycle, and webhooks are managed by the plugin. Use its endpoints/helpers rather than re-implementing Stripe calls:

```ts
// client
authClient.subscription.checkout({ plan: "pro", successUrl: "/billing", cancelUrl: "/billing" });
authClient.subscription.portal(); // customer portal

// server-side entitlement check in a procedure
const sub = await stripe.subscriptions.retrieve(user.subscriptionId);
const isActive = sub.status === "active" || sub.status === "trialing";
```

## Plan Gating

Plans come from the DB (`stripe-plans` plugin). Gate features by entitlement, not by Stripe status alone:

```ts
// capability-style check (MULTI-TENANCY.md) or a plan-level check
assertPlanAtLeast(membership, "pro"); // helper that maps plan → tier
```

- Free/pro/tiers live in the plans table; features gate on tier thresholds.
- Cache entitlement in the org/session layer where possible — don't hit Stripe on every list query.
- Downgrade/cancel: sync via webhook, then invalidate gated query keys.

## Webhooks

Webhooks are the source of truth for payment state changes — always process them and invalidate local data:

- **No session** — verify the Stripe signature instead (publicProcedure, raw body).
- **Idempotency** — store the `event.id` (or use Stripe's `Idempotency-Key`) and skip already-processed events.
- **Only POST** — Stripe only sends POST.
- Handle at least: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.

```ts
stripeWebhook: publicProcedure
  .input(z.object({ signature: z.string(), payload: z.string() }))
  .handler(async ({ input }) => {
    const event = stripe.webhooks.constructEvent(
      input.payload, input.signature, env.STRIPE_WEBHOOK_SECRET,
    );

    switch (event.type) {
      case "checkout.session.completed":
        await syncSubscription(event.data.object);
        break;
      case "invoice.payment_failed":
        await notifyPaymentFailed(event.data.object);
        break;
    }
    return { received: true };
  }),
```

After a sync, invalidate the affected org's billing query keys (QUERY_INVALIDATION.md).

## Money Handling

- Store amounts in **minor units (cents)** as integers — never floats.
- Format for display client-side only; never round on the server in a way that changes recorded totals.
- Currency is per-org/per-plan (`currency` column on plan/org) — don't hardcode `usd`.

## Anti-Patterns

- ❌ Leaking `STRIPE_SECRET_KEY` to the client
- ❌ Trusting client-claimed subscription state — read from Stripe/webhooks
- ❌ Non-idempotent webhook handling (double-applied events)
- ❌ Floats for money — always integer minor units
- ❌ Blocking list queries on a live Stripe call — cache entitlements
