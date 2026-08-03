---
name: better-t-stack-development
description: >
  Full-stack development patterns for the Better-T-Stack setup.
  Use this skill whenever working on any project in this stack — adding a feature,
  creating a route, building a form, writing a procedure, defining a schema,
  scaffolding a new package, reviewing code, or writing tests. Triggers on: new feature,
  new page, new form, new route, new endpoint, new procedure, new table, new package,
  new component, new hook, build a component, write a test, add a test, vitest, testing,
  test setup, better-auth plugin, auth plugin, custom plugin, oRPC, TanStack, better-auth,
  Drizzle, Hono, Expo, React 19, shadcn, monorepo, Turborepo, or any coding task in this stack.
---

# Better-T-Stack Development

Opinionated full-stack setup built on top of [Better-T-Stack](https://better-t-stack.dev). This skill captures the concrete decisions, patterns, and conventions used across projects — not the generic docs.

## Stack at a Glance

| Layer | Choice |
|---|---|
| Monorepo | Turborepo + Bun workspaces |
| Package manager | **Bun** (not npm/pnpm) |
| Web frontend | React 19 + Vite + TanStack Router |
| Native | Expo 54 + Expo Router |
| Backend | Hono (Bun runtime) |
| API | oRPC + TanStack Query |
| Auth | better-auth + custom plugins |
| Database | Drizzle ORM + PostgreSQL |
| Validation | Zod 4 (everywhere) |
| Web UI | shadcn/ui + base-ui (migrating from Radix) |
| Native UI | heroui-native + Tailwind (via uniwind) |
| Email | Resend + React Email |
| Payments | Stripe |
| Linting/Formatting | **Ultracite** (Biome under the hood) |
| AI | Vercel AI SDK + Google Gemini |

---

## Monorepo Structure

```
apps/
  web/        → Vite SPA (React 19, TanStack Router, shadcn/ui)
  native/     → Expo 54 (Expo Router, heroui-native)
  server/     → Hono API server (Bun runtime)
  fumadocs/   → Next.js docs site

packages/
  api/        → oRPC router, procedures, context, middleware
  auth/       → better-auth instance + custom plugins
  db/         → Drizzle schema + migrations (PostgreSQL)
  env/        → Typed env validation (server / web / native)
  payments/   → Stripe client helpers
  transactional/ → Resend email templates (React Email)
  config/     → Shared tsconfig base
```

**Common commands:**
```bash
bun dev               # All apps
bun dev:web           # Web only
bun dev:native        # Expo only
bun dev:server        # Server only
bun db:generate       # Generate Drizzle migrations
bun db:push           # Push schema to DB (dev only)
bun db:studio         # Open Drizzle Studio
bun x ultracite fix   # Format + lint all files
bun x ultracite check # Check without fixing
```

---

## Code Style (Ultracite / Biome)

Always run `bun x ultracite fix` before committing. Key rules enforced:

- `const` by default, `let` only when reassignment is needed — never `var`
- `for...of` over `.forEach()` and indexed loops
- Arrow functions for callbacks
- Optional chaining (`?.`) and nullish coalescing (`??`)
- Destructuring for object/array assignments
- `async/await` over promise chains
- Early returns over nested conditionals
- No `console.log` in production code — use logger
- No barrel files (`index.ts` that re-exports everything)
- No `any` — use `unknown` when type is genuinely unknown
- `satisfies` over type assertions
- React 19: use ref as prop, no `forwardRef`

---

## What to Read for Each Task

| Task | Reference |
|---|---|
| Building a component, hook, or UI feature | [references/COMPONENTS.md](references/COMPONENTS.md) |
| Setting up or writing tests | [references/TESTING.md](references/TESTING.md) |
| Building a custom better-auth plugin | [references/BETTER-AUTH-PLUGIN.md](references/BETTER-AUTH-PLUGIN.md) |
| Adding a new API procedure / router | [references/PROCEDURES.md](references/PROCEDURES.md) |
| Writing or modifying a DB schema | [references/DATABASE.md](references/DATABASE.md) |
| Building a new form | [references/FORMS.md](references/FORMS.md) |
| Adding a new web route / page | [references/ROUTING.md](references/ROUTING.md) |
| Working on the Expo native app | [references/NATIVE.md](references/NATIVE.md) |
| Query invalidation across oRPC + Better Auth (multi-tenant) | [references/QUERY_INVALIDATION.md](references/QUERY_INVALIDATION.md) |
| Migrating a component from Radix UI to Base UI | [references/BASE_UI_MIGRATION.md](references/BASE_UI_MIGRATION.md) |

---

## Key Architectural Decisions

### oRPC over tRPC
oRPC is used for the type-safe API layer. It has first-class TanStack Query integration via `@orpc/tanstack-query` and generates typed client utils directly from the router. Never call the API with raw `fetch` for app data — always go through the oRPC client.

### base-ui replacing Radix
The web app is migrating from shadcn (Radix) to base-ui components. New components use `@base-ui/react`. The custom `Field`, `FieldLabel`, `FieldError`, `FieldGroup`, `FieldDescription` components in `apps/web/src/components/ui/field.tsx` are the canonical form building blocks.

### Zod 4
All projects use Zod 4 (`zod@^4`). API uses `@orpc/zod` for schema integration. Use `z.int()` not `z.number().int()`, and `z.uuid()` not `z.string().uuid()`.

### String IDs everywhere
All DB tables use `text("id").primaryKey()` — no auto-increment integers. IDs are generated by better-auth (for auth tables) or `crypto.randomUUID()` elsewhere.

### Multi-tenancy (org-scoped data)
All new models belong to an organization. Every oRPC procedure that fetches org-scoped data must include `orgId` in its input — this puts the org in the query key, giving React Query automatic cache isolation per org. Use `orgProcedure` middleware to validate org membership server-side. See [references/QUERY_INVALIDATION.md](references/QUERY_INVALIDATION.md) for the full pattern including when to explicitly invalidate after Better Auth org mutations.

### Turborepo catalog
Shared dependency versions are pinned in the root `package.json` `catalog` field. When adding a shared dep, add it to the catalog first, then reference it as `catalog:` in individual packages.