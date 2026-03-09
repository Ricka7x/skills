# Queries & Mutations Reference

Complete patterns for data fetching with oRPC and TanStack Query.

## Query Patterns

### Basic oRPC Query

```tsx
import { useQuery } from "@tanstack/react-query"
import { orpc } from "@/utils/orpc"

function DashboardPage() {
  // Query without input
  const privateData = useQuery(orpc.privateData.queryOptions())

  if (privateData.isLoading) return <div>Loading...</div>
  if (privateData.error) return <div>Error: {privateData.error.message}</div>

  return <div>{privateData.data.message}</div>
}
```

**Benefits:**
- Type-safe input/output
- Auto-generated query keys
- Built-in error handling via global QueryCache

### Query with Input Parameters

```tsx
const invoices = useQuery(
  orpc.payments.listInvoices.queryOptions({
    input: {
      status: "paid",
      limit: 10,
    },
  })
)
```

**Important:** Input must be wrapped in an `input` object.

Input is validated against the Zod schema defined in the procedure.

### Query with Custom Options

```tsx
const data = useQuery(
  orpc.payments.listInvoices.queryOptions({
    input: { status: "paid" },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 60 * 1000, // 1 minute
    enabled: isAuthenticated, // Conditional fetching
  })
)
```

### Conditional Queries with skipToken

Use `skipToken` for type-safe conditional queries:

```tsx
import { skipToken } from "@tanstack/react-query"

const data = useQuery(
  orpc.planet.find.queryOptions({
    input: planetId ? { id: planetId } : skipToken,
  })
)

// Equivalent to:
const data = useQuery({
  ...orpc.planet.find.queryOptions({ input: { id: planetId! } }),
  enabled: !!planetId,
})
```

### Manual Query (External APIs)

Use when oRPC is not available (e.g., Better Auth client):

```tsx
import { authClient } from "@/lib/auth-client"

const subscriptions = useQuery({
  queryKey: ["subscriptions"],
  queryFn: async () => {
    const result = await authClient.subscription.list()
    return result?.data ?? []
  },
})
```

## Mutation Patterns

**Important:** Unlike queries, mutation input is passed directly to `mutateAsync()` or `mutate()`:
- ✅ `mutateAsync({ name: "Rick" })` - Direct input
- ❌ `mutateAsync({ input: { name: "Rick" } })` - Don't wrap in `input`

The `{ input: {} }` wrapper is only used when setting up `queryOptions()`, not when calling mutations.

### Basic oRPC Mutation

```tsx
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { orpc, queryClient } from "@/utils/orpc"

function SaveButton() {
  const saveFile = useMutation(orpc.s3.saveFile.mutationOptions())

  const handleSave = async () => {
    try {
      const result = await saveFile.mutateAsync({
        url: "https://...",
        name: "file.pdf",
        type: "application/pdf",
        size: 1024,
      })
      toast.success("File saved!")
      queryClient.invalidateQueries({ queryKey: ["files"] })
    } catch (error) {
      toast.error("Failed to save file")
    }
  }

  return (
    <button onClick={handleSave} disabled={saveFile.isPending}>
      {saveFile.isPending ? "Saving..." : "Save"}
    </button>
  )
}
```

**Pattern:**
1. Call `mutateAsync()` with input
2. Handle success (toast, invalidate queries)
3. Handle error (toast)
4. Show loading state with `isPending`

### Mutation with onSuccess Callback

```tsx
const addTodo = useMutation({
  ...orpc.todos.create.mutationOptions(),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["todos"] })
    toast.success("Todo added!")
  },
  onError: (error) => {
    toast.error(`Failed: ${error.message}`)
  },
})

// Usage
addTodo.mutate({ title: "New todo" })
```

### Sequential Mutations

For multi-step workflows:

```tsx
function FileUpload() {
  const getPresignedUrl = useMutation(
    orpc.s3.getPresignedUrl.mutationOptions()
  )
  const saveFile = useMutation(orpc.s3.saveFile.mutationOptions())
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (file: File) => {
    setUploading(true)
    try {
      // Step 1: Get presigned URL
      const { url } = await getPresignedUrl.mutateAsync({
        key: `uploads/${Date.now()}-${file.name}`,
        contentType: file.type,
      })

      // Step 2: Upload to S3
      const response = await fetch(url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      })

      if (!response.ok) {
        throw new Error("S3 upload failed")
      }

      // Step 3: Save metadata to DB
      const cleanUrl = url.split("?")[0]
      await saveFile.mutateAsync({
        url: cleanUrl,
        name: file.name,
        type: file.type,
        size: file.size,
      })

      toast.success("File uploaded and saved!")
    } catch (error) {
      console.error(error)
      toast.error("Upload failed")
    } finally {
      setUploading(false)
    }
  }

  return (
    <input
      type="file"
      onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
      disabled={uploading}
    />
  )
}
```

### Parallel Mutations

When mutations are independent:

```tsx
const updateProfile = useMutation(orpc.user.updateProfile.mutationOptions())
const uploadAvatar = useMutation(orpc.user.uploadAvatar.mutationOptions())

const handleSave = async () => {
  try {
    await Promise.all([
      updateProfile.mutateAsync({ name, bio }),
      uploadAvatar.mutateAsync({ file: avatarFile }),
    ])
    toast.success("Profile updated!")
  } catch (error) {
    toast.error("Update failed")
  }
}
```

## Query Invalidation

### Using oRPC Key Methods

oRPC provides helper methods for generating query keys:

```tsx
// Invalidate all planet queries (partial key)
queryClient.invalidateQueries({
  queryKey: orpc.planet.key(),
})

// Invalidate only regular (non-infinite) planet queries
queryClient.invalidateQueries({
  queryKey: orpc.planet.key({ type: "query" }),
})

// Invalidate specific query with input
queryClient.invalidateQueries({
  queryKey: orpc.planet.find.key({ input: { id: 123 } }),
})

// Update specific query data
queryClient.setQueryData(
  orpc.planet.find.queryKey({ input: { id: 123 } }),
  (old) => ({ ...old, name: "Earth" })
)
```

**Key methods:**
- `.key()` - Partial key for broad invalidation
- `.queryKey()` - Full key for specific query
- `.infiniteKey()` - Full key for infinite query
- `.mutationKey()` - Full key for mutation

### Invalidate on Mutation Success

```tsx
const addTodo = useMutation({
  ...orpc.todos.create.mutationOptions(),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: orpc.todos.key() })
  },
})
```

### Invalidate Multiple Queries

```tsx
await Promise.all([
  queryClient.invalidateQueries({ queryKey: ["todos"] }),
  queryClient.invalidateQueries({ queryKey: ["stats"] }),
])
```

### Refetch Active Queries

```tsx
// Refetch all active queries
queryClient.refetchQueries({ type: "active" })

// Refetch specific query immediately
queryClient.refetchQueries({ queryKey: ["todos"], exact: true })
```

## Optimistic Updates with oRPC

Two patterns available - choose based on complexity needs.

### Pattern 1: useMutationState (Recommended for Simple Cases)

Show pending mutations without cache manipulation. Best for **list appends** and **simple updates**.

```tsx
import { useMutation, useMutationState, useQuery } from "@tanstack/react-query"
import { orpc } from "@/utils/orpc"

function TodoList() {
  const { data: todos } = useQuery(orpc.todos.list.queryOptions())

  const addTodo = useMutation({
    mutationKey: ["addTodo"], // Required for tracking
    ...orpc.todos.create.mutationOptions(),
    onSuccess: () => {
      // Invalidate using oRPC key helper
      queryClient.invalidateQueries({ queryKey: orpc.todos.list.queryKey() })
    },
  })

  // Get pending todos
  const pendingTodos = useMutationState({
    filters: { mutationKey: ["addTodo"], status: "pending" },
    select: (mutation) => mutation.state.variables,
  })

  return (
    <ul>
      {/* Committed todos */}
      {todos?.map((todo) => (
        <li key={todo.id}>{todo.title}</li>
      ))}

      {/* Optimistic todos */}
      {pendingTodos.map((todo, i) => (
        <li key={`pending-${i}`} style={{ opacity: 0.5 }}>
          {todo.title} (saving...)
        </li>
      ))}
    </ul>
  )
}
```

