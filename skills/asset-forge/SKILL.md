---
name: asset-forge
description: Use the asset-forge CLI to generate and process image and video assets from the command line. Covers all commands: favicons, app icons, OG images, promo sets, PWA icons, optimization, video conversion, placeholders, and more. Trigger on any request to generate icons, favicons, OG images, app icons, marketing assets, sprite sheets, image thumbnails, video conversion, or bulk image processing using asset-forge.
---

# asset-forge

Complete CLI toolkit for generating and processing image and video assets.

**Install:** `brew tap Ricka7x/asset-forge && brew install asset-forge`

**Dependencies:**
- ImageMagick — required for all image commands
- ffmpeg — required for all video commands
- svgo — optional, SVG optimization
- exiftool — optional, faster metadata stripping

```bash
brew install imagemagick ffmpeg
```

---

## Configuration

Settings persist in `~/.config/asset-forge/config.json`.

```bash
forge config set outDir ~/Desktop/assets      # default output directory
forge config set fontBold /path/to/Bold.ttf   # bold font for text overlays
forge config set fontRegular /path/to/Regular.ttf
forge config get
forge config reset
```

### Output directory — always optional

The output argument is optional on every command. Priority order:

1. Explicit argument — `asset-forge favicon logo.png ./public`
2. `FORGE_OUT` env var — overrides for a single run
3. `outDir` config value — persistent default
4. Current working directory — fallback

If no `outDir` is configured and no explicit output is given, asset-forge writes to the current directory and prints a setup tip. Set a default to suppress it:

```bash
forge config set outDir ~/Desktop/assets
```

Override output dir per-run:
```bash
FORGE_OUT=/tmp/preview asset-forge og-image -b photo.jpg
```

Override font per-run:
```bash
FORGE_FONT_BOLD=/path/to/Bold.ttf asset-forge promo -b bg.jpg -l logo.png -t "Title"
```

---

## Image Generation Commands

### favicon — Complete web favicon set
```bash
asset-forge favicon <logo> [output_dir] [--ico-only]

asset-forge favicon logo.png ./public
asset-forge favicon logo.png ./public --ico-only           # just favicon.ico
asset-forge favicon logo.png ./public/icon.ico --ico-only  # custom path
```

Outputs: `favicon.ico`, `favicon-16x16.png`, `favicon-32x32.png`, `apple-touch-icon.png`, `android-chrome-192x192.png`, `android-chrome-512x512.png`, `site.webmanifest`

HTML snippet:
```html
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
```

---

### app-icons — Native app icon sets
```bash
asset-forge app-icons <logo> [output_dir] [--platform macos|ios|android]

asset-forge app-icons logo.png                                         # macOS (default)
asset-forge app-icons logo.png MyApp.appiconset --platform macos
asset-forge app-icons logo.png --platform ios
asset-forge app-icons logo.png app/src/main/res --platform android
```

| Platform | Output | Contents |
|---|---|---|
| `macos` | `AppIcon.appiconset` | 16–1024px, squircle mask, `Contents.json` |
| `ios` | `AppIcon.appiconset` | 20–1024px all sizes, `Contents.json` |
| `android` | `res/` | `mipmap-*/ic_launcher.png`, round variants, Play Store 512px |

---

### pwa-icons — PWA icon set with maskable variants
```bash
asset-forge pwa-icons <logo> [output_dir] [bg_color]

asset-forge pwa-icons logo.png
asset-forge pwa-icons logo.png ./pwa "#1a1a2e"   # dark bg for maskable icons
```

Generates all required sizes + maskable variants with safe zone. Outputs a `manifest.json` snippet to merge.

---

### og-image — Open Graph image (1200x630)
```bash
asset-forge og-image -b <image> [-t headline] [-s subtitle] [-l logo] [-o output.png] [-g gravity] [-c overlay] [-f text_color]

asset-forge og-image -b hero.jpg                                        # plain crop
asset-forge og-image -b hero.jpg -t "App Name" -s "Your tagline"
asset-forge og-image -b hero.jpg -l logo.png -t "App Name" -s "Tagline" -o og.png
```

| Flag | Default | Description |
|------|---------|-------------|
| `-b` | required | Background image |
| `-t` | — | Headline text |
| `-s` | — | Subtitle text |
| `-l` | — | Logo (shown left) |
| `-o` | `og-image.png` | Output file |
| `-g` | `Center` | Crop gravity: `Center`, `North`, `South`, etc. |
| `-c` | `rgba(0,0,0,0.45)` | Overlay color (applied when text/logo present) |
| `-f` | `white` | Text color |

