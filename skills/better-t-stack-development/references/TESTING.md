# Testing

Vitest for unit + integration tests. Testing Library for component tests. better-auth test-utils for auth flows. Playwright for E2E (optional, added per project).

**Strategy:** per-package Vitest configs (not root-level Vitest Projects) — this is the correct approach for Turborepo because it respects package boundaries and enables Turborepo caching. Turborepo Projects mode crosses package boundaries and breaks caching.

---

## TDD Workflow

Tests come **first** — they are the spec. Red → green → refactor:

1. **Red** — write a failing test that pins the behavior you're about to add.
   Run it (`bun run test` in the package). It must fail for the *right* reason
   (assertion mismatch / not found), not a compile or import error.
2. **Green** — implement the minimum code to make it pass. Don't build ahead.
3. **Refactor** — clean up while staying green, then re-run the suite.

Every new or changed behavior ships with its tests **in the same change**. For
genuinely visual work (animation, polish) tests may be written alongside the
code — but never deferred to a follow-up commit.

### Drive these with a test first

| Layer | What to pin | Write it as |
|---|---|---|
| Zod schema | validation rules, edge cases | unit test on the schema |
| Utility / pure function | all branches, edge cases | unit test |
| oRPC procedure | happy path, auth, not-found, forbidden | call the handler with a mocked context + test-created session |
| better-auth plugin | validation → session → admin check → DB write | `createTestAuth` + `testUtils` (in-memory) |
| Custom hook (`use*`) | returned values, state changes | `renderHook` + `createQueryWrapper` |
| Component | renders, interactions, conditional UI | Testing Library (query by role/label) |
| Form | validation errors, successful submit | RTL + mocked mutation |

### Definition of done

- New/changed behavior has a test (or an explicit, agreed exception)
- `bun run test` is green for the package (`turbo test --filter=<pkg>` at root)
- `bun x ultracite check` passes

A change that ships untested behavior or leaves the suite red is a **review
blocker**.

---

## Setup

### 1. Install deps in each package/app that needs tests

```bash
# For packages with pure logic (api, auth, db, payments)
bun add -D vitest @vitest/coverage-v8 --cwd packages/api

# For web app (needs DOM + React Testing Library)
bun add -D vitest @vitest/coverage-v8 @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom --cwd apps/web

# For auth package (needs better-auth test utils)
bun add -D vitest @vitest/coverage-v8 --cwd packages/auth
# better-auth/plugins is already in better-auth — no extra install needed
```

### 2. Shared Vitest config (root)

Create `vitest.shared.ts` at the repo root — individual package configs extend this:

```ts
// vitest.shared.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    passWithNoTests: true,
    reporters: ["verbose"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules", "dist", "**/*.d.ts", "**/*.config.*"],
    },
  },
});
```

### 3. Per-package vitest configs

**Logic-only package (e.g. `packages/api`):**

```ts
// packages/api/vitest.config.ts
import { mergeConfig } from "vitest/config";
import shared from "../../vitest.shared";

export default mergeConfig(shared, {
  test: {
    name: "api",
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
```

**Web app (`apps/web`) — needs jsdom:**

```ts
// apps/web/vitest.config.ts
import { mergeConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import shared from "../../vitest.shared";

export default mergeConfig(shared, {
  plugins: [react()],
  test: {
    name: "web",
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});
```

**Web test setup file:**

```ts
// apps/web/src/test/setup.ts
import "@testing-library/jest-dom";
```

### 4. Add scripts to each package's `package.json`

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

### 5. Register tasks in `turbo.json`

```json
{
  "tasks": {
    "test": {
      "outputs": ["coverage/**"]
    },
    "test:watch": {
      "cache": false,
      "persistent": true
    },
    "test:coverage": {
      "outputs": ["coverage/**"]
    }
  }
}
```

> **No `dependsOn: ["^build"]`** — packages use the internal packages pattern, exporting directly from `./src/*.ts`. There is no `dist/` to build before tests can import them.

### 6. Root convenience scripts in root `package.json`

```json
{
  "scripts": {
    "test": "turbo test",
    "test:watch": "turbo test:watch",
    "test:coverage": "turbo test:coverage"
  }
}
```

**Run specific package:**
```bash
turbo test --filter=@condomin-ia/api
turbo test --filter=web
```

---

## Testing by Layer

### Unit Tests — Pure Logic

For utilities, helpers, Zod schemas, and pure functions. No mocks needed.

