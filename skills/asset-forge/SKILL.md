---
name: asset-forge
description: "Use the asset-forge CLI or programmatic API to generate and process image and video assets. Covers all 38 commands: favicons, app icons, OG images, marketing assets, video conversion, optimization, resizing, color extraction, and more. Trigger on any request to generate icons, favicons, OG images, app icons, marketing assets, image thumbnails, video clips, or bulk asset processing."
---

# asset-forge

The complete asset toolkit for developers. High-performance image and video processing available via CLI and Node.js library.

**Install:** `npm install -g asset-forge` or `brew install ricka7x/tap/asset-forge`

**Zero system dependencies required.**

---

## Configuration

Settings are stored in `~/.config/asset-forge/config.json`.

```bash
forge config set outDir ~/Desktop/assets      # default output directory
forge config set fontBold /path/to/Bold.ttf     # bold font for text overlays
forge config set fontRegular /path/to/Reg.ttf   # regular font for text overlays
forge config get                                # show all settings
forge config reset                              # restore defaults
```

**Resolution Priority:** Explicit Arg > `FORGE_OUT` Env > `outDir` Config > CWD.

---

## Programmatic API

Asset Forge is a first-class Node.js library for your build scripts.

```javascript
import { optimize, resize, ogImage, promo, configure } from 'asset-forge'

// Setup defaults
configure({ outDir: './public', fontBold: './fonts/Inter-Bold.ttf' })

// High-level generation
await ogImage({ title: 'Modern Asset Forge', background: 'bg.jpg' })

// Marketing suites
await promo({ background: 'hero.jpg', logo: 'logo.png', title: 'Launch Sale' })

// Batch processing
await optimize('./src/images/**/*.{jpg,png}')
```

---

## Core Command Groups

### 🖼️ Image Processing
- `optimize <src> [dest] [quality]`: Compress to AVIF/WebP.
- `resize <src> <spec> [dest]`: Smart resizing (e.g., `800`, `800x600^`, `50%`).
- `thumbnail <src> <dest> [size]`: Center-cropped thumbnails.
- `shadow <src> [dest] [blur] [opacity]`: Professional drop shadows.
- `round-corners <src> [dest] [radius]`: Apply squircle/rounded corners.
- `palette <src> [count]`: Extract dominant hex codes.
- `placeholder <src>`: Generate LQIP Base64 data URI.

### 🌐 Web & Icons
- `favicon <logo> [dest]`: Generate `.ico`, Apple touch icons, and `site.webmanifest`.
- `app-icons <logo> [dest] --platform macos|ios|android`: Generate Xcode/Android iconsets.
- `og-image <title> -b <bg> -s [subtitle]`: Generate social sharing images (1200x630).
- `pwa-icons <logo> [dest]`: Generate maskable icons for PWA manifests.

### 📈 Marketing Suite
- `promo -b <bg> -l <logo> -t <title>`: Generate App Store, Instagram, and OG assets in one go.
- `feature-graphic -b <bg> -t <title> -l <logo>`: Google Play Store featured banner (1024x500).
- `github-social -b <bg> -t <title> -l <logo>`: GitHub repository social preview (1280x640).
- `email-banner -b <bg> -t <title>`: Optimized newsletter headers (600x200).

### 📹 Video & Animation
- `gif-to-video <gif> [dest]`: Convert heavy GIFs to high-performance MP4/WebM.
- `video-to-gif <video> [dest]`: High-quality 2-pass GIF creation.
- `extract-frames <video> [dest] [mode]`: Batch export frames as images.
- `compress-video <video> [dest] [targetMb]`: Social/Email video optimization.

---

## License: MIT