**Pros:**
- No cache manipulation
- No rollback logic needed
- Type-safe with mutation variables
- Simple to implement

**Cons:**
- Can't handle complex updates (edits, deletes)
- Separate rendering for pending items

### Pattern 2: Cache Manipulation (For Complex Updates)

Directly update cache for **instant feedback** on edits/deletes. Requires rollback on error.

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { isDefinedError } from "@orpc/client"
import { orpc } from "@/utils/orpc"

function TodoItem({ id }: { id: number }) {
  const queryClient = useQueryClient()
  const { data: todo } = useQuery(
    orpc.todos.detail.queryOptions({ input: { id } })
  )

  const updateTodo = useMutation({
    ...orpc.todos.update.mutationOptions(),
    // Step 1: Save snapshot and update cache immediately
    onMutate: async (newData) => {
      // Cancel in-flight queries
      await queryClient.cancelQueries({
        queryKey: orpc.todos.detail.key({ input: { id } })
      })

      // Snapshot current value
      const previousTodo = queryClient.getQueryData(
        orpc.todos.detail.queryKey({ input: { id } })
      )

      // Optimistically update cache
      queryClient.setQueryData(
        orpc.todos.detail.queryKey({ input: { id } }),
        (old) => ({ ...old, ...newData })
      )

      // Return rollback context
      return { previousTodo }
    },
    // Step 2: Rollback on error
    onError: (error, variables, context) => {
      if (context?.previousTodo) {
        queryClient.setQueryData(
          orpc.todos.detail.queryKey({ input: { id } }),
          context.previousTodo
        )
      }
      
      if (isDefinedError(error)) {
        toast.error(`Failed: ${error.message}`)
      }
    },
    // Step 3: Invalidate on success
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: orpc.todos.key() // Invalidate all todos
      })
    },
  })

  return (
    <div>
      <h3>{todo?.title}</h3>
      <button onClick={() => updateTodo.mutate({ title: "Updated!" })}>
        Update
      </button>
    </div>
  )
}
```

**Pros:**
- Instant UI updates
- Works for edits, deletes, complex updates
- Seamless UX

**Cons:**
- More complex implementation
- Requires rollback logic
- Must manage cache keys carefully

### When to Use Which Pattern

| Use Case | Pattern | Reason |
|----------|---------|--------|
| Adding items to list | useMutationState | Simple, no cache manipulation |
| Updating existing item | Cache Manipulation | Instant feedback, no duplicate rendering |
| Deleting item | Cache Manipulation | Can remove from cache immediately |
| Toggle/checkbox | Cache Manipulation | Immediate visual feedback |
| Multi-step forms | useMutationState | Don't need instant updates |
| Background sync | useMutationState | User doesn't need to see pending state |

## Conditional Queries

### Using skipToken (Recommended)

```tsx
import { skipToken } from "@tanstack/react-query"

const { data } = useQuery(
  orpc.user.profile.queryOptions({
    input: userId ? { userId } : skipToken,
  })
)
```

### Using enabled Option

```tsx
const { data } = useQuery(
  orpc.user.profile.queryOptions({
    input: { userId },
    enabled: !!userId, // Only run if userId exists
  })
)
```

### Enable Based on Auth

```tsx
import { skipToken } from "@tanstack/react-query"

function PrivateData() {
  const { session } = Route.useRouteContext()
  const isAuthenticated = !!session?.data?.user

  const data = useQuery(
    orpc.privateData.queryOptions({
      input: isAuthenticated ? {} : skipToken,
    })
  )

  if (!isAuthenticated) return <div>Please sign in</div>
  if (data.isLoading) return <div>Loading...</div>

  return <div>{data.data.message}</div>
}
```

## Prefetching with oRPC

### Prefetch on Intent (Hover/Focus)

Use `prefetchQuery` for better perceived performance:

```tsx
import { queryClient, orpc } from "@/utils/orpc"

