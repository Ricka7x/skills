# Forms (TanStack Form + Zod + base-ui)

Every form follows a strict 4-file architecture. This keeps validation, logic, UI, and mutation concerns completely separate — and lets the same form render inside a dialog, card, drawer, or page with zero duplication.

## The 4-File Pattern

```
components/forms/my-feature/
├── my-feature.schema.ts       → Zod schema + inferred types
├── use-my-feature-form.ts     → TanStack Form hook
├── my-feature-form.tsx        → Pure UI fields (no buttons, no mutation)
└── my-feature-dialog.tsx      → Mutation + layout container
```

## File 1: Schema

```ts
// my-feature.schema.ts
import { z } from "zod";

export const myFeatureSchema = z.object({
  name: z.string().min(1, "Name is required").max(200),
  email: z.string().email("Invalid email address"),
  role: z.enum(["admin", "user"]).default("user"),
});

export type MyFeatureFormValues = z.infer<typeof myFeatureSchema>;
```

- Single source of truth for validation
- Export both schema and inferred type
- Use Zod 4 — `z.int()` not `z.number().int()`, `z.email()` not `z.string().email()`

## File 2: Form Hook

```ts
// use-my-feature-form.ts
import { useForm } from "@tanstack/react-form";
import { type MyFeatureFormValues, myFeatureSchema } from "./my-feature.schema";

export function useMyFeatureForm(
  onSubmit: (values: MyFeatureFormValues) => Promise<void>,
  defaultValues?: Partial<MyFeatureFormValues>
) {
  return useForm({
    defaultValues: {
      name: "",
      email: "",
      role: "user" as const,
      ...defaultValues,
    } satisfies MyFeatureFormValues,
    validators: {
      onSubmit: myFeatureSchema,
    },
    onSubmit: async ({ value }) => {
      await onSubmit(value);
    },
  });
}
```

- Always use `onSubmit` validator — not `onChange` (less disruptive UX)
- `satisfies MyFeatureFormValues` ensures defaults match the schema type
- Accept optional `defaultValues` for edit forms

## File 3: Form Component (Pure UI)

```tsx
// my-feature-form.tsx
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { useMyFeatureForm } from "./use-my-feature-form";

interface MyFeatureFormProps {
  form: ReturnType<typeof useMyFeatureForm>;
  formId: string;
}

export function MyFeatureForm({ form, formId }: MyFeatureFormProps) {
  return (
    <form
      id={formId}
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <FieldGroup>
        <form.Field name="name">
          {(field) => {
            const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid;
            return (
              <Field data-invalid={isInvalid}>
                <FieldLabel htmlFor={field.name}>Name</FieldLabel>
                <Input
                  aria-invalid={isInvalid}
                  id={field.name}
                  name={field.name}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  placeholder="John Doe"
                  value={field.state.value}
                />
                <FieldDescription>Enter your full name.</FieldDescription>
                {isInvalid && <FieldError errors={field.state.meta.errors} />}
              </Field>
            );
          }}
        </form.Field>

        <form.Field name="email">
          {(field) => {
            const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid;
            return (
              <Field data-invalid={isInvalid}>
                <FieldLabel htmlFor={field.name}>Email</FieldLabel>
                <Input
                  aria-invalid={isInvalid}
                  autoComplete="email"
                  id={field.name}
                  name={field.name}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  placeholder="m@example.com"
                  type="email"
                  value={field.state.value}
                />
                {isInvalid && <FieldError errors={field.state.meta.errors} />}
              </Field>
            );
          }}
        </form.Field>
      </FieldGroup>
    </form>
  );
}
```

**🚨 Critical rules:**
- `id={formId}` on the `<form>` element — enables external submit buttons
- `e.stopPropagation()` on submit — prevents bubbling in nested forms
- Wrap all fields in `<FieldGroup>`
- `isInvalid = isTouched && !isValid` — never show errors before the user has interacted
- `data-invalid` on `<Field>`, `aria-invalid` on the input element
- **NEVER place submit buttons inside this file** — they go in the container

## File 4: Container (Mutation + Layout)

