# Component Development

Patterns for building components in this stack. React 19 + React Compiler + shadcn/ui + TanStack Query.

---

## File Structure

Every non-trivial feature gets its own folder. Co-locate everything that belongs together.

```
components/
└── user-card/
    ├── user-card.tsx          → Component(s)
    ├── use-user-card.ts       → Custom hook(s)
    ├── user-card.types.ts     → Types/interfaces (if substantial)
    └── index.ts               → Public re-export (optional)
```

Small, stateless, single-purpose components (e.g. a badge, a spinner) can be a single file — no folder needed.

**Rules:**
- No barrel `index.ts` files that re-export an entire folder
- `index.ts` is only acceptable as a single explicit re-export for a feature folder's public API
- Types that are only used in one file stay in that file — don't pre-emptively extract

---

## React 19 Patterns

### ref as prop (no forwardRef)

React 19 passes `ref` as a regular prop. Never use `forwardRef`.

```tsx
// ✅ React 19
interface InputProps extends React.ComponentProps<"input"> {
  label: string;
}

export function Input({ label, ref, ...props }: InputProps) {
  return (
    <div>
      <label>{label}</label>
      <input ref={ref} {...props} />
    </div>
  );
}

// ❌ Old — never use forwardRef
export const Input = forwardRef<HTMLInputElement, InputProps>(({ label, ...props }, ref) => {
  // ...
});
```

### use() for Context

`use()` can replace `useContext()` and supports conditional calls.

```tsx
import { use } from "react";

// Reading context
function UserAvatar() {
  const { user } = use(AuthContext);
  return <img src={user.image} alt={user.name} />;
}

// Conditionally reading (not possible with useContext)
function AdminBadge({ show }: { show: boolean }) {
  if (!show) return null;
  const { user } = use(AuthContext); // ✅ called conditionally
  return user.role === "admin" ? <Badge>Admin</Badge> : null;
}
```

### use() for Promises (Suspense)

Unwrap promises directly in components — pair with a `<Suspense>` boundary above.

```tsx
// In a route loader or parent, pass a promise down:
function PostsPage() {
  const postsPromise = orpc.posts.list.call(); // not awaited
  return (
    <Suspense fallback={<PostsSkeleton />}>
      <PostsList postsPromise={postsPromise} />
    </Suspense>
  );
}

function PostsList({ postsPromise }: { postsPromise: Promise<Post[]> }) {
  const posts = use(postsPromise); // suspends until resolved
  return posts.map((post) => <PostCard key={post.id} post={post} />);
}
```

> **Note:** For server-fetched data, prefer `useQuery(orpc.*.queryOptions())` — it integrates with TanStack Query's cache. Use `use()` with promises for one-off cases or when passing promises from parent to child.

### useOptimistic

Use for instant UI feedback before a mutation settles. Pairs naturally with TanStack mutations.

```tsx
import { useOptimistic } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { orpc } from "@/utils/orpc";

function TodoList({ todos }: { todos: Todo[] }) {
  const queryClient = useQueryClient();
  const [optimisticTodos, addOptimistic] = useOptimistic(
    todos,
    (current, newTodo: Todo) => [...current, newTodo]
  );

  const mutation = useMutation(orpc.todos.create.mutationOptions());

  const handleCreate = async (title: string) => {
    const tempTodo: Todo = { id: crypto.randomUUID(), title, done: false };
    addOptimistic(tempTodo); // instant UI update
    try {
      await mutation.mutateAsync({ title });
      queryClient.invalidateQueries({ queryKey: orpc.todos.list.key() });
    } catch {
      toast.error("Failed to create todo");
      // optimistic state reverts automatically on error
    }
  };

  return (
    <>
      {optimisticTodos.map((todo) => <TodoItem key={todo.id} todo={todo} />)}
      <CreateTodoButton onCreate={handleCreate} />
    </>
  );
}
```

### useActionState

Use for form submissions that don't need TanStack Form — simple one-off actions.

```tsx
import { useActionState } from "react";

type State = { error?: string; success?: boolean };

async function submitAction(prev: State, formData: FormData): Promise<State> {
  const email = formData.get("email") as string;
  try {
    await authClient.sendVerificationEmail({ email });
    return { success: true };
  } catch {
    return { error: "Failed to send email" };
  }
}

export function ResendVerificationForm() {
  const [state, action, isPending] = useActionState(submitAction, {});

  return (
    <form action={action}>
      <Input name="email" type="email" placeholder="you@example.com" />
      {state.error && <p className="text-destructive text-sm">{state.error}</p>}
      {state.success && <p className="text-sm">Check your inbox!</p>}
      <Button type="submit" disabled={isPending}>
        {isPending ? "Sending..." : "Resend email"}
      </Button>
    </form>
  );
}
```

