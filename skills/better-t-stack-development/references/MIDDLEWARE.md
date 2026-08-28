# Middleware & Authorization

Recipes for auth/authorization guards on oRPC procedures, layered on the base procedures in [PROCEDURES.md](PROCEDURES.md) and the org/capability model in [MULTI-TENANCY.md](MULTI-TENANCY.md).

**Order matters:** auth → authorization → resource checks. Middleware compose left-to-right, so put authentication before permission checks.

## Base Middleware

```ts
// packages/api/src/index.ts
const requireAuth = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED", { message: "You must be signed in" });
  }
  return await next({ context: { session: context.session } });
});

export const protectedProcedure = publicProcedure.use(requireAuth);
export const adminProcedure = protectedProcedure.use(requireAdmin);
```

### Optional Authentication

Only when a route must work for both guests and members (e.g. public listing shows extra data when signed in). Don't throw — pass the session as-is:

```ts
const optionalAuth = o.middleware(async ({ context, next }) => {
  return await next({ context: { session: context.session ?? null } });
});

export const optionalAuthProcedure = publicProcedure.use(optionalAuth);
```

## Role & Permission Guards

Role-string guards are fine for coarse checks; prefer **capability checks** for domain logic — see [MULTI-TENANCY.md](MULTI-TENANCY.md).

```ts
// Multi-role
const requireRole = (allowed: string[]) =>
  o.middleware(async ({ context, next }) => {
    if (!context.session?.user) throw new ORPCError("UNAUTHORIZED");
    if (!allowed.includes((context.session.user as any).role)) {
      throw new ORPCError("FORBIDDEN", { message: `Requires one of: ${allowed.join(", ")}` });
    }
    return await next({ context });
  });

// Permission-based
const requirePermission = (permission: string) =>
  o.middleware(async ({ context, next }) => {
    const perms = (context.session.user as any).permissions as string[] | undefined;
    if (!perms?.includes(permission)) {
      throw new ORPCError("FORBIDDEN", { message: `Missing permission: ${permission}` });
    }
    return await next({ context });
  });
```

## Resource Ownership

For row-level access, a middleware that loads the row, 404s if missing, and FORBIDs if the caller isn't the owner — then passes the row in context so the handler doesn't re-fetch:

```ts
const requirePostOwnership = o.middleware(async ({ context, input, next }) => {
  const post = await db.query.posts.findFirst({
    where: eq(posts.id, (input as { postId: string }).postId),
  });
  if (!post) throw new ORPCError("NOT_FOUND", { message: "Post not found" });
  if (post.userId !== context.session.user.id) {
    throw new ORPCError("FORBIDDEN", { message: "You don't own this post" });
  }
  return await next({ context: { post } });
});
```

Keep these **router-local** (co-located with the router), not in `index.ts`. For org-scoped ownership, prefer the membership/capability helpers in [MULTI-TENANCY.md](MULTI-TENANCY.md).

## Rate Limiting

Per-user/IP limit for public or costly endpoints. Beyond a simple limiter, this stack applies a global tier at the Hono layer (see [AUTH.md](AUTH.md)); add a procedure-level limiter for AI or bulk endpoints:

```ts
const withRateLimit = (maxRequests: number, windowMs: number) =>
  o.middleware(async ({ context, next }) => {
    const key = context.session?.user?.id ?? context.ip;
    const allowed = await rateLimiter.check(key, maxRequests, windowMs);
    if (!allowed) {
      throw new ORPCError("TOO_MANY_REQUESTS", { message: "Rate limit exceeded. Try again later." });
    }
    return await next({ context });
  });
```

## API Key Authentication

For programmatic access (the stack ships better-auth's API key plugin):

```ts
const requireApiKey = o.middleware(async ({ context, next }) => {
  const apiKey = context.headers.get("x-api-key");
  if (!apiKey) throw new ORPCError("UNAUTHORIZED", { message: "API key required" });

  const key = await db.query.apiKeys.findFirst({
    where: and(eq(apiKeys.key, apiKey), isNull(apiKeys.revokedAt)),
  });
  if (!key) throw new ORPCError("UNAUTHORIZED", { message: "Invalid API key" });

  void db.update(apiKeys).set({ lastUsedAt: new Date() }).where(eq(apiKeys.id, key.id));
  return await next({ context: { apiKey: key, userId: key.userId } });
});
```

## Gate by User State

```ts
// Email verification required
const requireEmailVerified = o.middleware(async ({ context, next }) => {
  if (!(context.session.user as any).emailVerified) {
    throw new ORPCError("FORBIDDEN", {
      message: "Email verification required",
      data: { action: "VERIFY_EMAIL", email: context.session.user.email },
    });
  }
  return await next({ context });
});

// Feature flag (feature-flags plugin)
const requireFeatureFlag = (flag: string) =>
  o.middleware(async ({ context, next }) => {
    const enabled = await checkFeatureFlag(flag, context.session?.user?.id);
    if (!enabled) throw new ORPCError("FORBIDDEN", { message: "This feature is not available" });
    return await next({ context });
  });

// Subscription tier (see PAYMENTS.md)
const requirePlan = (minTier: "free" | "pro" | "enterprise") =>
  o.middleware(async ({ context, next }) => {
    const tier = await getEntitlement(context.session.user.id);
    if (TIER_RANK[tier] < TIER_RANK[minTier]) {
      throw new ORPCError("PAYMENT_REQUIRED", {
        message: `This feature requires the ${minTier} plan`,
        data: { currentTier: tier, requiredTier: minTier },
      });
    }
    return await next({ context });
  });
```

## Combining Middleware

```ts
export const adminWithApiKey = publicProcedure.use(requireAuth).use(requireAdmin).use(requireApiKey);
// Conditional: owner OR admin
export const ownerOrAdmin = protectedProcedure.use(requireOwnerOrAdmin);
```

## Best Practices

1. Default to **deny** — throw unless explicitly allowed.
2. Auth before authorization; authorization before resource checks.
3. Explain *why* access was denied (`FORBIDDEN` with a message); don't leak existence (`NOT_FOUND`).
4. Cache permission/entitlement lookups; don't hit the DB or Stripe on every list query.
5. Audit-log authorization failures (audit-log plugin).
6. Prefer capability checks over role-string checks in domain handlers.
7. Rate-limit public and expensive (AI, bulk) endpoints.
8. Type context properly — middleware narrows it for handlers.
