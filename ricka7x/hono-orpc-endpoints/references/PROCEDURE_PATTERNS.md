# Procedure Patterns

Common patterns for designing oRPC procedures following REST-like conventions.

## CRUD Operations

### List (GET Collection)

**Purpose:** Retrieve multiple resources with pagination and filtering.

```typescript
import { z } from "zod"
import { protectedProcedure } from "../index"

list: protectedProcedure
  .input(z.object({
    // Pagination
    limit: z.int().min(1).max(100).optional().default(20),
    cursor: z.string().optional(), // For cursor-based
    page: z.int().min(1).optional().default(1), // For offset-based
    
    // Filtering
    status: z.enum(["active", "archived"]).optional(),
    category: z.string().optional(),
    search: z.string().optional(),
    
    // Sorting
    sortBy: z.enum(["createdAt", "updatedAt", "name"]).optional().default("createdAt"),
    sortOrder: z.enum(["asc", "desc"]).optional().default("desc"),
  }))
  .output(z.object({
    items: z.array(itemSchema),
    total: z.int(),
    hasMore: z.boolean(),
    nextCursor: z.string().optional(),
  }))
  .handler(async ({ input, context }) => {
    // Implementation
  })
```

**Best Practices:**
- Always paginate list endpoints
- Default to sensible page size (20-50 items)
- Limit maximum page size (100 items)
- Return total count for UI pagination
- Support sorting by common fields
- Add search/filter parameters as needed

### Get (GET Single Resource)

**Purpose:** Retrieve a specific resource by ID.

```typescript
get: protectedProcedure
  .input(z.object({
    id: z.uuid(),
  }))
  .output(itemSchema)
  .handler(async ({ input }) => {
    const item = await db.query.items.findFirst({
      where: eq(items.id, input.id),
    })

    if (!item) {
      throw new ORPCError("NOT_FOUND", {
        message: "Item not found",
      })
    }

    return item
  })
```

**Best Practices:**
- Always validate ID format (z.uuid())
- Throw NOT_FOUND if resource doesn't exist
- Check permissions before returning data
- Include related data if commonly needed

### Create (POST)

**Purpose:** Create a new resource.

```typescript
create: protectedProcedure
  .input(createItemSchema) // Omit id, createdAt, updatedAt
  .output(itemSchema)
  .handler(async ({ input, context }) => {
    // Validate business rules
    if (input.price < 0) {
      throw new ORPCError("BAD_REQUEST", {
        message: "Price must be positive",
      })
    }

    // Check permissions
    const canCreate = await checkPermission(context.session.user, "items:create")
    if (!canCreate) {
      throw new ORPCError("FORBIDDEN", {
        message: "You don't have permission to create items",
      })
    }

    const [item] = await db.insert(items).values({
      ...input,
      userId: context.session.user.id,
      createdAt: new Date(),
      updatedAt: new Date(),
    }).returning()

    return item
  })
```

**Best Practices:**
- Validate all required fields in schema
- Validate business rules in handler
- Set generated fields (id, timestamps) automatically
- Associate resource with authenticated user
- Return created resource
- Check creation permissions

### Update (PATCH)

**Purpose:** Update specific fields of an existing resource.

```typescript
update: protectedProcedure
  .input(z.object({
    id: z.uuid(),
    data: updateItemSchema, // Partial schema
  }))
  .output(itemSchema)
  .handler(async ({ input, context }) => {
    // Check resource exists
    const existing = await db.query.items.findFirst({
      where: eq(items.id, input.id),
    })

    if (!existing) {
      throw new ORPCError("NOT_FOUND")
    }

    // Check ownership/permissions
    if (existing.userId !== context.session.user.id) {
      throw new ORPCError("FORBIDDEN", {
        message: "You can only update your own items",
      })
    }

    const [updated] = await db.update(items)
      .set({
        ...input.data,
        updatedAt: new Date(),
      })
      .where(eq(items.id, input.id))
      .returning()

    return updated
  })
```

