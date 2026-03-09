# Authentication & Authorization Middleware

Patterns for implementing auth guards and permissions in oRPC procedures.

## Basic Middleware Setup

```typescript
// packages/api/src/index.ts
import { ORPCError, os } from "@orpc/server"
import type { Context } from "./context"

export const o = os.$context<Context>()

export const publicProcedure = o
```

## Authentication Middleware

### Require Authentication

```typescript
const requireAuth = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED", {
      message: "You must be signed in to access this resource",
    })
  }

  return await next({
    context: {
      session: context.session,
    },
  })
})

export const protectedProcedure = publicProcedure.use(requireAuth)
```

**Usage:**
```typescript
getProfile: protectedProcedure.handler(({ context }) => {
  // context.session.user is guaranteed to exist
  return { user: context.session.user }
})
```

### Optional Authentication

```typescript
const optionalAuth = o.middleware(async ({ context, next }) => {
  // Don't throw error, just pass session if it exists
  return await next({
    context: {
      session: context.session ?? null,
    },
  })
})

export const optionalAuthProcedure = publicProcedure.use(optionalAuth)
```

**Usage:**
```typescript
listPosts: optionalAuthProcedure.handler(({ context }) => {
  // Show different content based on auth status
  const isAuthenticated = !!context.session?.user

  return {
    posts: await fetchPosts({ includePrivate: isAuthenticated }),
  }
})
```

## Authorization Middleware

### Role-Based Access Control (RBAC)

```typescript
const requireAdmin = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED")
  }

  const user = context.session.user as Record<string, unknown>
  if (user.role !== "admin") {
    throw new ORPCError("FORBIDDEN", {
      message: "Admin access required",
    })
  }

  return await next({
    context: {
      session: context.session,
    },
  })
})

export const adminProcedure = publicProcedure.use(requireAdmin)
```

**Multi-Role Support:**
```typescript
const requireRole = (allowedRoles: string[]) =>
  o.middleware(async ({ context, next }) => {
    if (!context.session?.user) {
      throw new ORPCError("UNAUTHORIZED")
    }

    const user = context.session.user as Record<string, unknown>
    if (!allowedRoles.includes(user.role as string)) {
      throw new ORPCError("FORBIDDEN", {
        message: `Requires one of: ${allowedRoles.join(", ")}`,
      })
    }

    return await next({ context })
  })

// Usage
export const moderatorProcedure = publicProcedure.use(
  requireRole(["admin", "moderator"])
)
```

### Permission-Based Access Control

```typescript
const requirePermission = (permission: string) =>
  o.middleware(async ({ context, next }) => {
    if (!context.session?.user) {
      throw new ORPCError("UNAUTHORIZED")
    }

    const user = context.session.user as Record<string, unknown>
    const permissions = user.permissions as string[] | undefined

    if (!permissions?.includes(permission)) {
      throw new ORPCError("FORBIDDEN", {
        message: `Missing required permission: ${permission}`,
      })
    }

    return await next({ context })
  })

// Usage
export const canDeleteUserProcedure = protectedProcedure.use(
  requirePermission("users:delete")
)
```

## Resource-Based Authorization

### Check Resource Ownership

```typescript
// In router
const requirePostOwnership = o.middleware(async ({ context, input, next }) => {
  const postId = (input as { postId: string }).postId

  const post = await db.query.posts.findFirst({
    where: eq(posts.id, postId),
  })

  if (!post) {
    throw new ORPCError("NOT_FOUND", {
      message: "Post not found",
    })
  }

  if (post.userId !== context.session.user.id) {
    throw new ORPCError("FORBIDDEN", {
      message: "You don't have permission to modify this post",
    })
  }

  return await next({
    context: {
      post, // Pass post to handler
    },
  })
})

const ownedPostProcedure = protectedProcedure.use(requirePostOwnership)

export const postsRouter = {
  update: ownedPostProcedure
    .input(z.object({
      postId: z.uuid(),
      data: updatePostSchema,
    }))
    .handler(({ context, input }) => {
      // context.post is available and ownership is verified
      return updatePost(context.post.id, input.data)
    }),
}
```

### Organization Membership

```typescript
const requireOrgMembership = o.middleware(async ({ context, input, next }) => {
  const orgId = (input as { orgId: string }).orgId

  const membership = await db.query.orgMembers.findFirst({
    where: and(
      eq(orgMembers.orgId, orgId),
      eq(orgMembers.userId, context.session.user.id)
    ),
  })

  if (!membership) {
    throw new ORPCError("FORBIDDEN", {
      message: "You are not a member of this organization",
    })
  }

  return await next({
    context: {
      membership,
      userRole: membership.role,
    },
  })
})

const orgMemberProcedure = protectedProcedure.use(requireOrgMembership)
```

### Organization Role Check

```typescript
const requireOrgRole = (minRole: "member" | "admin" | "owner") =>
  o.middleware(async ({ context, next }) => {
    const roleHierarchy = { member: 1, admin: 2, owner: 3 }
    const userRole = context.membership?.role

    if (!userRole || roleHierarchy[userRole] < roleHierarchy[minRole]) {
      throw new ORPCError("FORBIDDEN", {
        message: `Requires ${minRole} role or higher`,
      })
    }

    return await next({ context })
  })

const orgAdminProcedure = orgMemberProcedure.use(requireOrgRole("admin"))
```

