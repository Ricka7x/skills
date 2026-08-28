# File Uploads (S3-compatible Storage)

Presigned URL uploads to S3-compatible storage (AWS S3, Cloudflare R2, MinIO). The server never holds the file bytes — it hands out short-lived URLs and the client uploads directly.

## Stack

- `@aws-sdk/client-s3` + `@aws-sdk/s3-request-presigner` (works with any S3-compatible provider).
- Bucket/region/endpoint/credentials come from env (ENV.md) — server only.
- In the app: S3 keys are per-org and per-user.

## The Two-Step Pattern

1. **`getUploadUrl`** — server generates a presigned PUT URL (short expiry) and returns a `fileId`.
2. Client PUTs the bytes straight to S3.
3. **`confirmUpload`** — server records metadata (URL/key, size, content type) in the DB.

```ts
// Step 1: presign
getUploadUrl: protectedProcedure
  .input(z.object({
    filename: z.string().max(255),
    contentType: z.enum(["image/png", "image/jpeg", "image/webp", "application/pdf"]),
    size: z.int().min(1).max(10 * 1024 * 1024), // 10MB cap
  }))
  .output(z.object({ uploadUrl: z.url(), fileId: z.uuid() }))
  .handler(async ({ input, context }) => {
    const fileId = crypto.randomUUID();
    const key = `uploads/${context.session.user.id}/${fileId}/${input.filename}`;
    const uploadUrl = await getSignedUrl(
      s3Client,
      new PutObjectCommand({
        Bucket: env.AWS_BUCKET_NAME,
        Key: key,
        ContentType: input.contentType,
      }),
      { expiresIn: 900 }, // 15 min
    );
    return { uploadUrl, fileId };
  }),

// Step 2: persist metadata
confirmUpload: protectedProcedure
  .input(z.object({ fileId: z.uuid(), url: z.url(), size: z.int(), contentType: z.string() }))
  .output(fileSchema)
  .handler(async ({ input, context }) => {
    const [file] = await db.insert(files).values({
      id: input.fileId,
      url: input.url,
      size: input.size,
      contentType: input.contentType,
      userId: context.session.user.id,
      orgId: /* from membership (MULTI-TENANCY.md) */,
    }).returning();
    return file;
  }),
```

## Key Naming Convention

```
uploads/{userId}/{fileId}/{filename}
```

- `userId` isolates per-user uploads; `fileId` (a UUID) makes keys unguessable and collision-free; `filename` is human-readable for the bucket UI.
- Never allow client-supplied keys/paths — always build the key server-side.

## Security

- **Content-type allowlist** — `z.enum` on the upload request, and set `ContentType` on the presign so S3 can't be told otherwise.
- **Size cap** — reject in the input schema and enforce via bucket policy/lambda for defense in depth.
- **Short expiry** (≤ 15 min) on presigned URLs.
- **Ownership on confirm** — the `fileId` came from *this* user's presign call; scope reads by `orgId`/`userId` (MULTI-TENANCY.md).
- Consider a bucket policy that blocks public reads if files are sensitive; serve via presigned GETs instead.

## Providers

Same client, different env:

| Provider | Env |
|---|---|
| AWS S3 | `AWS_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, region |
| Cloudflare R2 | `AWS_BUCKET_NAME`, endpoint `https://<account>.r2.cloudflarestorage.com`, R2 access keys |
| MinIO (local) | `AWS_BUCKET_NAME`, endpoint `http://localhost:9000`, local creds |

Always wire `endpoint` and `forcePathStyle` through env — don't hardcode a provider.

## Anti-Patterns

- ❌ Streaming file bytes through the server (defeats presigning)
- ❌ Client-supplied S3 key/path
- ❌ Long-lived or no-expiry presigned URLs
- ❌ Accepting arbitrary `contentType` / unbounded `size`
- ❌ Missing ownership check on `confirmUpload` / on reads
- ❌ Hardcoding a provider or bucket credentials
