# Complete Setup Guide

Step-by-step guide for setting up TanStack Router + TanStack Query + oRPC integration.

## 1. Install Dependencies

```bash
bun add @tanstack/react-router @tanstack/react-query @orpc/client @orpc/tanstack-query
bun add -d @tanstack/router-devtools @tanstack/react-query-devtools
```

## 2. Create oRPC Client (`apps/web/src/utils/orpc.ts`)

```typescript
import type { AppRouterClient } from "@condomin-ia/api/routers/index"
import { env } from "@condomin-ia/env/web"
import { createORPCClient } from "@orpc/client"
import { RPCLink } from "@orpc/client/fetch"
import { createTanstackQueryUtils } from "@orpc/tanstack-query"
import { QueryCache, QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

// Global QueryClient with error handling
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

// RPC link with credentials for session auth
export const link = new RPCLink({
  url: `${env.VITE_SERVER_URL}/rpc`,
  fetch(url, options) {
    return fetch(url, {
      ...options,
      credentials: "include", // Critical for cookie-based auth
    })
  },
})

// Type-safe oRPC client
export const client: AppRouterClient = createORPCClient(link)

// TanStack Query utilities (queries, mutations, etc.)
export const orpc = createTanstackQueryUtils(client)
```

**Key points:**
- Single global `queryClient` instance
- `credentials: "include"` enables session cookies
- Global error handler toasts all query failures
- Retry action invalidates failed query
- Export `orpc` utils for use in components

## 3. Define Router Context (`apps/web/src/routes/__root.tsx`)

```tsx
import type { AppRouterClient } from "@condomin-ia/api/routers/index"
import { createORPCClient } from "@orpc/client"
import { createTanstackQueryUtils } from "@orpc/tanstack-query"
import type { QueryClient } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import {
  createRootRouteWithContext,
  Outlet,
} from "@tanstack/react-router"
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools"

import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { link, type orpc } from "@/utils/orpc"
import "../index.css"

// Define context interface
export interface RouterAppContext {
  orpc: typeof orpc
  queryClient: QueryClient
}

// Create root route with typed context
export const Route = createRootRouteWithContext<RouterAppContext>()({
  component: RootComponent,
  head: () => ({
    meta: [
      { title: "My App" },
      { name: "description", content: "App description" },
    ],
    links: [{ rel: "icon", href: "/favicon.ico" }],
  }),
})

function RootComponent() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="theme">
      <Toaster />
      <Outlet />
      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools position="bottom-right" />
          <ReactQueryDevtools buttonPosition="bottom-left" />
        </>
      )}
    </ThemeProvider>
  )
}
```

**Key points:**
- `RouterAppContext` defines what's available to all routes
- `createRootRouteWithContext` provides type safety
- Devtools only in development
- Global providers (theme, toaster) at root

## 4. Create Router (`apps/web/src/main.tsx`)

```tsx
import { QueryClientProvider } from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import ReactDOM from "react-dom/client"

import Loader from "./components/loader"
import { routeTree } from "./routeTree.gen"
import { orpc, queryClient } from "./utils/orpc"

// Create router with context
const router = createRouter({
  routeTree,
  defaultPreload: "intent", // Preload on hover
  defaultPendingComponent: () => <Loader />,
  context: { orpc, queryClient }, // Pass context to all routes
  Wrap({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  },
})

// Register router for type safety
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

const rootElement = document.getElementById("app")
if (!rootElement) throw new Error("Root element not found")

if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(<RouterProvider router={router} />)
}
```

**Key points:**
- Pass `orpc` and `queryClient` to router context
- Wrap with `QueryClientProvider` 
- Register router for TypeScript autocomplete
- `defaultPreload: "intent"` for better UX

## 5. Define API Router (`packages/api/src/routers/index.ts`)

```typescript
import type { RouterClient } from "@orpc/server"
import { protectedProcedure, publicProcedure } from "../index"
import { paymentsRouter } from "./payments"
import { s3Router } from "./s3"

export const appRouter = {
  payments: paymentsRouter,
  s3: s3Router,
  healthCheck: publicProcedure.handler(() => "OK"),
  privateData: protectedProcedure.handler(({ context }) => ({
    message: "This is private",
    user: context.session?.user,
  })),
}

export type AppRouter = typeof appRouter
export type AppRouterClient = RouterClient<typeof appRouter>
```

**Key points:**
- Namespace routers by feature (payments, s3, etc.)
- Export `AppRouterClient` type for frontend
- Use `protectedProcedure` for auth-required endpoints

## 6. Create Procedures (`packages/api/src/index.ts`)

```typescript
import { ORPCError, os } from "@orpc/server"
import type { Context } from "./context"

export const o = os.$context<Context>()
export const publicProcedure = o

// Auth middleware
const requireAuth = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED")
  }
  return await next({
    context: { session: context.session },
  })
})

export const protectedProcedure = publicProcedure.use(requireAuth)

// Admin middleware
const requireAdmin = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) {
    throw new ORPCError("UNAUTHORIZED")
  }
  const user = context.session.user as Record<string, unknown>
  if (user.role !== "admin") {
    throw new ORPCError("FORBIDDEN")
  }
  return await next({
    context: { session: context.session },
  })
})

export const adminProcedure = publicProcedure.use(requireAdmin)
```

## 7. Environment Variables

**`packages/env/src/web.ts`:**
```typescript
import { createEnv } from "@t3-oss/env-core"
import { z } from "zod"

export const env = createEnv({
  clientPrefix: "VITE_",
  client: {
    VITE_SERVER_URL: z.string().url(),
  },
  runtimeEnv: import.meta.env,
})
```

**`.env`:**
```bash
VITE_SERVER_URL=http://localhost:3000
```

## 8. TypeScript Configuration

**`tsconfig.json`:**
```json
{
  "compilerOptions": {
    "strict": true,
    "types": ["vite/client", "@tanstack/react-router"],
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

## Verification Checklist

- [ ] `orpc` exports `queryOptions()` and `mutationOptions()` methods
- [ ] `queryClient` shows error toasts on query failures
- [ ] `credentials: "include"` is set in RPC link
- [ ] Router context provides `orpc` and `queryClient`
- [ ] Types auto-complete in components
- [ ] Devtools appear in development mode
- [ ] Environment variables load correctly
- [ ] Auth middleware throws UNAUTHORIZED for unauthenticated requests

## Common Setup Issues

**Types not working:**
- Regenerate route tree: `bun run dev` (auto-generates `routeTree.gen.ts`)
- Check router registration in `main.tsx`

**Auth not working:**
- Verify `credentials: "include"` in fetch
- Check cookies are set (DevTools → Application → Cookies)

**Queries fail silently:**
- Check `QueryCache` onError is configured
- Verify toast library is installed and configured

**oRPC methods not found:**
- Ensure API router is exported correctly
- Check import path matches `AppRouterClient` type
