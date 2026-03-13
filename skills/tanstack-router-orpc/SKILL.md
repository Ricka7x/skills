---
name: tanstack-router-orpc
description: Best practices for TanStack Router + TanStack Query + oRPC integration. Use when building routes with data fetching, implementing authentication guards, setting up oRPC clients, handling mutations, managing route context, optimistic updates, prefetching, or working with type-safe API calls in this project's setup.
---

# TanStack Router + TanStack Query + oRPC Integration

Production patterns for type-safe routing, data fetching, optimistic updates, and prefetching with oRPC in this Better-T-Stack project.

## Quick Reference

### oRPC Query (Preferred)
```tsx
import { useQuery } from "@tanstack/react-query"
import { orpc } from "@/utils/orpc"

// Query without input
const data = useQuery(orpc.payments.listInvoices.queryOptions())

// Query with input
const data = useQuery(
  orpc.planet.find.queryOptions({
    input: { id: 123 },
  })
)
```

### oRPC Mutation
```tsx
import { useMutation } from "@tanstack/react-query"
import { orpc } from "@/utils/orpc"

const mutation = useMutation(orpc.s3.saveFile.mutationOptions())
await mutation.mutateAsync({ url, name, type, size })
```

### Prefetching with oRPC
```tsx
import { queryClient, orpc } from "@/utils/orpc"

// Prefetch on hover (recommended for navigation)
function TodoList() {
  return (
    <div
      onMouseEnter={() => {
        queryClient.prefetchQuery(
          orpc.todos.detail.queryOptions({ input: { id: 123 } })
        )
      }}
    >
      View Details
    </div>
  )
}

// Prefetch in loader (TanStack Router)
export const Route = createFileRoute("/todos/$id")({  
  loader: ({ params }) => {
    queryClient.ensureQueryData(
      orpc.todos.detail.queryOptions({ input: { id: Number(params.id) } })
    )
  },
})
```

### Optimistic Updates

**Pattern 1: useMutationState** (Simple - for list appends)
```tsx
const addTodo = useMutation({
  mutationKey: ["addTodo"], // Required for useMutationState
  ...orpc.todos.create.mutationOptions(),
})

const pending = useMutationState({
  filters: { mutationKey: ["addTodo"], status: "pending" },
  select: (m) => m.state.variables
})
// Show pending items in UI with opacity
```

**Pattern 2: Cache Manipulation** (Complex - for edits/deletes)
```tsx
const update = useMutation({
  ...orpc.todos.update.mutationOptions(),
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: orpc.todos.key() })
    const previous = queryClient.getQueryData(orpc.todos.detail.queryKey({ input: { id } }))
    queryClient.setQueryData(orpc.todos.detail.queryKey({ input: { id } }), newData)
    return { previous }
  },
  onError: (err, vars, ctx) => {
    queryClient.setQueryData(orpc.todos.detail.queryKey({ input: { id } }), ctx.previous)
  }
})
```

