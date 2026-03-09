# Error Handling

Comprehensive error handling patterns for oRPC procedures using ORPCError.

## ORPCError Types

oRPC provides standard HTTP error codes:

```typescript
import { ORPCError } from "@orpc/server"

// 400 Bad Request
throw new ORPCError("BAD_REQUEST")

// 401 Unauthorized
throw new ORPCError("UNAUTHORIZED")

// 403 Forbidden
throw new ORPCError("FORBIDDEN")

// 404 Not Found
throw new ORPCError("NOT_FOUND")

// 409 Conflict
throw new ORPCError("CONFLICT")

// 429 Too Many Requests
throw new ORPCError("TOO_MANY_REQUESTS")

// 500 Internal Server Error
throw new ORPCError("INTERNAL_SERVER_ERROR")

// 503 Service Unavailable
throw new ORPCError("SERVICE_UNAVAILABLE")

// 402 Payment Required
throw new ORPCError("PAYMENT_REQUIRED")
```

## Error Messages

### Basic Error with Message

```typescript
throw new ORPCError("NOT_FOUND", {
  message: "User not found with the provided ID",
})
```

### Error with Metadata

```typescript
throw new ORPCError("BAD_REQUEST", {
  message: "Invalid file upload",
  data: {
    allowedTypes: ["image/png", "image/jpeg"],
    maxSize: "5MB",
    receivedType: "image/gif",
  },
})
```

### Validation Errors

```typescript
throw new ORPCError("BAD_REQUEST", {
  message: "Validation failed",
  data: {
    errors: [
      { field: "email", message: "Invalid email format" },
      { field: "password", message: "Password too short" },
    ],
  },
})
```

## Common Error Patterns

### Resource Not Found

```typescript
get: protectedProcedure
  .input(z.object({ id: z.uuid() }))
  .handler(async ({ input }) => {
    const user = await db.query.users.findFirst({
      where: eq(users.id, input.id),
    })

    if (!user) {
      throw new ORPCError("NOT_FOUND", {
        message: "User not found",
        data: { id: input.id },
      })
    }

    return user
  })
```

### Permission Denied

```typescript
delete: protectedProcedure
  .input(z.object({ id: z.uuid() }))
  .handler(async ({ input, context }) => {
    const post = await db.query.posts.findFirst({
      where: eq(posts.id, input.id),
    })

    if (!post) {
      throw new ORPCError("NOT_FOUND", {
        message: "Post not found",
      })
    }

    if (post.userId !== context.session.user.id) {
      throw new ORPCError("FORBIDDEN", {
        message: "You don't have permission to delete this post",
      })
    }

    await db.delete(posts).where(eq(posts.id, input.id))
    return { success: true }
  })
```

### Conflict/Duplicate

```typescript
create: protectedProcedure
  .input(z.object({ email: z.email(), name: z.string() }))
  .handler(async ({ input }) => {
    const existing = await db.query.users.findFirst({
      where: eq(users.email, input.email),
    })

    if (existing) {
      throw new ORPCError("CONFLICT", {
        message: "Email already in use",
        data: { field: "email" },
      })
    }

    const [user] = await db.insert(users).values(input).returning()
    return user
  })
```

### Invalid Input

```typescript
upload: protectedProcedure
  .input(z.object({
    filename: z.string(),
    contentType: z.string(),
    size: z.int(),
  }))
  .handler(async ({ input }) => {
    const allowedTypes = ["image/png", "image/jpeg", "image/webp"]

    if (!allowedTypes.includes(input.contentType)) {
      throw new ORPCError("BAD_REQUEST", {
        message: "Invalid file type",
        data: {
          allowedTypes,
          receivedType: input.contentType,
        },
      })
    }

    const maxSize = 5 * 1024 * 1024 // 5MB
    if (input.size > maxSize) {
      throw new ORPCError("BAD_REQUEST", {
        message: "File too large",
        data: {
          maxSize,
          receivedSize: input.size,
        },
      })
    }

    // Process upload
  })
```

### Rate Limit Exceeded

```typescript
sendEmail: protectedProcedure
  .input(z.object({ to: z.email(), subject: z.string() }))
  .handler(async ({ context }) => {
    const count = await getEmailsSentToday(context.session.user.id)

    if (count >= 100) {
      throw new ORPCError("TOO_MANY_REQUESTS", {
        message: "Daily email limit exceeded",
        data: {
          limit: 100,
          resetAt: new Date(Date.now() + 86400000).toISOString(),
        },
      })
    }

    // Send email
  })
```

### Payment Required

```typescript
generateReport: protectedProcedure
  .input(z.object({ type: z.enum(["basic", "advanced"]) }))
  .handler(async ({ input, context }) => {
    const subscription = await getSubscription(context.session.user.id)

    if (input.type === "advanced" && subscription.tier !== "pro") {
      throw new ORPCError("PAYMENT_REQUIRED", {
        message: "Advanced reports require Pro subscription",
        data: {
          currentTier: subscription.tier,
          requiredTier: "pro",
          upgradeUrl: "/pricing",
        },
      })
    }

    // Generate report
  })
```

### External Service Error

