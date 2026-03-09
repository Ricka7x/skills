# Validation Guide

Comprehensive patterns for input validation using Zod 5 in oRPC procedures.

## Zod 5 Syntax

Zod 5 introduces standalone type methods for common patterns:

```typescript
import { z } from "zod"

// ✅ Zod 5 (New Syntax)
z.email()         // Email validation
z.uuid()          // UUID validation
z.url()           // URL validation
z.int()           // Integer number
z.date()          // Date object

// ✅ Still valid in Zod 5
z.string()        // Any string
z.number()        // Any number
z.boolean()       // Boolean
z.enum([...])     // Enum

// Modifiers
z.string().min(1).max(100)
z.int().positive().min(0).max(100)
z.array(z.string()).min(1).max(10)
```

## Common Schema Patterns

### Identifiers

```typescript
// UUIDs (recommended for IDs)
const idSchema = z.uuid()

// Custom ID patterns
const customIdSchema = z.string().regex(/^[A-Z]{3}\d{6}$/)

// Numeric IDs
const numericIdSchema = z.int().positive()
```

### Strings

```typescript
// Basic string
const nameSchema = z.string().min(1).max(200)

// Email
const emailSchema = z.email()

// URL
const urlSchema = z.url()

// Phone (custom validation)
const phoneSchema = z.string().regex(/^\+?[1-9]\d{1,14}$/)

// Enum
const statusSchema = z.enum(["active", "pending", "archived"])

// Text with transformation
const trimmedSchema = z.string().trim().min(1)

// Optional with default
const roleSchema = z.enum(["user", "admin"]).optional().default("user")
```

### Numbers

```typescript
// Integer
const ageSchema = z.int().min(0).max(150)

// Positive integer
const quantitySchema = z.int().positive()

// Price (cents)
const priceSchema = z.int().min(0)

// Percentage
const percentageSchema = z.number().min(0).max(100)

// With step
const ratingSchema = z.number().min(0).max(5).step(0.5)
```

### Dates

```typescript
// Date object
const dateSchema = z.date()

// Coerce string to date
const coercedDateSchema = z.coerce.date()

// Date in future
const futureDate = z.date().refine(
  (date) => date > new Date(),
  { message: "Date must be in the future" }
)

// Date range
const dateRangeSchema = z.object({
  startDate: z.coerce.date(),
  endDate: z.coerce.date(),
}).refine(
  (data) => data.endDate > data.startDate,
  { message: "End date must be after start date" }
)
```

### Arrays

```typescript
// Array with limits
const tagsSchema = z.array(z.string()).min(1).max(10)

// Array of objects
const itemsSchema = z.array(z.object({
  id: z.uuid(),
  quantity: z.int().positive(),
})).min(1).max(100)

// Non-empty array
const categoriesSchema = z.array(z.string()).nonempty()

// Unique items
const uniqueEmailsSchema = z.array(z.email()).refine(
  (emails) => new Set(emails).size === emails.length,
  { message: "Emails must be unique" }
)
```

### Objects

```typescript
// Basic object
const addressSchema = z.object({
  street: z.string().min(1),
  city: z.string().min(1),
  state: z.string().length(2),
  zipCode: z.string().regex(/^\d{5}(-\d{4})?$/),
  country: z.string().default("US"),
})

// Nested objects
const userSchema = z.object({
  id: z.uuid(),
  name: z.string().min(1),
  email: z.email(),
  address: addressSchema.optional(),
})

// Partial (all fields optional)
const updateUserSchema = userSchema.partial()

// Omit fields
const createUserSchema = userSchema.omit({
  id: true,
  createdAt: true,
})

// Pick fields
const userSummarySchema = userSchema.pick({
  id: true,
  name: true,
  email: true,
})

// Extend schema
const adminUserSchema = userSchema.extend({
  role: z.literal("admin"),
  permissions: z.array(z.string()),
})
```

### Unions & Discriminated Unions

```typescript
// Simple union
const idSchema = z.union([z.uuid(), z.int()])

// Discriminated union (recommended)
const notificationSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("email"),
    email: z.email(),
    subject: z.string(),
    body: z.string(),
  }),
  z.object({
    type: z.literal("sms"),
    phone: z.string(),
    message: z.string(),
  }),
  z.object({
    type: z.literal("push"),
    deviceId: z.string(),
    title: z.string(),
    body: z.string(),
  }),
])
```

## Entity Schemas

### Base Entity Pattern

```typescript
// Base entity with common fields
const baseEntitySchema = z.object({
  id: z.uuid(),
  createdAt: z.coerce.date(),
  updatedAt: z.coerce.date(),
  deletedAt: z.coerce.date().optional(),
})

// Todo entity
const todoSchema = baseEntitySchema.extend({
  title: z.string().min(1).max(200),
  description: z.string().optional(),
  status: z.enum(["todo", "in_progress", "done"]),
  priority: z.enum(["low", "medium", "high"]).optional().default("medium"),
  dueDate: z.coerce.date().optional(),
  userId: z.uuid(),
})

// Create schema (omit generated fields)
const createTodoSchema = todoSchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true,
  deletedAt: true,
  userId: true, // Set from context
})

// Update schema (partial, without id)
const updateTodoSchema = createTodoSchema.partial()
```

### Reusable Schema Components

