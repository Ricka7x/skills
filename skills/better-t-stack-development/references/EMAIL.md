# Transactional Email (Resend + React Email)

Email templates and sending via **Resend** with **React Email** templates. Templates live in `packages/transactional`.

## Locations

```
packages/transactional/
├── src/
│   ├── index.ts       → send helpers (render + send)
│   └── emails/        → React Email templates
│       ├── welcome.tsx
│       ├── invite.tsx
│       └── password-reset.tsx
```

## Template Conventions

- One React Email component per email type. Props are the **only** dynamic content — full name, link, org name, etc. No markup in data.
- Use React Email components (`<Text>`, `<Button>`, `<Container>`, `<Heading>`) — not raw `<div>`/`<a>`, for mail-client compatibility.
- **Buttons must be full-width table links** — React Email `<Button>` handles this; don't hand-roll `<a>` styling.
- Include the recipient's name for personalization, and a plain-text version via `<Text>` content fallback where practical.
- Links expire short for security-sensitive emails (password reset, invite).

```tsx
// packages/transactional/src/emails/password-reset.tsx
import { Button, Container, Heading, Text } from "@react-email/components";

interface PasswordResetEmailProps {
  name: string;
  resetLink: string;
}

export function PasswordResetEmail({ name, resetLink }: PasswordResetEmailProps) {
  return (
    <Container>
      <Heading>Reset your password</Heading>
      <Text>Hi {name},</Text>
      <Text>Click the button below to set a new password. This link expires in 1 hour.</Text>
      <Button href={resetLink}>Reset password</Button>
    </Container>
  );
}
```

## Sending

Wrap render + send in a helper so call sites don't touch Resend directly:

```ts
// packages/transactional/src/index.ts
import { Resend } from "resend";
import { render } from "@react-email/render";
import { env } from "@condomin-ia/env/server";
import { PasswordResetEmail } from "./emails/password-reset";

const resend = new Resend(env.RESEND_API_KEY);
const FROM = "Condomin <no-reply@yourdomain.com>";

export async function sendPasswordReset(to: string, name: string, resetLink: string) {
  await resend.emails.send({
    from: FROM,
    to,
    subject: "Reset your password",
    html: await render(<PasswordResetEmail name={name} resetLink={resetLink} />),
  });
}
```

- Use a **single no-reply `From`** per product; keep a consistent sender identity for deliverability.
- Log failures server-side (EMAIL.md is not a place to swallow errors) — the caller decides whether a failed email fails the operation.
- Prefer **send after commit** in the procedure so a failed email doesn't leave half-committed state.

## Trigger Points

| Email | Trigger |
|---|---|
| Welcome | After `signUp` (or email verification) |
| Invite | Org invite created (MULTI-TENANCY.md) |
| Password reset | `auth.api.requestPasswordReset` |
| Payment failed | Stripe webhook (PAYMENTS.md) |

## Anti-Patterns

- ❌ Building email markup in procedures/handlers — templates live in `packages/transactional`
- ❌ Plain `<a>`/`<div>` in templates — use React Email components
- ❌ Calling `new Resend(...)` at every send site — use the singleton/helper
- ❌ Hardcoding `From` per call — single identity
- ❌ Swallowing send errors silently