**Best Practices:**
- Use partial schema for update (not all fields required)
- Verify resource exists before updating
- Check ownership/permissions
- Update modifiedAt timestamp
- Return updated resource
- Consider optimistic locking for concurrent updates

### Delete (DELETE)

**Purpose:** Remove a resource.

```typescript
delete: protectedProcedure
  .input(z.object({
    id: z.uuid(),
  }))
  .output(z.object({
    success: z.boolean(),
  }))
  .handler(async ({ input, context }) => {
    // Check resource exists
    const existing = await db.query.items.findFirst({
      where: eq(items.id, input.id),
    })

    if (!existing) {
      throw new ORPCError("NOT_FOUND")
    }

    // Check permissions
    if (existing.userId !== context.session.user.id) {
      throw new ORPCError("FORBIDDEN")
    }

    // Soft delete (recommended)
    await db.update(items)
      .set({ deletedAt: new Date() })
      .where(eq(items.id, input.id))

    // OR hard delete
    // await db.delete(items).where(eq(items.id, input.id))

    return { success: true }
  })
```

**Best Practices:**
- Verify resource exists
- Check delete permissions
- Prefer soft deletes (set deletedAt)
- Consider cascade deletes for related data
- Return success confirmation
- Log deletion for audit trail

## Pagination Patterns

### Cursor-Based Pagination (Recommended)

Best for infinite scroll and real-time data.

```typescript
list: protectedProcedure
  .input(z.object({
    limit: z.int().min(1).max(100).optional().default(20),
    cursor: z.string().optional(), // ID of last item from previous page
  }))
  .output(z.object({
    items: z.array(itemSchema),
    nextCursor: z.string().optional(),
    hasMore: z.boolean(),
  }))
  .handler(async ({ input }) => {
    // Fetch limit + 1 to check if more exist
    const items = await db.query.items.findMany({
      where: input.cursor
        ? gt(items.id, input.cursor)
        : undefined,
      orderBy: desc(items.createdAt),
      limit: input.limit + 1,
    })

    const hasMore = items.length > input.limit
    const data = hasMore ? items.slice(0, -1) : items
    const nextCursor = hasMore ? data[data.length - 1].id : undefined

    return {
      items: data,
      nextCursor,
      hasMore,
    }
  })
```

**Pros:**
- Efficient for large datasets
- Handles real-time updates well
- No skipped/duplicate items
- Good for infinite scroll

**Cons:**
- Can't jump to arbitrary page
- No total count
- More complex implementation

### Offset-Based Pagination

Best for traditional page navigation.

```typescript
list: protectedProcedure
  .input(z.object({
    page: z.int().min(1).optional().default(1),
    pageSize: z.int().min(1).max(100).optional().default(20),
  }))
  .output(z.object({
    items: z.array(itemSchema),
    total: z.int(),
    page: z.int(),
    pageSize: z.int(),
    totalPages: z.int(),
  }))
  .handler(async ({ input }) => {
    const offset = (input.page - 1) * input.pageSize

    const [items, [{ count }]] = await Promise.all([
      db.query.items.findMany({
        limit: input.pageSize,
        offset,
        orderBy: desc(items.createdAt),
      }),
      db.select({ count: sql`count(*)`.as("count") }).from(items),
    ])

    return {
      items,
      total: count,
      page: input.page,
      pageSize: input.pageSize,
      totalPages: Math.ceil(count / input.pageSize),
    }
  })
```

**Pros:**
- Simple to implement
- Can jump to any page
- Shows total pages/items
- Familiar UX

**Cons:**
- Slow for large offsets
- Inconsistent with real-time updates
- Can skip/duplicate items

## Filtering Patterns

### Single Filter

```typescript
list: protectedProcedure
  .input(z.object({
    status: z.enum(["active", "pending", "archived"]).optional(),
  }))
  .handler(async ({ input }) => {
    const items = await db.query.items.findMany({
      where: input.status ? eq(items.status, input.status) : undefined,
    })
    return { items }
  })
```

