# Naming Conventions

The canonical source for naming across the stack. Rules here apply everywhere; per-layer references may repeat them but this file is authoritative — follow it when the other files are silent.

## Quick Reference

| Scope | Style | Example |
|---|---|---|
| Files & folders | kebab-case | `api-key-form.tsx`, `use-login-form.ts`, `user-card/` |
| Schema files | kebab-case + `.schema.ts` suffix | `login.schema.ts`, `api-key.schema.ts` |
| Test files | kebab-case + `.test.ts`/`.test.tsx` | `posts.test.ts` |
| Component symbols | PascalCase | `StatusBadge`, `AppHeader` |
| Hook symbols | camelCase, `use` prefix | `useIsMobile`, `useUploadFile` |
| Functions / variables / params | camelCase | `createTestQueryClient`, `queryClient` |
| Types / interfaces | PascalCase | `StatusType`, `ApiKeyFormValues` |
| Component prop types | PascalCase + `Props` suffix | `StatusBadgeProps` |
| Enum members | PascalCase | `StatusType.Active` |
| DB tables | snake_case, singular | `post`, `organization_member` |
| DB columns | snake_case → camelCase in TS | `user_id` → `userId` |
| FK columns | `<parent>Id` | `orgId`, `userId`, `postId` |
| DB indexes | `<table>_<column>_idx` | `post_userId_idx` |
| Router file vars | `<domain>Router` | `paymentsRouter` |
| Router keys in `appRouter` | camelCase, plural, no `Router` suffix | `users`, `payments` |
| Procedures | CRUD verbs + domain verbs | `list`, `get`, `create`, `publish`, `archive` |
| Schemas | `<entity>Schema` + derived | `userSchema`, `createUserSchema` |
| Plugin endpoint paths | kebab-case, plugin-prefixed | `/audit-log/list-entries` |
| Public env vars | `VITE_` (web) / `EXPO_PUBLIC_` (native) | `VITE_SERVER_URL` |
| IDs | `text("id").primaryKey()`, UUID | — |

## Files & Folders

- Files and folders are **kebab-case** (`api-key-form.tsx`, `user-card/`, `use-user-card.ts`).
- Schema files end in `.schema.ts`; test files in `.test.ts` / `.test.tsx` (co-located in `__tests__/`).
- Hooks live in `use-*.ts` files (`use-upload-file.ts`).

## TypeScript Symbols

- **Components:** PascalCase (`StatusBadge`, `AppHeader`).
- **Hooks:** camelCase with a `use` prefix (`useIsMobile`, `useUploadFile`).
- **Functions, variables, params, keys:** camelCase (`paymentsRouter`, `queryClient`, `customerId`).
- **Types, interfaces, type params:** PascalCase (`StatusType`, `StatusBadgeProps`).
- **Enum members:** PascalCase (`Active`, `Pending`).
- **Constants:** camelCase for module constants; the thing they name, not the type (`isMobile`, not `boolean`).

## Database

- **Tables:** snake_case, **singular** (`post`, `organization_member`, `user`).
- **Columns:** snake_case in SQL, camelCase in TS via Drizzle mapping (`user_id` → `userId`).
- **Foreign keys:** `<parent>Id` (`orgId`, `userId`, `postId`), referenced and indexed.
- **Indexes:** `<table>_<column>_idx` (`post_userId_idx`).
- **IDs:** `text("id").primaryKey()`; timestamps `created_at` / `updated_at`.

## API

- **Router file vars:** `<domain>Router` (`paymentsRouter`).
- **Router keys in `appRouter`:** camelCase, plural, **no `Router` suffix** (`users: usersRouter`).
- **Procedures:** standard CRUD verbs — `list`, `get`, `create`, `update`, `delete` — plus domain verbs for actions (`publish`, `archive`, `approve`, `reject`, `verify`). No `getAll`/`getOne`/`createNew`.
- **Schemas:** `<entity>Schema` for the entity, `create<Entity>Schema` (omit `id`/`createdAt`), `update<Entity>Schema` (partial), `paginated<Entity>Schema` for list responses.
- **Plugin endpoint paths:** kebab-case, plugin-prefixed (`/audit-log/list-entries`) — client converts to camelCase (`authClient.auditLog.listEntries()`).

## Environment Variables

- Web public: `VITE_*`. Native public: `EXPO_PUBLIC_*`. Server: no prefix.
- Keys match between `packages/env/src/*.ts`, `.env.example`, and CI (see [ENV.md](ENV.md)).

## Where Each Layer Is Defined

| Naming area | Defined in more detail in |
|---|---|
| Files, symbols, components | [COMPONENTS.md](COMPONENTS.md) |
| Database | [DATABASE.md](DATABASE.md) |
| Procedures, routers, schemas | [PROCEDURES.md](PROCEDURES.md) |
| Plugin endpoints | [BETTER-AUTH-PLUGIN.md](BETTER-AUTH-PLUGIN.md) |
| Env vars | [ENV.md](ENV.md) |
