# Error Handling Reference

Complete error handling patterns for TanStack Query + oRPC + TanStack Router.

## Three-Tier Error Strategy

### 1. Global Query Errors (QueryCache)

Handles all query failures automatically with toast notifications.

**Setup in `apps/web/src/utils/orpc.ts`:**

```typescript
import { QueryCache, QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

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

**When it triggers:**
- Any `useQuery` fails
- Automatic toast with error message
- Retry button invalidates and refetches

**Disable for specific query:**

```tsx
const data = useQuery({
  ...orpc.posts.list.queryOptions(),
  meta: { errorHandler: "none" }, // Skip global handler
})
```

### 2. Local Mutation Errors (try-catch)

Handle mutation errors with specific messages and actions.

```tsx
const mutation = useMutation(orpc.user.update.mutationOptions())

const handleSubmit = async (data: FormData) => {
  try {
    await mutation.mutateAsync(data)
    toast.success("Profile updated successfully!")
    navigate({ to: "/dashboard" })
  } catch (error) {
    if (error.code === "CONFLICT") {
      toast.error("Email already in use")
    } else if (error.code === "VALIDATION_ERROR") {
      toast.error("Please check your inputs")
    } else {
      toast.error("Failed to update profile")
    }
  }
}
```

### 3. Component-Level Errors (UI States)

Display error states in the component tree.

```tsx
function PostList() {
  const posts = useQuery(orpc.posts.list.queryOptions())

  if (posts.isLoading) {
    return <Skeleton />
  }

  if (posts.error) {
    return (
      <div className="text-center">
        <p className="text-red-600">Failed to load posts</p>
        <p className="text-sm text-gray-500">{posts.error.message}</p>
        <button onClick={() => posts.refetch()}>Retry</button>
      </div>
    )
  }

  return <div>{posts.data.map((post) => ...)}</div>
}
```

## oRPC Error Types

### Type-Safe Error Handling

Use `isDefinedError` from `@orpc/client` for type-safe error handling:

```tsx
import { isDefinedError } from "@orpc/client"
import { useMutation } from "@tanstack/react-query"
import { orpc } from "@/utils/orpc"

