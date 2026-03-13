# Real-World Examples

Complete examples from the condomin-ia codebase showing production patterns.

## Payment Integration (Stripe)

Complete payment router with checkout and billing portal:

```typescript
// packages/api/src/routers/payments.ts
import {
  createOneTimeCheckout,
  createPortalSession,
  listInvoices,
} from "@condomin-ia/payments"
import { z } from "zod"
import { protectedProcedure } from "../index"

export const paymentsRouter = {
  // Create one-time checkout session
  createOneTimeCheckout: protectedProcedure
    .input(
      z.object({
        priceInCents: z.int().positive(),
        productName: z.string().min(1),
        description: z.string().optional(),
        successUrl: z.url(),
        cancelUrl: z.url(),
      })
    )
    .handler(async ({ context, input }) => {
      const user = context.session.user as Record<string, unknown>
      const customerId = user.stripeCustomerId as string | undefined

      if (!customerId) {
        throw new ORPCError("BAD_REQUEST", {
          message: "No Stripe customer ID found for this user",
        })
      }

      const session = await createOneTimeCheckout({
        customerId,
        priceInCents: input.priceInCents,
        productName: input.productName,
        description: input.description,
        successUrl: input.successUrl,
        cancelUrl: input.cancelUrl,
        metadata: {
          userId: user.id as string,
        },
      })

      return { url: session.url }
    }),

  // Create billing portal session
  createPortalSession: protectedProcedure
    .input(
      z.object({
        returnUrl: z.url(),
      })
    )
    .handler(async ({ context, input }) => {
      const user = context.session.user as Record<string, unknown>
      const customerId = user.stripeCustomerId as string | undefined

      if (!customerId) {
        throw new ORPCError("BAD_REQUEST", {
          message: "No Stripe customer ID found for this user",
        })
      }

      const session = await createPortalSession({
        customerId,
        returnUrl: input.returnUrl,
      })

      return { url: session.url }
    }),

  // List customer invoices with pagination
  listInvoices: protectedProcedure
    .input(
      z
        .object({
          limit: z.int().min(1).max(100).optional(),
          startingAfter: z.string().optional(),
        })
        .optional()
    )
    .handler(async ({ context, input }) => {
      const user = context.session.user as Record<string, unknown>
      const customerId = user.stripeCustomerId as string | undefined

      if (!customerId) {
        return { data: [], hasMore: false }
      }

      const invoices = await listInvoices({
        customerId,
        limit: input?.limit,
        startingAfter: input?.startingAfter,
      })

      return {
        data: invoices.data.map((inv) => ({
          id: inv.id,
          number: inv.number,
          status: inv.status,
          amountDue: inv.amount_due,
          amountPaid: inv.amount_paid,
          currency: inv.currency,
          created: inv.created,
          hostedInvoiceUrl: inv.hosted_invoice_url,
          invoicePdf: inv.invoice_pdf,
        })),
        hasMore: invoices.has_more,
      }
    }),
}
```

**Key Patterns:**
- ✅ Optional input for default parameters
- ✅ Cursor-based pagination (startingAfter)
- ✅ Data transformation in response
- ✅ Metadata for tracking
- ✅ Graceful handling of missing customerId

## File Upload (S3)

Two-step file upload with presigned URLs:

```typescript
// packages/api/src/routers/s3.ts
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3"
import { getSignedUrl } from "@aws-sdk/s3-request-presigner"
import { env } from "@condomin-ia/env/server"
import { z } from "zod"
import { protectedProcedure } from "../index"

const s3Client = new S3Client({
  region: env.AWS_REGION,
  credentials: {
    accessKeyId: env.AWS_ACCESS_KEY_ID,
    secretAccessKey: env.AWS_SECRET_ACCESS_KEY,
  },
})

export const s3Router = {
  // Step 1: Get presigned upload URL
  getPresignedUrl: protectedProcedure
    .input(
      z.object({
        key: z.string(),
        contentType: z.string(),
      })
    )
    .output(
      z.object({
        url: z.string(),
      })
    )
    .handler(async ({ input }) => {
      const command = new PutObjectCommand({
        Bucket: env.AWS_BUCKET_NAME,
        Key: input.key,
        ContentType: input.contentType,
      })

      const url = await getSignedUrl(s3Client, command, { expiresIn: 3600 })

      return { url }
    }),

  // Step 2: Save file metadata after upload
  saveFile: protectedProcedure
    .input(
      z.object({
        url: z.url(),
        name: z.string(),
        type: z.string(),
        size: z.int(),
      })
    )
    .output(
      z.object({
        id: z.string(),
      })
    )
    .handler(async ({ input, context }) => {
      const { db } = await import("@condomin-ia/db")
      const { file } = await import("@condomin-ia/db/schema/files")
      const { randomUUID } = await import("node:crypto")

      const fileId = randomUUID()

      await db.insert(file).values({
        id: fileId,
        name: input.name,
        type: input.type,
        size: input.size,
        url: input.url,
        userId: context.session.user.id,
      })

      return { id: fileId }
    }),
}
```