---

### promo — Full marketing asset set
```bash
asset-forge promo -b <background> -l <logo> -t <headline> [-s <subtitle>] [-c <overlay>] [-f <text_color>] [-o <output_dir>]

asset-forge promo -b bg.jpg -l logo.png -t "App Name" -s "The tagline"
asset-forge promo -b bg.jpg -l logo.png -t "Launch Sale" -s "50% off" -c "rgba(0,0,80,0.6)" -o ./marketing
```

Outputs:

| File | Size | Use |
|------|------|-----|
| `promo-appstore-iphone.png` | 1290×2796 | App Store iPhone 15 Pro Max |
| `promo-appstore-ipad.png` | 2048×1536 | App Store iPad landscape |
| `promo-social-square.png` | 1080×1080 | Instagram / Facebook post |
| `promo-social-story.png` | 1080×1920 | Stories / Reels / TikTok |
| `promo-twitter-banner.png` | 1500×500 | Twitter/X profile banner |
| `promo-og.png` | 1200×630 | Open Graph / LinkedIn |

---

### feature-graphic — Google Play feature graphic (1024x500)
```bash
asset-forge feature-graphic -b <bg> -t <headline> [-l logo] [-s subtitle] [-o output.png]

asset-forge feature-graphic -b bg.jpg -l logo.png -t "App Name" -s "Tagline"
```

---

### github-social — GitHub social preview (1280x640)
```bash
asset-forge github-social -b <bg> -t <headline> [-l logo] [-s subtitle] [-o output.png]

asset-forge github-social -b bg.jpg -l logo.png -t "my-repo" -s "One-line description"
```

Upload at: **Settings → Social preview → Edit → Upload image**

---

### email-banner — Email header banner (600x200)
```bash
asset-forge email-banner -b <bg> [-l logo] [-t headline] [-s subtitle] [-o output.png]

asset-forge email-banner -b bg.jpg -l logo.png -t "We just launched!" -s "Check it out"
```

---

## Image Processing Commands

### optimize — Compress images (AVIF > WebP > original)
```bash
asset-forge optimize <src> <dest> [quality]

asset-forge optimize ./images ./public/img
asset-forge optimize ./images ./public/img 80
asset-forge optimize hero.jpg ./public/img/hero.avif
QUALITY=75 asset-forge optimize ./images ./dist/img
```

Default quality: `95`. Also settable via `QUALITY=` env var.

---

### thumbnail — Center-cropped thumbnails
```bash
asset-forge thumbnail <src> <dest> [size] [gravity]

asset-forge thumbnail ./photos ./thumbs                   # 400x400 center crop
asset-forge thumbnail hero.jpg ./thumbs/hero.jpg 800x600
asset-forge thumbnail ./photos ./thumbs 400x400 North
```

---

### resize — Batch resize with ImageMagick spec syntax
```bash
asset-forge resize <file_or_dir> <spec> [output_dir]

asset-forge resize hero.jpg 1200            # 1200px wide, auto height
asset-forge resize hero.jpg 1200x630       # fit within box, preserve ratio
asset-forge resize hero.jpg 1200x630!      # force exact size
asset-forge resize hero.jpg 1200x630^      # fill and crop
asset-forge resize hero.jpg 50%            # scale to 50%
asset-forge resize ./photos 800 ./thumbs   # batch
```

---

### convert — Convert image format
```bash
asset-forge convert <input> <output.ext> [quality]

asset-forge convert logo.png logo.webp
asset-forge convert photo.jpg photo.avif 85
asset-forge convert image.webp image.png
```

---

### strip-meta — Strip EXIF metadata in-place
```bash
asset-forge strip-meta <file_or_dir>

asset-forge strip-meta photo.jpg
asset-forge strip-meta ./uploads
```

Uses `exiftool` if available, falls back to ImageMagick.

---

### watermark — Add logo or text watermark
```bash
asset-forge watermark <src> <dest> [-l logo] [-t text] [-p position] [-o opacity]

asset-forge watermark ./photos ./watermarked -l logo.png
asset-forge watermark photo.jpg watermarked.jpg -l logo.png
asset-forge watermark ./photos ./watermarked -t "© 2025 MyApp" -p SouthWest -o 50
```

Positions: `SouthEast` (default), `NorthEast`, `SouthWest`, `NorthWest`, `Center`
Opacity: 0–100, default 70.

---

