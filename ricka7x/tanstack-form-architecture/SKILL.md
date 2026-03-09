---
name: tanstack-form-architecture
description: Scaffold reusable, scalable forms using the 4-layer architecture pattern (Schema + Hook + Form + Container). Use when creating new forms, refactoring existing forms for reusability, or building features that need forms in dialogs/cards/drawers with TanStack Form, Zod validation, React Query mutations, and shadcn UI. Triggers on "create form", "build form", "new form", "form for [feature]", "reusable form", "form architecture".
---

# TanStack Form Architecture Pattern

Production-grade pattern for building scalable, reusable forms with clean separation of concerns.

## Quick Reference: Complete Example

Here's what a modern form looks like with base-ui Field components:

```typescript
"use client"

import { useForm } from "@tanstack/react-form"
import { toast } from "sonner"
import * as z from "zod"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"

const formSchema = z.object({
  username: z
    .string()
    .min(3, "Username must be at least 3 characters.")
    .max(10, "Username must be at most 10 characters."),
})

export function ProfileForm() {
  const form = useForm({
    defaultValues: {
      username: "",
    },
    validators: {
      onSubmit: formSchema,
    },
    onSubmit: async ({ value }) => {
      toast.success("Profile updated", {
        description: `Username: ${value.username}`,
      })
    },
  })

  return (
    <Card className="w-full sm:max-w-md">
      <CardHeader>
        <CardTitle>Profile Settings</CardTitle>
        <CardDescription>
          Update your profile information below.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          id="profile-form"
          onSubmit={(e) => {
            e.preventDefault()
            form.handleSubmit()
          }}
        >
          <FieldGroup>
            <form.Field name="username">
              {(field) => {
                const isInvalid =
                  field.state.meta.isTouched && !field.state.meta.isValid
                return (
                  <Field data-invalid={isInvalid}>
                    <FieldLabel htmlFor="profile-form-username">
                      Username
                    </FieldLabel>
                    <Input
                      id="profile-form-username"
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={isInvalid}
                      placeholder="shadcn"
                      autoComplete="username"
                    />
                    <FieldDescription>
                      This is your public display name.
                    </FieldDescription>
                    {isInvalid && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )
              }}
            </form.Field>
          </FieldGroup>
        </form>
      </CardContent>
      <CardFooter>
        <Field orientation="horizontal">
          <Button type="button" variant="outline" onClick={() => form.reset()}>
            Reset
          </Button>
          <Button type="submit" form="profile-form">
            Save
          </Button>
        </Field>
      </CardFooter>
    </Card>
  )
}
```

**Key Pattern Elements:**
- ✅ `FieldGroup` wraps all fields for consistent spacing
- ✅ `isInvalid` calculated from `isTouched && !isValid`
- ✅ `data-invalid` attribute on Field wrapper
- ✅ `aria-invalid` attribute on input elements
- ✅ `FieldLabel` with descriptive `htmlFor`
- ✅ `FieldDescription` for help text
- ✅ `FieldError` component handles error display
- ✅ `Field orientation="horizontal"` for button groups

## Stack

- **TanStack Form** - Form state management
- **Zod** - Schema validation
- **TanStack Query** - Server mutations
- **shadcn/ui** - UI components (with base-ui Field components)

## Architecture Layers

| Layer | Responsibility | File |
|-------|---------------|------|
| Schema | Validation rules | `feature.schema.ts` |
| Hook | Form state & logic | `use-feature-form.ts` |
| Form | Pure UI fields | `feature-form.tsx` |
| Container | Mutation & layout | `create-feature-dialog.tsx` |

**Benefits:**
- ✅ Zero validation duplication
- ✅ Forms reusable across layouts (dialog, card, drawer, inline)
- ✅ External submit buttons (using `form={formId}`)
- ✅ Clean mutation integration
- ✅ 5-10 min to scaffold new forms

## 🚨 Critical Architecture Rule: Submit Buttons

