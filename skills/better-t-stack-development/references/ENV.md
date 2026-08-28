# Environment Variables (@t3-oss/env-core)

All env vars are validated with `@t3-oss/env-core` in `packages/env` — one source of truth per platform.

## Locations

```
packages/env/src/
├── index.ts      → re-exports
├── server.ts     → server-side vars (DB, auth secret, Stripe, S3, Resend, AI)
├── web.ts        → public `VITE_*` vars
└── native.ts     → public `EXPO_PUBLIC_*` vars
```

```ts
// packages/env/src/server.ts
import { createEnv } from "@t3-oss/env-core";
import { z } from "zod";

export const env = createEnv({
  server: {
    DATABASE_URL: z.string().url(),
    AUTH_SECRET: z.string().min(32),
    STRIPE_SECRET_KEY: z.string().startsWith("sk_"),
  },
  runtimeEnv: process.env,
});
```

Usage — import the right namespace, never `process.env` directly:

```ts
import { env } from "@condomin-ia/env/server";
import { env as webEnv } from "@condomin-ia/env/web";
```

## Adding a New Env Variable

1. Add its `zod` schema to the matching file in `packages/env/src/` (server/web/native).
2. Add the key to the matching `.env.example` (with a **placeholder**, never a real value).
3. Add it to the CI env block (`.github/workflows/*.yml`) with a placeholder if CI needs it.
4. Reference it via the typed `env` import.

Rules:

- **Server vars** (secrets) only exist in `server.ts` — never in `web.ts`/`native.ts` (they ship to the browser).
- **Public vars** are prefixed `VITE_` (web) / `EXPO_PUBLIC_` (native) and are safe to expose.
- Secrets get **no default** — fail fast at startup if missing.
- No fallbacks that silently mask a missing config.

## Security

- `.env` files are gitignored (`.env`, `.env.*.local`). Never commit them.
- Never log env values — a leaked `AUTH_SECRET` or `DATABASE_URL` is a credential exposure.
- Never send server env to the client via an RPC response "for convenience".

## Anti-Patterns

- ❌ `process.env.X` / `import.meta.env.X` scattered across apps — use `@condomin-ia/env`
- ❌ A secret in `web.ts` or `native.ts`
- ❌ Committing a real `.env` or real values into `.env.example`
- ❌ Defaults for secrets (silent failures) — require them
