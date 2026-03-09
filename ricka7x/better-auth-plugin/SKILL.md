---
name: better-auth-plugin
description: >
  Create better-auth plugins with proper server/client structure, endpoints, schemas,
  hooks, middleware, pagination, filtering, searching, sorting, and typed options.
  Use when the user asks to "create a better-auth plugin", "build an auth plugin",
  "add a plugin for better-auth", "better-auth server plugin", "better-auth client plugin",
  or needs help structuring endpoints with pagination/filtering in the better-auth ecosystem.
---

# Better Auth Plugin Creation

## Plugin Architecture

Every better-auth plugin is a **server/client pair**. The server plugin is the backbone; the client plugin infers endpoint types from it and provides frontend API access.

### File Structure

```
my-plugin/
├── index.ts        # Re-exports from main plugin file
├── my-plugin.ts    # Main plugin factory + assembled endpoints
├── routes.ts       # Endpoint definitions (createAuthEndpoint calls)
├── schema.ts       # Database schema extensions
├── types.ts        # Options interface + extended model types
├── client.ts       # Client plugin with $InferServerPlugin
└── error-codes.ts  # Plugin-specific error code constants (optional)
```

## Server Plugin

### Minimal Skeleton

```ts
import type { BetterAuthPlugin } from 'better-auth';

export const myPlugin = (options?: MyPluginOptions) => {
  const opts = {
    ...options,
    // merge defaults here
  };

  return {
    id: 'my-plugin',
    schema,           // from ./schema.ts
    endpoints: {      // from ./routes.ts
      listItems: listItems(opts),
      getItem: getItem(opts),
      createItem: createItem(opts),
    },
    hooks: { before: [], after: [] },  // optional
    // onRequest, onResponse, rateLimit, middlewares — all optional
  } satisfies BetterAuthPlugin;
};
```

### Passing Options

Define an options interface in `types.ts`. The plugin factory receives it and merges defaults before forwarding to every route factory.

```ts
// types.ts
export interface MyPluginOptions {
  /** Items returned per page @default 20 */
  defaultPageSize?: number;
  /** Custom schema overrides */
  schema?: InferOptionSchema<typeof pluginSchema>;
  // add any plugin-level config here
}
```

```ts
// my-plugin.ts — merge defaults at the top
export const myPlugin = (options?: MyPluginOptions) => {
  const opts = {
    ...options,
    defaultPageSize: options?.defaultPageSize ?? 20,
  } as Required<Pick<MyPluginOptions, 'defaultPageSize'>> & MyPluginOptions;
  // ...
};
```

Each route factory `(opts) => createAuthEndpoint(...)` receives the merged options so it can read config values inside the handler.

## Schema

Extend existing tables (`user`, `session`) or create new ones. Fields added to `user`/`session` are auto-inferred in `getSession`, `signUpEmail`, etc.

```ts
// schema.ts
import type { BetterAuthPluginDBSchema } from 'better-auth';

export const schema = {
  // Extend the user table
  user: {
    fields: {
      plan: {
        type: 'string',      // string | number | boolean | date
        required: false,
        input: false,         // exclude from signup body
      },
    },
  },
  // Create a new table
  myPluginItems: {
    fields: {
      name:      { type: 'string', required: true },
      userId:    { type: 'string', required: true, references: { model: 'user', field: 'id', onDelete: 'cascade' } },
      isActive:  { type: 'boolean', required: false, defaultValue: true },
      createdAt: { type: 'date', required: false },
    },
    // modelName: 'my_plugin_items',  // optional SQL table name override
    // disableMigration: false,
  },
} satisfies BetterAuthPluginDBSchema;
```

**Field properties:** `type`, `required` (default true), `unique` (default false), `references` (optional FK), `input` (default true — set false to hide from client write endpoints), `defaultValue`.

Run `npx @better-auth/cli generate` after schema changes.

## Endpoints (Routes)

Use `createAuthEndpoint` from `better-auth/api`. See [references/PAGINATION_FILTERING.md](references/PAGINATION_FILTERING.md) for the full list-endpoint pattern.

### Rules

- Paths **must** be kebab-case, prefixed with plugin name: `/my-plugin/list-items`
- Only `GET` (reads) or `POST` (mutations) — no PUT/PATCH/DELETE
- Validate with Zod via `body` (POST) or `query` (GET)
- Use `sessionMiddleware` from `better-auth/api` to require auth
- Throw `APIError` from `better-auth/api` for errors

### GET Endpoint (Read)

```ts
import { createAuthEndpoint, sessionMiddleware } from 'better-auth/api';
import { APIError } from 'better-auth/api';
import * as z from 'zod';

const getItemQuerySchema = z.object({
  id: z.string(),
});

export const getItem = (opts: MyPluginOptions) =>
  createAuthEndpoint(
    '/my-plugin/get-item',
    {
      method: 'GET',
      query: getItemQuerySchema,
      use: [sessionMiddleware],
      metadata: {
        openapi: {
          operationId: 'getItem',
          summary: 'Get an item by ID',
          responses: { 200: { description: 'The item' } },
        },
      },
    },
    async (ctx) => {
      const item = await ctx.context.adapter.findOne({
        model: 'myPluginItems',
        where: [{ field: 'id', operator: 'eq', value: ctx.query.id }],
      });
      if (!item) throw new APIError('NOT_FOUND', { message: 'Item not found' });
      return ctx.json(item);
    },
  );
```

