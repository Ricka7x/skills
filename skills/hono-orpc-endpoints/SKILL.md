---
name: hono-orpc-endpoints
description: Production patterns for designing well-structured API endpoints with Hono and oRPC. Use when creating new endpoints, designing routers, implementing auth guards, validating inputs, or refactoring existing procedures in this Better-T-Stack project.
---

# Hono + oRPC Endpoint Design

Production-ready patterns for creating well-designed, type-safe API endpoints using Hono and oRPC in this Better-T-Stack architecture.

## Quick Reference

### Basic CRUD Pattern

```typescript
import { z } from "zod"
import { protectedProcedure, publicProcedure } from "../index"

export const todosRouter = {
  // List with pagination
  list: protectedProcedure
    .input(z.object({
      limit: z.int().min(1).max(100).optional().default(20),
      cursor: z.string().optional(),
    }))
    .output(z.object({
      items: z.array(todoSchema),
      nextCursor: z.string().optional(),
    }))
    .handler(async ({ input }) => { /* ... */ }),

  // Get by ID
  get: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .output(todoSchema)
    .handler(async ({ input }) => { /* ... */ }),

  // Create
  create: protectedProcedure
    .input(createTodoSchema)
    .output(todoSchema)
    .handler(async ({ input, context }) => { /* ... */ }),

  // Update
  update: protectedProcedure
    .input(z.object({
      id: z.uuid(),
      data: updateTodoSchema,
    }))
    .output(todoSchema)
    .handler(async ({ input }) => { /* ... */ }),

  // Delete
  delete: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .output(z.object({ success: z.boolean() }))
    .handler(async ({ input }) => { /* ... */ }),
}
```

### Validation Schemas (Zod 5)

```typescript
import { z } from "zod"

// Entity schema
const todoSchema = z.object({
  id: z.uuid(),
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  status: z.enum(["todo", "in_progress", "done"]),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
})

// Create schema (omit generated fields)
const createTodoSchema = todoSchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true,
})

// Update schema (partial)
const updateTodoSchema = createTodoSchema.partial()

// Pagination schema
const paginationSchema = z.object({
  limit: z.int().min(1).max(100).optional().default(20),
  cursor: z.string().optional(),
})

// Filter schema
const filterSchema = z.object({
  status: z.enum(["todo", "in_progress", "done"]).optional(),
  search: z.string().optional(),
  createdAfter: z.coerce.date().optional(),
})
```

### Auth Middleware Usage

```typescript
import { publicProcedure, protectedProcedure, adminProcedure } from "../index"

export const usersRouter = {
  // Anyone can access
  healthCheck: publicProcedure.handler(() => "OK"),

  // Requires authentication
  profile: protectedProcedure.handler(({ context }) => ({
    user: context.session.user,
  })),

  // Requires admin role
  listAllUsers: adminProcedure.handler(async () => { /* ... */ }),
}
```

### Error Handling

```typescript
import { ORPCError } from "@orpc/server"

// Standard errors
throw new ORPCError("UNAUTHORIZED") // 401
throw new ORPCError("FORBIDDEN") // 403
throw new ORPCError("NOT_FOUND") // 404
throw new ORPCError("BAD_REQUEST") // 400
throw new ORPCError("INTERNAL_SERVER_ERROR") // 500

// Custom message
throw new ORPCError("NOT_FOUND", {
  message: "Todo not found with the provided ID",
})

// With metadata
throw new ORPCError("BAD_REQUEST", {
  message: "Invalid file type",
  data: { allowedTypes: ["image/png", "image/jpeg"] },
})
```

## Core Principles

### 1. Resource-Oriented Design

Structure endpoints around resources (entities), not actions:

```typescript
// ✅ Good: Resource-oriented
export const postsRouter = {
  list: protectedProcedure.handler(...),
  get: protectedProcedure.handler(...),
  create: protectedProcedure.handler(...),
  update: protectedProcedure.handler(...),
  delete: protectedProcedure.handler(...),
  publish: protectedProcedure.handler(...), // Resource-specific action
}

// ❌ Bad: Action-oriented
export const postsRouter = {
  getAllPosts: protectedProcedure.handler(...),
  createNewPost: protectedProcedure.handler(...),
  updateExistingPost: protectedProcedure.handler(...),
}
```

### 2. Consistent Naming

**Procedures:** Use standard CRUD verbs
- `list` - Get multiple items (with pagination)
- `get` - Get single item by ID
- `create` - Create new item
- `update` - Update existing item (full or partial)
- `delete` - Remove item

**Routers:** `{domain}Router` format
- `usersRouter`, `postsRouter`, `paymentsRouter`

**Schemas:** Clear, specific names
- `userSchema` - Entity shape
- `createUserSchema` - Create input
- `updateUserSchema` - Update input
- `paginatedUsersSchema` - List response

### 3. Input Validation

Always validate with `.input()`:

```typescript
// ✅ Always validate input
create: protectedProcedure
  .input(createTodoSchema)
  .handler(async ({ input }) => {
    // input is fully typed and validated
  })

// ❌ Never skip validation
create: protectedProcedure
  .handler(async ({ context }) => {
    // Unvalidated data from context
  })
```

