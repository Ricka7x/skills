# Data Tables (TanStack Table + Filters + Pagination)

Pattern for the tables used all over the app. Covers the headless table layer, and the decision of **backend vs local** pagination / search / filtering.

## Stack

- **TanStack Table** (`@tanstack/react-table`) — headless table logic: column defs, sorting, row selection, visibility, virtualization. It does **not** render anything; you render rows yourself.
- **shadcn/ui table components** (or base-ui) for the presentational layer — `<Table>`, `<TableHeader>`, `<TableRow>`, `<TableCell>`.
- **Data source:** oRPC + TanStack Query — the table never talks to the server directly.

---

## The Big Decision: Backend vs Local

| Criterion | Local (client-side) | Backend (server-side) |
|---|---|---|
| Dataset size | < ~500 rows, bounded | Large / growing |
| Data source | Already in memory (one small list) | Cross-org, filtered, searched |
| Freshness | Static-ish, refetched wholesale | Changes frequently |
| Search scope | Few fields, in-memory | Many columns, arbitrary text |
| Pagination | UI-only slice | Real DB pagination + accurate `total` |
| `total` / export counts | Not needed | Must be correct |
| Best for | Lookup options, settings lists, reference data, recently-loaded sublists | Main entity collections (payments, expenses, incidents, members, …) |

**Default rule:** real entity collections → **backend**. Go local only when the whole dataset is already loaded in memory and will stay small.

**Hybrid (when it makes sense):** let the backend filter (search + status + org scope), then paginate/sort locally on the filtered result. Acceptable when the filtered set is bounded (< ~1–2k rows) and users filter before paging. Do **not** do this for unbounded tables.

---

## Backend Tables (recommended for real data)

### Procedure shape

`list` returns `{ items, total }` with offset pagination, or `{ items, nextCursor, hasMore }` with cursor pagination for large/frequently-appended tables. Full patterns in [PROCEDURES.md](PROCEDURES.md).

> `total` **must** come from a real count query with the same filters — never `items.length` (that is the page size, not the total).

### Input schema (filtering, search, sorting)

Allowlist everything. Never build filters from arbitrary client strings.

```ts
const sortableFields = ["createdAt", "amount", "status", "name"] as const;
const filterableStatuses = ["pending", "approved", "rejected"] as const;

export const listSchema = z.object({
  // Pagination
  page: z.int().min(1).default(1),
  pageSize: z.int().min(1).max(100).default(20),

  // Filtering — enum / typed values only
  status: z.enum(filterableStatuses).optional(),
  orgId: z.string(), // always org-scoped (see MULTI-TENANCY.md)

  // Search — one debounced query, matched against allowlisted columns
  search: z.string().max(200).optional(),

  // Sorting — allowlisted column + direction
  sortBy: z.enum(sortableFields).default("createdAt"),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
});
```

Rules:

- `search` is **one** debounced free-text field, not a filter per column.
- Structural filters (status, type, org) are **typed enums**, not free text.
- `sortBy` is an `as const` enum of real column names — never client-supplied strings.
- `pageSize` is capped (`max(100)`) so the client can't request unbounded rows.

### Handler

```ts
list: protectedProcedure
  .input(listSchema)
  .output(z.object({
    items: z.array(paymentSchema),
    total: z.int(),
  }))
  .handler(async ({ input, context }) => {
    await assertCapability(membership, "payments:read"); // see MULTI-TENANCY.md

    const conditions = [
      eq(payments.orgId, input.orgId),
      input.status ? eq(payments.status, input.status) : undefined,
      input.search
        ? or(
            ilike(payments.reference, `%${input.search}%`),
            ilike(payments.payerName, `%${input.search}%`),
          )
        : undefined,
    ];

    const where = and(...conditions);
    const offset = (input.page - 1) * input.pageSize;
    const orderBy = input.sortOrder === "asc" ? asc : desc;

    const [items, total] = await Promise.all([
      db.query.payments.findMany({ where, orderBy: orderBy(payments[input.sortBy]), limit: input.pageSize, offset }),
      db.select({ count: count() }).from(payments).where(where),
    ]);

    return { items, total: total[0].count };
  }),
```

