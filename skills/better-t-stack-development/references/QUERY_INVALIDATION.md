# Query Invalidation: oRPC + Better Auth

This project has two query systems sharing the same `queryClient`. Understanding how they interact is essential for multi-tenant (org-scoped) features.

## The Two Namespaces

| System | Key shape | Example |
|---|---|---|
| Better Auth (manual `useQuery`) | String tuples | `["organizations"]` |
| oRPC (`orpc.*`) | Structured tuples | `[["invoices","list"], {input:{orgId:"…"}}]` |

They don't conflict, but need a deliberate coordination strategy.

---

## The Core Pattern: `orgId` in oRPC Inputs

Every oRPC procedure that fetches org-scoped data must include `orgId` in its input. The oRPC query key includes the input — so changing orgs changes the key, which React Query treats as a different query and fetches fresh data automatically.

**Server (procedure):**

```ts
// packages/api/src/routers/invoices.ts
export const invoicesRouter = {
  list: protectedProcedure
    .input(z.object({
      orgId: z.string(),
      page: z.int().min(1).default(1),
      pageSize: z.int().min(1).max(100).default(20),
    }))
    .output(z.object({ items: z.array(invoiceSchema), total: z.int() }))
    .handler(async ({ input, context }) => {
      // Still validate org membership on the server
      await assertOrgMember(context.session.user.id, input.orgId);
      return db.query.invoices.findMany({ where: eq(invoices.orgId, input.orgId) });
    }),
};
```

**Client (query):**

```ts
const { data: activeOrg } = authClient.useActiveOrganization();

const { data } = useQuery(
  orpc.invoices.list.queryOptions({
    input: { orgId: activeOrg!.id, page: 1, pageSize: 20 },
    enabled: !!activeOrg,
  })
);
```

When the user switches org, `activeOrg.id` changes → the query key changes → auto-refetch. **No explicit invalidation needed for org switches.**

---

## The `orgProcedure` Middleware (Recommended)

Add a middleware to `packages/api/src/index.ts` that reads `activeOrganizationId` from the Better Auth session and injects it into context. This keeps org validation on the server without requiring every handler to do it manually.

```ts
// packages/api/src/index.ts
import { auth } from "@condomin-ia/auth";

const requireOrg = o.middleware(async ({ context, next }) => {
  if (!context.session?.user) throw new ORPCError("UNAUTHORIZED");

  const session = context.session.session as Record<string, unknown>;
  const orgId = session.activeOrganizationId as string | undefined;
  if (!orgId) throw new ORPCError("FORBIDDEN", { message: "No active organization" });

  // Verify user actually belongs to this org
  const member = await auth.api.getActiveMember({ headers: ... }); // or direct DB check
  if (!member) throw new ORPCError("FORBIDDEN");

  return await next({ context: { session: context.session, orgId } });
});

export const orgProcedure = publicProcedure.use(requireOrg);
```

With `orgProcedure`, handlers receive `context.orgId` directly — no need to pass it in every handler body. But **you still pass `orgId` as input from the client** so it ends up in the query key for cache isolation.

> **Never authorize from `input.orgId`.** It exists for the query key only. Authorization always derives from the session (middleware/`context.orgId`) — a client can send any `orgId`. See [MULTI-TENANCY.md](MULTI-TENANCY.md).

```ts
// Server handler — uses context.orgId (validated server-side)
export const invoicesRouter = {
  list: orgProcedure
    .input(z.object({ orgId: z.string(), page: z.int().min(1).default(1) }))
    .handler(async ({ input, context }) => {
      // context.orgId is validated by middleware
      // input.orgId is used only for the client-side query key
      return db.query.invoices.findMany({ where: eq(invoices.orgId, context.orgId) });
    }),
};
```

---

## When to Explicitly Invalidate

### oRPC mutations within the same org

```ts
const mutation = useMutation(
  orpc.invoices.create.mutationOptions({
    onSuccess: () => {
      // Invalidate all invoices.list queries (all orgs, all pages)
      queryClient.invalidateQueries({ queryKey: orpc.invoices.list.key() });

      // Or scope to the current org only
      queryClient.invalidateQueries({
        queryKey: orpc.invoices.list.key({ input: { orgId: activeOrg.id } }),
      });
    },
  })
);
```

### Better Auth mutations that affect org structure

After `authClient.organization.create/leave/delete`, invalidate both namespaces:

```ts
onSuccess: () => {
  // Better Auth queries (string keys)
  queryClient.invalidateQueries({ queryKey: ["organizations"] });
  queryClient.invalidateQueries({ queryKey: ["orgMembersSummary"] });

  // All oRPC org-scoped data
  queryClient.invalidateQueries({ queryKey: orpc.invoices.list.key() });
  // Or nuke everything if access scope fundamentally changed
  queryClient.invalidateQueries();
}
```

---

## Invalidation Cheat Sheet

| Scenario | Action |
|---|---|
| User switches active org | No invalidation — `activeOrg.id` in key changes automatically |
| oRPC mutation changes data within same org | `queryClient.invalidateQueries({ queryKey: orpc.router.proc.key() })` |
| Better Auth creates/deletes/leaves an org | Invalidate `["organizations"]` + all relevant `orpc.*.key()` |
| Active org membership changes | Consider `queryClient.invalidateQueries()` (full cache wipe) |

---

## Anti-Patterns

- Don't omit `orgId` from oRPC inputs for org-scoped data — without it, all orgs share a cache entry and switching orgs shows stale data
- Don't put `orgId` only in query params without it flowing through the key — `useQuery({ queryKey: ["invoices"] })` with `orgId` only in the `queryFn` body breaks isolation
- Don't trust `input.orgId` on the server without validating membership — always verify via session or middleware