**Key Patterns:**
- ✅ Two-step upload process for security
- ✅ Presigned URLs with expiration
- ✅ Explicit input/output schemas
- ✅ Dynamic imports for code splitting
- ✅ Associate uploaded files with user

## Complete CRUD Router

Full-featured resource router with all operations:

```typescript
// packages/api/src/routers/posts.ts
import { db } from "@condomin-ia/db"
import { posts } from "@condomin-ia/db/schema/posts"
import { eq, desc, and, like, sql } from "drizzle-orm"
import { z } from "zod"
import { protectedProcedure, publicProcedure } from "../index"

// Validation schemas
const createPostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(1),
  published: z.boolean().default(false),
  tags: z.array(z.string()).optional(),
})

const updatePostSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  content: z.string().min(1).optional(),
  published: z.boolean().optional(),
  tags: z.array(z.string()).optional(),
})

const listPostsSchema = z.object({
  cursor: z.string().optional(),
  limit: z.int().min(1).max(100).default(10),
  search: z.string().optional(),
  published: z.boolean().optional(),
  sortBy: z.enum(["createdAt", "title"]).default("createdAt"),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
})

export const postsRouter = {
  // Create post
  create: protectedProcedure
    .input(createPostSchema)
    .handler(async ({ input, context }) => {
      const [post] = await db
        .insert(posts)
        .values({
          ...input,
          userId: context.session.user.id,
        })
        .returning()

      return post
    }),

  // List posts with filtering, search, and pagination
  list: publicProcedure
    .input(listPostsSchema)
    .handler(async ({ input }) => {
      const conditions = []

      // Filter by published status
      if (input.published !== undefined) {
        conditions.push(eq(posts.published, input.published))
      }

      // Search in title and content
      if (input.search) {
        conditions.push(
          sql`${posts.title} ILIKE ${"%" + input.search + "%"} OR ${
            posts.content
          } ILIKE ${"%" + input.search + "%"}`
        )
      }

      // Cursor pagination
      if (input.cursor) {
        conditions.push(sql`${posts.id} > ${input.cursor}`)
      }

      const where = conditions.length > 0 ? and(...conditions) : undefined

      const items = await db.query.posts.findMany({
        where,
        limit: input.limit + 1,
        orderBy:
          input.sortOrder === "desc"
            ? [desc(posts[input.sortBy])]
            : [posts[input.sortBy]],
      })

      const hasMore = items.length > input.limit
      const data = hasMore ? items.slice(0, -1) : items

      return {
        data,
        nextCursor: hasMore ? data[data.length - 1].id : undefined,
      }
    }),

  // Get single post
  get: publicProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input }) => {
      const post = await db.query.posts.findFirst({
        where: eq(posts.id, input.id),
      })

      if (!post) {
        throw new ORPCError("NOT_FOUND", {
          message: "Post not found",
        })
      }

      return post
    }),

  // Update post
  update: protectedProcedure
    .input(
      z.object({
        id: z.uuid(),
        data: updatePostSchema,
      })
    )
    .handler(async ({ input, context }) => {
      // Check if post exists and user owns it
      const existing = await db.query.posts.findFirst({
        where: eq(posts.id, input.id),
      })

      if (!existing) {
        throw new ORPCError("NOT_FOUND", {
          message: "Post not found",
        })
      }

      if (existing.userId !== context.session.user.id) {
        throw new ORPCError("FORBIDDEN", {
          message: "You don't have permission to update this post",
        })
      }

      const [updated] = await db
        .update(posts)
        .set({
          ...input.data,
          updatedAt: new Date(),
        })
        .where(eq(posts.id, input.id))
        .returning()

      return updated
    }),

  // Delete post
  delete: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input, context }) => {
      const existing = await db.query.posts.findFirst({
        where: eq(posts.id, input.id),
      })

      if (!existing) {
        throw new ORPCError("NOT_FOUND", {
          message: "Post not found",
        })
      }

      if (existing.userId !== context.session.user.id) {
        throw new ORPCError("FORBIDDEN", {
          message: "You don't have permission to delete this post",
        })
      }

      await db.delete(posts).where(eq(posts.id, input.id))

      return { success: true }
    }),

  // Publish/unpublish post
  togglePublish: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input, context }) => {
      const existing = await db.query.posts.findFirst({
        where: eq(posts.id, input.id),
      })

      if (!existing) {
        throw new ORPCError("NOT_FOUND", {
          message: "Post not found",
        })
      }

      if (existing.userId !== context.session.user.id) {
        throw new ORPCError("FORBIDDEN", {
          message: "You don't have permission to modify this post",
        })
      }

      const [updated] = await db
        .update(posts)
        .set({ published: !existing.published })
        .where(eq(posts.id, input.id))
        .returning()

      return updated
    }),

  // Get user's posts
  myPosts: protectedProcedure
    .input(
      z.object({
        cursor: z.string().optional(),
        limit: z.int().min(1).max(100).default(10),
      })
    )
    .handler(async ({ input, context }) => {
      const conditions = [eq(posts.userId, context.session.user.id)]

      if (input.cursor) {
        conditions.push(sql`${posts.id} > ${input.cursor}`)
      }

      const items = await db.query.posts.findMany({
        where: and(...conditions),
        limit: input.limit + 1,
        orderBy: [desc(posts.createdAt)],
      })

      const hasMore = items.length > input.limit
      const data = hasMore ? items.slice(0, -1) : items

      return {
        data,
        nextCursor: hasMore ? data[data.length - 1].id : undefined,
      }
    }),
}
```

