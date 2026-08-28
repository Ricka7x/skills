# AI Features (Vercel AI SDK + Google Gemini)

AI features built on the **Vercel AI SDK** with **`@ai-sdk/google`** (gemini models). The AI SDK is used for generation; how it's exposed to the app follows the same oRPC rules as everything else.

## Stack

- `ai` (Vercel AI SDK) — `generateText`, `streamText`, `generateObject`, tools.
- `@ai-sdk/google` — `google("gemini-2.5-flash")` provider.
- `@ai-sdk/react` — `useChat`, `useCompletion` React hooks.
- Provider/model and keys come from env (ENV.md) — server only.

## Server-Side (procedures)

Wrap AI calls in oRPC procedures like any other logic. Keys/streaming stay server-side.

```ts
import { generateText } from "ai";
import { google } from "@ai-sdk/google";

summarize: protectedProcedure
  .input(z.object({ text: z.string().min(1).max(10_000) }))
  .output(z.object({ summary: z.string() }))
  .handler(async ({ input, context }) => {
    await assertCapability(membership, "assistant:use"); // MULTI-TENANCY.md

    const { text } = await generateText({
      model: google(env.AI_MODEL, { apiKey: env.GEMINI_API_KEY }),
      system: "Summarize the provided text in 3 bullet points.",
      prompt: input.text,
    });

    return { summary: text };
  }),
```

Rules:

- **Never run AI calls in the client** — model + keys are server env (ENV.md).
- Rate-limit AI procedures harder than the rest of the API (cost per call).
- Validate/constrain input size (`max`) — untrusted free text is a cost risk.
- Capability-gate AI features when they're plan-based (PAYMENTS.md).

## Structured Output

Prefer `generateObject` over parsing free text — typed, no regex guessing:

```ts
import { generateObject } from "ai";
import { z } from "zod";

const { object } = await generateObject({
  model: google(env.AI_MODEL, { apiKey: env.GEMINI_API_KEY }),
  schema: z.object({
    title: z.string(),
    tags: z.array(z.string().max(30)).max(5),
  }),
  prompt: input.text,
});
```

## Streaming to the Client

For chat-like UIs, expose a streaming procedure and use `useChat`/`useCompletion` client-side. Keep the streaming transport on the RPC layer — don't bolt a separate SSE route unless the oRPC link can't carry it.

```tsx
// client
const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
  // wired to the streaming procedure via the orpc client link
});
```

## Tool Calling

Give the model access to app data through tools that call oRPC-backed functions — never raw DB access:

```ts
const { toolCalls } = await generateText({
  model: google(env.AI_MODEL, { apiKey: env.GEMINI_API_KEY }),
  tools: {
    searchPayments: {
      description: "Search payments in the org",
      parameters: z.object({ query: z.string() }),
      execute: async ({ query }) => searchPayments({ orgId: membership.organizationId, query }),
    },
  },
  prompt: input.text,
});
```

## Anti-Patterns

- ❌ AI calls in client components (key exposure)
- ❌ Free-form LLM output trusted as structured data — use `generateObject`
- ❌ Unlimited prompt sizes — cap input, cap cost
- ❌ Unauthenticated / ungated AI procedures
- ❌ Bypassing rate limits on AI endpoints
