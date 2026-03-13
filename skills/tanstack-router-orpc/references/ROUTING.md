# Routing & Guards Reference

Complete patterns for TanStack Router with authentication and navigation.

## Route Definition

### Basic Route

```tsx
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/about")({
  component: AboutPage,
})

function AboutPage() {
  return <div>About</div>
}
```

### Route with Search Params

```tsx
import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

export const Route = createFileRoute("/search")({
  component: SearchPage,
  validateSearch: z.object({
    q: z.string().optional(),
    page: z.number().int().positive().optional().default(1),
    sort: z.enum(["asc", "desc"]).optional(),
  }),
})

function SearchPage() {
  const { q, page, sort } = Route.useSearch()
  
  return (
    <div>
      <p>Query: {q}</p>
      <p>Page: {page}</p>
      <p>Sort: {sort}</p>
    </div>
  )
}
```

**Access search params:**
```tsx
const search = Route.useSearch()
// URL: /search?q=hello&page=2&sort=desc
// search = { q: "hello", page: 2, sort: "desc" }
```

### Route with Path Params

```tsx
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/posts/$postId")({
  component: PostPage,
})

function PostPage() {
  const { postId } = Route.useParams()
  
  return <div>Post ID: {postId}</div>
}
```

## Authentication Guards

### Basic Auth Guard

```tsx
import { createFileRoute, redirect } from "@tanstack/react-router"
import { authClient } from "@/lib/auth-client"

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
  beforeLoad: async () => {
    const session = await authClient.getSession()
    
    if (!session.data) {
      redirect({
        to: "/login",
        throw: true, // Critical: stops execution
      })
    }
    
    return { session } // Pass to route context
  },
})

function DashboardPage() {
  const { session } = Route.useRouteContext()
  const user = session.data?.user
  
  return <div>Welcome, {user?.email}!</div>
}
```

**Key points:**
- Use `redirect({ throw: true })` to halt execution
- Return session data for use in components
- Access via `Route.useRouteContext()`

### Role-Based Guard

```tsx
export const Route = createFileRoute("/dashboard/admin")({
  component: AdminPage,
  beforeLoad: async () => {
    const session = await authClient.getSession()
    const user = session.data?.user as Record<string, unknown> | undefined

    if (!session.data) {
      redirect({ to: "/login", throw: true })
    }

    if (user?.role !== "admin") {
      redirect({ to: "/dashboard", throw: true })
    }

    return { session }
  },
})
```

### Redirect with Return URL

```tsx
export const Route = createFileRoute("/billing")({
  beforeLoad: async ({ location }) => {
    const session = await authClient.getSession()
    
    if (!session.data) {
      redirect({
        to: "/login",
        search: { redirectTo: location.href }, // Preserve destination
        throw: true,
      })
    }
    
    return { session }
  },
})
```

**Login page handles redirect:**

```tsx
export const Route = createFileRoute("/login")({
  validateSearch: z.object({
    redirectTo: z.string().optional(),
  }),
})

function LoginPage() {
  const navigate = useNavigate()
  const { redirectTo } = Route.useSearch()

  const handleSuccess = () => {
    navigate({ to: redirectTo || "/dashboard" })
  }

  return <LoginForm onSuccess={handleSuccess} />
}
```

## Layout Routes

### Shared Layout with Auth

```tsx
// apps/web/src/routes/dashboard/route.tsx
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { authClient } from "@/lib/auth-client"

export const Route = createFileRoute("/dashboard")({
  component: DashboardLayout,
  beforeLoad: async () => {
    const session = await authClient.getSession()
    if (!session.data) {
      redirect({ to: "/login", throw: true })
    }
    return { session }
  },
})

function DashboardLayout() {
  const { session } = Route.useRouteContext()

  return (
    <div>
      <Sidebar user={session.data?.user} />
      <main>
        <Outlet /> {/* Child routes render here */}
      </main>
    </div>
  )
}
```

**Child routes inherit auth:**

```tsx
// apps/web/src/routes/dashboard/settings.tsx
export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
})

function SettingsPage() {
  const { session } = Route.useRouteContext() // Inherited from parent
  return <div>Settings for {session.data?.user?.email}</div>
}
```

## Navigation

### Programmatic Navigation

```tsx
import { useNavigate } from "@tanstack/react-router"

function MyComponent() {
  const navigate = useNavigate()

  const handleClick = () => {
    navigate({ to: "/dashboard" })
  }

  const handleClickWithSearch = () => {
    navigate({
      to: "/search",
      search: { q: "hello", page: 1 },
    })
  }

  return <button onClick={handleClick}>Go to Dashboard</button>
}
```

### Link Component

```tsx
import { Link } from "@tanstack/react-router"

<Link to="/dashboard">Dashboard</Link>

<Link to="/search" search={{ q: "hello", page: 1 }}>
  Search
</Link>

<Link to="/posts/$postId" params={{ postId: "123" }}>
  View Post
</Link>
```