**NEVER place submit buttons inside the form component.** Submit buttons belong in the parent container's footer (DialogFooter, CardFooter, etc.).

**Why?** This architecture enables form reusability:
- ✅ Same form works in dialogs, cards, drawers, pages
- ✅ Parent controls button layout and behavior
- ✅ Form component stays pure and layout-agnostic
- ✅ Different contexts can have different button configurations

**Pattern:**
```typescript
// ❌ WRONG - Button inside form component
export function UserForm({ form, formId }: UserFormProps) {
  return (
    <form id={formId}>
      <FieldGroup>
        {/* fields */}
      </FieldGroup>
      <Button type="submit">Submit</Button> {/* ❌ DON'T DO THIS */}
    </form>
  )
}

// ✅ CORRECT - Button in parent footer
export function CreateUserDialog() {
  const formId = useId()
  const form = useUserForm(async (values) => { /* ... */ })
  
  return (
    <Dialog>
      <DialogContent>
        <UserForm form={form} formId={formId} />
        <DialogFooter>
          <Button type="submit" form={formId}> {/* ✅ Correct location */}
            Create User
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**The `form={formId}` attribute links the external button to the form, enabling submission from outside the form element.**

## Where Do Submit Buttons Go?

**Quick Answer:** In the **parent container's footer** - DialogFooter, CardFooter, etc. NEVER inside the form component.

| Container | Button Location | Example |
|-----------|----------------|---------|
| Dialog | `<DialogFooter>` | Create/Edit dialogs |
| Card | `<CardFooter>` | Inline editor cards |
| Sheet/Drawer | `<SheetFooter>` | Side panel forms |
| Page | Outside form | Full-page forms |

**Component Responsibility:**
```
Form Component (user-form.tsx)
├─ <form id={formId}>        ✅ Has id
├─   <FieldGroup>            ✅ Field wrapper
├─     <form.Field ...>      ✅ Form fields only
└─   </FieldGroup>
                              ❌ NO BUTTONS HERE

Container (create-user-dialog.tsx)
├─ <Dialog>
├─   <DialogContent>
├─     <UserForm />          ✅ Renders pure form
├─     <DialogFooter>
└─       <Button form={id}>  ✅ Button with form={id}
```

## Folder Structure

```
features/
  users/
    user.schema.ts
    use-user-form.ts
    user-form.tsx
    create-user-dialog.tsx
    edit-user-card.tsx (reuses same form)
```

## Layer 1: Schema (Validation)

**File:** `user.schema.ts`

```typescript
import { z } from "zod"

export const userSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
  role: z.enum(["admin", "user", "guest"]).default("user"),
})

export type UserFormValues = z.infer<typeof userSchema>
```

**Rules:**
- Single source of truth for validation
- Export both schema and inferred type
- Co-locate related schemas in same file

## Layer 2: Hook (Form Logic)

**File:** `use-user-form.ts`

```typescript
import { useForm } from "@tanstack/react-form"
import { userSchema, type UserFormValues } from "./user.schema"

export function useUserForm(
  onSubmit: (values: UserFormValues) => Promise<void>,
  defaultValues?: Partial<UserFormValues>
) {
  return useForm({
    defaultValues: {
      name: "",
      email: "",
      role: "user" as const,
      ...defaultValues,
    },
    validators: {
      onSubmit: userSchema,
    },
    onSubmit: async ({ value }) => {
      await onSubmit(value)
    },
  })
}
```

**Rules:**
- Accept `onSubmit` callback and optional `defaultValues`
- Set sensible defaults for all fields
- Use `onSubmit` validator for explicit validation timing
- Return form instance directly

**Validation Modes:**
```typescript
validators: {
  onChange: userSchema,   // Real-time (every keystroke)
  onBlur: userSchema,     // On focus loss
  onSubmit: userSchema,   // On submit only (recommended)
}
```

## Layer 3: Form Component (Pure UI)

**File:** `user-form.tsx`

```typescript
import { Input } from "@/components/ui/input"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface UserFormProps {
  form: ReturnType<typeof useUserForm>
  formId: string
}