```typescript
// Pagination
const paginationSchema = z.object({
  limit: z.int().min(1).max(100).optional().default(20),
  cursor: z.string().optional(),
})

const offsetPaginationSchema = z.object({
  page: z.int().min(1).optional().default(1),
  pageSize: z.int().min(1).max(100).optional().default(20),
})

// Sorting
const sortingSchema = z.object({
  sortBy: z.string(),
  sortOrder: z.enum(["asc", "desc"]).optional().default("desc"),
})

// Date range
const dateRangeSchema = z.object({
  startDate: z.coerce.date().optional(),
  endDate: z.coerce.date().optional(),
})

// Search
const searchSchema = z.object({
  search: z.string().min(3).optional(),
})

// Combine for list endpoints
const listInputSchema = paginationSchema
  .merge(sortingSchema)
  .merge(searchSchema)
```

### Paginated Response Schema

```typescript
// Generic paginated response
function paginatedResponse<T extends z.ZodType>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    total: z.int(),
    hasMore: z.boolean(),
    nextCursor: z.string().optional(),
  })
}

// Usage
const paginatedTodosSchema = paginatedResponse(todoSchema)
```

## Custom Validations

### Refinements

```typescript
// Single field validation
const passwordSchema = z.string()
  .min(8, "Password must be at least 8 characters")
  .refine(
    (val) => /[A-Z]/.test(val),
    { message: "Password must contain uppercase letter" }
  )
  .refine(
    (val) => /[0-9]/.test(val),
    { message: "Password must contain a number" }
  )

// Object-level validation
const dateRangeSchema = z.object({
  startDate: z.coerce.date(),
  endDate: z.coerce.date(),
}).refine(
  (data) => data.endDate > data.startDate,
  {
    message: "End date must be after start date",
    path: ["endDate"],
  }
)

// Async validation (check uniqueness)
const emailSchema = z.email().refine(
  async (email) => {
    const existing = await db.query.users.findFirst({
      where: eq(users.email, email),
    })
    return !existing
  },
  { message: "Email already in use" }
)
```

### Transforms

```typescript
// Trim and lowercase email
const emailSchema = z.string()
  .trim()
  .toLowerCase()
  .pipe(z.email())

// Parse and format phone
const phoneSchema = z.string()
  .transform((val) => val.replace(/\D/g, ""))
  .pipe(z.string().length(10))

// Slugify
const slugSchema = z.string()
  .transform((val) => 
    val.toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
  )
```

## File Upload Schemas

```typescript
const fileUploadSchema = z.object({
  filename: z.string().min(1).max(255),
  contentType: z.string().regex(/^[a-z]+\/[a-z0-9\-\+\.]+$/i),
  size: z.int().min(1).max(10 * 1024 * 1024), // 10MB max
})

const imageUploadSchema = fileUploadSchema.extend({
  contentType: z.enum([
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
  ]),
  size: z.int().max(5 * 1024 * 1024), // 5MB max for images
})
```

## Metadata & Settings Schemas

```typescript
// JSON/Dynamic schemas
const metadataSchema = z.record(z.string(), z.unknown())

// Typed metadata
const postMetadataSchema = z.object({
  tags: z.array(z.string()).optional(),
  readTime: z.int().optional(),
  featured: z.boolean().optional().default(false),
  customFields: z.record(z.string(), z.string()).optional(),
})

// Settings with defaults
const userSettingsSchema = z.object({
  theme: z.enum(["light", "dark", "auto"]).default("auto"),
  notifications: z.object({
    email: z.boolean().default(true),
    sms: z.boolean().default(false),
    push: z.boolean().default(true),
  }).default({}),
  language: z.string().default("en"),
  timezone: z.string().default("UTC"),
})
```

## Input Sanitization

```typescript
// Remove dangerous characters
const sanitizedString = z.string()
  .transform((val) => val.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ""))

// Trim whitespace
const trimmedString = z.string().trim()

// Remove null bytes
const safeString = z.string()
  .transform((val) => val.replace(/\0/g, ""))

// Normalize unicode
const normalizedString = z.string()
  .transform((val) => val.normalize("NFC"))
```

## Validation Error Handling

```typescript
// In procedure handler
.handler(async ({ input }) => {
  // Zod automatically validates input
  // If validation fails, oRPC throws appropriate error
  
  // For custom validation
  const isValid = await customValidation(input)
  if (!isValid) {
    throw new ORPCError("BAD_REQUEST", {
      message: "Validation failed",
      data: {
        field: "email",
        reason: "Already in use",
      },
    })
  }
})
```

## Schema Testing

```typescript
import { describe, it, expect } from "bun:test"

describe("todoSchema", () => {
  it("validates correct todo", () => {
    const result = createTodoSchema.safeParse({
      title: "Test todo",
      status: "todo",
    })
    
    expect(result.success).toBe(true)
  })

  it("rejects invalid status", () => {
    const result = createTodoSchema.safeParse({
      title: "Test",
      status: "invalid",
    })
    
    expect(result.success).toBe(false)
  })
})
```

## Best Practices

1. **Always set limits** - Use `.min()` and `.max()` on strings, arrays, numbers
2. **Use specific types** - Prefer `z.email()`, `z.uuid()` over generic `z.string()`
3. **Provide defaults** - Use `.optional().default()` for optional fields
4. **Validate early** - Put validations in schema, not handler
5. **Reuse schemas** - Create base schemas and extend them
6. **Document** - Use `.describe()` for field documentation
7. **Transform carefully** - Be aware transforms affect output type
8. **Test schemas** - Write tests for complex validation logic
9. **Security** - Always sanitize user input, especially for SQL/HTML
10. **Performance** - Avoid async refinements when possible