### add-text — Text overlay on image
```bash
asset-forge add-text <input> <text> [output.png] [gravity] [size] [color] [font]

asset-forge add-text photo.jpg "Hello World"
asset-forge add-text photo.jpg "© 2025" caption.jpg South 32 white
```

---

### shadow — Drop shadow on PNG
```bash
asset-forge shadow <input> [output.png] [blur] [opacity] [offset_x] [offset_y] [color]

asset-forge shadow icon.png                          # blur=20, opacity=80, offset=10,10
asset-forge shadow icon.png shadow.png 30 60 15 15
asset-forge shadow icon.png shadow.png 20 90 0 0 "#333333"
```

---

### round-corners — Rounded corners with transparency
```bash
asset-forge round-corners <input> [output.png] [radius]

asset-forge round-corners photo.jpg rounded.png       # 10% radius
asset-forge round-corners photo.jpg rounded.png 24    # 24px
asset-forge round-corners photo.jpg rounded.png 15%   # 15% of width
```

---

### border — Add solid border
```bash
asset-forge border <file_or_dir> [output_dir] [size] [color]

asset-forge border photo.jpg                         # 4px black, in-place
asset-forge border photo.jpg bordered.jpg 8 white
asset-forge border ./photos ./bordered 2 "#FF0000"
```

---

### trim — Auto-trim transparent/white/black borders
```bash
asset-forge trim <file_or_dir> [output_dir] [fuzz]

asset-forge trim logo.png               # in-place
asset-forge trim logo.png trimmed.png
asset-forge trim ./exports ./trimmed 10  # batch, 10% tolerance
```

---

### sprites — Sprite sheet + CSS
```bash
asset-forge sprites <images_dir> [output_name] [css_prefix]

asset-forge sprites ./icons sprite .icon
```

Outputs `sprite.png` and `sprite.css`. Usage: `<span class="sprite sprite-arrow-left"></span>`

---

### montage — Image grid / collage
```bash
asset-forge montage <images_dir> [output.png] [columns] [tile_size] [gap]

asset-forge montage ./screenshots
asset-forge montage ./screenshots collage.png 3 600x600 20
```

---

### srcset — Retina variants (@1x, @2x, @3x)
```bash
asset-forge srcset <image> [output_dir] [scales]

asset-forge srcset hero.png ./img
asset-forge srcset logo.png ./img 1,2    # skip @3x
```

Prints the ready-to-use HTML `srcset` attribute.

---

## Placeholder Commands

### placeholder — LQIP (Low Quality Image Placeholder)
```bash
asset-forge placeholder <image> [output.png]

asset-forge placeholder hero.jpg                 # prints base64 data URI
asset-forge placeholder hero.jpg placeholder.png # saves PNG + prints URI
DATA_URI=$(asset-forge placeholder hero.jpg)     # capture URI
```

Generates a tiny 20px-wide blurred image as base64 data URI.

---

### blur-hash — BlurHash placeholder string
```bash
asset-forge blur-hash <image>
# Requires: pip install Pillow blurhash

asset-forge blur-hash hero.jpg
# → prints: LGF5?xYk^6#M@-5c,1J5@[or[Q6.
```

Set `X_COMPONENTS` and `Y_COMPONENTS` env vars to control detail (default: 4x3).

---

## Inspection & Utility Commands

### info — Image metadata inspector
```bash
asset-forge info <image> [image2 ...]

asset-forge info photo.jpg
asset-forge info *.png
```

Prints dimensions, format, file size, color space, EXIF data.

---

### audit — Audit images for issues
```bash
asset-forge audit <file_or_dir> [size_threshold_kb]

asset-forge audit ./public/images
asset-forge audit hero.jpg
asset-forge audit ./public/images 100
```

Checks: oversized files, PNG/JPG that could be WebP/AVIF, animated GIFs that should be video, missing @2x retina variants, suspiciously small images.

---

### palette — Extract dominant colors
```bash
asset-forge palette <image> [num_colors] [swatch.png]

asset-forge palette logo.png              # prints 6 hex codes
asset-forge palette photo.jpg 8 swatch.png
```

---

### compare — Visual side-by-side diff
```bash
asset-forge compare <image_a> <image_b> [output.png] [horizontal|vertical]

asset-forge compare before.png after.png diff.png
asset-forge compare original.jpg optimized.jpg diff.png vertical
```

---

### duplicates — Find visually similar images
```bash
asset-forge duplicates <dir> [threshold]
# Requires: pip install Pillow

asset-forge duplicates ./photos          # threshold 6 (default)
asset-forge duplicates ./photos 0        # exact duplicates only
asset-forge duplicates ./photos 12       # lenient (catches crops/resizes)
```