export function UserForm({ form, formId }: UserFormProps) {
  return (
    <form
      id={formId}
      onSubmit={(e) => {
        e.preventDefault()
        form.handleSubmit()
      }}
    >
      <FieldGroup>
        <form.Field name="name">
          {(field) => {
            const isInvalid =
              field.state.meta.isTouched && !field.state.meta.isValid
            return (
              <Field data-invalid={isInvalid}>
                <FieldLabel htmlFor={`${formId}-${field.name}`}>
                  Name
                </FieldLabel>
                <Input
                  id={`${formId}-${field.name}`}
                  name={field.name}
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  aria-invalid={isInvalid}
                  placeholder="John Doe"
                  autoComplete="name"
                />
                <FieldDescription>
                  Enter your full name.
                </FieldDescription>
                {isInvalid && (
                  <FieldError errors={field.state.meta.errors} />
                )}
              </Field>
            )
          }}
        </form.Field>

        <form.Field name="email">
          {(field) => {
            const isInvalid =
              field.state.meta.isTouched && !field.state.meta.isValid
            return (
              <Field data-invalid={isInvalid}>
                <FieldLabel htmlFor={`${formId}-${field.name}`}>
                  Email
                </FieldLabel>
                <Input
                  id={`${formId}-${field.name}`}
                  name={field.name}
                  type="email"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  aria-invalid={isInvalid}
                  placeholder="john@example.com"
                  autoComplete="email"
                />
                <FieldDescription>
                  We'll never share your email with anyone else.
                </FieldDescription>
                {isInvalid && (
                  <FieldError errors={field.state.meta.errors} />
                )}
              </Field>
            )
          }}
        </form.Field>

        <form.Field name="role">
          {(field) => {
            const isInvalid =
              field.state.meta.isTouched && !field.state.meta.isValid
            return (
              <Field data-invalid={isInvalid}>
                <FieldLabel htmlFor={`${formId}-${field.name}`}>
                  Role
                </FieldLabel>
                <Select
                  name={field.name}
                  value={field.state.value}
                  onValueChange={field.handleChange}
                >
                  <SelectTrigger
                    id={`${formId}-${field.name}`}
                    aria-invalid={isInvalid}
                  >
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="user">User</SelectItem>
                    <SelectItem value="guest">Guest</SelectItem>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Choose the appropriate role for this user.
                </FieldDescription>
                {isInvalid && (
                  <FieldError errors={field.state.meta.errors} />
                )}
              </Field>
            )
          }}
        </form.Field>
      </FieldGroup>
    </form>
  )
}
```

**Rules:**
- Accept `form` and `formId` props
- Use `id={formId}` on `<form>` element (enables external buttons)
- Wrap all fields in `<FieldGroup>` for consistent spacing
- Use base-ui Field components for accessibility
- Calculate `isInvalid` based on `isTouched` and `isValid`
- Pass `data-invalid` to Field and `aria-invalid` to input
- Use `FieldError` component with `errors` prop
- Include `FieldDescription` for helpful context
- Add `name` attribute to inputs for better form semantics
- **🚨 CRITICAL: NO submit button inside form - buttons go in parent footer**
- No mutation logic
- Layout-agnostic (no card/dialog wrappers)

**Field Pattern Template (Input):**
```typescript
<form.Field name="fieldName">
  {(field) => {
    const isInvalid =
      field.state.meta.isTouched && !field.state.meta.isValid
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel htmlFor={`${formId}-${field.name}`}>
          Label
        </FieldLabel>
        <Input
          id={`${formId}-${field.name}`}
          name={field.name}
          value={field.state.value}
          onChange={(e) => field.handleChange(e.target.value)}
          onBlur={field.handleBlur}
          aria-invalid={isInvalid}
          placeholder="Placeholder text"
          autoComplete="field-name"
        />
        <FieldDescription>
          Description or help text for the field.
        </FieldDescription>
        {isInvalid && (
          <FieldError errors={field.state.meta.errors} />
        )}
      </Field>
    )
  }}
