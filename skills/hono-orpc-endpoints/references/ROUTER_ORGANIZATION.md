# Router Organization

Best practices for structuring and organizing oRPC routers in your API.

## Directory Structure

```
packages/api/src/
├── index.ts                  # Procedures & middleware
├── context.ts                # Context factory
└── routers/
    ├── index.ts              # App router composition
    ├── users.ts              # User operations
    ├── posts.ts              # Post operations
    ├── comments.ts           # Comment operations
    ├── payments/             # Complex domain (folder)
    │   ├── index.ts          # Payment router composition
    │   ├── checkout.ts       # Checkout procedures
    │   ├── invoices.ts       # Invoice procedures
    │   └── subscriptions.ts  # Subscription procedures
    └── files.ts              # File operations
```

## Router Composition

### Simple Router

```typescript
// packages/api/src/routers/users.ts
import { z } from "zod"
import { protectedProcedure, publicProcedure } from "../index"

const userSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  email: z.email(),
})

export const usersRouter = {
  list: protectedProcedure
    .input(z.object({ limit: z.int().optional().default(20) }))
    .handler(async ({ input }) => {
      // Implementation
    }),

  get: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input }) => {
      // Implementation
    }),

  create: protectedProcedure
    .input(z.object({
      name: z.string(),
      email: z.email(),
    }))
    .handler(async ({ input, context }) => {
      // Implementation
    }),

  update: protectedProcedure
    .input(z.object({
      id: z.uuid(),
      data: z.object({
        name: z.string().optional(),
        email: z.email().optional(),
      }),
    }))
    .handler(async ({ input }) => {
      // Implementation
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input }) => {
      // Implementation
    }),
}
```

### Nested Router

```typescript
// packages/api/src/routers/users.ts
export const usersRouter = {
  // Top-level user operations
  list: protectedProcedure.handler(...),
  get: protectedProcedure.handler(...),
  create: protectedProcedure.handler(...),

  // Nested: user preferences
  preferences: {
    get: protectedProcedure
      .input(z.object({ userId: z.uuid() }))
      .handler(async ({ input }) => { /* ... */ }),

    update: protectedProcedure
      .input(z.object({
        userId: z.uuid(),
        preferences: preferencesSchema,
      }))
      .handler(async ({ input }) => { /* ... */ }),
  },

  // Nested: user sessions
  sessions: {
    list: protectedProcedure
      .input(z.object({ userId: z.uuid() }))
      .handler(async ({ input }) => { /* ... */ }),

    revoke: protectedProcedure
      .input(z.object({ sessionId: z.uuid() }))
      .handler(async ({ input }) => { /* ... */ }),
  },
}
```

**Note:** Limit nesting to 2 levels maximum for clarity.

### Complex Domain Router (Multi-File)

```typescript
// packages/api/src/routers/payments/checkout.ts
export const checkoutRouter = {
  createSession: protectedProcedure.handler(...),
  completeSession: protectedProcedure.handler(...),
}

// packages/api/src/routers/payments/invoices.ts
export const invoicesRouter = {
  list: protectedProcedure.handler(...),
  get: protectedProcedure.handler(...),
  download: protectedProcedure.handler(...),
}

// packages/api/src/routers/payments/index.ts
import { checkoutRouter } from "./checkout"
import { invoicesRouter } from "./invoices"
import { subscriptionsRouter } from "./subscriptions"

export const paymentsRouter = {
  checkout: checkoutRouter,
  invoices: invoicesRouter,
  subscriptions: subscriptionsRouter,
  
  // Top-level payment procedures
  createPortal: protectedProcedure.handler(...),
}
```

### App Router Composition

```typescript
// packages/api/src/routers/index.ts
import type { RouterClient } from "@orpc/server"
import { publicProcedure, protectedProcedure } from "../index"
import { usersRouter } from "./users"
import { postsRouter } from "./posts"
import { paymentsRouter } from "./payments"
import { filesRouter } from "./files"

export const appRouter = {
  // Top-level procedures
  healthCheck: publicProcedure.handler(() => "OK"),
  
  ping: publicProcedure
    .input(z.object({ message: z.string() }))
    .handler(({ input }) => ({ echo: input.message })),

  // Feature routers
  users: usersRouter,
  posts: postsRouter,
  payments: paymentsRouter,
  files: filesRouter,
}

// Export types for frontend
export type AppRouter = typeof appRouter
export type AppRouterClient = RouterClient<typeof appRouter>
```

## Naming Conventions

### Router Names

```typescript
// ✅ Good: Plural noun + Router suffix
usersRouter
postsRouter
commentsRouter
paymentsRouter
notificationsRouter

// ❌ Bad
userRouter         // Should be plural
UserRouter         // Should be camelCase
users              // Missing Router suffix
manageUsers        // Action-oriented
```

### Procedure Names

```typescript
// ✅ Good: Simple verbs
list, get, create, update, delete
publish, archive, approve, reject

// ❌ Bad
getAll, getOne     // Use 'list' and 'get'
createNew          // Redundant 'New'
updateExisting     // Redundant 'Existing'
```

### Schema Names

```typescript
// ✅ Good
userSchema               // Entity
createUserSchema         // Create input
updateUserSchema         // Update input
paginatedUsersSchema     // Paginated response

// ❌ Bad
user                     // Too generic
UserSchema               // Should be camelCase
inputUser                // Unclear purpose
```

## Schema Organization

### Inline Schemas (Simple)

```typescript
get: protectedProcedure
  .input(z.object({ id: z.uuid() }))
  .output(z.object({
    id: z.uuid(),
    name: z.string(),
  }))
  .handler(...)
```

**Use when:** Schema is simple and used only once.

### Shared Schemas (Complex)