```typescript
sendNotification: protectedProcedure
  .input(z.object({ message: z.string() }))
  .handler(async ({ input }) => {
    try {
      await externalNotificationService.send(input.message)
    } catch (error) {
      console.error("Notification service error:", error)

      throw new ORPCError("SERVICE_UNAVAILABLE", {
        message: "Unable to send notification. Please try again later.",
        data: {
          service: "notifications",
          retryAfter: 60, // seconds
        },
      })
    }

    return { success: true }
  })
```

## Error Handling Strategies

### Try-Catch for External Services

```typescript
getWeather: publicProcedure
  .input(z.object({ city: z.string() }))
  .handler(async ({ input }) => {
    try {
      const response = await fetch(
        `https://api.weather.com/v1/weather?city=${input.city}`
      )

      if (!response.ok) {
        throw new Error("Weather API request failed")
      }

      return await response.json()
    } catch (error) {
      console.error("Weather API error:", error)

      throw new ORPCError("SERVICE_UNAVAILABLE", {
        message: "Unable to fetch weather data",
      })
    }
  })
```

### Database Transaction Errors

```typescript
createOrder: protectedProcedure
  .input(createOrderSchema)
  .handler(async ({ input, context }) => {
    try {
      const order = await db.transaction(async (tx) => {
        // Create order
        const [newOrder] = await tx.insert(orders).values({
          userId: context.session.user.id,
          total: input.total,
        }).returning()

        // Create order items
        await tx.insert(orderItems).values(
          input.items.map(item => ({
            orderId: newOrder.id,
            productId: item.productId,
            quantity: item.quantity,
          }))
        )

        return newOrder
      })

      return order
    } catch (error) {
      console.error("Order creation failed:", error)

      throw new ORPCError("INTERNAL_SERVER_ERROR", {
        message: "Failed to create order. Please try again.",
      })
    }
  })
```

### Validation Errors from Zod

Zod automatically validates input and throws appropriate errors. However, for custom validation:

```typescript
create: protectedProcedure
  .input(createUserSchema)
  .handler(async ({ input }) => {
    // Zod handles basic validation

    // Custom business logic validation
    const age = calculateAge(input.birthDate)
    if (age < 18) {
      throw new ORPCError("BAD_REQUEST", {
        message: "User must be at least 18 years old",
        data: {
          field: "birthDate",
          minAge: 18,
          providedAge: age,
        },
      })
    }

    // Async validation
    const emailExists = await checkEmailExists(input.email)
    if (emailExists) {
      throw new ORPCError("CONFLICT", {
        message: "Email already registered",
        data: { field: "email" },
      })
    }

    return await createUser(input)
  })
```

## Global Error Handling

### Server-Level Error Interceptor

```typescript
// apps/server/src/index.ts
import { onError } from "@orpc/server"

export const rpcHandler = new RPCHandler(appRouter, {
  interceptors: [
    onError((error) => {
      // Log all errors
      console.error("RPC Error:", {
        message: error.message,
        code: error.code,
        timestamp: new Date().toISOString(),
      })

      // Send to error tracking service
      if (env.NODE_ENV === "production") {
        errorTracker.captureException(error)
      }
    }),
  ],
})
```

### Frontend Error Handling

With oRPC + TanStack Query on frontend:

```typescript
// Global error handler in QueryClient
const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      if (isDefinedError(error)) {
        // Handle specific error codes
        if (error.code === 401) {
          toast.error("Session expired. Please sign in again.")
          router.navigate({ to: "/login" })
        } else if (error.code === 403) {
          toast.error("You don't have permission to perform this action.")
        } else {
          toast.error(error.message || "An error occurred")
        }
      }
    },
  }),
})
```

## Error Response Structure

Errors from oRPC follow this structure:

```typescript
interface ORPCErrorResponse {
  code: number              // HTTP status code
  message: string           // Error message
  data?: Record<string, unknown>  // Additional details
}
```

Example error response:

```json
{
  "code": 400,
  "message": "Invalid file upload",
  "data": {
    "allowedTypes": ["image/png", "image/jpeg"],
    "maxSize": "5MB",
    "receivedType": "image/gif"
  }
}
```

## Best Practices

1. **Always Provide Context** - Include helpful error details
2. **Use Correct Status Codes** - Match HTTP semantics
3. **Sanitize Errors** - Never expose internal details in production
4. **Log Everything** - Log errors server-side for debugging
5. **User-Friendly Messages** - Write clear, actionable error messages
6. **Include Recovery Info** - Tell users how to fix the issue
7. **Consistent Structure** - Use same error format everywhere
8. **Validate Early** - Catch errors at input validation
9. **Handle Async Errors** - Always try-catch external calls
10. **Test Error Paths** - Write tests for error scenarios

## Testing Error Handling

```typescript
import { describe, it, expect } from "bun:test"

describe("createUser", () => {
  it("throws CONFLICT when email exists", async () => {
    await db.insert(users).values({
      email: "test@example.com",
      name: "Existing User",
    })

    try {
      await appRouter.users.create({
        input: {
          email: "test@example.com",
          name: "New User",
        },
      })
      expect.fail("Should have thrown CONFLICT error")
    } catch (error) {
      expect(error.code).toBe(409)
      expect(error.message).toContain("Email already")
    }
  })

  it("throws NOT_FOUND when user doesn't exist", async () => {
    try {
      await appRouter.users.get({
        input: { id: "non-existent-uuid" },
      })
      expect.fail("Should have thrown NOT_FOUND error")
    } catch (error) {
      expect(error.code).toBe(404)
    }
  })
})
```