```ts
// packages/api/src/lib/__tests__/file-validation.test.ts
import { describe, it, expect } from "vitest";
import { validateFileType, validateFileSize } from "../file-validation";

describe("validateFileType", () => {
  it("accepts allowed image types", () => {
    expect(validateFileType("image/png")).toBe(true);
    expect(validateFileType("image/jpeg")).toBe(true);
  });

  it("rejects disallowed types", () => {
    expect(validateFileType("application/exe")).toBe(false);
  });
});

describe("validateFileSize", () => {
  it("rejects files over the limit", () => {
    expect(validateFileSize(10 * 1024 * 1024 + 1)).toBe(false); // > 10MB
  });

  it("accepts files within limit", () => {
    expect(validateFileSize(5 * 1024 * 1024)).toBe(true);
  });
});
```

### Integration Tests — oRPC Procedures

Test procedures directly — no HTTP layer needed. Import the handler and call it with a mocked context.

```ts
// packages/api/src/routers/__tests__/posts.test.ts
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { auth } from "@condomin-ia/auth";
import { db } from "@condomin-ia/db";
import type { TestHelpers } from "better-auth/plugins";
import { postsRouter } from "../posts";

describe("postsRouter", () => {
  let test: TestHelpers;
  let userId: string;

  beforeAll(async () => {
    const ctx = await auth.$context;
    test = ctx.test;

    const user = test.createUser({ email: "posts-test@example.com" });
    await test.saveUser(user);
    userId = user.id;
  });

  afterAll(async () => {
    await test.deleteUser(userId);
  });

  it("list returns empty array for new user", async () => {
    const headers = await test.getAuthHeaders({ userId });
    const session = await auth.api.getSession({ headers });

    const result = await postsRouter.list.handler({
      input: { page: 1, pageSize: 20 },
      context: { session },
    });

    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });

  it("create adds a post", async () => {
    const headers = await test.getAuthHeaders({ userId });
    const session = await auth.api.getSession({ headers });

    const result = await postsRouter.create.handler({
      input: { title: "Hello World" },
      context: { session },
    });

    expect(result.title).toBe("Hello World");
    expect(result.userId).toBe(userId);
  });

  it("throws NOT_FOUND for unknown id", async () => {
    const headers = await test.getAuthHeaders({ userId });
    const session = await auth.api.getSession({ headers });

    await expect(
      postsRouter.get.handler({
        input: { id: crypto.randomUUID() },
        context: { session },
      })
    ).rejects.toThrow("NOT_FOUND");
  });
});
```

### Auth Integration Tests — better-auth test-utils

> **Prefer a test-only auth instance.** The Better Auth docs recommend keeping
> `testUtils()` out of the production auth config. A separate instance avoids the
> TypeScript inference caveat of conditionally spreading `testUtils()` into
> `plugins` (which can stop `ctx.test` from being inferred correctly) and lets
> you run against an **in-memory database** — no Postgres/Docker/env needed.

The auth package ships a `createTestAuth` helper
(`packages/auth/src/test-utils.ts`) that builds an isolated Better Auth instance
on `betterAuth/adapters/memory` with `testUtils()` pre-installed. It pre-seeds
the memory adapter with every table declared by the loaded plugins, so
`findMany`/`count` work before any row exists.

```ts
// packages/auth/src/plugins/my-plugin/__tests__/my-plugin.test.ts
import { beforeAll, describe, expect, it } from "vitest";
import type { TestHelpers } from "better-auth/plugins";
import { createTestAuth } from "../../../test-utils";
import { myPlugin } from "../index";

const buildAuth = () => createTestAuth([myPlugin({ /* options */ })]);
let auth: Awaited<ReturnType<typeof buildAuth>>;
let test: TestHelpers;

describe("my-plugin", () => {
  beforeAll(async () => {
    auth = await buildAuth();
    const ctx = await auth.$context;
    test = ctx.test;
  });
});
```

> Keep the `plugins` array as a literal (or via a `buildAuth` factory) — that
> preserves Better Auth's endpoint type inference, so `auth.api.<endpoint>` is
> fully typed. Passing a pre-built `BetterAuthPlugin[]` variable collapses the
> inferred `auth.api` to the base endpoints.

**Testing protected routes:**

```ts
it("getSession returns null with no headers", async () => {
  const session = await auth.api.getSession({ headers: new Headers() });
  expect(session).toBeNull();
});

it("getSession returns user for valid session", async () => {
  const user = test.createUser({ email: "session-test@example.com" });
  await test.saveUser(user);

  const headers = await test.getAuthHeaders({ userId: user.id });
  const session = await auth.api.getSession({ headers });

  expect(session?.user.id).toBe(user.id);
  expect(session?.user.email).toBe("session-test@example.com");

  await test.deleteUser(user.id);
});
```

**Testing OTP flows:**

OTP capture requires `testUtils({ captureOTP: true })` — build a dedicated
instance for it (or add the option to `createTestAuth`):

```ts
import { betterAuth } from "better-auth";
import { memoryAdapter } from "better-auth/adapters/memory";
import { testUtils, emailOTP } from "better-auth/plugins";

const db: Record<string, unknown[]> = {};
const auth = betterAuth({
  database: memoryAdapter(db),
  plugins: [testUtils({ captureOTP: true }), emailOTP({ /* ... */ })],
});
```

