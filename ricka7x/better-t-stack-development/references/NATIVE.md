# Native App (Expo + Expo Router)

## Stack

- **Expo 54** + Expo Router 6 (file-based routing)
- **React Native 0.81** + React 19
- **UI:** heroui-native + Tailwind (via `uniwind`)
- **Auth:** better-auth/expo client
- **API:** oRPC client (shared `@condomin-ia/api` types)
- **Data:** TanStack Query + `@orpc/tanstack-query`
- **Animations:** React Native Reanimated 4 + Gesture Handler
- **Bottom sheets:** `@gorhom/bottom-sheet`

## File Structure

```
apps/native/
├── app/
│   ├── _layout.tsx               → Root layout (providers, auth)
│   ├── (drawer)/
│   │   ├── _layout.tsx           → Drawer navigator
│   │   ├── (tabs)/
│   │   │   ├── _layout.tsx       → Tab navigator
│   │   │   └── index.tsx         → Home tab
│   │   ├── ai.tsx
│   │   └── index.tsx
│   ├── modal.tsx
│   └── +not-found.tsx
├── components/                   → Shared UI components
├── contexts/                     → React contexts (theme, etc.)
├── lib/
│   ├── auth-client.ts            → better-auth/expo client
│   └── s3.ts
└── utils/
    └── orpc.ts                   → oRPC client + queryClient
```

## oRPC Client (Native)

```ts
// apps/native/utils/orpc.ts
import type { AppRouterClient } from "@condomin-ia/api/routers/index";
import { env } from "@condomin-ia/env/native";
import { createORPCClient } from "@orpc/client";
import { RPCLink } from "@orpc/client/fetch";
import { createTanstackQueryUtils } from "@orpc/tanstack-query";
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient();

export const link = new RPCLink({
  url: `${env.EXPO_PUBLIC_SERVER_URL}/rpc`,
  // Note: React Native uses expo-secure-store for cookies via better-auth/expo
});

export const client: AppRouterClient = createORPCClient(link);
export const orpc = createTanstackQueryUtils(client);
```

## Auth (better-auth/expo)

```ts
// apps/native/lib/auth-client.ts
import { createAuthClient } from "better-auth/react";
import { expoClient } from "@better-auth/expo/client";
import { passkeyClient } from "@better-auth/passkey/client";
import { env } from "@condomin-ia/env/native";

export const authClient = createAuthClient({
  baseURL: `${env.EXPO_PUBLIC_SERVER_URL}/api/auth`,
  plugins: [
    expoClient({
      scheme: "myapp",
      storagePrefix: "myapp",
    }),
    passkeyClient(),
  ],
});
```

better-auth/expo handles session storage via `expo-secure-store` automatically.

## UI: heroui-native

Use heroui-native components for the native app. Always prefer heroui-native components over building custom ones.

```tsx
import { Button, Input, Card } from "heroui-native";

// Theming is via Tailwind classes (uniwind)
<Button className="bg-primary-500">
  Press me
</Button>
```

Tailwind in React Native via `uniwind` — same class names as web, applied via NativeWind-style transformer.

## Styling

```tsx
// Use Tailwind classes directly via ClassValue (tailwind-variants)
import { tv } from "tailwind-variants";

const button = tv({
  base: "rounded-lg px-4 py-2",
  variants: {
    intent: {
      primary: "bg-blue-500",
      secondary: "bg-gray-200",
    },
  },
});

// In component
<Pressable className={button({ intent: "primary" })} />
```

## Navigation (Expo Router)

Same file-based convention as TanStack Router but for native:

```tsx
import { router, useLocalSearchParams } from "expo-router";

// Navigate
router.push("/modal");
router.push({ pathname: "/(drawer)/(tabs)/", params: { id: "123" } });
router.back();

// Params
const { id } = useLocalSearchParams<{ id: string }>();
```

**Layout types:**
- `<Stack>` — standard stack navigator
- `<Tabs>` — bottom tab bar
- `<Drawer>` — side drawer (via `@react-navigation/drawer`)

## Data Fetching (Same Pattern as Web)

```tsx
import { useQuery, useMutation } from "@tanstack/react-query";
import { orpc, queryClient } from "@/utils/orpc";

// Query
const { data, isPending } = useQuery(orpc.posts.list.queryOptions());

// Mutation
const mutation = useMutation(orpc.posts.create.mutationOptions());

const handleCreate = async () => {
  await mutation.mutateAsync({ title });
  queryClient.invalidateQueries({ queryKey: orpc.posts.list.key() });
};
```

## Performance Rules

- Use `useCallback` for FlatList `renderItem` and `keyExtractor`
- Use `React.memo` on expensive list item components
- Prefer `expo-image` over React Native's `<Image>` for caching
- Use `Pressable` over `TouchableOpacity`
- Never put inline objects or arrow functions as FlatList props (creates new references on every render)
- For scroll position — use `ref` not state
- Avoid `&&` short-circuit rendering (falsy 0 renders as text in RN) — use ternary `? <A /> : null`

```tsx
// ❌ — renders "0" as text when count is 0
{count && <Component />}

// ✅
{count > 0 && <Component />}
// or
{count ? <Component /> : null}
```

## Animations (Reanimated 4)

```tsx
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from "react-native-reanimated";
import { Gesture, GestureDetector } from "react-native-gesture-handler";

const offset = useSharedValue(0);

const style = useAnimatedStyle(() => ({
  transform: [{ translateX: offset.value }],
}));

const pan = Gesture.Pan().onUpdate((e) => {
  offset.value = e.translationX;
});

return (
  <GestureDetector gesture={pan}>
    <Animated.View style={style} />
  </GestureDetector>
);
```

- Use `GestureDetector` + `Gesture.*` (not the old `PanResponder`)
- Animate GPU-friendly properties: `transform`, `opacity` — not `left`/`top`
- Shared values must not be destructured in worklets if using React Compiler

## Anti-Patterns

- ❌ Use `TouchableOpacity` — use `Pressable`
- ❌ Use React Native `<Image>` — use `expo-image`
- ❌ Inline styles on FlatList props (causes re-renders)
- ❌ `&&` with falsy non-boolean values in JSX
- ❌ Store scroll position in state — use ref
- ❌ Use `navigate()` from React Navigation directly — use `router.*` from expo-router