</form.Field>
```

**Field Pattern Template (Select):**
```typescript
<form.Field name="fieldName">
  {(field) => {
    const isInvalid =
      field.state.meta.isTouched && !field.state.meta.isValid
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel htmlFor={`${formId}-${field.name}`}>
          Label
        </FieldLabel>
        <Select
          name={field.name}
          value={field.state.value}
          onValueChange={field.handleChange}
        >
          <SelectTrigger
            id={`${formId}-${field.name}`}
            aria-invalid={isInvalid}
          >
            <SelectValue placeholder="Select an option" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
            <SelectItem value="option2">Option 2</SelectItem>
          </SelectContent>
        </Select>
        <FieldDescription>
          Description or help text for the field.
        </FieldDescription>
        {isInvalid && (
          <FieldError errors={field.state.meta.errors} />
        )}
      </Field>
    )
  }}
</form.Field>
```

## Layer 4: Container (Mutation + Layout)

### Dialog Example

**File:** `create-user-dialog.tsx`

```typescript
"use client"

import { useId, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"

import { UserForm } from "./user-form"
import { useUserForm } from "./use-user-form"
import type { UserFormValues } from "./user.schema"

export function CreateUserDialog() {
  const [open, setOpen] = useState(false)
  const formId = useId()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Initialize form with submit handler
  const form = useUserForm(async (values) => {
    setIsSubmitting(true)
    try {
      const res = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      })

      if (!res.ok) {
        const error = await res.json()
        toast.error(error.message || "Failed to create user")
        return
      }

      const data = await res.json()
      toast.success("User created successfully", {
        description: `${data.name} has been added to the system.`,
      })
      
      form.reset()
      setOpen(false)
    } catch (error) {
      console.error(error)
      toast.error("An error occurred while creating user")
    } finally {
      setIsSubmitting(false)
    }
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button onClick={() => setOpen(true)}>
        Create User
      </Button>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
          <DialogDescription>
            Add a new user to your organization. Fill in the details below.
          </DialogDescription>
        </DialogHeader>

        <UserForm form={form} formId={formId} />

        <DialogFooter>
          {/* ✅ Submit button in footer, NOT in form component */}
          <form.Subscribe
            selector={(state) => ({
              canSubmit: state.canSubmit,
              isDirty: state.isDirty,
            })}
          >
            {({ canSubmit, isDirty }) => (
              <Button
                type="submit"
                form={formId}  // Links to form by ID
                disabled={!(canSubmit && isDirty) || isSubmitting}
              >
                {isSubmitting ? "Creating..." : "Create User"}
              </Button>
            )}
          </form.Subscribe>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Submit Button Pattern:**

```typescript
<DialogFooter>
  {/* ✅ Button outside form, linked via form={formId} */}
  <form.Subscribe
    selector={(state) => ({
      canSubmit: state.canSubmit,
      isDirty: state.isDirty,
    })}
  >
    {({ canSubmit, isDirty }) => (
      <Button
        type="submit"
        form={formId}  // 🔑 Links to form by ID
        disabled={!(canSubmit && isDirty) || isSubmitting}
      >
        {isSubmitting ? "Saving..." : "Save"}
      </Button>
    )}
  </form.Subscribe>
</DialogFooter>
```

**Key Points:**
- `form.Subscribe` provides reactive state access
- `form={formId}` links external button to form
- `type="submit"` triggers form submission
- Manage `isSubmitting` state in container component
- Button is in **DialogFooter** or **CardFooter**, NEVER inside form component

### Card Example (Edit Mode)

**File:** `edit-user-card.tsx`

```typescript
"use client"

import { useId } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Field } from "@/components/ui/field"

import { UserForm } from "./user-form"
import { useUserForm } from "./use-user-form"
import type { UserFormValues } from "./user.schema"

interface EditUserCardProps {
  userId: string
  initialData: UserFormValues
}

export function EditUserCard({ userId, initialData }: EditUserCardProps) {
  const formId = useId()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useUserForm(
    async (values) => {
      setIsSubmitting(true)
      try {
        const res = await fetch(`/api/users/${userId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(values),
        })

        if (!res.ok) {
          const error = await res.json()
          toast.error(error.message || "Failed to update user")
          return
        }

        const data = await res.json()
        toast.success("User updated successfully", {
          description: `Changes to ${data.name} have been saved.`,
        })
        form.reset()
      } catch (error) {
        console.error(error)
        toast.error("An error occurred while updating user")
      } finally {
        setIsSubmitting(false)
      }
    },
    initialData // ✅ Populate with existing data
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit User</CardTitle>
        <CardDescription>
          Update user information and save your changes.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <UserForm form={form} formId={formId} />
      </CardContent>

      <CardFooter>
        {/* ✅ Buttons in footer, NOT in form component */}
        <form.Subscribe
          selector={(state) => ({
            canSubmit: state.canSubmit,
            isDirty: state.isDirty,
          })}
        >
          {({ canSubmit, isDirty }) => (
            <Field orientation="horizontal">
              <Button
                type="button"
                variant="outline"
                onClick={() => form.reset()}
                disabled={!isDirty || isSubmitting}
              >
                Reset
              </Button>
              <Button
                type="submit"
                form={formId}
                disabled={!(canSubmit && isDirty) || isSubmitting}
              >
                {isSubmitting ? "Updating..." : "Update User"}
              </Button>
            </Field>
          )}
        </form.Subscribe>
      </CardFooter>
    </Card>
  )
}
```

## oRPC Integration (Better-T-Stack)

For projects using oRPC (like Better-T-Stack), integrate with the oRPC client:

```typescript
import { orpc } from "@/utils/orpc"