> **When to use `useActionState` vs TanStack Form:** Use `useActionState` for simple single-field or auth-adjacent actions. Use the [4-file TanStack Form pattern](FORMS.md) for anything with multiple fields, complex validation, or reuse across layouts.

---

## shadcn/ui Usage

Always use shadcn components. Never build from scratch what shadcn already covers.

**Import from `@/components/ui/*`:**
```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
```

**Extending with CVA:**

When you need variants beyond what shadcn ships, extend with `class-variance-authority`:

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusBadge = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      status: {
        active: "bg-green-100 text-green-800",
        inactive: "bg-gray-100 text-gray-800",
        pending: "bg-yellow-100 text-yellow-800",
        banned: "bg-red-100 text-red-800",
      },
    },
    defaultVariants: {
      status: "inactive",
    },
  }
);

interface StatusBadgeProps extends VariantProps<typeof statusBadge> {
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn(statusBadge({ status }), className)}>
      {status}
    </span>
  );
}
```

**Rules:**
- Always accept and forward `className` on any component that wraps a DOM element
- Use `cn()` (from `@/lib/utils`) to merge classes — never string concatenation
- Don't override shadcn's internal Tailwind classes via inline styles

---

## Component Patterns

### Composition Over Prop Drilling

Pass components as children instead of drilling props through multiple levels.

```tsx
// ❌ Prop drilling
<PageHeader title="Users" description="Manage users" showCreateButton onCreateClick={handleCreate} />

// ✅ Composition
<PageHeader>
  <PageHeader.Title>Users</PageHeader.Title>
  <PageHeader.Description>Manage users</PageHeader.Description>
  <PageHeader.Actions>
    <Button onClick={handleCreate}>Create User</Button>
  </PageHeader.Actions>
</PageHeader>
```

### Compound Components

For components with multiple related parts, use static properties:

```tsx
interface CardProps { children: React.ReactNode; className?: string }
interface CardSectionProps { children: React.ReactNode; className?: string }

function Card({ children, className }: CardProps) {
  return <div className={cn("rounded-lg border bg-card", className)}>{children}</div>;
}

Card.Header = function CardHeader({ children, className }: CardSectionProps) {
  return <div className={cn("flex items-center p-6", className)}>{children}</div>;
};

Card.Body = function CardBody({ children, className }: CardSectionProps) {
  return <div className={cn("p-6 pt-0", className)}>{children}</div>;
};

// Usage
<Card>
  <Card.Header>
    <h2>Title</h2>
  </Card.Header>
  <Card.Body>Content</Card.Body>
</Card>
```

> Use this for custom composite components. For standard cards/dialogs, use shadcn's named exports directly (`CardHeader`, `CardContent`, etc.).

### No Boolean Props — Use Explicit Variants

```tsx
// ❌ Boolean props are ambiguous and don't scale
<Button primary />
<Button isDestructive />
<Alert warning />

// ✅ Explicit string variants
<Button intent="primary" />
<Button intent="destructive" />
<Alert variant="warning" />
```

### Children Over Render Props

```tsx
// ❌ Render props (outdated pattern)
<DataProvider render={(data) => <Table data={data} />} />

// ✅ Children
<DataProvider>
  {(data) => <Table data={data} />}
</DataProvider>

// ✅ Even better — just compose
<DataProvider>
  <Table />
</DataProvider>
```

---

## Custom Hook Patterns

Extract logic into hooks when a component has more than trivial local state or side effects.

```ts
// use-user-card.ts
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { orpc } from "@/utils/orpc";
import { toast } from "sonner";