function TodoItem({ id }: { id: number }) {
  const handleMouseEnter = () => {
    // Prefetch detail when user hovers
    queryClient.prefetchQuery(
      orpc.todos.detail.queryOptions({ input: { id } })
    )
  }

  return (
    <Link to="/todos/$id" params={{ id }} onMouseEnter={handleMouseEnter}>
      Todo #{id}
    </Link>
  )
}
```

### Prefetch in Route Loaders

**TanStack Router pattern:**

```tsx
import { createFileRoute } from "@tanstack/react-router"
import { queryClient, orpc } from "@/utils/orpc"

export const Route = createFileRoute("/todos/$id")({  
  // Prefetch before component renders
  loader: ({ params }) => {
    return queryClient.ensureQueryData(
      orpc.todos.detail.queryOptions({ input: { id: Number(params.id) } })
    )
  },
  component: TodoDetail,
})

function TodoDetail() {
  const { id } = Route.useParams()
  // Data is already loaded by loader
  const { data } = useQuery(
    orpc.todos.detail.queryOptions({ input: { id: Number(id) } })
  )
  return <div>{data.title}</div>
}
```

**Why ensureQueryData over prefetchQuery:**
- `ensureQueryData` - Fetches if missing, returns existing data if present
- `prefetchQuery` - Always fetches, ignores existing cache

### Prefetch Related Data

```tsx
const { data: user } = useQuery(
  orpc.user.profile.queryOptions({ input: { id } })
)

// Prefetch related data when user loads
useEffect(() => {
  if (user?.organizationId) {
    queryClient.prefetchQuery(
      orpc.organization.detail.queryOptions({
        input: { id: user.organizationId }
      })
    )
  }
}, [user?.organizationId])
```

### Configure Stale Time When Prefetching

```tsx
// Prefetch with longer stale time to avoid immediate refetch
queryClient.prefetchQuery({
  ...orpc.todos.list.queryOptions(),
  staleTime: 5 * 60 * 1000, // 5 minutes
})
```

**Note:** With oRPC's `queryOptions`, you can override any TanStack Query option while keeping type-safe input.

## Loading States

### Component-Level Loading

```tsx
const data = useQuery(orpc.posts.list.queryOptions())

if (data.isLoading) {
  return <Skeleton />
}

if (data.error) {
  return <ErrorMessage error={data.error} />
}

return <PostList posts={data.data} />
```

### Inline Loading State

```tsx
<div>
  {data.isLoading ? (
    <Spinner />
  ) : (
    <PostList posts={data.data} />
  )}
</div>
```

### Global Loading Indicator

```tsx
import { useIsFetching } from "@tanstack/react-query"

function GlobalLoader() {
  const isFetching = useIsFetching()
  return isFetching > 0 ? <LoadingBar /> : null
}
```

## Error Handling

### Type-Safe Error Handling

Use `isDefinedError` for type-safe error handling:

```tsx
import { isDefinedError } from "@orpc/client"
import { useMutation } from "@tanstack/react-query"
import { orpc } from "@/utils/orpc"

const mutation = useMutation(
  orpc.planet.create.mutationOptions({
    onError: (error) => {
      if (isDefinedError(error)) {
        // Type-safe error with proper typing
        console.error(error.code, error.message, error.data)
      }
    },
  })
)

mutation.mutate({ name: "Earth" })

if (mutation.error && isDefinedError(mutation.error)) {
  // Handle the error with full type safety
}
```

### Global Error Handling

Already configured in `orpc.ts`:

```typescript
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      toast.error(`Error: ${error.message}`, {
        action: {
          label: "retry",
          onClick: query.invalidate,
        },
      })
    },
  }),
})
```

### Local Error Handling

```tsx
import { isDefinedError } from "@orpc/client"

const mutation = useMutation(orpc.action.mutationOptions())

const handleSubmit = async () => {
  try {
    await mutation.mutateAsync(input)
    toast.success("Success!")
  } catch (error) {
    if (isDefinedError(error)) {
      if (error.code === "CONFLICT") {
        toast.error("Item already exists")
      } else if (error.code === "UNAUTHORIZED") {
        toast.error("Please sign in")
      } else {
        toast.error("Something went wrong")
      }
    }
  }
}
```

### Error Boundaries

```tsx
import { QueryErrorResetBoundary } from "@tanstack/react-query"
import { ErrorBoundary } from "react-error-boundary"

