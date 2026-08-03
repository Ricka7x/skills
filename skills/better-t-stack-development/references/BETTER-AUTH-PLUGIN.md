# Better Auth Plugins

How we write custom plugins in this project. Plugins live in `packages/auth/src/plugins/`.

---

## Plugin Location

```
packages/auth/
├── src/
│   ├── index.ts          → betterAuth({ plugins: [...] })
│   ├── client.ts         → createAuthClient({ plugins: [...] })
│   └── plugins/
│       └── my-plugin/
│           ├── index.ts        → re-exports server plugin
│           ├── my-plugin.ts    → plugin factory + assembled object
│           ├── routes.ts       → createAuthEndpoint definitions
│           ├── schema.ts       → DB schema extensions
│           ├── types.ts        → options interface + model types
│           ├── client.ts       → client plugin
│           └── error-codes.ts  → error constants (optional)
```

Register in `packages/auth/src/index.ts`:

```ts
import { betterAuth } from "better-auth";
import { myPlugin } from "./plugins/my-plugin";

export const auth = betterAuth({
  // ... existing config
  plugins: [
    // ... existing plugins
    myPlugin({ /* options */ }),
  ],
});
```

Register client plugin in `packages/auth/src/client.ts`:

```ts
import { createAuthClient } from "better-auth/client";
import { myPluginClient } from "./plugins/my-plugin/client";

export const authClient = createAuthClient({
  // ... existing config
  plugins: [
    // ... existing plugins
    myPluginClient(),
  ],
});
```

After any schema changes run:
```bash
bun plugin:generate   # alias for npx @better-auth/cli generate
```

---

## Complete Plugin Example

A realistic plugin for this project — audit logging on sign-in.

### `schema.ts`

```ts
import type { BetterAuthPluginDBSchema } from "better-auth";

export const schema = {
  auditLog: {
    fields: {
      userId:    { type: "string", required: true, references: { model: "user", field: "id", onDelete: "cascade" } },
      action:    { type: "string", required: true },   // e.g. "sign-in", "password-reset"
      ipAddress: { type: "string", required: false },
      userAgent: { type: "string", required: false },
      createdAt: { type: "date",   required: true },
    },
  },
} satisfies BetterAuthPluginDBSchema;
```

### `types.ts`

```ts
export interface AuditLogOptions {
  /** Actions to record. Defaults to all. */
  actions?: ("sign-in" | "sign-out" | "password-reset" | "sign-up")[];
  /** Max logs to return per page @default 50 */
  defaultPageSize?: number;
}

export type ResolvedAuditLogOptions = Required<AuditLogOptions>;
```

### `routes.ts`

```ts
import { createAuthEndpoint, sessionMiddleware, APIError } from "better-auth/api";
import type { Where } from "better-auth";
import * as z from "zod";
import type { ResolvedAuditLogOptions } from "./types";

export const listAuditLogs = (opts: ResolvedAuditLogOptions) =>
  createAuthEndpoint(
    "/audit-log/list",
    {
      method: "GET",
      use: [sessionMiddleware],
      query: z.object({
        userId: z.string().optional(),
        action: z.string().optional(),
        page:   z.coerce.number().int().min(1).default(1),
        limit:  z.coerce.number().int().min(1).max(100).optional(),
      }),
      metadata: {
        openapi: {
          operationId: "listAuditLogs",
          summary: "List audit log entries",
          responses: { 200: { description: "Paginated audit logs" } },
        },
      },
    },
    async (ctx) => {
      const session = ctx.context.session;
      const limit = ctx.query.limit ?? opts.defaultPageSize;
      const offset = (ctx.query.page - 1) * limit;

      const where: Where[] = [];
      // Scope to own user unless calling on behalf of another (admin use-case)
      const targetUserId = ctx.query.userId ?? session.user.id;
      where.push({ field: "userId", operator: "eq", value: targetUserId });
      if (ctx.query.action) {
        where.push({ field: "action", operator: "eq", value: ctx.query.action });
      }

      const logs = await ctx.context.adapter.findMany({
        model: "auditLog",
        where,
        limit,
        offset,
        sortBy: { field: "createdAt", direction: "desc" },
      });

      return ctx.json({ logs, page: ctx.query.page, limit });
    },
  );
```

### `my-plugin.ts`