**Key Patterns:**
- ✅ Separate schemas for create/update
- ✅ Public list, protected mutations
- ✅ Ownership checks before mutations
- ✅ Cursor pagination with hasMore
- ✅ Full-text search with SQL
- ✅ Flexible filtering and sorting
- ✅ Resource-specific actions (togglePublish)
- ✅ User-scoped queries (myPosts)

## Frontend Integration

How to use these endpoints on the frontend:

### Payment Flow

```typescript
// apps/web/src/routes/billing.tsx
import { orpc } from "@/utils/orpc"

export function BillingPage() {
  const createCheckout = orpc.payments.createOneTimeCheckout.useMutation({
    onSuccess: (data) => {
      window.location.href = data.url
    },
  })

  const handlePurchase = () => {
    createCheckout.mutate({
      input: {
        priceInCents: 2999,
        productName: "Pro Plan",
        description: "Annual subscription",
        successUrl: window.location.origin + "/billing/success",
        cancelUrl: window.location.origin + "/billing",
      },
    })
  }

  return (
    <button onClick={handlePurchase} disabled={createCheckout.isPending}>
      {createCheckout.isPending ? "Processing..." : "Upgrade to Pro"}
    </button>
  )
}
```

### File Upload Flow

```typescript
// apps/web/src/routes/upload.tsx
import { orpc } from "@/utils/orpc"

export function UploadPage() {
  const getPresignedUrl = orpc.s3.getPresignedUrl.useMutation()
  const saveFile = orpc.s3.saveFile.useMutation()

  const handleFileUpload = async (file: File) => {
    // Step 1: Get presigned URL
    const { url } = await getPresignedUrl.mutateAsync({
      input: {
        key: `uploads/${Date.now()}-${file.name}`,
        contentType: file.type,
      },
    })

    // Step 2: Upload to S3
    await fetch(url, {
      method: "PUT",
      body: file,
      headers: {
        "Content-Type": file.type,
      },
    })

    // Step 3: Save file metadata
    const result = await saveFile.mutateAsync({
      input: {
        url: url.split("?")[0], // Remove query params
        name: file.name,
        type: file.type,
        size: file.size,
      },
    })

    console.log("File saved:", result.id)
  }

  return <input type="file" onChange={(e) => handleFileUpload(e.target.files[0])} />
}
```

### Posts with Infinite Scroll

```typescript
// apps/web/src/routes/posts.tsx
import { orpc } from "@/utils/orpc"

export function PostsPage() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = orpc.posts.list.useInfiniteQuery({
    input: {
      limit: 10,
      published: true,
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor,
  })

  const allPosts = data?.pages.flatMap((page) => page.data) ?? []

  return (
    <div>
      {allPosts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}

      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? "Loading..." : "Load More"}
        </button>
      )}
    </div>
  )
}
```

### Optimistic Updates

```typescript
// apps/web/src/routes/posts/$postId.tsx
import { orpc } from "@/utils/orpc"
import { useQueryClient } from "@tanstack/react-query"

export function PostDetailPage({ postId }: { postId: string }) {
  const utils = orpc.useUtils()
  const queryClient = useQueryClient()

  const togglePublish = orpc.posts.togglePublish.useMutation({
    onMutate: async ({ input }) => {
      // Cancel outgoing refetches
      await utils.posts.get.cancel({ input: { id: input.id } })

      // Snapshot previous value
      const previous = utils.posts.get.getData({ input: { id: input.id } })

      // Optimistically update
      utils.posts.get.setData({ input: { id: input.id } }, (old) => {
        if (!old) return old
        return { ...old, published: !old.published }
      })

      return { previous }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previous) {
        utils.posts.get.setData(
          { input: { id: variables.input.id } },
          context.previous
        )
      }
    },
    onSettled: () => {
      // Refetch after mutation
      utils.posts.get.invalidate()
    },
  })

  return (
    <button onClick={() => togglePublish.mutate({ input: { id: postId } })}>
      Toggle Publish
    </button>
  )
}
```

## Router Composition

Combining routers into main app router:

```typescript
// packages/api/src/index.ts
import { paymentsRouter } from "./routers/payments"
import { postsRouter } from "./routers/posts"
import { s3Router } from "./routers/s3"
import { usersRouter } from "./routers/users"

export const appRouter = {
  payments: paymentsRouter,
  posts: postsRouter,
  s3: s3Router,
  users: usersRouter,
}

export type AppRouter = typeof appRouter
```

These examples demonstrate production-ready patterns from the actual condomin-ia codebase.
