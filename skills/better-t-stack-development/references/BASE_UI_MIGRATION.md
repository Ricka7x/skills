# Radix UI → Base UI Migration

This project is migrating shadcn's Radix-based primitives to `@base-ui/react`. Use this when converting a component that's still on Radix, or writing a brand-new primitive.

## Quick Checklist

- [ ] Swap the import: `@radix-ui/react-*` → `@base-ui/react/*` (single package, tree-shakable)
- [ ] Replace every `asChild` with `render` (and `nativeButton={false}` for non-native trigger elements)
- [ ] Convert `className`/`style` to function form wherever they need to react to open/side/state
- [ ] Rename parts per the table below (`Content` → `Popup`, `Overlay` → `Backdrop`, etc.)
- [ ] Replace Portal's `forceMount` with `keepMounted`
- [ ] Re-check any CSS keyed off `data-state="open"` — Base UI uses boolean `[data-open]`/`[data-closed]` instead
- [ ] If the component needs form integration, reach for `Field.Root`/`Field.Label`/`Field.Error` (see `FORMS.md` for this project's canonical `Field` wrappers)

## `asChild` → `render` / `nativeButton`

The single biggest API difference. Radix merges props onto a child via `asChild`; Base UI takes an explicit `render` prop instead.

```tsx
// Radix
<RadixPopover.Trigger asChild>
  <a href="/docs">Documentation</a>
</RadixPopover.Trigger>

// Base UI — render prop, children stay as the visible content
<Popover.Trigger render={<a href="/docs" />} nativeButton={false}>
  Documentation
</Popover.Trigger>
```

`nativeButton={false}` keeps the element keyboard-accessible without forcing it to render as a real `<button>`.

## Styling: function-form className/style

Base UI accepts a function for `className`/`style` that receives the component's current state — no wrapper div or extra library needed for state-based styling:

```tsx
<Popover.Popup
  className={({ open, side }) =>
    cn("popup", open && "popup--open", `popup--${side}`)
  }
  style={({ open }) => ({ opacity: open ? 1 : 0 })}
>
  Content
</Popover.Popup>
```

## Part Renames

| Radix | Base UI | Notes |
|---|---|---|
| `Popover.Content` | `Popover.Popup` | |
| `Popover.Anchor` | `createHandle()` | see below — detached triggers are handle-based now |
| `Dialog.Overlay` | `Dialog.Backdrop` | |
| `Select.Content` | `Select.Popup` | |
| Portal `forceMount` | Portal `keepMounted` | |
| — | `Field.Root` | Base UI ships form-field primitives Radix doesn't have |

## Portal

```tsx
// Radix
<RadixPopover.Portal forceMount>
  <RadixPopover.Content>...</RadixPopover.Content>
</RadixPopover.Portal>

// Base UI
<Popover.Portal keepMounted>
  <Popover.Popup>...</Popover.Popup>
</Popover.Portal>
```

Supports a custom container too: `<Popover.Portal container={customElement}>`.

## Detached Triggers: `createHandle()`

Replaces Radix's `Anchor` pattern, and can carry typed payload data:

```tsx
const popover = Popover.createHandle<{ id: string }>();

<Popover.Trigger handle={popover} payload={{ id: "item-1" }}>
  Item 1
</Popover.Trigger>

<Popover.Root handle={popover}>
  {({ payload }) => <Popover.Popup>Content for {payload?.id}</Popover.Popup>}
</Popover.Root>
```

## Data Attributes for CSS

Base UI has more granular boolean attributes than Radix's single `data-state`:

```css
/* Radix */
[data-state="open"] { }
[data-side="bottom"] { }

/* Base UI */
[data-open] { }
[data-closed] { }
[data-side="bottom"] { }
[data-align="center"] { }
[data-starting-style] { } /* enter animation */
[data-ending-style] { }   /* exit animation */
```

## Form Integration

Base UI ships `Field` primitives — but in **this project**, always use the project's own wrappers (`@/components/ui/field`: `Field`, `FieldLabel`, `FieldError`, `FieldGroup`, `FieldDescription`) rather than importing `@base-ui/react/field` directly, so styling and the `data-invalid`/`aria-invalid` conventions stay consistent with `FORMS.md`.

## Dialog Example (before/after)

```tsx
// Radix
<Dialog.Root open={isOpen} onOpenChange={setIsOpen}>
  <Dialog.Trigger asChild><button>Open</button></Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Overlay className="overlay" />
    <Dialog.Content className="content">
      <Dialog.Title>Title</Dialog.Title>
      <Dialog.Close asChild><button>Close</button></Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>

// Base UI — no asChild needed on Trigger/Close at all
<Dialog.Root open={isOpen} onOpenChange={setIsOpen}>
  <Dialog.Trigger>Open</Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Backdrop />
    <Dialog.Popup className="content">
      <Dialog.Title>Title</Dialog.Title>
      <Dialog.Close>Close</Dialog.Close>
    </Dialog.Popup>
  </Dialog.Portal>
</Dialog.Root>
```

## Common Pitfalls

- **Reaching for `asChild`** — it doesn't exist in Base UI; use `render` or `nativeButton={false}`.
- **Forgetting Portal isolation** — add `isolation: isolate` to the root layout so stacking contexts behave.
- **Missing `body { position: relative }`** — required for correct modal/popover rendering on iOS 26+.
- **Still passing `forceMount`** — it's `keepMounted` in Base UI.
- **CSS still keyed off `data-state="open"`** — switch to the boolean `[data-open]`/`[data-closed]` attributes.
