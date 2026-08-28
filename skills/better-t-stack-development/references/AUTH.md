# Authentication (Better Auth)

Usage of the **base better-auth instance** — config, clients, sessions, flows. For writing **custom plugins**, see [BETTER-AUTH-PLUGIN.md](BETTER-AUTH-PLUGIN.md).

## Locations

```
packages/auth/src/
├── index.ts       → betterAuth() server instance (config + plugins)
├── client.ts      → createAuthClient() shared client
└── plugins/       → custom plugins (BETTER-AUTH-PLUGIN.md)

apps/web/src/lib/auth-client.ts     → web auth client
apps/native/src/lib/auth-client.ts  → native auth client (@better-auth/expo)
packages/api/src/context.ts         → reads session into the oRPC context
```

## Session in the oRPC context

Every oRPC handler gets the session through context. `createContext` resolves it once per request; middleware narrows it.

```ts
// packages/api/src/context.ts
export async function createContext({ context }: CreateContextOptions) {
  const session = await auth.api.getSession({
    headers: context.req.raw.headers,
  });
  return { session };
}
```

```ts
// packages/api/src/index.ts
export const o = os.$context<Context>();

export const publicProcedure = o;                                              // anyone
export const protectedProcedure = publicProcedure.use(requireAuth);            // session required
export const adminProcedure = publicProcedure.use(requireAdmin);               // admin role required
```

`requireAuth` narrows `context.session` to non-null — inside a `protectedProcedure` handler `context.session.user` is always defined.

## Clients

**Web** — `better-auth/react` (`createAuthClient`):

```ts
import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: `${import.meta.env.VITE_SERVER_URL}/api/auth`,
});
```

```ts
const { data: session } = authClient.useSession();
await authClient.signIn.email({ email, password });
await authClient.signUp.email({ email, password, name });
await authClient.signOut();
authClient.useActiveOrganization(); // org switcher (MULTI-TENANCY.md)
```

**Native** — `@better-auth/expo` client (`expoClient`). Session storage is handled automatically via `expo-secure-store`:

```ts
import { createAuthClient } from "better-auth/react";
import { expoClient } from "@better-auth/expo/client";

export const authClient = createAuthClient({
  baseURL: `${env.EXPO_PUBLIC_SERVER_URL}/api/auth`,
  plugins: [expoClient({ scheme: "myapp", storagePrefix: "myapp" })],
});
```

## Built-in Plugins in This Stack

| Plugin | Purpose |
|---|---|
| email/password | Core credential auth, email verification, password reset |
| passkey | WebAuthn passkeys |
| API keys | Programmatic access tokens |
| organization | Multi-tenant orgs + membership (MULTI-TENANCY.md) |
| admin | Admin user management endpoints |
| custom plugins | `audit-log`, `feature-flags`, `stripe-plans`, `last-active-org` (BETTER-AUTH-PLUGIN.md) |

## Adding or Changing Plugins

1. Register the plugin in `packages/auth/src/index.ts` **and** the matching client in `client.ts`.
2. If the plugin adds DB models/schema, regenerate the schema:

   ```bash
   bun plugin:generate   # npx @better-auth/cli generate
   bun db:generate
   bun db:push           # dev only — db:migrate in prod
   ```

3. Never edit `packages/db/src/schema/auth.ts` by hand — it's generated.

## Auth Flows

- **Sign-up:** `signUp.email()` → (optional) send verification email → user verifies → allow access to sensitive features.
- **Sign-in:** `signIn.email()`. Failed attempts are throttled by the auth rate limit.
- **Password reset:** `authClient.requestPasswordReset()` / server `auth.api.requestPasswordReset` → email with token → `authClient.resetPassword({ newPassword, token })`.
- **Passkeys:** register after login (`passkeyClient().addPasskey`), authenticate via `signIn.passkey()`.

## Security Conventions

- **Auth routes are rate limited** tighter than the rest of the API (e.g. 20 req/min vs 200) to blunt brute force. Never relax this.
- Auth `secret` and database credentials come from env only (ENV.md) — never hardcode.
- Require **verified email** for sensitive operations (payments, password changes).
- Use `getSessionFromCtx` in hooks/plugins where a session may legitimately be absent — return early, don't throw.
- Throw `UNAUTHORIZED` (not signed in) vs `FORBIDDEN` (signed in, not allowed) — see PROCEDURES.md.

## Anti-Patterns

- ❌ Calling `auth.api.*` with raw `headers` from anywhere but `createContext`/middleware
- ❌ Trusting the client to tell you who the user is — always read from the session
- ❌ Storing sessions in localStorage on native — use `expo-secure-store` via `expoClient`
- ❌ Editing generated auth schema by hand
- ❌ Bypassing rate limiting on auth endpoints
