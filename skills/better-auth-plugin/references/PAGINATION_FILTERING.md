# Pagination, Filtering, Searching & Sorting

Complete pattern for list endpoints, extracted from the better-auth admin plugin.

## Table of Contents

- [Pagination, Filtering, Searching \& Sorting](#pagination-filtering-searching--sorting)
  - [Table of Contents](#table-of-contents)
  - [Query Schema](#query-schema)
    - [Key Design Decisions](#key-design-decisions)
  - [Where Clause Builder](#where-clause-builder)
  - [Full List Endpoint Example](#full-list-endpoint-example)
    - [Response Shape](#response-shape)
  - [Reusable Query Schema Factory](#reusable-query-schema-factory)
  - [Client Usage](#client-usage)
    - [Cursor-Based Pagination Alternative](#cursor-based-pagination-alternative)

## Query Schema

The list endpoint uses a `GET` with query params. All pagination/filter params are optional — the endpoint works as a simple "get all" if none are provided.

```ts
import * as z from 'zod';
import { whereOperators } from 'better-auth/db';
// whereOperators = ['eq', 'ne', 'lt', 'lte', 'gt', 'gte', 'in', 'not_in', contains', 'starts_with', 'ends_with'] (approx)

const listItemsQuerySchema = z.object({
  // --- Search ---
  searchValue: z.string().optional().meta({
    description: 'The value to search for. Eg: "some name"',
  }),
  searchField: z
    .string()
    .optional()
    .meta({
      description: 'The field to search in. Defaults to "name".',
    }),
  searchOperator: z
    .enum(['contains', 'starts_with', 'ends_with'])
    .optional()
    .meta({
      description: 'Search operator. Defaults to "contains".',
    }),

  // --- Pagination ---
  limit: z
    .string()
    .or(z.number())
    .optional()
    .meta({ description: 'Number of items to return' }),
  offset: z
    .string()
    .or(z.number())
    .optional()
    .meta({ description: 'Offset to start from' }),

  // --- Sorting ---
  sortBy: z
    .string()
    .optional()
    .meta({ description: 'Field to sort by' }),
  sortDirection: z
    .enum(['asc', 'desc'])
    .optional()
    .meta({ description: 'Sort direction' }),

  // --- Filtering ---
  filterField: z
    .string()
    .optional()
    .meta({ description: 'Field to filter by' }),
  filterValue: z
    .string()
    .or(z.number())
    .or(z.boolean())
    .or(z.array(z.string()))
    .or(z.array(z.number()))
    .optional()
    .meta({ description: 'Value to filter by' }),
  filterOperator: z
    .enum(whereOperators)
    .optional()
    .meta({ description: 'Filter operator. Defaults to "eq".' }),
});
```

### Key Design Decisions

- `limit` and `offset` accept both `string` (from query params) and `number` — always coerce with `Number()` in the handler.
- `searchField` uses a constrained enum per-model to prevent arbitrary column access.
- `filterField` is a free string — the adapter validates it against the model.
- `filterOperator` uses the full `whereOperators` enum from better-auth's adapter.

## Where Clause Builder

Build the `Where[]` array from query params:

```ts
import type { Where } from 'better-auth';

function buildWhereClause(query: z.infer<typeof listItemsQuerySchema>): Where[] {
  const where: Where[] = [];

  // Search
  if (query.searchValue) {
    where.push({
      field: query.searchField || 'name',
      operator: query.searchOperator || 'contains',
      value: query.searchValue,
    });
  }

  // Filter
  if (query.filterValue !== undefined) {
    where.push({
      field: query.filterField || 'name',
      operator: query.filterOperator || 'eq',
      value: query.filterValue,
    });
  }

  return where;
}
```

For **multiple filters**, extend the schema to accept arrays:

```ts
// Alternative: support multiple filter conditions
const multiFilterSchema = z.object({
  filters: z.array(z.object({
    field: z.string(),
    operator: z.enum(whereOperators),
    value: z.union([z.string(), z.number(), z.boolean()]),
  })).optional(),
});
```

## Full List Endpoint Example

```ts
import { createAuthEndpoint, sessionMiddleware } from 'better-auth/api';
import type { Where } from 'better-auth';
import * as z from 'zod';

export const listItems = (opts: MyPluginOptions) =>
  createAuthEndpoint(
    '/my-plugin/list-items',
    {
      method: 'GET',
      use: [sessionMiddleware],
      query: listItemsQuerySchema,
      metadata: {
        openapi: {
          operationId: 'listItems',
          summary: 'List items with pagination, search, filter, and sort',
          responses: {
            200: {
              description: 'Paginated list of items',
              content: {
                'application/json': {
                  schema: {
                    type: 'object',
                    properties: {
                      items:  { type: 'array', items: { $ref: '#/components/schemas/MyPluginItem' } },
                      total:  { type: 'number' },
                      limit:  { type: 'number' },
                      offset: { type: 'number' },
                    },
                    required: ['items', 'total'],
                  },
                },
              },
            },
          },
        },
      },
    },
    async (ctx) => {
      const where: Where[] = [];

      // --- Build search condition ---
      if (ctx.query?.searchValue) {
        where.push({
          field: ctx.query.searchField || 'name',
          operator: ctx.query.searchOperator || 'contains',
          value: ctx.query.searchValue,
        });
      }

      // --- Build filter condition ---
      if (ctx.query?.filterValue !== undefined) {
        where.push({
          field: ctx.query.filterField || 'name',
          operator: ctx.query.filterOperator || 'eq',
          value: ctx.query.filterValue,
        });
      }

      // --- Scope to current user (optional) ---
      // Uncomment to restrict items to the logged-in user:
      // where.push({ field: 'userId', operator: 'eq', value: ctx.context.session.user.id });

      const limit = Number(ctx.query?.limit) || opts.defaultPageSize || 20;
      const offset = Number(ctx.query?.offset) || 0;
      const sortBy = ctx.query?.sortBy
        ? { field: ctx.query.sortBy, direction: ctx.query.sortDirection || 'asc' as const }
        : undefined;

      try {
        const items = await ctx.context.adapter.findMany({
          model: 'myPluginItems',
          where: where.length ? where : undefined,
          limit,
          offset,
          sortBy,
        });

        // Total count with same filters (for pagination UI)
        const total = await ctx.context.adapter.count({
          model: 'myPluginItems',
          where: where.length ? where : undefined,
        });

        return ctx.json({
          items,
          total,
          limit,
          offset,
        });
      } catch {
        return ctx.json({ items: [], total: 0, limit, offset });
      }
    },
  );
```

### Response Shape

```ts
{
  items: Item[];   // The page of results
  total: number;   // Total matching records (for computing page count)
  limit?: number;  // Echo back the limit used
  offset?: number; // Echo back the offset used
}
```

The admin plugin uses `internalAdapter.listUsers(limit, offset, sortBy, where)` and `internalAdapter.countTotalUsers(where)` — these are built-in internal adapter methods for the `user` model. For custom tables, use `ctx.context.adapter.findMany()` and `ctx.context.adapter.count()`.

## Reusable Query Schema Factory

To DRY up list endpoints across multiple models:

```ts
export function createListQuerySchema<T extends string>(searchableFields: readonly T[]) {
  return z.object({
    searchValue: z.string().optional(),
    searchField: z.enum(searchableFields as [T, ...T[]]).optional(),
    searchOperator: z.enum(['contains', 'starts_with', 'ends_with']).optional(),
    limit: z.string().or(z.number()).optional(),
    offset: z.string().or(z.number()).optional(),
    sortBy: z.string().optional(),
    sortDirection: z.enum(['asc', 'desc']).optional(),
    filterField: z.string().optional(),
    filterValue: z.string().or(z.number()).or(z.boolean()).or(z.array(z.string())).or(z.array(z.number())).optional(),
    filterOperator: z.enum(whereOperators).optional(),
  });
}

// Usage:
const listItemsQuery = createListQuerySchema(['name', 'description'] as const);
const listOrdersQuery = createListQuerySchema(['status', 'customerName'] as const);
```

## Client Usage

Once the server endpoint exists, the client calls it automatically via inferred types:

```ts
// GET endpoints — pass query params in query option
const { data, error } = await authClient.myPlugin.listItems({
  query: {
    searchValue: 'foo',
    searchField: 'name',
    searchOperator: 'contains',
    limit: '10',
    offset: '0',
    sortBy: 'createdAt',
    sortDirection: 'desc',
    filterField: 'isActive',
    filterValue: 'true',
    filterOperator: 'eq',
  },
});
// data.items, data.total, data.limit, data.offset

// POST endpoints — pass data in body
const { data: item } = await authClient.myPlugin.createItem({
  name: 'New Item',
});
```

### Cursor-Based Pagination Alternative

If you prefer cursor-based pagination over offset:

```ts
const cursorPaginationSchema = z.object({
  cursor: z.string().optional().meta({ description: 'Cursor for next page (item ID)' }),
  limit: z.string().or(z.number()).optional(),
});

// In handler:
const where: Where[] = [];
if (ctx.query?.cursor) {
  where.push({ field: 'id', operator: 'gt', value: ctx.query.cursor });
}
const items = await ctx.context.adapter.findMany({
  model: 'myPluginItems',
  where: where.length ? where : undefined,
  limit: Number(ctx.query?.limit) || 20,
  sortBy: { field: 'id', direction: 'asc' },
});
const nextCursor = items.length ? items[items.length - 1].id : null;
return ctx.json({ items, nextCursor });
```