Uses perceptual hashing (dHash). Threshold 0–64 hamming distance.

---

### rename — Batch rename images
```bash
asset-forge rename <dir> [options]

asset-forge rename ./photos --slugify                    # "My Photo 1.jpg" → "my-photo-1.jpg"
asset-forge rename ./exports --prefix "app-" --slugify   # → "app-icon-dark.png"
asset-forge rename ./shots --sequence                    # → "0001.jpg", "0002.jpg"
asset-forge rename ./shots --sequence 10                 # start from 0010
asset-forge rename ./shots --prefix "hero-" --dry-run   # preview without renaming
```

---

### device-frame — Wrap screenshot in device mockup
```bash
asset-forge device-frame <screenshot> [output.png] [device]
# device: iphone (default), android, browser

asset-forge device-frame screenshot.png framed.png
asset-forge device-frame screenshot.png framed.png browser
```

---

## Video Commands

### gif-to-video — Animated GIF to mp4 + webm
```bash
asset-forge gif-to-video <input.gif> [output_dir]

asset-forge gif-to-video animation.gif ./video
```

Prints an HTML `<video>` snippet.

---

### video-to-gif — Video clip to optimized GIF
```bash
asset-forge video-to-gif <input_video> [output.gif] [fps] [width]

asset-forge video-to-gif demo.mp4
asset-forge video-to-gif demo.mp4 demo.gif 12 320   # 12fps, 320px wide
```

Uses 2-pass palette approach for best color quality.

---

### convert-video — Convert between video formats
```bash
asset-forge convert-video <input> <output.ext> [quality]
# quality: CRF 0-51 (lower = better), default 23

asset-forge convert-video clip.mov output.mp4
asset-forge convert-video clip.mp4 output.webm
asset-forge convert-video clip.mp4 output.gif
```

Supported: `.mp4`, `.webm`, `.mov`, `.gif`

---

### trim-video — Cut video clip (no re-encode)
```bash
asset-forge trim-video <input> <start> <end> [output]
# Times: HH:MM:SS, MM:SS, or plain seconds

asset-forge trim-video demo.mp4 0:30 1:45
asset-forge trim-video demo.mp4 90 150 clip.mp4
```

---

### compress-video — Shrink video for sharing
```bash
asset-forge compress-video <input> [output] [target_mb]

asset-forge compress-video video.mp4                    # quality mode (720p max, CRF 28)
asset-forge compress-video video.mp4 small.mp4 8        # target 8MB (WhatsApp)
asset-forge compress-video video.mp4 email.mp4 25       # target 25MB (email)
```

---

### extract-frames — Pull frames from video as images
```bash
asset-forge extract-frames <video> [output_dir] [mode] [--format png|webp|jpg] [--count N] [--scroll]
# mode: 1 (1fps, default), 0.5 (1 every 2s), 24 (24fps), all (every frame)

asset-forge extract-frames demo.mp4
asset-forge extract-frames demo.mp4 ./frames all
asset-forge extract-frames demo.mp4 ./frames 0.25       # 1 frame every 4 seconds
asset-forge extract-frames demo.mp4 --count 60          # exactly 60 frames evenly distributed
asset-forge extract-frames demo.mp4 --scroll            # scroll animation: 60 WebP frames + manifest.json + JS snippet
asset-forge extract-frames demo.mp4 --scroll --count 30 # scroll mode with custom frame count
```

---

## Common Workflows

### New web project — generate all web assets from logo
```bash
asset-forge favicon logo.png ./public
asset-forge pwa-icons logo.png ./public/icons
asset-forge og-image -b hero.jpg -l logo.png -t "App Name" -s "Tagline" -o ./public/og.png
```

### New app — generate platform icon sets
```bash
asset-forge app-icons logo.png --platform macos
asset-forge app-icons logo.png --platform ios
asset-forge app-icons logo.png app/src/main/res --platform android
```

### Marketing launch — full promo set
```bash
asset-forge promo -b background.jpg -l logo.png -t "App Name" -s "Tagline" -o ./marketing
asset-forge feature-graphic -b background.jpg -l logo.png -t "App Name" -s "Tagline"
asset-forge github-social -b background.jpg -l logo.png -t "repo-name" -s "What it does"
```

### Optimize images before shipping
```bash
asset-forge audit ./public/images          # find issues first
asset-forge strip-meta ./public/images     # remove EXIF
asset-forge optimize ./public/images ./dist/images 85
```