### Multiple Filters (AND)

```typescript
list: protectedProcedure
  .input(z.object({
    status: z.enum(["active", "archived"]).optional(),
    category: z.string().optional(),
    minPrice: z.int().optional(),
    maxPrice: z.int().optional(),
  }))
  .handler(async ({ input }) => {
    const conditions = []

    if (input.status) {
      conditions.push(eq(items.status, input.status))
    }

    if (input.category) {
      conditions.push(eq(items.category, input.category))
    }

    if (input.minPrice !== undefined) {
      conditions.push(gte(items.price, input.minPrice))
    }

    if (input.maxPrice !== undefined) {
      conditions.push(lte(items.price, input.maxPrice))
    }

    const result = await db.query.items.findMany({
      where: conditions.length > 0 ? and(...conditions) : undefined,
    })

    return { items: result }
  })
```

### Search (Text Matching)

```typescript
list: protectedProcedure
  .input(z.object({
    search: z.string().min(3).optional(),
  }))
  .handler(async ({ input }) => {
    const items = await db.query.items.findMany({
      where: input.search
        ? or(
            ilike(items.title, `%${input.search}%`),
            ilike(items.description, `%${input.search}%`)
          )
        : undefined,
    })
    return { items }
  })
```

### Date Range

```typescript
list: protectedProcedure
  .input(z.object({
    createdAfter: z.coerce.date().optional(),
    createdBefore: z.coerce.date().optional(),
  }))
  .handler(async ({ input }) => {
    const conditions = []

    if (input.createdAfter) {
      conditions.push(gte(items.createdAt, input.createdAfter))
    }

    if (input.createdBefore) {
      conditions.push(lte(items.createdAt, input.createdBefore))
    }

    const result = await db.query.items.findMany({
      where: and(...conditions),
    })

    return { items: result }
  })
```

## Sorting Patterns

### Basic Sorting

```typescript
const sortableFields = ["createdAt", "updatedAt", "title", "price"] as const

list: protectedProcedure
  .input(z.object({
    sortBy: z.enum(sortableFields).optional().default("createdAt"),
    sortOrder: z.enum(["asc", "desc"]).optional().default("desc"),
  }))
  .handler(async ({ input }) => {
    const orderFn = input.sortOrder === "asc" ? asc : desc
    const column = items[input.sortBy]

    const result = await db.query.items.findMany({
      orderBy: orderFn(column),
    })

    return { items: result }
  })
```

### Multiple Sort Fields

```typescript
list: protectedProcedure
  .input(z.object({
    sort: z.array(z.object({
      field: z.enum(["createdAt", "title", "price"]),
      order: z.enum(["asc", "desc"]),
    })).optional().default([{ field: "createdAt", order: "desc" }]),
  }))
  .handler(async ({ input }) => {
    const orderBy = input.sort.map(s => {
      const orderFn = s.order === "asc" ? asc : desc
      return orderFn(items[s.field])
    })

    const result = await db.query.items.findMany({
      orderBy,
    })

    return { items: result }
  })
```

## Resource Actions

Beyond CRUD, add domain-specific actions:

```typescript
export const postsRouter = {
  list: protectedProcedure.handler(...),
  get: protectedProcedure.handler(...),
  create: protectedProcedure.handler(...),
  update: protectedProcedure.handler(...),
  delete: protectedProcedure.handler(...),

  // Domain-specific actions
  publish: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input }) => {
      await db.update(posts)
        .set({ status: "published", publishedAt: new Date() })
        .where(eq(posts.id, input.id))
      return { success: true }
    }),

  archive: protectedProcedure
    .input(z.object({ id: z.uuid() }))
    .handler(async ({ input }) => {
      await db.update(posts)
        .set({ status: "archived" })
        .where(eq(posts.id, input.id))
      return { success: true }
    }),
}
```

**Naming:** Use action verbs that describe the business operation (publish, archive, approve, reject, etc.)