const mutation = useMutation({
  mutationFn: async (values: UserFormValues) => {
    return orpc.users.create(values)
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["users"] })
  },
})
```

## Base-UI Field Components

The form uses shadcn's base-ui Field components for consistent, accessible forms:

### Available Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `Field` | Wrapper for form field | `data-invalid`, `orientation` |
| `FieldLabel` | Accessible label | `htmlFor` (required) |
| `FieldDescription` | Help text | - |
| `FieldError` | Displays errors | `errors` (string array) |
| `FieldGroup` | Groups multiple fields | - |

### Field Component Props

```typescript
// Field wrapper
<Field 
  data-invalid={boolean}  // Applies invalid styles
  orientation="vertical" | "horizontal"  // Layout direction
>

// FieldLabel
<FieldLabel 
  htmlFor={string}  // Must match input id
>

// FieldError
<FieldError 
  errors={string[]}  // Array of error messages
/>
```

### Styling States

The Field component automatically applies styles based on `data-invalid`:

```css
[data-invalid="true"] {
  /* Invalid state styles applied automatically */
}
```

### Orientation Modes

```typescript
// Vertical (default) - Label above input
<Field orientation="vertical">
  <FieldLabel>Name</FieldLabel>
  <Input />
</Field>

// Horizontal - Label and input side-by-side
<Field orientation="horizontal">
  <Button variant="outline">Cancel</Button>
  <Button type="submit">Save</Button>
