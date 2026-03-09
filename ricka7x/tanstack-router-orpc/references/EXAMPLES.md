# Real-World Examples

Production patterns from this codebase.

## Example 1: Billing Page with Subscriptions

**File:** `apps/web/src/routes/dashboard/billing.tsx`

Demonstrates mixing oRPC queries with external API (Better Auth).

```tsx
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { authClient } from "@/lib/auth-client"
import { orpc } from "@/utils/orpc"

export const Route = createFileRoute("/dashboard/billing")({
  component: BillingPage,
})

function BillingPage() {
  const [portalLoading, setPortalLoading] = useState(false)

  // oRPC query for invoices (no input needed)
  const invoices = useQuery(orpc.payments.listInvoices.queryOptions())
  
  // With input parameters, use:
  // const invoices = useQuery(
  //   orpc.payments.listInvoices.queryOptions({
  //     input: { status: "paid", limit: 10 }
  //   })
  // )

  // Better Auth client query for subscriptions
  const subscriptions = useQuery({
    queryKey: ["subscriptions"],
    queryFn: async () => {
      const result = await authClient.subscription.list()
      return result?.data ?? []
    },
  })

  const activeSub = subscriptions.data?.[0]

  const handleManageSubscription = async () => {
    setPortalLoading(true)
    try {
      const result = await authClient.subscription.billingPortal({
        returnUrl: window.location.href,
      })
      if (result?.data?.url) {
        window.location.href = result.data.url
      }
    } catch (error) {
      toast.error("Failed to open billing portal")
      console.error(error)
    } finally {
      setPortalLoading(false)
    }
  }

  const renderCurrentPlan = () => {
    if (subscriptions.isLoading) {
      return (
        <div className="animate-pulse space-y-2">
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="h-4 w-48 rounded bg-muted" />
        </div>
      )
    }

    if (activeSub) {
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="font-bold text-2xl capitalize">
              {activeSub.name}
            </span>
            {getStatusBadge(activeSub.status)}
          </div>
          <button
            onClick={handleManageSubscription}
            disabled={portalLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded"
          >
            {portalLoading ? "Loading..." : "Manage Subscription"}
          </button>
        </div>
      )
    }

    return <div>No active subscription</div>
  }

  return (
    <div className="space-y-6">
      <section>
        <h2 className="font-semibold text-xl">Current Plan</h2>
        {renderCurrentPlan()}
      </section>

      <section>
        <h2 className="font-semibold text-xl">Invoices</h2>
        {invoices.isLoading && <div>Loading invoices...</div>}
        {invoices.error && <div>Failed to load invoices</div>}
        {invoices.data && (
          <div className="space-y-2">
            {invoices.data.map((invoice) => (
              <div key={invoice.id} className="border rounded p-4">
                <p>{invoice.number}</p>
                <p>{invoice.status}</p>
                <p>${invoice.amount / 100}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function getStatusBadge(status: string) {
  const styles: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    trialing: "bg-blue-100 text-blue-800",
    past_due: "bg-yellow-100 text-yellow-800",
    canceled: "bg-red-100 text-red-800",
    incomplete: "bg-gray-100 text-gray-800",
  }

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs ${styles[status]}`}>
      {status}
    </span>
  )
}
```

**Key patterns:**
- Mix oRPC and external API queries
- Loading states for both queries
- Local state for async actions (portalLoading)
- Error handling with toast
- Skeleton loading UI

## Example 2: File Upload (Sequential Mutations)

**File:** `apps/web/src/routes/dashboard/test-upload.tsx`

Multi-step mutation workflow: presigned URL → S3 upload → save metadata.

```tsx
import { useMutation } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { orpc } from "@/utils/orpc"

export const Route = createFileRoute("/dashboard/test-upload")({
  component: TestUploadPage,
})

function TestUploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null)

  const getPresignedUrl = useMutation(
    orpc.s3.getPresignedUrl.mutationOptions()
  )
  const saveFile = useMutation(orpc.s3.saveFile.mutationOptions())

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target?.files?.[0]) {
      setFile(e.target.files[0])
      setUploadedUrl(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    try {
      // Step 1: Get presigned URL from API
      // Note: Input is passed directly to mutateAsync (not wrapped in { input: {} })
      const { url } = await getPresignedUrl.mutateAsync({
        key: `uploads/${Date.now()}-${file.name}`,
        contentType: file.type,
      })

      // Step 2: Upload file directly to S3
      const response = await fetch(url, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type,
        },
      })

      if (!response.ok) {
        throw new Error("Failed to upload file to S3")
      }

      // Step 3: Save file metadata to database
      const cleanUrl = url.split("?")[0] // Remove query params
      await saveFile.mutateAsync({
        url: cleanUrl,
        name: file.name,
        type: file.type,
        size: file.size,
      })

      toast.success("File uploaded and saved!")
      setUploadedUrl(cleanUrl)
    } catch (error) {
      console.error(error)
      toast.error("Upload failed. Check console for details.")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-bold text-2xl">Test File Upload</h1>
        <p className="text-gray-600 text-sm">
          Upload files to S3 and save metadata to database
        </p>
      </div>

      <div className="space-y-4">
        <input
          type="file"
          onChange={handleFileChange}
          disabled={uploading}
          className="block w-full"
        />

        {file && (
          <div className="rounded border bg-gray-50 p-4">
            <p className="font-medium text-sm">Selected file:</p>
            <p className="text-gray-600 text-sm">{file.name}</p>
            <p className="text-gray-500 text-xs">
              {(file.size / 1024).toFixed(2)} KB
            </p>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload File"}
        </button>

        {uploadedUrl && (
          <div className="rounded border border-green-300 bg-green-50 p-4">
            <p className="font-medium text-green-800 text-sm">
              Upload successful!
            </p>
            <a
              href={uploadedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 text-sm underline"
            >
              View file
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
```

**Key patterns:**
- Sequential mutations with await
- Local loading state (uploading)
- Error handling at each step
- Success state with URL display
- Disabled states during upload

## Example 3: Auth Guard Layout

**File:** `apps/web/src/routes/dashboard/route.tsx`

Shared layout with authentication guard for all child routes.

```tsx
import {
  createFileRoute,
  Link,
  Outlet,
  redirect,
} from "@tanstack/react-router"
import { authClient } from "@/lib/auth-client"

export const Route = createFileRoute("/dashboard")({
  component: DashboardLayout,
  beforeLoad: async () => {
    const session = await authClient.getSession()
    
    if (!session.data) {
      redirect({
        to: "/login",
        throw: true,
      })
    }
    
    return { session }
  },
})

const sidebarLinks = [
  { to: "/dashboard", label: "Overview" },
  { to: "/dashboard/billing", label: "Billing" },
  { to: "/dashboard/settings", label: "Settings" },
  { to: "/dashboard/organization", label: "Organization" },
] as const

function DashboardLayout() {
  const { session } = Route.useRouteContext()
  const user = session.data?.user as Record<string, unknown> | undefined
  const currentSession = session.data?.session as Record<string, unknown>
  const isAdmin = user?.role === "admin"
  const isImpersonating = !!currentSession?.impersonatedBy

  const handleStopImpersonating = async () => {
    await authClient.admin.stopImpersonating()
    window.location.reload()
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-gray-50 p-6">
        <nav className="space-y-2">
          {sidebarLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="block rounded px-4 py-2 hover:bg-gray-100"
              activeProps={{
                className: "bg-blue-100 text-blue-700 font-medium",
              }}
            >
              {link.label}
            </Link>
          ))}
          
          {isAdmin && (
            <Link
              to="/dashboard/admin"
              className="block rounded px-4 py-2 hover:bg-gray-100"
              activeProps={{
                className: "bg-blue-100 text-blue-700 font-medium",
              }}
            >
              Admin
            </Link>
          )}
        </nav>

        {isImpersonating && (
          <div className="mt-4 rounded border border-yellow-300 bg-yellow-50 p-3">
            <p className="font-medium text-yellow-800 text-xs">
              Impersonating
            </p>
            <button
              onClick={handleStopImpersonating}
              className="mt-2 text-yellow-700 text-xs underline"
            >
              Stop Impersonation
            </button>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8">
        <Outlet /> {/* Child routes render here */}
      </main>
    </div>
  )
}
```

**Key patterns:**
- `beforeLoad` guards all child routes
- Session passed to route context
- Layout component with sidebar
- Active link styling
- Role-based link visibility
- Impersonation detection and control

## Example 4: Role-Based Admin Guard

**File:** `apps/web/src/routes/dashboard/admin.tsx`

Admin-only route with role check.

```tsx
import { createFileRoute, redirect } from "@tanstack/react-router"
import { authClient } from "@/lib/auth-client"

export const Route = createFileRoute("/dashboard/admin")({
  component: AdminPage,
  beforeLoad: async () => {
    const session = await authClient.getSession()

    const user = session.data?.user as Record<string, unknown> | undefined
    
    if (user?.role !== "admin") {
      redirect({
        to: "/dashboard",
        throw: true,
      })
    }
  },
})

function AdminPage() {
  // Admin-only content
  return (
    <div>
      <h1 className="font-bold text-2xl">Admin Dashboard</h1>
      {/* Admin features */}
    </div>
  )
}
```

**Key patterns:**
- Role check in beforeLoad
- Redirect non-admins to dashboard
- No need to return session (inherited from parent layout)

## Example 5: Login with Search Params

**File:** `apps/web/src/routes/login.tsx`

Login page with validated search params and redirect handling.

```tsx
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { z } from "zod"
import SignInForm from "@/components/sign-in-form"
import SignUpForm from "@/components/sign-up-form"

export const Route = createFileRoute("/login")({
  component: LoginPage,
  validateSearch: z.object({
    redirectTo: z.string().optional(),
    showSignIn: z.boolean().optional(),
  }),
})

function LoginPage() {
  const search = Route.useSearch()
  const [showSignIn, setShowSignIn] = useState(search.showSignIn ?? false)

  return (
    <div className="flex min-h-screen items-center justify-center">
      {showSignIn ? (
        <SignInForm
          redirectTo={search.redirectTo}
          onSwitchToSignUp={() => setShowSignIn(false)}
        />
      ) : (
        <SignUpForm
          redirectTo={search.redirectTo}
          onSwitchToSignIn={() => setShowSignIn(true)}
        />
      )}
    </div>
  )
}
```

**Key patterns:**
- `validateSearch` with Zod for type-safe params
- Access params with `Route.useSearch()`
- Toggle between sign in/sign up
- Pass redirectTo to forms

## Example 6: Simple Query

**File:** `apps/web/src/routes/dashboard/index.tsx`

Basic dashboard with single query.

```tsx
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { orpc } from "@/utils/orpc"

export const Route = createFileRoute("/dashboard/")({
  component: DashboardPage,
})

function DashboardPage() {
  const privateData = useQuery(orpc.privateData.queryOptions())

  if (privateData.isLoading) {
    return <div>Loading...</div>
  }

  if (privateData.error) {
    return <div>Error: {privateData.error.message}</div>
  }

  return (
    <div>
      <h1 className="font-bold text-2xl">Dashboard</h1>
      <p className="text-gray-600">{privateData.data.message}</p>
      <pre className="mt-4 rounded bg-gray-100 p-4">
        {JSON.stringify(privateData.data.user, null, 2)}
      </pre>
    </div>
  )
}
```

**Key patterns:**
- Simple oRPC query
- Loading and error states
- Display data when loaded

## Common Patterns Summary

1. **Mix oRPC + External APIs** - Use oRPC for your API, manual queries for third-party
2. **Sequential mutations** - await each step, handle errors at each stage
3. **Auth guards** - beforeLoad with redirect for protected routes
4. **Layout routes** - Shared auth logic in parent, Outlet for children
5. **Search params** - validateSearch for type safety, useSearch to access
6. **Loading states** - Local state for actions, query state for data
7. **Error handling** - try-catch with specific toast messages
