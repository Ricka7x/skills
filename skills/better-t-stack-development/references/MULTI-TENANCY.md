# Multi-Tenancy & Permissions (org-scoped data)

This stack is multi-tenant: **every domain model belongs to an organization**, and access is granted per membership with role-based capabilities.

## Data Model

```ts
// Every domain table carries an org FK — indexed, cascaded
orgId: text("org_id")
  .notNull()
  .references(() => organization.id, { onDelete: "cascade" }),

// Better Auth's organization plugin provides:
// organization, member (organization_member) tables + membership endpoints
```

Rules:

- **All new models belong to an org.** A table without `orgId` is the exception, not the rule (e.g. system-wide lookup tables).
- Index `orgId` on every table — every list query filters by it (DATABASE.md).
- Use the built-in `organization` plugin for memberships — don't reinvent org membership.

## Two Sources of "Org"

There are two `orgId`s in play, and they serve different purposes:

| Source | Purpose | Trust level |
|---|---|---|
| **Session** (server-derived) | *Authorization* — the org the user is actually in | **Trusted — authorize from this** |
| **Input** `orgId` (client-sent) | *Cache isolation* — lands in the oRPC query key (QUERY_INVALIDATION.md) | **Untrusted — never authorize from this** |

**Never authorize a request based on `input.orgId`.** A client can pass any org id. Validate membership from the session, then use the session's org for queries. `input.orgId` is for the query key so React Query scopes the cache per org.

## Roles & Capabilities

Memberships carry a role; roles map to **capabilities** (per-resource × per-action). Prefer capability checks over role string checks in handlers — they survive role renames and support granular permissions.

```ts
// Convention (per project): a permission/capability type
type Permission = `${Resource}:${Action}`; // e.g. "payments:read", "members:manage"

const OWNER_ROLE = "owner"; // admins of the org
```

Handler flow:

1. `getMembership(context)` — resolve the user's membership for the active org (from session).
2. `assertCapability(membership, "payments:read")` — throw `FORBIDDEN` if the role lacks the capability.
3. `assertOwnership(membership, row)` — for row-level access (e.g. property-scoped rows), verify the row belongs to what the user can see.

```ts
list: protectedProcedure
  .input(z.object({ orgId: z.string(), page: z.int().min(1).default(1) }))
  .handler(async ({ input, context }) => {
    // 1. Resolve membership from the SESSION (never from input.orgId)
    const membership = await getMembership(context);
    // 2. Capability check
    assertCapability(membership, "payments:read");
    // 3. Scope the query to the user's org
    return db.query.payments.findMany({
      where: eq(payments.orgId, membership.organizationId),
    });
  }),
```

- Keep capability/ownership checks in **shared helpers** (e.g. `packages/api/src/community-access.ts`) — not copy-pasted per router.
- Batch handlers must run ownership checks **per item**, not just once.

## Active Org & Switching

- Better Auth persists the "active org" on the session (`last-active-org` plugin keeps it across sessions).
- `authClient.useActiveOrganization()` on the client; the org id flows into every org-scoped oRPC input → the query key → automatic cache isolation on switch (QUERY_INVALIDATION.md).
- After org **structure** mutations (create/leave/delete org, membership changes), invalidate both the Better Auth namespaces (`["organizations"]`) and all org-scoped oRPC queries.

## Visibility Scopes

Some rows are visible org-wide, others are scoped to a subset (e.g. one property). Convention:

- `org_wide` — visible to every member with the capability.
- `property_scoped` — visible only to members who can access that property.

Encode this in a helper (e.g. `getVisiblePropertyIds(membership)` returning a list or `"all"`) and apply it as a `inArray` condition. Don't leak property ids the user can't see.

## Invitations

- Use the organization plugin's invite endpoints (`authClient.organization.inviteMember` / accept flow).
- Accept-invitation page lives under `(public)/accept-invitation` (ROUTING.md).
- After accept, refresh the active-org data.

## Anti-Patterns

- ❌ Authorizing from `input.orgId` instead of the session
- ❌ Capability checks in only some handlers — every handler that fetches by id runs them
- ❌ Returning rows from other orgs because the `WHERE` forgot `orgId`
- ❌ Role-string checks scattered in handlers instead of capability helpers
- ❌ Forgetting to index `orgId`
- ❌ Missing invalidation after org membership changes (QUERY_INVALIDATION.md)