</Field>
```

## Form State Reference

Access these properties from `form.state`:

```typescript
form.state.canSubmit    // Form is valid and can be submitted
form.state.isDirty      // Form has unsaved changes
form.state.isSubmitting // Form is currently submitting
form.state.errors       // Form-level errors
```

## Reusability Patterns

Once implemented, the same form can be reused in:

1. **Create Dialog** - `create-feature-dialog.tsx`
2. **Edit Card** - `edit-feature-card.tsx`
3. **Settings Drawer** - `feature-settings-drawer.tsx`
4. **Inline Editor** - `inline-feature-editor.tsx`
5. **Wizard Step** - `feature-wizard-step.tsx`

**Zero duplication of:**
- Validation rules
- Field components
- Form logic
- Submit handling

## Scaffolding Checklist

When creating a new form:

- [ ] Create `feature.schema.ts` with Zod schema
- [ ] Create `use-feature-form.ts` hook
- [ ] Create `feature-form.tsx` component (pure UI)
- [ ] Create container (dialog/card/drawer)
- [ ] Define mutation with proper error handling
- [ ] Wire up cache invalidation
- [ ] Add loading/disabled states
- [ ] Test form validation
- [ ] Test submission flow
- [ ] Test reset/cancel behavior

## Common Patterns

### Required Imports

For the patterns below, you may need these additional imports:

```typescript
import { Checkbox } from "@/components/ui/checkbox"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
```

### Conditional Fields

```typescript
<form.Field name="notifyByEmail">
  {(emailField) => {
    const isEmailInvalid =
      emailField.state.meta.isTouched && !emailField.state.meta.isValid
    return (
      <Field data-invalid={isEmailInvalid}>
        <FieldLabel htmlFor={`${formId}-${emailField.name}`}>
          Notify by Email
        </FieldLabel>
        <Checkbox
          id={`${formId}-${emailField.name}`}
          checked={emailField.state.value}
          onCheckedChange={emailField.handleChange}
        />
        {isEmailInvalid && (
          <FieldError errors={emailField.state.meta.errors} />
        )}
      </Field>
    )
  }}
</form.Field>

{form.getFieldValue("notifyByEmail") && (
  <form.Field name="email">
    {(field) => {
      const isInvalid =
        field.state.meta.isTouched && !field.state.meta.isValid
      return (
        <Field data-invalid={isInvalid}>
          <FieldLabel htmlFor={`${formId}-${field.name}`}>
            Email Address
          </FieldLabel>
          <Input
            id={`${formId}-${field.name}`}
            name={field.name}
            type="email"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            aria-invalid={isInvalid}
          />
          {isInvalid && (
            <FieldError errors={field.state.meta.errors} />
          )}
        </Field>
      )
    }}
  </form.Field>
)}
```

### Textarea Fields

```typescript
<form.Field name="bio">
  {(field) => {
    const isInvalid =
      field.state.meta.isTouched && !field.state.meta.isValid
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel htmlFor={`${formId}-${field.name}`}>
          Bio
        </FieldLabel>
        <Textarea
          id={`${formId}-${field.name}`}
          name={field.name}
          value={field.state.value}
          onChange={(e) => field.handleChange(e.target.value)}
          onBlur={field.handleBlur}
          aria-invalid={isInvalid}
          placeholder="Tell us about yourself..."
          rows={4}
        />
        <FieldDescription>
          Brief description for your profile. Maximum 500 characters.
        </FieldDescription>
        {isInvalid && (
          <FieldError errors={field.state.meta.errors} />
        )}
      </Field>
    )
  }}
</form.Field>
```

### Checkbox Fields

```typescript
<form.Field name="acceptTerms">
  {(field) => {
    const isInvalid =
      field.state.meta.isTouched && !field.state.meta.isValid
    return (
      <Field data-invalid={isInvalid}>
        <div className="flex items-center gap-2">
          <Checkbox
            id={`${formId}-${field.name}`}
            name={field.name}
            checked={field.state.value}
            onCheckedChange={field.handleChange}
            aria-invalid={isInvalid}
          />
          <FieldLabel
            htmlFor={`${formId}-${field.name}`}
            className="!mt-0"
          >
            I accept the terms and conditions
          </FieldLabel>
        </div>
        {isInvalid && (
          <FieldError errors={field.state.meta.errors} />
        )}
      </Field>
    )
  }}