<QueryErrorResetBoundary>
  {({ reset }) => (
    <ErrorBoundary
      onReset={reset}
      fallbackRender={({ resetErrorBoundary }) => (
        <div>
          <p>Error occurred</p>
          <button onClick={resetErrorBoundary}>Retry</button>
        </div>
      )}
    >
      <MyComponent />
    </ErrorBoundary>
  )}
</QueryErrorResetBoundary>
```

## Infinite Queries

For pagination with infinite scroll:

```tsx
import { useInfiniteQuery } from "@tanstack/react-query"

const query = useInfiniteQuery(
  orpc.planet.list.infiniteOptions({
    input: (pageParam: number | undefined) => ({
      limit: 10,
      offset: pageParam,
    }),
    initialPageParam: undefined,
    getNextPageParam: (lastPage) => lastPage.nextPageParam,
  })
)

// Access pages
query.data?.pages.flatMap((page) => page.items)

// Load more
<button
  onClick={() => query.fetchNextPage()}
  disabled={!query.hasNextPage || query.isFetchingNextPage}
>
  {query.isFetchingNextPage ? "Loading..." : "Load More"}
</button>
```

**Important:** The `input` parameter must be a function that accepts the page parameter.

## Query Keys

oRPC provides helper methods for generating query keys:

```tsx
// Partial key for broad invalidation
orpc.todos.key() // Matches all todos queries

// Specific query type
orpc.todos.key({ type: "query" }) // Only regular queries
orpc.todos.key({ type: "infinite" }) // Only infinite queries

// Full key for specific query
orpc.todos.list.queryKey({ input: { status: "active" } })

// Infinite query key
orpc.todos.list.infiniteKey({ input: (page) => ({ offset: page }) })

// Mutation key
orpc.todos.create.mutationKey()

// Manual invalidation
queryClient.invalidateQueries({
  queryKey: orpc.todos.key(),
})
```

## Advanced Features

### Client Context

Pass context to configure request behavior:

```tsx
const query = useQuery(
  orpc.planet.find.queryOptions({
    input: { id: 123 },
    context: { cache: true }, // Custom context
  })
)
```

**Warning:** oRPC excludes client context from query keys. Override query keys manually if needed to prevent unwanted query deduplication.

### Default Options

Configure default options for all queries/mutations:

```typescript
import { createTanstackQueryUtils } from "@orpc/tanstack-query"

const orpc = createTanstackQueryUtils(client, {
  experimental_defaults: {
    planet: {
      find: {
        queryOptions: {
          staleTime: 60 * 1000, // 1 minute
          retry: 3,
        },
      },
      create: {
        mutationOptions: {
          onSuccess: (output, input, _, ctx) => {
            ctx.client.invalidateQueries({ queryKey: orpc.planet.key() })
          },
        },
      },
    },
  },
})
```

### Direct Client Calls

Call procedure client directly with `.call()`:

```tsx
const planet = await orpc.planet.find.call({ id: 123 })
```

## Best Practices

**Do:**
- ✅ Wrap input in `input` object: `{ input: { id: 123 } }`
- ✅ Use `skipToken` for conditional queries
- ✅ Use `isDefinedError` for type-safe error handling
- ✅ Use key methods (`.key()`, `.queryKey()`) for invalidation
- ✅ Use `mutateAsync` for error handling control
- ✅ Invalidate queries after mutations
- ✅ Show loading states with `isPending` / `isLoading`

**Don't:**
- ❌ Forget to wrap input: `queryOptions(data)` → `queryOptions({ input: data })`
- ❌ Mix oRPC options with manual queryFn (redundant)
- ❌ Use manual query keys when oRPC provides them
- ❌ Forget to invalidate after mutations
- ❌ Ignore loading/error states
- ❌ Use `mutate` when you need error handling (use `mutateAsync`)