### POST Endpoint (Mutation)

```ts
const createItemBodySchema = z.object({
  name: z.string().min(1),
});

export const createItem = (opts: MyPluginOptions) =>
  createAuthEndpoint(
    '/my-plugin/create-item',
    {
      method: 'POST',
      body: createItemBodySchema,
      use: [sessionMiddleware],
    },
    async (ctx) => {
      const session = ctx.context.session;
      const item = await ctx.context.adapter.create({
        model: 'myPluginItems',
        data: {
          name: ctx.body.name,
          userId: session.user.id,
          createdAt: new Date(),
        },
      });
      return ctx.json({ item });
    },
  );
```

### List Endpoint with Pagination, Filtering, Searching, Sorting

See [references/PAGINATION_FILTERING.md](references/PAGINATION_FILTERING.md) for the complete reusable pattern extracted from the admin plugin.

## Hooks

Run code before/after **any** route — even when the endpoint is called directly on the server (unlike middleware which only runs on HTTP requests).

```ts
import { createAuthMiddleware } from 'better-auth/plugins';
import { APIError } from 'better-auth/api';

hooks: {
  before: [
    {
      matcher: (context) => context.path?.startsWith('/sign-up/email') ?? false,
      handler: createAuthMiddleware(async (ctx) => {
        // validate, enrich, or reject
        if (!ctx.body.someField) {
          throw new APIError('BAD_REQUEST', { message: 'Missing field' });
        }
        return { context: ctx };
      }),
    },
  ],
  after: [
    {
      matcher: (context) => context.path === '/list-sessions',
      handler: createAuthMiddleware(async (ctx) => {
        // transform response
        return ctx.json(filteredData);
      }),
    },
  ],
},
```

## Middleware

Only runs on HTTP client requests (not direct server calls). Use for path-specific request interception.

```ts
middlewares: [
  {
    path: '/my-plugin/hello-world',
    middleware: createAuthMiddleware(async (ctx) => {
      // throw APIError or return Response to short-circuit
    }),
  },
],
```

## Client Plugin

```ts
// client.ts
import type { BetterAuthClientPlugin } from 'better-auth/client';
import type { myPlugin } from './my-plugin';

type MyPlugin = typeof myPlugin;

export const myPluginClient = () => {
  return {
    id: 'my-plugin',
    $InferServerPlugin: {} as ReturnType<MyPlugin>,
  } satisfies BetterAuthClientPlugin;
};
```

Endpoint paths auto-convert to camelCase methods: `/my-plugin/list-items` → `authClient.myPlugin.listItems()`.

### Custom Client Actions

```ts
import type { BetterFetchOption } from '@better-fetch/fetch';

export const myPluginClient = () => ({
  id: 'my-plugin',
  $InferServerPlugin: {} as ReturnType<MyPlugin>,
  getActions: ($fetch) => ({
    myCustomAction: async (
      data: { foo: string },
      fetchOptions?: BetterFetchOption,
    ) => {
      return $fetch('/my-plugin/custom', {
        method: 'POST',
        body: { foo: data.foo },
        ...fetchOptions,
      });
    },
  }),
}) satisfies BetterAuthClientPlugin;
```

Each action takes **one data arg + optional fetchOptions**. Return `{ data, error }`.

## Context Object Reference

Inside `createAuthEndpoint` handlers, `ctx.context` provides:

| Property | Description |
|---|---|
| `adapter` | ORM-like DB functions (`findOne`, `findMany`, `create`, `update`, `delete`) — **preferred** |
| `db` | Raw Kysely instance for complex SQL |
| `internalAdapter` | Built-in helpers (`findUserById`, `createSession`, `listUsers`, etc.) |
| `options` | The BetterAuth instance options |
| `secret` | Server secret key |
| `baseURL` | Auth server base URL |
| `logger` | Logger instance |
| `session` | Available when `sessionMiddleware` is in `use` array |
| `createAuthCookie` | Cookie helper |
| `isTrustedOrigin` | Origin validation helper |

## Helper Functions

- `sessionMiddleware` — add to `use: [sessionMiddleware]` to require auth & populate `ctx.context.session`
- `getSessionFromCtx(ctx)` — manually get session in hooks/middleware
- `APIError.from(status, code)` or `new APIError(status, { message })` — throw HTTP errors

## Error Codes Pattern

```ts
// error-codes.ts
export const MY_PLUGIN_ERROR_CODES = {
  ITEM_NOT_FOUND: 'Item not found',
  DUPLICATE_ITEM: 'An item with this name already exists',
} as const;
```