```ts
import type { BetterAuthPlugin } from "better-auth";
import { createAuthMiddleware, getSessionFromCtx } from "better-auth/api";
import { schema } from "./schema";
import { listAuditLogs } from "./routes";
import type { AuditLogOptions, ResolvedAuditLogOptions } from "./types";
import { AUDIT_LOG_ERROR_CODES } from "./error-codes";

export const auditLog = (options?: AuditLogOptions) => {
  const opts: ResolvedAuditLogOptions = {
    actions: options?.actions ?? ["sign-in", "sign-out", "password-reset", "sign-up"],
    defaultPageSize: options?.defaultPageSize ?? 50,
  };

  return {
    id: "audit-log",
    $ERROR_CODES: AUDIT_LOG_ERROR_CODES,
    schema,
    endpoints: {
      listAuditLogs: listAuditLogs(opts),
    },
    hooks: {
      after: [
        {
          // Record an audit log entry after sign-in
          matcher: (context) => context.path?.startsWith("/sign-in") ?? false,
          handler: createAuthMiddleware(async (ctx) => {
            const session = await getSessionFromCtx(ctx);
            if (!session) return;

            const ip = ctx.headers?.get("x-forwarded-for") ?? ctx.headers?.get("cf-connecting-ip") ?? null;
            const ua = ctx.headers?.get("user-agent") ?? null;

            await ctx.context.adapter.create({
              model: "auditLog",
              data: {
                userId:    session.user.id,
                action:    "sign-in",
                ipAddress: ip,
                userAgent: ua,
                createdAt: new Date(),
              },
            });
          }),
        },
      ],
    },
  } satisfies BetterAuthPlugin;  // satisfies — NOT `: BetterAuthPlugin` return type
};
```

### `client.ts`

```ts
import type { BetterAuthClientPlugin } from "better-auth/client";
import type { auditLog } from "./my-plugin";

type AuditLogPlugin = typeof auditLog;

export const auditLogClient = () => {
  return {
    id: "audit-log",
    $InferServerPlugin: {} as ReturnType<AuditLogPlugin>,
  } satisfies BetterAuthClientPlugin;
};
```

### `error-codes.ts`

```ts
export const AUDIT_LOG_ERROR_CODES = {
  NOT_FOUND:  "Audit log entry not found",
  FORBIDDEN:  "You don't have access to this audit log",
} as const;
```

### `index.ts`

```ts
export { auditLog } from "./my-plugin";
```

---

## Key Rules — Don't Get These Wrong

### 1. Never annotate the plugin factory return type as `BetterAuthPlugin`

This erases endpoint type info and breaks client inference.

```ts
// ✅ satisfies on the object — validates shape, preserves types
export const myPlugin = (options?: Options) => {
  return {
    id: "my-plugin",
    endpoints: { listItems: listItems(opts) },
  } satisfies BetterAuthPlugin;
};

// ❌ return type annotation — client gets generic BetterAuthPlugin, no endpoint types
export const myPlugin = (options?: Options): BetterAuthPlugin => { ... };
```

### 2. Import `Where` from `better-auth`, not `better-auth/db`

```ts
import type { Where } from "better-auth";       // ✅
import type { Where } from "better-auth/types";  // ✅
import type { Where } from "better-auth/db";     // ❌ no exported member
```

Always annotate where-clause arrays as `Where[]` to prevent operator literal widening:

```ts
const where: Where[] = [
  { field: "userId", operator: "eq", value: id },  // operator stays narrowly typed
];
```

### 3. Hook `context.path` is optional — always guard it

```ts
// ✅
matcher: (context) => context.path?.startsWith("/sign-in") ?? false,

// ❌ TypeScript error — path can be undefined
matcher: (context) => context.path.startsWith("/sign-in"),
```

### 4. Hooks vs Middleware — know the difference

| | Hooks | Middleware |
|---|---|---|
| Runs when endpoint called server-side | ✅ Yes | ❌ No |
| Runs on HTTP API requests | ✅ Yes | ✅ Yes |
| Use for | Auth logic, data recording, response transformation | Request validation, rate limiting, HTTP-only concerns |

### 5. Only GET and POST methods

```ts
// ✅
method: "GET"   // fetches data
method: "POST"  // mutations (create, update, delete)

// ❌ Never use PUT, PATCH, DELETE
```

### 6. Endpoint paths — kebab-case, plugin-prefixed

```ts
"/audit-log/list-entries"   // ✅
"/auditLog/listEntries"     // ❌ not camelCase
"/list-entries"             // ❌ not prefixed — will conflict with other plugins
```

Client usage auto-converts path to camelCase:

```ts
// /audit-log/list-entries → authClient.auditLog.listEntries()
const { data, error } = await authClient.auditLog.listEntries({ page: 1 });
```

### 7. Defaults object must not use `as const` with mutable array properties

When merging defaults into a resolved-options type, `as const` makes arrays `readonly`, which is incompatible with a plain `string[]` field on the options interface:

```ts
// ❌ WRONG — readonly ["admin"] is not assignable to string[]
const DEFAULTS = {
  roles: ["admin"],
  pageSize: 50,
} as const;

// ✅ Correct — explicit type annotation keeps arrays mutable
const DEFAULTS: Pick<ResolvedOptions, "roles" | "pageSize"> = {
  roles: ["admin"],
  pageSize: 50,
};
```

### 8. Don't redefine the adapter interface with `operator: string`

When typing a function that receives `ctx.context` (the auth context), use the real `Where` type rather than a hand-rolled shape — `operator: string` won't be assignable to the real `WhereOperator` union:

```ts
// ❌ WRONG — operator: string is not assignable to WhereOperator
interface MyContext {
  adapter: {
    findMany: <T>(opts: {
      model: string;
      where?: Array<{ field: string; operator: string; value: unknown }>;
    }) => Promise<T[]>;
  };
}

// ✅ Correct — use Where from better-auth
import type { Where } from "better-auth";

interface MyContext {
  adapter: {
    findMany: <T>(opts: { model: string; where?: Where[] }) => Promise<T[]>;
  };
}
```

---

## Context Object Reference

Inside `createAuthEndpoint` handlers, `ctx.context` provides:

| Property | Description |
|---|---|
| `adapter` | ORM-like DB functions (`findOne`, `findMany`, `create`, `update`, `delete`, `count`) — **preferred** over raw SQL |
| `db` | Raw Kysely instance for complex joins/SQL |
| `internalAdapter` | Built-in helpers (`findUserById`, `createSession`, `listUsers`, etc.) |
| `options` | The BetterAuth instance options |
| `secret` | Server secret key |
| `baseURL` | Auth server base URL |
| `logger` | Logger instance |
| `session` | Available when `sessionMiddleware` is in the endpoint's `use` array |
| `createAuthCookie` | Cookie helper |
| `isTrustedOrigin` | Origin validation helper |

---

## Session Access Patterns

```ts
// In endpoints with sessionMiddleware in use[] — direct
const endpoint = createAuthEndpoint("/my-plugin/action", {
  method: "POST",
  use: [sessionMiddleware],
}, async (ctx) => {
  const { user, session } = ctx.context.session;  // typed, safe
});

// In hooks — use getSessionFromCtx (may return null)
import { getSessionFromCtx } from "better-auth/api";

handler: createAuthMiddleware(async (ctx) => {
  const session = await getSessionFromCtx(ctx);
  if (!session) return; // unauthenticated — don't throw, just skip
  // ...
}),
```

---

## Adapter Usage

Prefer `ctx.context.adapter` for all DB operations — it gives ORM-like methods and respects the Drizzle adapter config. Use `ctx.context.db` (raw Kysely) only for complex joins or raw SQL.

```ts
// Find one
const item = await ctx.context.adapter.findOne({
  model: "auditLog",
  where: [{ field: "id", operator: "eq", value: id }],
});

// Find many with sorting + pagination
const items = await ctx.context.adapter.findMany({
  model: "auditLog",
  where: [{ field: "userId", operator: "eq", value: userId }],
  limit: 50,
  offset: 0,
  sortBy: { field: "createdAt", direction: "desc" },
});

// Create
const created = await ctx.context.adapter.create({
  model: "auditLog",
  data: { userId, action, createdAt: new Date() },
});

// Update
const updated = await ctx.context.adapter.update({
  model: "auditLog",
  where: [{ field: "id", operator: "eq", value: id }],
  update: { action: "updated-action" },
});

// Delete
await ctx.context.adapter.delete({
  model: "auditLog",
  where: [{ field: "id", operator: "eq", value: id }],
});
```

---

## Pagination, Filtering, Searching & Sorting

Full pattern for a list endpoint, extracted from the better-auth admin plugin. The audit-log example above only shows simple `page`/`limit` — reach for this when a list endpoint also needs search, arbitrary-field filtering, or sorting.

### Query Schema

All params are optional — the endpoint works as a plain "get all" if none are provided.