```ts
import { describe, it, expect, beforeAll, beforeEach } from "vitest";
import type { TestHelpers } from "better-auth/plugins";

describe("OTP verification", () => {
  let test: TestHelpers;

  beforeAll(async () => {
    const ctx = await auth.$context;
    test = ctx.test;
  });

  beforeEach(() => {
    test.clearOTPs(); // clear between tests
  });

  it("captures and verifies OTP", async () => {
    const email = "otp-test@example.com";
    const user = test.createUser({ email, emailVerified: false });
    await test.saveUser(user);

    await auth.api.sendVerificationOTP({
      body: { email, type: "email-verification" },
    });

    const otp = test.getOTP(email);
    expect(otp).toBeDefined();

    await auth.api.verifyEmail({ body: { email, otp } });

    await test.deleteUser(user.id);
  });
});
```

**Testing custom better-auth plugins:**

```ts
// packages/auth/src/plugins/audit-log/__tests__/audit-log.test.ts
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { admin, organization } from "better-auth/plugins";
import type { TestHelpers } from "better-auth/plugins";
import { createTestAuth } from "../../../test-utils";
import { auditLog } from "../index";

const buildAuth = () =>
  createTestAuth([admin(), organization(), auditLog({ adminRoles: ["admin"] })]);
let auth: Awaited<ReturnType<typeof buildAuth>>;
let test: TestHelpers;
let userId: string;

describe("audit-log plugin", () => {
  beforeAll(async () => {
    auth = await buildAuth();
    const ctx = await auth.$context;
    test = ctx.test;

    const user = test.createUser({ email: "audit-test@example.com", role: "admin" });
    await test.saveUser(user);
    userId = user.id;
  });

  afterAll(async () => {
    await test.deleteUser(userId);
  });

  it("records sign-in event", async () => {
    const headers = await test.getAuthHeaders({ userId });

    // Trigger an action that creates an audit log
    await auth.api.getSession({ headers });

    // Query the audit log via the plugin's endpoint
    const result = await auth.api.listAuditLogs({
      headers,
      query: { userId },
    });

    expect(result.events.length).toBeGreaterThan(0);
  });
});
```

### Test Utilities (`apps/web/src/test/utils.tsx`)

Shared helpers for tests that need TanStack Query context. Always import from here instead of rolling your own wrapper.

| Export | Purpose |
| --- | --- |
| `createTestQueryClient()` | Fresh `QueryClient` with retries off + `gcTime: Infinity` |
| `createQueryWrapper()` | `wrapper` for `renderHook` when the hook uses `useQuery`/`useMutation` |
| `renderWithQuery(ui, options?)` | Drop-in for `render()` — wraps with `QueryClientProvider`, also returns `queryClient` |

**Components with query hooks:**

```tsx
import { renderWithQuery } from "@/test/utils";
import { screen, waitFor } from "@testing-library/react";

vi.mock("@/utils/orpc", () => ({
  orpc: {
    users: {
      list: { queryOptions: vi.fn(() => ({ queryKey: ["users"], queryFn: async () => [] })) },
    },
  },
}));

it("renders user list", async () => {
  renderWithQuery(<UserList />);
  await waitFor(() => expect(screen.getByText("No users")).toBeInTheDocument());
});
```

**Hooks that use useQuery/useMutation:**

```tsx
import { renderHook, waitFor } from "@testing-library/react";
import { createQueryWrapper } from "@/test/utils";

it("fetches data", async () => {
  const { result } = renderHook(() => useMyHook(), {
    wrapper: createQueryWrapper(),
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data).toEqual([]);
});
```

**Inspecting query cache state:**

```tsx
it("invalidates cache on mutation", async () => {
  const { queryClient } = renderWithQuery(<MyForm />);
  // after submission...
  expect(queryClient.getQueryState(["users"])).toBeUndefined(); // invalidated
});
```

---

### Component Tests — React Testing Library

Test behavior, not implementation. Query by accessible roles/labels (never by class or test ID unless last resort).

```tsx
// apps/web/src/components/user-card/__tests__/user-card.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UserCard } from "../user-card";

const mockUser = {
  id: "1",
  name: "Alice Martin",
  email: "alice@example.com",
  role: "admin" as const,
};

describe("UserCard", () => {
  it("renders user name and email", () => {
    render(<UserCard user={mockUser} onDelete={vi.fn()} />);

    expect(screen.getByText("Alice Martin")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("calls onDelete when delete button clicked", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<UserCard user={mockUser} onDelete={onDelete} />);

    await user.click(screen.getByRole("button", { name: /delete/i }));

    expect(onDelete).toHaveBeenCalledWith("1");
  });

  it("shows admin badge for admin role", () => {
    render(<UserCard user={mockUser} onDelete={vi.fn()} />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });
});
```