Pass to the plugin object as `$ERROR_CODES: MY_PLUGIN_ERROR_CODES` for typed error inference.

## Rate Limiting

```ts
rateLimit: [
  {
    pathMatcher: (path) => path.startsWith('/my-plugin/'),
    limit: 100,
    window: 60, // seconds
  },
],
```

## Registration / Initialization

```ts
// Server
import { betterAuth } from 'better-auth';
import { myPlugin } from './my-plugin';
export const auth = betterAuth({ plugins: [myPlugin({ defaultPageSize: 50 })] });

// Client
import { createAuthClient } from 'better-auth/client';
import { myPluginClient } from './my-plugin/client';
const authClient = createAuthClient({ plugins: [myPluginClient()] });
```

After adding the plugin, run `npx @better-auth/cli generate` to create/update DB tables.

## Common Type Pitfalls

These are verified type constraints that **must** be followed to avoid compile errors.

### 1. NEVER add an explicit return type to the plugin factory

The plugin factory must **not** have `: BetterAuthPlugin` as a return type annotation. This erases all specific endpoint type information, making `$InferServerPlugin` on the client return a generic `{ endpoints?: { [key: string]: Endpoint } }` — so `authClient.myPlugin.listItems()` won't exist.

Use `satisfies BetterAuthPlugin` on the return **object** instead — this validates structure while preserving the concrete inferred type that the client needs.

```ts
// ✅ Correct — client can infer all endpoint types
export const myPlugin = (options?: MyPluginOptions) => {
  return {
    id: 'my-plugin',
    endpoints: { listItems: listItems(opts) },
  } satisfies BetterAuthPlugin;  // validates without widening
};

// ❌ WRONG — client sees generic BetterAuthPlugin, no endpoint types
export const myPlugin = (options?: MyPluginOptions): BetterAuthPlugin => {
  return {
    id: 'my-plugin',
    endpoints: { listItems: listItems(opts) },
  } satisfies BetterAuthPlugin;
};
```

### 2. `Where` type import path

`Where` is **not** exported from `better-auth/db`. Import it from the main entry or `better-auth/types`:

```ts
// ✅ Correct
import type { Where } from 'better-auth';
// ✅ Also correct
import type { Where } from 'better-auth/types';

// ❌ WRONG — will fail with "no exported member"
import type { Where } from 'better-auth/db';
```

The `Where` type definition (from `@better-auth/core/db/adapter`):
```ts
type WhereOperator = 'eq' | 'ne' | 'lt' | 'lte' | 'gt' | 'gte'
  | 'in' | 'not_in' | 'contains' | 'starts_with' | 'ends_with';

type Where = {
  operator?: WhereOperator | undefined;  // defaults to 'eq'
  value: string | number | boolean | string[] | number[] | Date | null;
  field: string;
  connector?: ('AND' | 'OR') | undefined;  // defaults to 'AND'
};
```

Always annotate where-clause arrays as `Where[]` to prevent TypeScript from widening operator string literals:
```ts
// ✅ Correct — operator stays narrowly typed
const where: Where[] = [
  { field: 'createdAt', operator: 'lt', value: cutoffDate },
];

// ❌ Risky — operator widens to `string`, fails assignability
const where = [
  { field: 'createdAt', operator: 'lt', value: cutoffDate },
];
```

`whereOperators` (the runtime array) **is** exported from `better-auth/db` — only the `Where` type is not:
```ts
import { whereOperators } from 'better-auth/db';  // ✅ runtime array
import type { Where } from 'better-auth';          // ✅ type
```

### 3. Hook matcher `path` is optional

`HookEndpointContext` defines `path?: string` (possibly `undefined`). Always guard:

```ts
// ✅ Correct
matcher: (context) => context.path?.startsWith('/my-plugin/') ?? false,

// ✅ Also correct
matcher: (context) => {
  if (!context.path) return false;
  return context.path === '/my-plugin/action';
},

// ❌ WRONG — Type error: string | undefined is not assignable to string
matcher: (context: { path: string }) => context.path === '/my-plugin/action',
```

### 4. Defaults object must not use `as const` with mutable array properties

When merging defaults into `ResolvedOptions`, `as const` makes arrays `readonly`, which is incompatible with `string[]`:

```ts
// ❌ WRONG — readonly ["admin"] is not assignable to string[]
const DEFAULTS = {
  roles: ['admin'],
  pageSize: 50,
} as const;

// ✅ Correct — explicit type annotation keeps arrays mutable
const DEFAULTS: Pick<ResolvedOptions, 'roles' | 'pageSize'> = {
  roles: ['admin'],
  pageSize: 50,
};
```

### 5. Adapter interface compatibility

When typing a function that receives `ctx.context` (the auth context), do **not** redefine the adapter interface with `operator: string`. Use the real `Where` type:

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
import type { Where } from 'better-auth';

interface MyContext {
  adapter: {
    findMany: <T>(opts: {
      model: string;
      where?: Where[];
    }) => Promise<T[]>;
  };
}
```