### 4. Output Schemas 

Define output schemas for guaranteed response shape:

```typescript
get: protectedProcedure
  .input(z.object({ id: z.uuid() }))
  .output(todoSchema) // Validates response matches schema
  .handler(async ({ input }) => {
    return await db.query.todos.findFirst({ where: eq(todos.id, input.id) })
  })
```

### 5. Type-Safe Context

Always type your context properly:

```typescript
// packages/api/src/index.ts
export const o = os.$context<Context>()

export const protectedProcedure = publicProcedure.use(requireAuth)

// In handler
handler: async ({ context }) => {
  // context.session is typed
  const userId = context.session.user.id
}
```

## Common Patterns

### Pagination (Cursor-Based)

Recommended for scalable pagination:

```typescript
import { z } from "zod"

const paginatedResponseSchema = <T extends z.ZodType>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    nextCursor: z.string().optional(),
    hasMore: z.boolean(),
  })

export const postsRouter = {
  list: protectedProcedure
    .input(z.object({
      limit: z.int().min(1).max(100).optional().default(20),
      cursor: z.string().optional(),
    }))
    .output(paginatedResponseSchema(postSchema))
    .handler(async ({ input }) => {
      const items = await db.query.posts.findMany({
        limit: input.limit + 1, // Fetch one extra to check hasMore
        where: input.cursor
          ? gt(posts.id, input.cursor)
          : undefined,
        orderBy: desc(posts.createdAt),
      })

      const hasMore = items.length > input.limit
      const data = hasMore ? items.slice(0, -1) : items
      const nextCursor = hasMore ? items[items.length - 2].id : undefined

      return { items: data, nextCursor, hasMore }
    }),
}
```

### Pagination (Offset-Based)

Simpler but less performant for large datasets:

```typescript
list: protectedProcedure
  .input(z.object({
    page: z.int().min(1).optional().default(1),
    pageSize: z.int().min(1).max(100).optional().default(20),
  }))
  .output(z.object({
    items: z.array(postSchema),
    total: z.int(),
    page: z.int(),
    pageSize: z.int(),
    totalPages: z.int(),
  }))
  .handler(async ({ input }) => {
    const offset = (input.page - 1) * input.pageSize

    const [items, [{ count }]] = await Promise.all([
      db.query.posts.findMany({
        limit: input.pageSize,
        offset,
      }),
      db.select({ count: sql`count(*)`.as("count") }).from(posts),
    ])

    return {
      items,
      total: count,
      page: input.page,
      pageSize: input.pageSize,
      totalPages: Math.ceil(count / input.pageSize),
    }
  }),
```

### Filtering & Search

```typescript
list: protectedProcedure
  .input(z.object({
    limit: z.int().min(1).max(100).optional().default(20),
    // Filters
    status: z.enum(["active", "archived"]).optional(),
    category: z.string().optional(),
    search: z.string().optional(),
    createdAfter: z.coerce.date().optional(),
  }))
  .handler(async ({ input }) => {
    const conditions = []

    if (input.status) {
      conditions.push(eq(posts.status, input.status))
    }

    if (input.category) {
      conditions.push(eq(posts.category, input.category))
    }

    if (input.search) {
      conditions.push(
        or(
          ilike(posts.title, `%${input.search}%`),
          ilike(posts.content, `%${input.search}%`)
        )
      )
    }

    if (input.createdAfter) {
      conditions.push(gte(posts.createdAt, input.createdAfter))
    }

    const items = await db.query.posts.findMany({
      where: and(...conditions),
      limit: input.limit,
    })

    return { items }
  }),
```

### Sorting

```typescript
const sortableFields = ["createdAt", "updatedAt", "title"] as const

list: protectedProcedure
  .input(z.object({
    sortBy: z.enum(sortableFields).optional().default("createdAt"),
    sortOrder: z.enum(["asc", "desc"]).optional().default("desc"),
  }))
  .handler(async ({ input }) => {
    const orderByFn = input.sortOrder === "asc" ? asc : desc
    const orderByColumn = posts[input.sortBy]

    const items = await db.query.posts.findMany({
      orderBy: orderByFn(orderByColumn),
    })

    return { items }
  }),
```

### Multi-Step Operations

For complex workflows like file uploads:

```typescript
export const filesRouter = {
  // Step 1: Get presigned URL
  getUploadUrl: protectedProcedure
    .input(z.object({
      filename: z.string(),
      contentType: z.string(),
    }))
    .output(z.object({
      uploadUrl: z.url(),
      fileId: z.uuid(),
    }))
    .handler(async ({ input, context }) => {
      const fileId = randomUUID()
      const key = `uploads/${context.session.user.id}/${fileId}/${input.filename}`

      const uploadUrl = await getSignedUrl(s3Client, new PutObjectCommand({
        Bucket: env.AWS_BUCKET_NAME,
        Key: key,
        ContentType: input.contentType,
      }), { expiresIn: 3600 })

      return { uploadUrl, fileId }
    }),

  // Step 2: Confirm upload
  confirmUpload: protectedProcedure
    .input(z.object({
      fileId: z.uuid(),
      url: z.url(),
      size: z.int(),
    }))
    .output(z.object({ success: z.boolean() }))
    .handler(async ({ input, context }) => {
      await db.insert(files).values({
        id: input.fileId,
        url: input.url,
        size: input.size,
        userId: context.session.user.id,
      })

      return { success: true }
    }),
}
```