```typescript
// At top of router file
const userSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  email: z.email(),
  role: z.enum(["user", "admin"]),
  createdAt: z.coerce.date(),
})

const createUserSchema = userSchema.omit({ id: true, createdAt: true })
const updateUserSchema = createUserSchema.partial()

export const usersRouter = {
  get: protectedProcedure
    .output(userSchema)
    .handler(...),
    
  create: protectedProcedure
    .input(createUserSchema)
    .output(userSchema)
    .handler(...),
}
```

**Use when:** Schema is reused across multiple procedures.

### External Schema Files

```typescript
// packages/api/src/schemas/user.ts
export const userSchema = z.object({ ... })
export const createUserSchema = userSchema.omit({ ... })
export const updateUserSchema = createUserSchema.partial()

// packages/api/src/routers/users.ts
import { userSchema, createUserSchema } from "../schemas/user"
```

**Use when:** Schemas are shared across multiple routers.

## Procedure Organization

### Order Procedures Logically

```typescript
export const postsRouter = {
  // Query operations first (reads)
  list: protectedProcedure.handler(...),
  get: protectedProcedure.handler(...),
  search: protectedProcedure.handler(...),
  
  // Mutation operations (writes)
  create: protectedProcedure.handler(...),
  update: protectedProcedure.handler(...),
  delete: protectedProcedure.handler(...),
  
  // Special actions last
  publish: protectedProcedure.handler(...),
  archive: protectedProcedure.handler(...),
}
```

### Group Related Procedures

```typescript
export const postsRouter = {
  // CRUD operations
  list: protectedProcedure.handler(...),
  get: protectedProcedure.handler(...),
  create: protectedProcedure.handler(...),
  update: protectedProcedure.handler(...),
  delete: protectedProcedure.handler(...),
  
  // Status management
  publish: protectedProcedure.handler(...),
  unpublish: protectedProcedure.handler(...),
  archive: protectedProcedure.handler(...),
  
  // Additional features
  duplicate: protectedProcedure.handler(...),
  export: protectedProcedure.handler(...),
}
```

## Code Splitting

### When to Create Separate File

Create separate router file when:
- Router has 5+ procedures
- Router has complex domain logic
- Router needs dedicated tests
- Router is reused across projects

### When to Use Folder

Create router folder when:
- Domain has multiple sub-routers (3+)
- Each sub-router has 5+ procedures
- Complex business logic needs separation
- Multiple developers work on same domain

### Example: Large Router Split

**Before (single file):**
```typescript
// packages/api/src/routers/ecommerce.ts (too large)
export const ecommerceRouter = {
  // Products (10 procedures)
  listProducts: ...,
  getProduct: ...,
  // ... 8 more
  
  // Orders (12 procedures)
  listOrders: ...,
  getOrder: ...,
  // ... 10 more
  
  // Cart (8 procedures)
  getCart: ...,
  addToCart: ...,
  // ... 6 more
}
```

**After (split into folder):**
```typescript
// packages/api/src/routers/ecommerce/products.ts
export const productsRouter = { ... }

// packages/api/src/routers/ecommerce/orders.ts
export const ordersRouter = { ... }

// packages/api/src/routers/ecommerce/cart.ts
export const cartRouter = { ... }

// packages/api/src/routers/ecommerce/index.ts
export const ecommerceRouter = {
  products: productsRouter,
  orders: ordersRouter,
  cart: cartRouter,
}
```

## Middleware Organization

### Shared Middleware

```typescript
// packages/api/src/index.ts
export const o = os.$context<Context>()

// Authentication
const requireAuth = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED")
  }
  return await next({ context: { session: context.session } })
})

// Authorization
const requireAdmin = o.middleware(async ({ context, next }) => {
  const user = context.session.user as Record<string, unknown>
  if (user.role !== "admin") {
    throw new ORPCError("FORBIDDEN")
  }
  return await next({ context })
})

// Procedures
export const publicProcedure = o
export const protectedProcedure = publicProcedure.use(requireAuth)
export const adminProcedure = protectedProcedure.use(requireAdmin)
```

### Router-Specific Middleware

```typescript
// packages/api/src/routers/posts.ts
const requirePostOwnership = o.middleware(async ({ context, input, next }) => {
  const post = await db.query.posts.findFirst({
    where: eq(posts.id, input.postId),
  })
  
  if (post.userId !== context.session.user.id) {
    throw new ORPCError("FORBIDDEN", {
      message: "You don't own this post",
    })
  }
  
  return await next({ context: { post } })
})

const protectedPostProcedure = protectedProcedure.use(requirePostOwnership)

export const postsRouter = {
  update: protectedPostProcedure
    .input(z.object({ postId: z.uuid(), data: updateSchema }))
    .handler(({ context }) => {
      // context.post is available
    }),
}
```

## Type Exports

```typescript
// packages/api/src/routers/index.ts
export const appRouter = { ... }

// Export router type
export type AppRouter = typeof appRouter

// Export typed client
export type AppRouterClient = RouterClient<typeof appRouter>

// Export individual router types (if needed)
export type UsersRouter = typeof usersRouter
export type PostsRouter = typeof postsRouter
```

## Best Practices

1. **Single Responsibility** - Each router handles one domain
2. **Consistent Naming** - Use standard CRUD verbs
3. **Logical Grouping** - Group related procedures together
4. **Shallow Nesting** - Max 2 levels of nesting
5. **Schema Co-location** - Keep schemas near usage
6. **Type Safety** - Export types for frontend use
7. **Code Splitting** - Split large routers into folders
8. **Middleware Reuse** - Share common middleware logic
9. **Clear Boundaries** - Each router = one feature
10. **Documentation** - Add comments for complex logic