const mutation = useMutation(
  orpc.planet.create.mutationOptions({
    onError: (error) => {
      if (isDefinedError(error)) {
        // Handle type-safe error with proper typing
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

### Standard Error Codes

oRPC uses standardized error codes:

```typescript
// In procedures (packages/api/src/...)
import { ORPCError } from "@orpc/server"

// Throw errors
throw new ORPCError("UNAUTHORIZED") // 401
throw new ORPCError("FORBIDDEN") // 403
throw new ORPCError("NOT_FOUND") // 404
throw new ORPCError("CONFLICT") // 409
throw new ORPCError("INTERNAL_SERVER_ERROR") // 500
```

### Handling Specific Codes

```tsx
import { isDefinedError } from "@orpc/client"

try {
  await mutation.mutateAsync(input)
} catch (error) {
  if (isDefinedError(error)) {
    switch (error.code) {
      case "UNAUTHORIZED":
        toast.error("Please sign in")
        navigate({ to: "/login" })
        break
      case "FORBIDDEN":
        toast.error("You don't have permission")
        break
      case "NOT_FOUND":
        toast.error("Resource not found")
        break
      case "CONFLICT":
        toast.error("Item already exists")
        break
      default:
        toast.error("Something went wrong")
    }
  }
}
```

### Error with Custom Data

```typescript
// Backend
throw new ORPCError("VALIDATION_ERROR", {
  message: "Invalid input",
  data: {
    field: "email",
    reason: "Email already registered",
  },
})
```

```tsx
// Frontend
import { isDefinedError } from "@orpc/client"

try {
  await mutation.mutateAsync(input)
} catch (error) {
  if (isDefinedError(error) && error.code === "VALIDATION_ERROR") {
    const field = error.data?.field
    const reason = error.data?.reason
    toast.error(`${field}: ${reason}`)
  }
}
```

## Query Error Handling

### Silent Errors (No Toast)

```tsx
const data = useQuery({
  ...orpc.posts.list.queryOptions(),
  retry: false, // Don't retry
  onError: (error) => {
    // Custom handling, prevents global toast
    console.error("Silent error:", error)
  },
})
```

### Retry Configuration

```tsx
const data = useQuery({
  ...orpc.posts.list.queryOptions(),
  retry: 3, // Retry 3 times
  retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
})
```

### Error Boundaries

```tsx
import { QueryErrorResetBoundary } from "@tanstack/react-query"
import { ErrorBoundary } from "react-error-boundary"

function App() {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ error, resetErrorBoundary }) => (
            <div className="p-4">
              <h2 className="font-bold text-xl">Something went wrong</h2>
              <pre className="mt-2 text-sm">{error.message}</pre>
              <button
                onClick={resetErrorBoundary}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
              >
                Try again
              </button>
            </div>
          )}
        >
          <MyComponent />
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  )
}
```

## Mutation Error Handling

### onError Callback

```tsx
import { isDefinedError } from "@orpc/client"

const mutation = useMutation({
  ...orpc.user.update.mutationOptions(),
  onError: (error, variables, context) => {
    console.error("Mutation failed:", error)
    
    if (isDefinedError(error)) {
      toast.error(`Failed to update: ${error.message}`)
      
      // Rollback optimistic update if needed
      if (context?.previousData) {
        queryClient.setQueryData(["user"], context.previousData)
      }
    }
  },
  onSuccess: () => {
    toast.success("Updated successfully!")
    queryClient.invalidateQueries({ queryKey: orpc.user.key() })
  },
})
```

### Form Error Handling

```tsx
import { useForm } from "@tanstack/react-form"

function ProfileForm() {
  const mutation = useMutation(orpc.user.update.mutationOptions())
  
  const form = useForm({
    defaultValues: { name: "", email: "" },
    onSubmit: async ({ value }) => {
      try {
        await mutation.mutateAsync(value)
        toast.success("Profile updated!")
      } catch (error) {
        // Set form-level error
        form.setFieldMeta("email", (meta) => ({
          ...meta,
          errors: [error.message],
        }))
      }
    },
  })

  return (
    <form onSubmit={form.handleSubmit}>
      {/* form fields */}
    </form>
  )
}
```

## Router Error Handling

### Route-Level Error Component

```tsx
export const Route = createFileRoute("/posts/$postId")({
  component: PostPage,
  errorComponent: ({ error, reset }) => (
    <div className="p-8 text-center">
      <h1 className="font-bold text-2xl">Failed to load post</h1>
      <p className="text-gray-600 mt-2">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
      >
        Try Again
      </button>
    </div>
  ),
})
```

### Not Found Handling

```tsx
export const Route = createFileRoute("/posts/$postId")({
  component: PostPage,
  beforeLoad: async ({ params }) => {
    const post = await fetchPost(params.postId)
    
    if (!post) {
      redirect({ to: "/404", throw: true })
    }
    
    return { post }
  },
})
```

## Network Error Handling

### Offline Detection

```tsx
import { useOnlineStatus } from "@tanstack/react-query"

function App() {
  const isOnline = useOnlineStatus()

  if (!isOnline) {
    return (
      <div className="fixed top-0 left-0 right-0 bg-yellow-500 text-center py-2">
        You're offline. Some features may not work.
      </div>
    )
  }

  return <YourApp />
}
```

### Network Retry

```tsx
const data = useQuery({
  ...orpc.posts.list.queryOptions(),
  networkMode: "offlineFirst", // Use cache when offline
  retry: (failureCount, error) => {
    // Don't retry on client errors
    if (error.status >= 400 && error.status < 500) {
      return false
    }
    // Retry server errors up to 3 times
    return failureCount < 3
  },
})
```

## Loading & Error States Pattern

### Complete Pattern

```tsx
function DataComponent() {
  const data = useQuery(orpc.posts.list.queryOptions())

  // Loading state
  if (data.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    )
  }

  // Error state
  if (data.error) {
    return (
      <div className="rounded border border-red-300 bg-red-50 p-4">
        <h3 className="font-semibold text-red-800">Error</h3>
        <p className="text-red-600 text-sm">{data.error.message}</p>
        <button
          onClick={() => data.refetch()}
          className="mt-2 text-red-700 text-sm underline"
        >
          Try again
        </button>
      </div>
    )
  }

  // Empty state
  if (data.data.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        <p>No posts found</p>
      </div>
    )
  }

  // Success state
  return (
    <div>
      {data.data.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  )
}
```

## Error Logging

### Log to Service

```typescript
// utils/error-logger.ts
export function logError(error: Error, context?: Record<string, any>) {
  // Send to Sentry, LogRocket, etc.
  console.error("Error:", error, context)
  
  if (import.meta.env.PROD) {
    // Send to error tracking service
  }
}

// In query cache
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      logError(error, {
        queryKey: query.queryKey,
        queryHash: query.queryHash,
      })
      
      toast.error(`Error: ${error.message}`, {
        action: { label: "retry", onClick: query.invalidate },
      })
    },
  }),
})
```

## Best Practices

**Do:**
- ✅ Use `isDefinedError` for type-safe error handling
- ✅ Use global QueryCache for standard query errors
- ✅ Handle mutations with try-catch for specific messages
- ✅ Show loading and error states in UI
- ✅ Provide retry actions in error toasts
- ✅ Log errors to monitoring service in production
- ✅ Use error boundaries for catastrophic failures
- ✅ Handle specific error codes (UNAUTHORIZED, CONFLICT, etc.)

**Don't:**
- ❌ Ignore error states in components
- ❌ Show generic "Error" messages without context
- ❌ Retry infinitely (set retry limits)
- ❌ Swallow errors silently
- ❌ Forget to reset form state on error
- ❌ Use alert() for errors (use toast notifications)
- ❌ Access error properties without `isDefinedError` check
