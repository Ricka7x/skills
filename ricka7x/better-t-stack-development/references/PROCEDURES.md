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

## Hono Server Wiring

The server in `apps/server/src/index.ts` mounts oRPC at `/rpc` and OpenAPI at `/api-reference`. Auth is handled separately at `/api/auth/*`. No need to change server wiring when adding new routers — just update `appRouter`.

## Anti-Patterns

- ❌ Skip `.input()` validation on any procedure
- ❌ Put auth logic inside handlers — use `protectedProcedure` / `adminProcedure`
- ❌ Return DB errors directly — throw `ORPCError` with user-friendly messages
- ❌ Use integer IDs — always `z.uuid()` for ID inputs
- ❌ Skip `.output()` schema — always define response shape
- ❌ Create deeply nested routers — max 2 levels
