# OpenAPI & API Docs

oRPC generates an **OpenAPI spec** from your routers, served by the Hono server, and surfaced in the docs site (`apps/fumadocs`).

## How It Works

- oRPC contracts/routers in `packages/api` are introspectable — the spec is derived from input/output schemas, not hand-written.
- The Hono server mounts oRPC at `/rpc` and the generated OpenAPI UI at `/api-reference`.
- Auth lives separately at `/api/auth/*` (better-auth's own routes).

## Conventions

- **Schemas are the docs.** Clean, well-named Zod schemas (PROCEDURES.md) produce clean specs — no separate spec authoring.
- Give procedures clear names (`payments.list`, not `getStuff`) — they become operationIds and route paths.
- Provide human-readable `message`s on `ORPCError`s — they surface in error responses shown by generated docs/tools.
- Keep the spec mount **server-side only** — never expose `/api-reference` or the spec publicly in production without auth if it leaks internal shape.

## Docs Site (Fumadocs)

`apps/fumadocs` is the documentation site:

- Write human docs alongside the API reference — procedures generate the reference, Fumadocs pages explain workflows (multi-tenant auth, uploads, billing).
- Reference the generated endpoints from Fumadocs pages rather than duplicating request/response shapes by hand.

## When You Change the API

- Procedure shape changes are reflected automatically in the spec.
- Re-run the docs build / type generation if the site pre-generates snippets (`apps/fumadocs`).
- Breaking contract changes (renames, removed fields) ripple into the spec and the docs site — coordinate the update.

## Anti-Patterns

- ❌ Hand-maintaining an OpenAPI file that oRPC already generates
- ❌ Vague procedure names that produce ambiguous operationIds
- ❌ Exposing `/api-reference` in production without gating
- ❌ Duplicating request/response shapes in Fumadocs pages