## Rate Limiting

```typescript
import { RateLimiter } from "@/lib/rate-limiter"

const rateLimiter = new RateLimiter({
  windowMs: 60 * 1000, // 1 minute
  maxRequests: 100,
})

const withRateLimit = o.middleware(async ({ context, next }) => {
  const userId = context.session?.user?.id ?? context.ip

  const allowed = await rateLimiter.check(userId)
  if (!allowed) {
    throw new ORPCError("TOO_MANY_REQUESTS", {
      message: "Rate limit exceeded. Please try again later.",
    })
  }

  return await next({ context })
})

export const rateLimitedProcedure = publicProcedure.use(withRateLimit)
```

## API Key Authentication

```typescript
const requireApiKey = o.middleware(async ({ context, next }) => {
  const apiKey = context.headers.get("x-api-key")

  if (!apiKey) {
    throw new ORPCError("UNAUTHORIZED", {
      message: "API key required",
    })
  }

  const key = await db.query.apiKeys.findFirst({
    where: and(
      eq(apiKeys.key, apiKey),
      isNull(apiKeys.revokedAt)
    ),
  })

  if (!key) {
    throw new ORPCError("UNAUTHORIZED", {
      message: "Invalid API key",
    })
  }

  // Update last used timestamp
  await db.update(apiKeys)
    .set({ lastUsedAt: new Date() })
    .where(eq(apiKeys.id, key.id))

  return await next({
    context: {
      apiKey: key,
      userId: key.userId,
    },
  })
})

export const apiKeyProcedure = publicProcedure.use(requireApiKey)
```

## Email Verification Requirement

```typescript
const requireEmailVerified = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED")
  }

  const user = context.session.user as Record<string, unknown>
  if (!user.emailVerified) {
    throw new ORPCError("FORBIDDEN", {
      message: "Email verification required",
      data: {
        action: "VERIFY_EMAIL",
        email: user.email,
      },
    })
  }

  return await next({ context })
})

export const verifiedUserProcedure = protectedProcedure.use(requireEmailVerified)
```

## Feature Flags

```typescript
const requireFeatureFlag = (flag: string) =>
  o.middleware(async ({ context, next }) => {
    const enabled = await checkFeatureFlag(flag, context.session?.user?.id)

    if (!enabled) {
      throw new ORPCError("FORBIDDEN", {
        message: "This feature is not available",
      })
    }

    return await next({ context })
  })

export const betaFeatureProcedure = protectedProcedure.use(
  requireFeatureFlag("beta_features")
)
```

## Subscription Requirement

```typescript
const requireSubscription = (minTier: "free" | "pro" | "enterprise") =>
  o.middleware(async ({ context, next }) => {
    const tierHierarchy = { free: 1, pro: 2, enterprise: 3 }

    const subscription = await db.query.subscriptions.findFirst({
      where: and(
        eq(subscriptions.userId, context.session.user.id),
        eq(subscriptions.status, "active")
      ),
    })

    const userTier = subscription?.tier ?? "free"

    if (tierHierarchy[userTier] < tierHierarchy[minTier]) {
      throw new ORPCError("PAYMENT_REQUIRED", {
        message: `This feature requires ${minTier} subscription`,
        data: {
          currentTier: userTier,
          requiredTier: minTier,
        },
      })
    }

    return await next({ context })
  })

export const proProcedure = protectedProcedure.use(requireSubscription("pro"))
```

## IP Whitelist

```typescript
const requireWhitelistedIP = o.middleware(async ({ context, next }) => {
  const allowedIPs = env.ALLOWED_IPS.split(",")
  const clientIP = context.ip

  if (!allowedIPs.includes(clientIP)) {
    throw new ORPCError("FORBIDDEN", {
      message: "Access denied from this IP address",
    })
  }

  return await next({ context })
})

export const whitelistedProcedure = publicProcedure.use(requireWhitelistedIP)
```

## Combining Middleware

```typescript
// Stack multiple middleware
export const adminWithApiKey = publicProcedure
  .use(requireAuth)
  .use(requireAdmin)
  .use(requireApiKey)

// Conditional middleware
const requireOwnerOrAdmin = o.middleware(async ({ context, input, next }) => {
  const resourceUserId = (input as { userId: string }).userId
  const currentUser = context.session.user as Record<string, unknown>

  const isOwner = currentUser.id === resourceUserId
  const isAdmin = currentUser.role === "admin"

  if (!isOwner && !isAdmin) {
    throw new ORPCError("FORBIDDEN", {
      message: "Must be resource owner or admin",
    })
  }

  return await next({ context })
})
```

## Best Practices

1. **Fail Securely** - Default to deny access
2. **Clear Messages** - Explain why access was denied
3. **Type Safety** - Type context properly in middleware
4. **Performance** - Cache permission checks when possible
5. **Audit Trail** - Log all authorization failures
6. **Granular Permissions** - Use specific permissions over broad roles
7. **Test Thoroughly** - Test all auth paths
8. **Rate Limit** - Add rate limiting to public endpoints
9. **Middleware Order** - Auth before authorization
10. **Error Details** - Provide actionable error data