See [QUERIES_MUTATIONS.md](references/QUERIES_MUTATIONS.md#optimistic-updates-with-orpc) for complete patterns and when to use each.

### Route with Auth Guard
```tsx
import { createFileRoute, redirect } from "@tanstack/react-router"
import { authClient } from "@/lib/auth-client"

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
  beforeLoad: async () => {
    const session = await authClient.getSession()
    if (!session.data) {
      redirect({ to: "/login", throw: true })
    }
    return { session }
  },
})
```

### Search Params Validation
```tsx
import { z } from "zod"

export const Route = createFileRoute("/login")({
  validateSearch: z.object({
    redirectTo: z.string().optional(),
    showSignIn: z.boolean().optional(),
  }),
})

// In component
const search = Route.useSearch()
```

## Core Patterns

### 1. oRPC Client Setup

**Location:** `apps/web/src/utils/orpc.ts`

- Single global `orpc` instance created with `createTanstackQueryUtils`
- `RPCLink` configured with credentials and custom fetch
- `QueryClient` with global error handling via `QueryCache`
- Export both `orpc` utils and `queryClient`

See [SETUP.md](references/SETUP.md) for complete configuration.

### 2. Router Context

**Location:** `apps/web/src/routes/__root.tsx`

- Define `RouterAppContext` interface with orpc and queryClient
- Create router with context in `main.tsx`
- Access via `Route.useRouteContext()` in any route component

### 3. Data Fetching

**Always use oRPC-generated options when available:**

```tsx
// ✅ Preferred - Type-safe, auto-generated keys
useQuery(orpc.namespace.method.queryOptions({ input: { id: 123 } }))
useMutation(orpc.namespace.method.mutationOptions())

// ❌ Avoid - Manual when oRPC is available
useQuery({ queryKey: [...], queryFn: ... })
```

**Key generation methods:**
```tsx
// Partial key for invalidation
queryClient.invalidateQueries({ queryKey: orpc.planet.key() })

// Full key for specific query
queryClient.setQueryData(
  orpc.planet.find.queryKey({ input: { id: 123 } }),
  newData
)
```

**Use manual queries only for:**
- External APIs (Better Auth client, Stripe, etc.)
- Custom cache strategies not supported by oRPC

See [QUERIES_MUTATIONS.md](references/QUERIES_MUTATIONS.md) for all patterns.

### 4. Authentication & Route Guards

**`beforeLoad` for auth checks:**

- Check session before route loads
- Redirect unauthenticated users with `redirect({ throw: true })`
- Pass session through route context for components
- Implement role-based guards (admin, user, etc.)

**Key pattern:**
```tsx
beforeLoad: async () => {
  const session = await authClient.getSession()
  if (!session.data) {
    redirect({ to: "/login", throw: true })
  }
  return { session } // Available in components
}
```

See [ROUTING.md](references/ROUTING.md) for complete patterns.

### 5. Error Handling Strategy

**Three-tier approach:**

1. **Global QueryCache** - Toast all query errors with retry action
2. **Mutation try-catch** - Handle specific mutation errors locally
3. **Component boundaries** - Loading/error states in UI

```tsx
// Global (already configured in orpc.ts)
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      toast.error(`Error: ${error.message}`, {
        action: { label: "retry", onClick: query.invalidate },
      })
    },
  }),
})

// Local mutation handling
try {
  await mutation.mutateAsync(input)
  toast.success("Success!")
} catch (error) {
  toast.error("Operation failed")
}
```

See [ERROR_HANDLING.md](references/ERROR_HANDLING.md) for patterns.

## Common Workflows

### Creating a New Route

1. Create file in `apps/web/src/routes/` (e.g., `dashboard/users.tsx`)
2. Export Route with `createFileRoute`
3. Add `beforeLoad` for auth if protected
4. Use `orpc.*.queryOptions()` for data fetching
5. Handle loading/error states

### Adding a New API Endpoint

1. Define procedure in `packages/api/src/routers/*.ts`
2. Add to `appRouter` in `packages/api/src/routers/index.ts`
3. Use `orpc.namespace.method.queryOptions()` in routes
4. Types automatically inferred from router

### Sequential Mutations

For multi-step operations (e.g., S3 upload flow):

```tsx
const step1 = useMutation(orpc.s3.getPresignedUrl.mutationOptions())
const step2 = useMutation(orpc.s3.saveFile.mutationOptions())

const handleUpload = async () => {
  try {
    const { url } = await step1.mutateAsync({ key, contentType })
    await fetch(url, { method: "PUT", body: file })
    await step2.mutateAsync({ url: cleanUrl, name, type, size })
    toast.success("Done!")
  } catch (error) {
    toast.error("Failed")
  }
}
```

See [EXAMPLES.md](references/EXAMPLES.md) for real-world patterns from this codebase.

## Anti-Patterns

**Don't:**

- ❌ Create multiple oRPC clients (use singleton from `utils/orpc.ts`)
- ❌ Omit `credentials: "include"` in fetch (breaks session auth)
- ❌ Skip query invalidation after mutations
- ❌ Use `navigate()` in `beforeLoad` (use `redirect({ throw: true })`)
- ❌ Mix oRPC queryOptions with manual queryFn (redundant)
- ❌ Forget to handle loading/error states in UI
- ❌ Define queries in beforeLoad (use loader or component queries)
- ❌ Use cache manipulation for simple list appends (use useMutationState)
- ❌ Prefetch data that changes frequently (use regular queries)
- ❌ Prefetch without considering staleTime (may refetch immediately)

**Do:**

- ✅ Use oRPC-generated options for all API routes
- ✅ Add `beforeLoad` auth guards for protected routes
- ✅ Validate search params with Zod `validateSearch`
- ✅ Invalidate queries after successful mutations
- ✅ Show loading states and error boundaries
- ✅ Keep route context minimal (session, orpc, queryClient)
- ✅ Use useMutationState for simple optimistic updates
- ✅ Use cache manipulation only for complex updates (edits/deletes)
- ✅ Prefetch on user intent (hover, route transition)
- ✅ Set appropriate staleTime when prefetching

## File Structure

```
apps/web/src/
├── utils/
│   └── orpc.ts              # oRPC client, queryClient, exports
├── routes/
│   ├── __root.tsx           # Context definition
│   ├── index.tsx            # Public routes
│   ├── login.tsx            # Auth routes with validateSearch
│   └── dashboard/
│       ├── route.tsx        # Layout with beforeLoad guard
│       ├── index.tsx        # Protected route
│       └── billing.tsx      # Data fetching example
└── main.tsx                 # Router creation with context
```

## Type Safety

This setup provides full type safety:

- **Router types** - Auto-inferred from `appRouter` in API package
- **Input/Output** - Validated with Zod schemas in procedures
- **Search params** - Validated with `validateSearch` option
- **Context** - Typed via `RouterAppContext` interface
- **Query/Mutation** - Full autocomplete from oRPC utils

## Resources

- [Complete Setup Guide](references/SETUP.md)
- [Queries & Mutations Reference](references/QUERIES_MUTATIONS.md)
- [Routing & Guards](references/ROUTING.md)
- [Error Handling](references/ERROR_HANDLING.md)
- [Real Examples](references/EXAMPLES.md)
- [TanStack Router Docs](https://tanstack.com/router)
- [TanStack Query Docs](https://tanstack.com/query)
- [oRPC Docs](https://orpc.unnoq.com)