- Fetch rows and the **filtered** count in parallel (`Promise.all`).
- Capability check runs before any query.

---

## Client Wiring

### URL is the source of truth for page/filters

Page, search, and active filters live in **TanStack Router search params** (`validateSearch` + `useSearch` / `useNavigate`). This gives shareable, refresh-safe, back-button-aware table state — no local state, no `nuqs`.

```tsx
const tableSearchSchema = z.object({
  page: z.int().min(1).default(1),
  pageSize: z.int().min(1).max(100).default(20),
  search: z.string().optional(),
  status: z.enum(["pending", "approved", "rejected"]).optional(),
  sortBy: z.enum(["createdAt", "amount", "status", "name"]).default("createdAt"),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
});

export const Route = createFileRoute("/(app)/payments")({
  validateSearch: tableSearchSchema,
  loader: ({ context, search }) => {
    context.queryClient.ensureQueryData(
      context.orpc.payments.list.queryOptions({ input: search }),
    );
  },
  component: PaymentsPage,
});
```

- Debounce `search` writes into the URL (e.g. `useDebouncedCallback`); page/sort writes are immediate.
- Prefetch in the route `loader` so the first page renders instantly.
- Changing `search` should reset `page` back to 1.

### TanStack Table wiring

```tsx
import { getCoreRowModel, getSortedRowModel, useReactTable } from "@tanstack/react-table";

function PaymentsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { data } = useQuery(orpc.payments.list.queryOptions({ input: search }));

  const columns = useMemo<ColumnDef<Payment>[]>(() => [
    { accessorKey: "reference", header: "Reference" },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "amount",
      header: "Amount",
      cell: ({ row }) => formatCurrency(row.original.amount),
    },
    // ...sortable columns set sortable: true
  ], []);

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    state: { sorting: search.sortBy ? [{ id: search.sortBy, desc: search.sortOrder === "desc" }] : [] },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualSorting: true,  // sorting is server-side — table just reports intent
    onSortingChange: (updater) => {
      const sorting = updater instanceof Function ? updater(table.getState().sorting) : updater;
      const s = sorting[0];
      void navigate({ search: { ...search, sortBy: s?.id ?? "createdAt", sortOrder: s?.desc ? "desc" : "asc", page: 1 } });
    },
  });

  return <PaymentsTable table={table} total={data?.total ?? 0} />;
}
```

Rules:

- `manualSorting: true` / `manualPagination: true` — the table **reports** sort/page changes; the server does the work.
- Column defs are typed with the procedure's output item type (`z.infer<typeof paymentSchema>`).
- Row selection and column visibility are client-only concerns — keep them in TanStack Table state.

### Pagination controls

Driven by `total` from the server:

```tsx
const pageCount = Math.ceil(total / pageSize);

<TablePagination
  page={page}
  pageCount={pageCount}
  onPageChange={(page) => void navigate({ search: { ...search, page } })}
/>
```

---

## Local Tables

Only for small, already-loaded data (lookup options, settings, sublists of a parent entity).

- Filter with `array.filter` over the in-memory array; sort with `array.sort` / TanStack Table's client models.
- No `page`/`pageSize`/`total` in the procedure — return the whole list.
- If the list grows past the threshold, **migrate it to a backend table** (add pagination to the procedure + URL params).

---

## Anti-Patterns

- ❌ `total: items.length` — wrong count; always a real count query
- ❌ Unbounded client-supplied `sortBy`/`filterField` strings — allowlist with enums
- ❌ Server-side pagination with client-side `getPaginationRowModel` — pick one side
- ❌ Duplicating `page`/`search` in both URL params and local state — URL only
- ❌ `nuqs` — TanStack Router search params already cover URL state, typed
- ❌ Fetching the full table just to filter locally when it can grow
- ❌ Debouncing on every keystroke without canceling in-flight requests
- ❌ Page size above 100 without a specific, documented reason