export function useUserCard(userId: string) {
  const [isEditing, setIsEditing] = useState(false);
  const queryClient = useQueryClient();

  const deleteMutation = useMutation(orpc.users.delete.mutationOptions());

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({ id: userId });
      queryClient.invalidateQueries({ queryKey: orpc.users.list.key() });
      toast.success("User deleted");
    } catch {
      toast.error("Failed to delete user");
    }
  };

  return {
    isEditing,
    setIsEditing,
    handleDelete,
    isDeleting: deleteMutation.isPending,
  };
}
```

**Rules:**
- Hook files are named `use-*.ts` (kebab-case)
- Always return a plain object — not an array (unless it mirrors a built-in like `useState`)
- Never call hooks conditionally inside the hook body
- Hooks should have a single, clear responsibility — split if doing two unrelated things

---

## State Management

| State type | Tool |
|---|---|
| Server / async data | TanStack Query (`useQuery`, `useMutation`) |
| Shareable URL state | `nuqs` (`useQueryState`) |
| Global UI state (theme, auth) | React Context |
| Complex local state | `useReducer` |
| Simple local state | `useState` |
| Derived state | Compute inline — never duplicate into state |

### Server State — TanStack Query Only

No Redux, no Zustand, no global store for server data. If it comes from the API, it lives in TanStack Query.

```tsx
// ✅
const { data: users } = useQuery(orpc.users.list.queryOptions());

// ❌ Never copy server data into local state
const [users, setUsers] = useState([]);
useEffect(() => { fetchUsers().then(setUsers); }, []);
```

### URL State — nuqs

Use `nuqs` for state that should survive a page refresh, be shareable, or drive filtering/pagination:

```tsx
import { useQueryState, parseAsInteger, parseAsString } from "nuqs";

function UsersPage() {
  const [page, setPage] = useQueryState("page", parseAsInteger.withDefault(1));
  const [search, setSearch] = useQueryState("search", parseAsString.withDefault(""));

  const { data } = useQuery(orpc.users.list.queryOptions({
    input: { page, search },
  }));
  // ...
}
```

### Derived State — Never Duplicate

```tsx
// ❌ Duplicating state that can be computed
const [items, setItems] = useState<Item[]>([]);
const [count, setCount] = useState(0); // duplicated!

// ✅ Derive it
const [items, setItems] = useState<Item[]>([]);
const count = items.length; // computed, not stored
```

### useReducer for Complex Local State

Use `useReducer` when local state has multiple sub-values that update together, or when next state depends on previous:

```tsx
type State = {
  step: "idle" | "uploading" | "processing" | "done" | "error";
  progress: number;
  error?: string;
};

type Action =
  | { type: "start" }
  | { type: "progress"; percent: number }
  | { type: "done" }
  | { type: "error"; message: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start": return { step: "uploading", progress: 0 };
    case "progress": return { ...state, progress: action.percent };
    case "done": return { step: "done", progress: 100 };
    case "error": return { step: "error", progress: 0, error: action.message };
  }
}

function UploadButton() {
  const [state, dispatch] = useReducer(reducer, { step: "idle", progress: 0 });
  // ...
}
```

---

## Performance

**This project uses React Compiler.** Do not add manual `memo`, `useMemo`, or `useCallback` unless you have a specific measured reason — the compiler handles it.

### When Manual Optimization IS Still Needed

1. **Reanimated worklet callbacks** — the compiler can't optimize shared values passed into worklets
2. **Third-party lib callbacks** that require stable references (e.g. virtual list `renderItem` if the library opts out of compiler)
3. **Expensive non-rendering computations** that run on every render with large data sets — profile first

```tsx
// ✅ Let the compiler handle this — no manual memo needed
function UserList({ users }: { users: User[] }) {
  const filtered = users.filter((u) => u.active); // compiler optimizes this
  return filtered.map((u) => <UserRow key={u.id} user={u} />);
}

// ✅ Manual memo only when compiler can't help (Reanimated worklets)
const animatedStyle = useAnimatedStyle(() => ({
  opacity: sharedValue.value,
})); // Reanimated worklets are outside React Compiler's scope
```

### Lazy Loading

Split heavy components out of the initial bundle:

```tsx
import { lazy, Suspense } from "react";

// Heavy components (charts, rich text editors, date pickers)
const RevenueChart = lazy(() => import("@/components/revenue-chart"));
const RichTextEditor = lazy(() => import("@/components/rich-text-editor"));

// Usage — always wrap in Suspense
<Suspense fallback={<ChartSkeleton />}>
  <RevenueChart data={data} />