### Active Link Styling

```tsx
<Link
  to="/dashboard"
  activeProps={{
    className: "font-bold text-blue-600",
  }}
  inactiveProps={{
    className: "text-gray-600",
  }}
>
  Dashboard
</Link>
```

## Route Context

### Defining Context

```tsx
// __root.tsx
export interface RouterAppContext {
  orpc: typeof orpc
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<RouterAppContext>()({
  component: RootComponent,
})
```

### Passing Context

```tsx
// main.tsx
const router = createRouter({
  routeTree,
  context: { orpc, queryClient },
})
```

### Using Context

```tsx
function MyPage() {
  const { orpc, queryClient } = Route.useRouteContext()
  
  const data = useQuery(orpc.healthCheck.queryOptions())
  
  return <div>{data.data}</div>
}
```

### Adding to Context in beforeLoad

```tsx
export const Route = createFileRoute("/dashboard")({
  beforeLoad: async () => {
    const session = await authClient.getSession()
    if (!session.data) {
      redirect({ to: "/login", throw: true })
    }
    return { session } // Merged into route context
  },
})

// Child routes can access session
function ChildPage() {
  const { session } = Route.useRouteContext() // Has session + orpc + queryClient
}
```

## Loading States

### Global Pending Component

```tsx
// main.tsx
const router = createRouter({
  routeTree,
  defaultPendingComponent: () => <Loader />,
})
```

### Route-Specific Pending

```tsx
export const Route = createFileRoute("/slow-page")({
  component: SlowPage,
  pendingComponent: () => <div>Loading slow page...</div>,
})
```

### Pending in Component

```tsx
import { useRouterState } from "@tanstack/react-router"

function MyComponent() {
  const isLoading = useRouterState({ select: (s) => s.isLoading })
  
  return isLoading ? <Spinner /> : <Content />
}
```

## Error Handling

### Route-Level Error Component

```tsx
export const Route = createFileRoute("/posts/$postId")({
  component: PostPage,
  errorComponent: ({ error }) => (
    <div>
      <h1>Error loading post</h1>
      <p>{error.message}</p>
    </div>
  ),
})
```

### Global Error Component

```tsx
// __root.tsx
export const Route = createRootRouteWithContext<RouterAppContext>()({
  component: RootComponent,
  errorComponent: ({ error, reset }) => (
    <div>
      <h1>Something went wrong</h1>
      <p>{error.message}</p>
      <button onClick={reset}>Try Again</button>
    </div>
  ),
})
```

## Preloading

### Intent Preloading (Default)

```tsx
// main.tsx
const router = createRouter({
  defaultPreload: "intent", // Preload on hover/focus
})
```

### Manual Preload

```tsx
<Link to="/posts/$postId" params={{ postId: "123" }} preload="intent">
  View Post
</Link>
```

Options:
- `"intent"` - Preload on hover/focus
- `"render"` - Preload when link renders
- `false` - No preloading

## Advanced Patterns

### Conditional Redirect in Component

```tsx
function SettingsPage() {
  const navigate = useNavigate()
  const { session } = Route.useRouteContext()

  useEffect(() => {
    if (!session.data?.user?.isVerified) {
      navigate({ to: "/verify-email" })
    }
  }, [session, navigate])

  return <div>Settings</div>
}
```

### Search Params in beforeLoad

```tsx
export const Route = createFileRoute("/invite")({
  validateSearch: z.object({
    token: z.string(),
  }),
  beforeLoad: async ({ search }) => {
    // Validate token before rendering
    const isValid = await validateInviteToken(search.token)
    
    if (!isValid) {
      redirect({ to: "/", throw: true })
    }
  },
})
```

### Multiple Guards

```tsx
export const Route = createFileRoute("/admin/users")({
  beforeLoad: async () => {
    // Guard 1: Check auth
    const session = await authClient.getSession()
    if (!session.data) {
      redirect({ to: "/login", throw: true })
    }

    // Guard 2: Check role
    const user = session.data.user as Record<string, unknown>
    if (user.role !== "admin") {
      redirect({ to: "/dashboard", throw: true })
    }

    // Guard 3: Check permissions
    const hasPermission = await checkPermission(user.id, "manage_users")
    if (!hasPermission) {
      redirect({ to: "/dashboard", throw: true })
    }

    return { session }
  },
})
```

## Best Practices

**Do:**
- ✅ Use `redirect({ throw: true })` in beforeLoad
- ✅ Validate search params with Zod
- ✅ Return session from beforeLoad for component access
- ✅ Use layout routes for shared auth logic
- ✅ Use `useNavigate()` for programmatic navigation

**Don't:**
- ❌ Use `navigate()` in beforeLoad (use `redirect()`)
- ❌ Forget `throw: true` in redirect (will continue execution)
- ❌ Put queries in beforeLoad (use component or loader)
- ❌ Mix route params with search params (different APIs)
- ❌ Mutate route context (it's read-only)