## Advanced Patterns

### Nested Resources

```typescript
export const usersRouter = {
  get: protectedProcedure.handler(...),

  // Nested resource: user's posts
  posts: {
    list: protectedProcedure
      .input(z.object({ userId: z.uuid() }))
      .handler(async ({ input }) => {
        return await db.query.posts.findMany({
          where: eq(posts.userId, input.userId),
        })
      }),
  },

  // Nested resource: user's settings
  settings: {
    get: protectedProcedure
      .input(z.object({ userId: z.uuid() }))
      .handler(...),

    update: protectedProcedure
      .input(z.object({
        userId: z.uuid(),
        settings: settingsSchema,
      }))
      .handler(...),
  },
}
```

### Batch Operations

```typescript
bulkCreate: protectedProcedure
  .input(z.object({
    items: z.array(createTodoSchema).min(1).max(100),
  }))
  .output(z.object({
    created: z.array(todoSchema),
    failed: z.array(z.object({
      index: z.int(),
      error: z.string(),
    })),
  }))
  .handler(async ({ input, context }) => {
    const created = []
    const failed = []

    for (const [index, item] of input.items.entries()) {
      try {
        const todo = await db.insert(todos).values({
          ...item,
          userId: context.session.user.id,
        }).returning()
        created.push(todo[0])
      } catch (error) {
        failed.push({
          index,
          error: error.message,
        })
      }
    }

    return { created, failed }
  }),
```

### WebHooks

```typescript
// Note: Webhooks typically use publicProcedure with custom validation
stripeWebhook: publicProcedure
  .input(z.object({
    signature: z.string(),
    payload: z.string(),
  }))
  .handler(async ({ input }) => {
    // Verify signature
    const event = stripe.webhooks.constructEvent(
      input.payload,
      input.signature,
      env.STRIPE_WEBHOOK_SECRET
    )

    // Handle event
    switch (event.type) {
      case "payment_intent.succeeded":
        await handlePaymentSuccess(event.data.object)
        break
      case "payment_intent.failed":
        await handlePaymentFailed(event.data.object)
        break
    }

    return { received: true }
  }),
```

## Router Organization

### Structure

```
packages/api/src/
├── index.ts              # Procedures & middleware
├── context.ts            # Context factory
└── routers/
    ├── index.ts          # App router composition
    ├── users.ts          # User operations
    ├── posts.ts          # Post operations
    ├── payments.ts       # Payment operations
    └── files.ts          # File operations
```

### Composition

```typescript
// packages/api/src/routers/index.ts
import { usersRouter } from "./users"
import { postsRouter } from "./posts"
import { paymentsRouter } from "./payments"
import { filesRouter } from "./files"

export const appRouter = {
  users: usersRouter,
  posts: postsRouter,
  payments: paymentsRouter,
  files: filesRouter,
}

export type AppRouter = typeof appRouter
export type AppRouterClient = RouterClient<typeof appRouter>
```

## Anti-Patterns

**Don't:**

- ❌ Skip input validation
- ❌ Use inconsistent naming (getPosts, createPost, deleteTodo)
- ❌ Put auth logic in handlers (use middleware)
- ❌ Return database errors directly to clients
- ❌ Use generic error messages ("Something went wrong")
- ❌ Ignore pagination for list endpoints
- ❌ Accept unlimited array sizes
- ❌ Use string IDs without validation (use z.uuid())
- ❌ Mix snake_case and camelCase
- ❌ Create deeply nested routers (max 2 levels)

**Do:**

- ✅ Always validate inputs with Zod schemas
- ✅ Use consistent CRUD naming (list, get, create, update, delete)
- ✅ Define middleware for cross-cutting concerns (auth, logging)
- ✅ Transform errors into user-friendly messages
- ✅ Provide specific error details with ORPCError
- ✅ Implement pagination for all list endpoints
- ✅ Set limits on array sizes (.max(100))
- ✅ Use z.uuid() for ID validation
- ✅ Use camelCase consistently
- ✅ Keep router nesting shallow and logical

## Resources

- [Procedure Patterns](references/PROCEDURE_PATTERNS.md) - CRUD operations, pagination
- [Validation Guide](references/VALIDATION.md) - Zod schemas and patterns
- [Router Organization](references/ROUTER_ORGANIZATION.md) - Structure and composition
- [Auth Middleware](references/AUTH_MIDDLEWARE.md) - Authentication patterns
- [Error Handling](references/ERROR_HANDLING.md) - ORPCError usage
- [Real Examples](references/EXAMPLES.md) - Working code from this project
- [oRPC Docs](https://orpc.dev/docs/)
- [Hono Docs](https://hono.dev/docs/)