```ts
import * as z from "zod";
import { whereOperators } from "better-auth/db";
// whereOperators ≈ ["eq", "ne", "lt", "lte", "gt", "gte", "in", "not_in", "contains", "starts_with", "ends_with"]

const listItemsQuerySchema = z.object({
  // --- Search ---
  searchValue: z.string().optional(),
  searchField: z.string().optional(), // defaults to "name" in the handler
  searchOperator: z.enum(["contains", "starts_with", "ends_with"]).optional(),

  // --- Pagination ---
  limit: z.string().or(z.number()).optional(),
  offset: z.string().or(z.number()).optional(),

  // --- Sorting ---
  sortBy: z.string().optional(),
  sortDirection: z.enum(["asc", "desc"]).optional(),

  // --- Filtering ---
  filterField: z.string().optional(),
  filterValue: z
    .string()
    .or(z.number())
    .or(z.boolean())
    .or(z.array(z.string()))
    .or(z.array(z.number()))
    .optional(),
  filterOperator: z.enum(whereOperators).optional(), // defaults to "eq"
});
```

- `limit`/`offset` accept both `string` (raw query params) and `number` — always coerce with `Number()` in the handler.
- `searchField` should be a constrained enum per-model in real usage, to prevent arbitrary column access — see the reusable factory below.
- `filterOperator` uses the full `whereOperators` enum from better-auth's adapter.

### Full List Endpoint

```ts
import { createAuthEndpoint, sessionMiddleware } from "better-auth/api";
import type { Where } from "better-auth";

export const listItems = (opts: MyPluginOptions) =>
  createAuthEndpoint(
    "/my-plugin/list-items",
    { method: "GET", use: [sessionMiddleware], query: listItemsQuerySchema },
    async (ctx) => {
      const where: Where[] = [];

      if (ctx.query?.searchValue) {
        where.push({
          field: ctx.query.searchField || "name",
          operator: ctx.query.searchOperator || "contains",
          value: ctx.query.searchValue,
        });
      }

      if (ctx.query?.filterValue !== undefined) {
        where.push({
          field: ctx.query.filterField || "name",
          operator: ctx.query.filterOperator || "eq",
          value: ctx.query.filterValue,
        });
      }

      const limit = Number(ctx.query?.limit) || opts.defaultPageSize || 20;
      const offset = Number(ctx.query?.offset) || 0;
      const sortBy = ctx.query?.sortBy
        ? { field: ctx.query.sortBy, direction: ctx.query.sortDirection || ("asc" as const) }
        : undefined;

      const items = await ctx.context.adapter.findMany({
        model: "myPluginItems",
        where: where.length ? where : undefined,
        limit,
        offset,
        sortBy,
      });

      // Total count with the same filters, for pagination UI
      const total = await ctx.context.adapter.count({
        model: "myPluginItems",
        where: where.length ? where : undefined,
      });

      return ctx.json({ items, total, limit, offset });
    },
  );
```

Response shape: `{ items: Item[]; total: number; limit?: number; offset?: number }`.

For the built-in `user` model specifically, better-auth's admin plugin exposes `internalAdapter.listUsers(limit, offset, sortBy, where)` / `internalAdapter.countTotalUsers(where)` instead — use `ctx.context.adapter.findMany()`/`.count()` for custom tables.

### Reusable Query Schema Factory

DRY this up across multiple models by constraining `searchField` to that model's actual searchable columns:

```ts
export function createListQuerySchema<T extends string>(searchableFields: readonly T[]) {
  return z.object({
    searchValue: z.string().optional(),
    searchField: z.enum(searchableFields as [T, ...T[]]).optional(),
    searchOperator: z.enum(["contains", "starts_with", "ends_with"]).optional(),
    limit: z.string().or(z.number()).optional(),
    offset: z.string().or(z.number()).optional(),
    sortBy: z.string().optional(),
    sortDirection: z.enum(["asc", "desc"]).optional(),
    filterField: z.string().optional(),
    filterValue: z.string().or(z.number()).or(z.boolean()).or(z.array(z.string())).or(z.array(z.number())).optional(),
    filterOperator: z.enum(whereOperators).optional(),
  });
}

// Usage:
const listItemsQuery = createListQuerySchema(["name", "description"] as const);
const listOrdersQuery = createListQuerySchema(["status", "customerName"] as const);
```

### Client Usage

```ts
const { data, error } = await authClient.myPlugin.listItems({
  query: {
    searchValue: "foo",
    searchField: "name",
    limit: "10",
    offset: "0",
    sortBy: "createdAt",
    sortDirection: "desc",
    filterField: "isActive",
    filterValue: "true",
  },
});
// data.items, data.total, data.limit, data.offset
```