</Suspense>
```

---

## Accessibility

Rely on shadcn/base-ui for the heavy lifting — don't break what it gives you.

**Rules:**
- Always use semantic HTML: `<button>`, `<nav>`, `<main>`, `<section>`, `<header>` — not `<div onClick>`
- Every form input must have a visible `<label>` with `htmlFor` — never skip it
- Interactive elements must be reachable via keyboard (`Tab`, `Enter`, `Space`)
- Use `aria-invalid` + `aria-describedby` on inputs with errors (already enforced in the form pattern)
- Provide `alt` text on all images — empty string `alt=""` for decorative images
- Never use color alone to convey information — pair with an icon or text
- Don't remove `outline` / `focus-visible` styles from interactive elements

```tsx
// ✅ Semantic + accessible
<button
  type="button"
  aria-label="Delete user John Doe"
  onClick={handleDelete}
>
  <Trash2Icon className="h-4 w-4" aria-hidden="true" />
</button>

// ❌ Div as button — no keyboard access, no semantics
<div onClick={handleDelete}>
  <Trash2Icon className="h-4 w-4" />
</div>
```

**Icon buttons** must always have an `aria-label` — icons alone are not accessible:
```tsx
<Button variant="ghost" size="icon" aria-label="Open settings">
  <Settings2Icon className="h-4 w-4" aria-hidden="true" />
</Button>
```

---

## Error Handling

**Pattern: error boundaries per feature section + try/catch for mutations.**

### Error Boundaries (Async Rendering)

Wrap independent sections so one failure doesn't crash the whole page:

```tsx
import { ErrorBoundary } from "react-error-boundary";

function DashboardPage() {
  return (
    <div>
      <ErrorBoundary fallback={<SectionError message="Failed to load stats" />}>
        <StatsSection />
      </ErrorBoundary>

      <ErrorBoundary fallback={<SectionError message="Failed to load activity" />}>
        <ActivityFeed />
      </ErrorBoundary>
    </div>
  );
}

function SectionError({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-destructive/50 p-4 text-sm text-destructive">
      {message}
    </div>
  );
}
```

### Mutations — try/catch + toast

```tsx
const mutation = useMutation(orpc.users.delete.mutationOptions());

const handleDelete = async (id: string) => {
  try {
    await mutation.mutateAsync({ id });
    queryClient.invalidateQueries({ queryKey: orpc.users.list.key() });
    toast.success("User deleted");
  } catch (error) {
    // ORPCError messages are user-safe
    const message = error instanceof Error ? error.message : "Something went wrong";
    toast.error(message);
  }
};
```

### Never Swallow Errors

```tsx
// ❌ Swallowed — silent failure
try {
  await doSomething();
} catch {}

// ❌ Re-thrown without context
try {
  await doSomething();
} catch (e) {
  throw e;
}

// ✅ Handle or surface
try {
  await doSomething();
} catch (error) {
  toast.error("Operation failed");
  console.error("[handleAction]", error); // log for debugging
}
```

---

## Code Splitting

```
Route level    → TanStack Router handles this automatically via file-based routes
Feature level  → React.lazy for heavy components not needed on initial render
Library level  → Dynamic import for large third-party libs
```

```tsx
// Route-level: automatic via TanStack Router file-based routing

// Feature-level: lazy load modals, charts, editors
const AnalyticsChart = lazy(() => import("./analytics-chart"));
const InviteMemberDialog = lazy(() => import("./invite-member-dialog"));

// Library-level: dynamic import for large libs
const loadDatePicker = () => import("react-day-picker");

// Always wrap lazy components in Suspense with a meaningful fallback
<Suspense fallback={<Skeleton className="h-64 w-full" />}>
  <AnalyticsChart />
</Suspense>
```

**What to lazy load:**
- Charts / data visualizations
- Rich text editors
- Date pickers
- Heavy dialogs/modals not shown on initial render
- Admin-only sections

**What NOT to lazy load:**
- Navigation, headers, layout components
- Anything visible on initial render (causes layout shift)
- Small components — the network overhead isn't worth it

---

## Quick Anti-Patterns Reference

| ❌ Don't | ✅ Do |
|---|---|
| `forwardRef` | ref as prop |
| `useContext` | `use(Context)` |
| Boolean variant props (`isDestructive`) | String variants (`intent="destructive"`) |
| Manual `memo`/`useMemo`/`useCallback` everywhere | Trust React Compiler |
| `useEffect` to sync server data | TanStack Query |
| `useEffect` to compute derived state | Compute inline |
| Prop drilling 3+ levels | Composition / Context |
| `<div onClick>` | `<button>` |
| Icon buttons without `aria-label` | Always `aria-label` on icon buttons |
| Swallowing errors in `catch {}` | Always handle or surface |
| Barrel `index.ts` re-exporting everything | Explicit imports |