### Form Tests

Test validation and submission flow — mock the mutation:

```tsx
// apps/web/src/components/forms/login/__tests__/login-container.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginContainer } from "../login-container";

// Mock the auth client
vi.mock("@/lib/auth-client", () => ({
  authClient: {
    signIn: {
      email: vi.fn().mockResolvedValue({ data: { user: { id: "1" } }, error: null }),
    },
  },
}));

describe("LoginContainer", () => {
  it("shows validation errors for empty submit", async () => {
    const user = userEvent.setup();
    render(<LoginContainer />);

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
    });
  });

  it("submits with valid credentials", async () => {
    const user = userEvent.setup();
    render(<LoginContainer />);

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(authClient.signIn.email).toHaveBeenCalledWith({
        email: "alice@example.com",
        password: "password123",
      });
    });
  });
});
```

---

## Test File Conventions

```
src/
└── components/
    └── user-card/
        ├── user-card.tsx
        ├── use-user-card.ts
        └── __tests__/
            └── user-card.test.tsx   ← co-located in __tests__ folder

packages/api/src/
└── routers/
    ├── posts.ts
    └── __tests__/
        └── posts.test.ts
```

- Test files: `*.test.ts` / `*.test.tsx`
- Test folder: `__tests__/` co-located with the code it tests
- No separate `tests/` directory at project root
- One `describe` block per component/module
- Test names describe behavior, not implementation: `"shows error when email is invalid"` not `"calls setError"`

---

## Best Practices

### What to test

| Layer | Test type | What to cover |
|---|---|---|
| Zod schemas | Unit | Valid inputs, invalid inputs, edge cases |
| Utility functions | Unit | All branches, edge cases |
| oRPC procedures | Integration | Happy path, auth checks, not found, forbidden |
| Auth flows | Integration | Sessions, OTP, custom plugin endpoints |
| Custom hooks | Unit | State changes, returned values |
| Components | Component | Renders correctly, user interactions, conditional rendering |
| Forms | Component | Validation errors, successful submission |

### What NOT to test

- Shadcn/Radix internals — they have their own tests
- TanStack Query/Router internals
- Drizzle ORM queries in isolation — test at the procedure level
- Implementation details (internal state, private methods)
- Every single CSS class

### Mocking

```ts
// Mock a module
vi.mock("@/lib/auth-client", () => ({
  authClient: { signIn: { email: vi.fn() } },
}));

// Mock orpc in component tests — use MSW or vi.mock
vi.mock("@/utils/orpc", () => ({
  orpc: {
    users: {
      list: { queryOptions: vi.fn(() => ({ queryKey: ["users"], queryFn: vi.fn() })) },
    },
  },
  queryClient: { invalidateQueries: vi.fn() },
}));

// Spy on a function
const spy = vi.spyOn(console, "error").mockImplementation(() => {});
// ... test ...
spy.mockRestore();
```

### Setup / Teardown

```ts
describe("my suite", () => {
  let test: TestHelpers;
  let userId: string;

  beforeAll(async () => {
    // Runs once — expensive setup (DB connections, auth context)
    const ctx = await auth.$context;
    test = ctx.test;
  });

  beforeEach(async () => {
    // Runs before each test — create fresh test data
    const user = test.createUser();
    await test.saveUser(user);
    userId = user.id;
  });

  afterEach(async () => {
    // Runs after each test — clean up
    await test.deleteUser(userId);
  });
});
```

### Query Priority (Testing Library)

Always use the most accessible query:

```ts
// ✅ Priority order — use the first one that works
screen.getByRole("button", { name: /submit/i })   // 1. Role (best)
screen.getByLabelText(/email/i)                    // 2. Label (forms)
screen.getByPlaceholderText(/search/i)             // 3. Placeholder
screen.getByText(/welcome/i)                       // 4. Text content
screen.getByAltText(/avatar/i)                     // 5. Alt text
screen.getByTestId("submit-button")                // 6. data-testid (last resort)

// ❌ Never query by class name or internal implementation
document.querySelector(".submit-btn")
```

### Async Testing

```ts
// ✅ Always await user events
const user = userEvent.setup();
await user.click(screen.getByRole("button"));
await user.type(screen.getByLabelText(/email/i), "test@example.com");

// ✅ Use waitFor for async state changes
await waitFor(() => {
  expect(screen.getByText("Success")).toBeInTheDocument();
});

// ✅ findBy* queries are async by default (combines getBy + waitFor)
const element = await screen.findByText("Loaded!");
```

---

## CI Integration

Add to your GitHub Actions workflow:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: bun test

- name: Upload coverage
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage/coverage-final.json
```

The `turbo test` command only re-runs tests for packages that have changed since the last run — Turborepo caching makes CI fast.