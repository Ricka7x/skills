# API Procedures (oRPC + Hono)

## File Locations

```
packages/api/src/
├── index.ts          → Procedure base, middleware, exports
├── context.ts        → Context factory (session from better-auth)
└── routers/
    ├── index.ts      → appRouter composition + type exports
    ├── payments.ts   → Example domain router
    └── s3.ts         → Example domain router
```

## Context

```ts
// packages/api/src/context.ts
export async function createContext({ context }: CreateContextOptions) {
  const session = await auth.api.getSession({
    headers: context.req.raw.headers,
  });
  return { session };
}

export type Context = Awaited<ReturnType<typeof createContext>>;
```

## The Three Procedure Levels

```ts
// packages/api/src/index.ts
export const o = os.$context<Context>();

export const publicProcedure = o;                          // Anyone
export const protectedProcedure = publicProcedure.use(requireAuth);  // Authenticated users
export const adminProcedure = publicProcedure.use(requireAdmin);     // Admin role only
```

`requireAuth` narrows `context.session` to non-null — inside a `protectedProcedure` handler, `context.session.user` is always defined.

## Adding a New Router

**1. Create `packages/api/src/routers/my-feature.ts`:**

```ts
import { ORPCError } from "@orpc/server";
import { z } from "zod";
import { db } from "@condomin-ia/db";
import { eq } from "@condomin-ia/db";
import { myTable } from "@condomin-ia/db/schema";
import { protectedProcedure, publicProcedure } from "../index";

// Entity schema — reuse on client for type inference
export const myItemSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  userId: z.string(),
  createdAt: z.coerce.date(),
});

export const myFeatureRouter = {
  list: protectedProcedure
    .input(z.object({
      page: z.int().min(1).default(1),
      pageSize: z.int().min(1).max(100).default(20),
    }))
    .output(z.object({
      items: z.array(myItemSchema),
      total: z.int(),
    }))
    .handler(async ({ input, context }) => {
      const offset = (input.page - 1) * input.pageSize;
      const items = await db.query.myTable.findMany({
        where: eq(myTable.userId, context.session.user.id),
        limit: input.pageSize,
        offset,
      });
      return { items, total: items.length };
    }),

  get: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .output(myItemSchema)
    .handler(async ({ input, context }) => {
      const item = await db.query.myTable.findFirst({
        where: eq(myTable.id, input.id),
      });
      if (!item) throw new ORPCError("NOT_FOUND", { message: "Item not found" });
      if (item.userId !== context.session.user.id) throw new ORPCError("FORBIDDEN");
      return item;
    }),

  create: protectedProcedure
    .input(z.object({ name: z.string().min(1).max(200) }))
    .output(myItemSchema)
    .handler(async ({ input, context }) => {
      const [item] = await db.insert(myTable).values({
        id: crypto.randomUUID(),
        name: input.name,
        userId: context.session.user.id,
        createdAt: new Date(),
      }).returning();
      return item;
    }),

  update: protectedProcedure
    .input(z.object({
      id: z.uuid(),
      name: z.string().min(1).max(200),
    }))
    .output(myItemSchema)
    .handler(async ({ input, context }) => {
      const existing = await db.query.myTable.findFirst({
        where: eq(myTable.id, input.id),
      });
      if (!existing) throw new ORPCError("NOT_FOUND");
      if (existing.userId !== context.session.user.id) throw new ORPCError("FORBIDDEN");

      const [updated] = await db.update(myTable)
        .set({ name: input.name })
        .where(eq(myTable.id, input.id))
        .returning();
      return updated;
    }),

  delete: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .output(z.object({ success: z.boolean() }))
    .handler(async ({ input, context }) => {
      const existing = await db.query.myTable.findFirst({
        where: eq(myTable.id, input.id),
      });
      if (!existing) throw new ORPCError("NOT_FOUND");
      if (existing.userId !== context.session.user.id) throw new ORPCError("FORBIDDEN");

      await db.delete(myTable).where(eq(myTable.id, input.id));
      return { success: true };
    }),
};
```

**2. Register in `packages/api/src/routers/index.ts`:**

```ts
import { myFeatureRouter } from "./my-feature";

export const appRouter = {
  payments: paymentsRouter,
  s3: s3Router,
  myFeature: myFeatureRouter, // ← add here
};

export type AppRouter = typeof appRouter;
export type AppRouterClient = RouterClient<typeof appRouter>;
```

## Naming Conventions

**Procedure names** — standard CRUD verbs only:
- `list` — paginated/filtered collection
- `get` — single item by ID
- `create` — new item
- `update` — modify existing (full or partial)
- `delete` — remove item
- Domain-specific actions: `publish`, `archive`, `verify`

**Router names** — camelCase, no "Router" suffix in the `appRouter` key:
```ts
// ✅
export const appRouter = { users: usersRouter, posts: postsRouter }
// ❌
export const appRouter = { usersRouter, postsRouter }
```

## Error Handling

```ts
import { ORPCError } from "@orpc/server";

throw new ORPCError("UNAUTHORIZED")     // 401 — not logged in
throw new ORPCError("FORBIDDEN")        // 403 — logged in but not allowed
throw new ORPCError("NOT_FOUND", { message: "Todo not found" })     // 404
throw new ORPCError("BAD_REQUEST", { message: "Invalid file type",  // 400
  data: { allowedTypes: ["image/png", "image/jpeg"] },
})
throw new ORPCError("INTERNAL_SERVER_ERROR")  // 500
```

Always check ownership before mutating — never trust that a user owns a resource just because they're authenticated.

## Cursor-Based Pagination

Offset pagination (above) is simplest, but for large/frequently-appended tables prefer a cursor:

```ts
const paginatedResponseSchema = <T extends z.ZodType>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    nextCursor: z.string().optional(),
    hasMore: z.boolean(),
  });

list: protectedProcedure
  .input(z.object({
    limit: z.int().min(1).max(100).default(20),
    cursor: z.string().optional(),
  }))
  .output(paginatedResponseSchema(postSchema))
  .handler(async ({ input }) => {
    const items = await db.query.posts.findMany({
      limit: input.limit + 1, // fetch one extra to know if there's more
      where: input.cursor ? gt(posts.id, input.cursor) : undefined,
      orderBy: desc(posts.createdAt),
    });

    const hasMore = items.length > input.limit;
    const data = hasMore ? items.slice(0, -1) : items;
    const nextCursor = hasMore ? data.at(-1)?.id : undefined;

    return { items: data, nextCursor, hasMore };
  }),
```

## Filtering, Search & Sorting

```ts
const sortableFields = ["createdAt", "updatedAt", "title"] as const;

list: protectedProcedure
  .input(z.object({
    status: z.enum(["active", "archived"]).optional(),
    category: z.string().optional(),
    search: z.string().optional(),
    createdAfter: z.coerce.date().optional(),
    sortBy: z.enum(sortableFields).default("createdAt"),
    sortOrder: z.enum(["asc", "desc"]).default("desc"),
  }))
  .handler(async ({ input }) => {
    const conditions = [
      input.status ? eq(posts.status, input.status) : undefined,
      input.category ? eq(posts.category, input.category) : undefined,
      input.search
        ? or(ilike(posts.title, `%${input.search}%`), ilike(posts.content, `%${input.search}%`))
        : undefined,
      input.createdAfter ? gte(posts.createdAt, input.createdAfter) : undefined,
    ];

    const orderByFn = input.sortOrder === "asc" ? asc : desc;

    return await db.query.posts.findMany({
      where: and(...conditions),
      orderBy: orderByFn(posts[input.sortBy]),
    });
  }),
```

## Nested Resources

Keep router nesting shallow (max 2 levels) but a sub-collection under a parent entity is a legitimate case:

```ts
export const usersRouter = {
  get: protectedProcedure.handler(/* ... */),

  posts: {
    list: protectedProcedure
      .input(z.object({ userId: z.uuid() }))
      .handler(async ({ input }) =>
        db.query.posts.findMany({ where: eq(posts.userId, input.userId) })
      ),
  },
};
```

## Batch Operations

For "do this to N items, report per-item success/failure" — don't let one bad item fail the whole batch:

```ts
bulkCreate: protectedProcedure
  .input(z.object({ items: z.array(createTodoSchema).min(1).max(100) }))
  .output(z.object({
    created: z.array(todoSchema),
    failed: z.array(z.object({ index: z.int(), error: z.string() })),
  }))
  .handler(async ({ input, context }) => {
    const created: (typeof todoSchema._type)[] = [];
    const failed: { index: number; error: string }[] = [];

    for (const [index, item] of input.items.entries()) {
      try {
        const [row] = await db.insert(todos)
          .values({ ...item, userId: context.session.user.id })
          .returning();
        created.push(row);
      } catch (error) {
        failed.push({ index, error: error instanceof Error ? error.message : "Unknown error" });
      }
    }

    return { created, failed };
  }),
```

## Multi-Step Operations (e.g. File Upload)

```ts
export const filesRouter = {
  // Step 1: presigned URL
  getUploadUrl: protectedProcedure
    .input(z.object({ filename: z.string(), contentType: z.string() }))
    .output(z.object({ uploadUrl: z.url(), fileId: z.uuid() }))
    .handler(async ({ input, context }) => {
      const fileId = crypto.randomUUID();
      const key = `uploads/${context.session.user.id}/${fileId}/${input.filename}`;
      const uploadUrl = await getSignedUrl(s3Client, new PutObjectCommand({
        Bucket: env.AWS_BUCKET_NAME,
        Key: key,
        ContentType: input.contentType,
      }), { expiresIn: 3600 });
      return { uploadUrl, fileId };
    }),

  // Step 2: confirm + persist metadata
  confirmUpload: protectedProcedure
    .input(z.object({ fileId: z.uuid(), url: z.url(), size: z.int() }))
    .output(z.object({ success: z.boolean() }))
    .handler(async ({ input, context }) => {
      await db.insert(files).values({
        id: input.fileId,
        url: input.url,
        size: input.size,
        userId: context.session.user.id,
      });
      return { success: true };
    }),
};
```

## Webhooks

Webhooks use `publicProcedure` — auth comes from verifying the provider's signature, not a session:

```ts
stripeWebhook: publicProcedure
  .input(z.object({ signature: z.string(), payload: z.string() }))
  .handler(async ({ input }) => {
    const event = stripe.webhooks.constructEvent(
      input.payload,
      input.signature,
      env.STRIPE_WEBHOOK_SECRET
    );

    switch (event.type) {
      case "payment_intent.succeeded":
        await handlePaymentSuccess(event.data.object);
        break;
      case "payment_intent.failed":
        await handlePaymentFailed(event.data.object);
        break;
    }

    return { received: true };
  }),
```

## Hono Server Wiring

The server in `apps/server/src/index.ts` mounts oRPC at `/rpc` and OpenAPI at `/api-reference`. Auth is handled separately at `/api/auth/*`. No need to change server wiring when adding new routers — just update `appRouter`.

## Anti-Patterns

- ❌ Skip `.input()` validation on any procedure
- ❌ Put auth logic inside handlers — use `protectedProcedure` / `adminProcedure`
- ❌ Return DB errors directly — throw `ORPCError` with user-friendly messages
- ❌ Use integer IDs — always `z.uuid()` for ID inputs
- ❌ Skip `.output()` schema — always define response shape
- ❌ Create deeply nested routers — max 2 levels