### Cursor-Based Pagination Alternative

Prefer this over offset pagination for large, frequently-appended tables:

```ts
const cursorPaginationSchema = z.object({
  cursor: z.string().optional(), // item ID to start after
  limit: z.string().or(z.number()).optional(),
});

// In handler:
const where: Where[] = [];
if (ctx.query?.cursor) {
  where.push({ field: "id", operator: "gt", value: ctx.query.cursor });
}
const items = await ctx.context.adapter.findMany({
  model: "myPluginItems",
  where: where.length ? where : undefined,
  limit: Number(ctx.query?.limit) || 20,
  sortBy: { field: "id", direction: "asc" },
});
const nextCursor = items.length ? items[items.length - 1].id : null;
return ctx.json({ items, nextCursor });
```

---

## Throwing Errors

```ts
import { APIError } from "better-auth/api";

// 404
throw new APIError("NOT_FOUND", { message: "Item not found" });

// 400 validation
throw new APIError("BAD_REQUEST", { message: "Invalid input" });

// 401 unauthenticated
throw new APIError("UNAUTHORIZED", { message: "Sign in required" });

// 403 forbidden
throw new APIError("FORBIDDEN", { message: "You don't have access" });

// 409 conflict
throw new APIError("CONFLICT", { message: "Already exists" });

// 500 unexpected
throw new APIError("INTERNAL_SERVER_ERROR", { message: "Unexpected error" });
```

---

## Testing Plugins

Use the `testUtils` plugin (gate behind `NODE_ENV === "test"`) to create sessions and test endpoints. See [TESTING.md](TESTING.md) for the full pattern.

Quick example:

```ts
import { describe, it, expect, beforeAll } from "vitest";
import { auth } from "../../index";
import type { TestHelpers } from "better-auth/plugins";

describe("auditLog plugin", () => {
  let test: TestHelpers;

  beforeAll(async () => {
    const ctx = await auth.$context;
    test = ctx.test;
  });

  it("records a sign-in event", async () => {
    const user = test.createUser({ email: "audit-test@example.com" });
    await test.saveUser(user);

    // Simulate sign-in to trigger the hook
    const headers = await test.getAuthHeaders({ userId: user.id });

    // Query via the plugin endpoint
    const result = await auth.api.auditLog.listEntries({
      headers,
      query: { userId: user.id },
    });

    expect(result.logs.length).toBeGreaterThan(0);
    expect(result.logs[0].action).toBe("sign-in");

    await test.deleteUser(user.id);
  });
});
```

---

## Custom Client Actions (getActions)

Use when you need client-side logic beyond what endpoint inference gives you — e.g. chaining calls, local processing, or custom error handling.

```ts
import type { BetterAuthClientPlugin } from "better-auth/client";
import type { BetterFetchOption } from "@better-fetch/fetch";
import type { myPlugin } from "./my-plugin";

export const myPluginClient = () => ({
  id: "my-plugin",
  $InferServerPlugin: {} as ReturnType<typeof myPlugin>,
  getActions: ($fetch) => ({
    // Always: one data arg + optional fetchOptions second arg
    uploadAndCreate: async (
      data: { file: File; name: string },
      fetchOptions?: BetterFetchOption,
    ) => {
      // Custom logic before the API call
      const url = await uploadToStorage(data.file);
      return $fetch("/my-plugin/create-item", {
        method: "POST",
        body: { name: data.name, fileUrl: url },
        ...fetchOptions,
      });
    },
  }),
}) satisfies BetterAuthClientPlugin;
```

---

## Rate Limiting

```ts
rateLimit: [
  {
    pathMatcher: (path) => path.startsWith("/audit-log/"),
    limit: 60,
    window: 60, // seconds
  },
],
```

---

## Quick Reference: Import Cheatsheet

```ts
// Server plugin types
import type { BetterAuthPlugin, BetterAuthPluginDBSchema, Where } from "better-auth";

// Endpoint + middleware factories
import { createAuthEndpoint, sessionMiddleware, APIError } from "better-auth/api";
import { createAuthMiddleware, getSessionFromCtx } from "better-auth/api";

// Client plugin
import type { BetterAuthClientPlugin } from "better-auth/client";
import type { BetterFetchOption } from "@better-fetch/fetch";

// Schema
import * as z from "zod";
```