```tsx
// create-my-feature-dialog.tsx
import { useId, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { orpc } from "@/utils/orpc";
import { MyFeatureForm } from "./my-feature-form";
import { useMyFeatureForm } from "./use-my-feature-form";
import type { MyFeatureFormValues } from "./my-feature.schema";

export function CreateMyFeatureDialog() {
  const [open, setOpen] = useState(false);
  const formId = useId();
  const queryClient = useQueryClient();

  const mutation = useMutation(orpc.myFeature.create.mutationOptions());

  const form = useMyFeatureForm(async (values: MyFeatureFormValues) => {
    try {
      await mutation.mutateAsync(values);
      queryClient.invalidateQueries({ queryKey: orpc.myFeature.list.key() });
      toast.success("Created successfully");
      form.reset();
      setOpen(false);
    } catch {
      toast.error("Failed to create");
    }
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Item</DialogTitle>
          <DialogDescription>Fill in the details below.</DialogDescription>
        </DialogHeader>

        <MyFeatureForm form={form} formId={formId} />

        <DialogFooter>
          <form.Subscribe selector={(s) => ({ canSubmit: s.canSubmit, isDirty: s.isDirty })}>
            {({ canSubmit, isDirty }) => (
              <Button
                disabled={!(canSubmit && isDirty) || mutation.isPending}
                form={formId}
                type="submit"
              >
                {mutation.isPending ? "Creating..." : "Create"}
              </Button>
            )}
          </form.Subscribe>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Key points:**
- `useId()` for `formId` — unique even with multiple forms on the same page
- `form={formId}` on the button — links the external button to the form
- `form.Subscribe` for reactive `canSubmit` / `isDirty` state — prevents unnecessary re-renders
- Use `orpc.*.mutationOptions()` — never raw fetch for app mutations
- Invalidate after success: `queryClient.invalidateQueries({ queryKey: orpc.*.list.key() })`
- Reset and close after success: `form.reset()` then `setOpen(false)`

## Field Patterns

### Input
```tsx
<form.Field name="fieldName">
  {(field) => {
    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid;
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel htmlFor={field.name}>Label</FieldLabel>
        <Input
          aria-invalid={isInvalid}
          id={field.name}
          name={field.name}
          onBlur={field.handleBlur}
          onChange={(e) => field.handleChange(e.target.value)}
          value={field.state.value}
        />
        {isInvalid && <FieldError errors={field.state.meta.errors} />}
      </Field>
    );
  }}
</form.Field>
```

### Select (shadcn)
```tsx
<form.Field name="role">
  {(field) => {
    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid;
    return (
      <Field data-invalid={isInvalid}>
        <FieldLabel htmlFor={field.name}>Role</FieldLabel>
        <Select name={field.name} value={field.state.value} onValueChange={field.handleChange}>
          <SelectTrigger aria-invalid={isInvalid} id={field.name}>
            <SelectValue placeholder="Select role" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="admin">Admin</SelectItem>
            <SelectItem value="user">User</SelectItem>
          </SelectContent>
        </Select>
        {isInvalid && <FieldError errors={field.state.meta.errors} />}
      </Field>
    );
  }}
</form.Field>
```

### Checkbox
```tsx
<form.Field name="acceptTerms">
  {(field) => {
    const isInvalid = field.state.meta.isTouched && !field.state.meta.isValid;
    return (
      <Field data-invalid={isInvalid}>
        <div className="flex items-center gap-2">
          <Checkbox
            aria-invalid={isInvalid}
            checked={field.state.value}
            id={field.name}
            name={field.name}
            onCheckedChange={field.handleChange}
          />
          <FieldLabel className="!mt-0" htmlFor={field.name}>
            Accept terms
          </FieldLabel>
        </div>
        {isInvalid && <FieldError errors={field.state.meta.errors} />}
      </Field>
    );
  }}
</form.Field>
```

## Container Variants

The same form component (`MyFeatureForm`) works in all of these — zero duplication:

| Container | Submit button location |
|---|---|
| `create-my-feature-dialog.tsx` | `<DialogFooter>` |
| `edit-my-feature-card.tsx` | `<CardFooter>` |
| `my-feature-sheet.tsx` | `<SheetFooter>` |
| Full page form | Below `<MyFeatureForm />` |

## Anti-Patterns

- ❌ Submit button inside the form component
- ❌ Mutation logic inside the form component
- ❌ Skipping `e.stopPropagation()` on nested form submits
- ❌ Showing errors before user interaction (`!isValid` without `isTouched`)
- ❌ Using `react-hook-form` — this project uses TanStack Form
- ❌ Using `@hookform/resolvers` for new forms (legacy only)
- ❌ Duplicating validation rules across schema and component