</form.Field>
```

### Radio Group Fields

```typescript
<form.Field name="plan">
  {(field) => {
    const isInvalid =
      field.state.meta.isTouched && !field.state.meta.isValid
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel>Choose a plan</FieldLabel>
        <RadioGroup
          name={field.name}
          value={field.state.value}
          onValueChange={field.handleChange}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="free" id={`${formId}-plan-free`} />
            <Label htmlFor={`${formId}-plan-free`}>Free</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="pro" id={`${formId}-plan-pro`} />
            <Label htmlFor={`${formId}-plan-pro`}>Pro</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="enterprise" id={`${formId}-plan-enterprise`} />
            <Label htmlFor={`${formId}-plan-enterprise`}>Enterprise</Label>
          </div>
        </RadioGroup>
        <FieldDescription>
          Select the plan that best fits your needs.
        </FieldDescription>
        {isInvalid && (
          <FieldError errors={field.state.meta.errors} />
        )}
      </Field>
    )
  }}
</form.Field>
```

### Optimistic Updates

```typescript
const mutation = useMutation({
  mutationFn: createUser,
  onMutate: async (newUser) => {
    await queryClient.cancelQueries({ queryKey: ["users"] })
    const previousUsers = queryClient.getQueryData(["users"])
    
    queryClient.setQueryData(["users"], (old) => [...old, newUser])
    
    return { previousUsers }
  },
  onError: (err, newUser, context) => {
    queryClient.setQueryData(["users"], context.previousUsers)
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ["users"] })
  },
})
```

### Server Errors

```typescript
const mutation = useMutation({
  mutationFn: createUser,
  onError: (error) => {
    if (error.response?.status === 409) {
      form.setFieldValue("email", "", {
        errors: ["Email already exists"],
      })
    }
  },
})
```

## Tips

### Architecture
- **🚨 Submit buttons go in parent footer** - NEVER inside form component (enables reusability)
- **Use `form={formId}` attribute** - Links external buttons to form by ID
- **Use `form.Subscribe` for button state** - Provides reactive access to canSubmit, isDirty
- **Manage `isSubmitting` locally** - Track submission state in container component
- **Generate formId with `useId()`** - Ensures unique IDs for multiple forms on same page

### Form Fields
- **Wrap fields in `FieldGroup`** - Provides consistent spacing and layout
- **Calculate `isInvalid` consistently** - Always use `isTouched && !isValid` pattern
- **Use base-ui Field components** - Better accessibility and consistent styling
- **Pass `data-invalid` to Field** - Enables CSS styling for invalid states
- **Pass `aria-invalid` to inputs** - Screen reader accessibility
- **Use `FieldError` component** - Automatically formats and displays validation errors
- **Include `FieldDescription`** - Provide helpful context for users
- **Add `name` attribute** - Improves form semantics and browser autofill

### UX & State Management
- **Reset form after success** - `form.reset()` clears form and dirty state
- **Close modal after success** - `setOpen(false)` provides clean UX
- **Show loading in button** - User feedback during async operations
- **Validate on submit by default** - Less disruptive than onChange
- **Use `form.state.isDirty`** - Prevent accidental data loss
- **Show toast notifications** - Inform users of success/error states
- **Use `Field orientation="horizontal"`** - For button groups in footers

## Time to Scaffold New Forms

Once this pattern is internalized:

- New form: **5-10 minutes**
- Reuse in different layout: **30 seconds**
## Summary: The Submit Button Rule

**Remember:** The key to this architecture is **separation of concerns**.

✅ **Form Component** (`user-form.tsx`)
- Contains ONLY fields and validation UI
- Has `id={formId}` on the `<form>` element
- NO buttons inside

✅ **Container Component** (`create-user-dialog.tsx`)
- Manages submission logic and state
- Places buttons in `<DialogFooter>` or `<CardFooter>`
- Links buttons with `form={formId}` attribute
- Uses `form.Subscribe` for reactive state

**This enables:**
- 🔄 Same form in dialogs, cards, drawers
- 🎨 Different button layouts per context
- 🧪 Easy testing of form logic separately
- 📦 True component reusability