# TipJar → Google Play Store (TWA) Guide

TipJar is now an installable **PWA** (Progressive Web App). Users can install it directly via the
**"Download App"** button in the header (Android Chrome shows a native install prompt; iOS uses
Share → "Add to Home Screen"). To publish it on the **Google Play Store**, wrap the PWA as a
**Trusted Web Activity (TWA)** with Bubblewrap. No app rewrite needed.

## Ready-made assets (in /app/frontend/public)
- `icon-512.png` — 512×512 app icon (Play Store requires this)
- `icon-192.png` — 192×192
- `apple-touch-icon.png` — 180×180
- `manifest.json` — web app manifest (name, icons, theme #09090B, standalone)
- `service-worker.js` — offline shell + installability

You still need (create in a graphics tool): a **1024×500 Feature Graphic** and **2–8 phone
screenshots** for the store listing.

## Generated store graphics (ready to upload) — in /app/frontend/public/store
After you redeploy, these are reachable at your domain:
- Feature graphic (1024×500): `https://ai-credit-saver.emergent.host/store/feature-graphic.png`
- Screenshot 1 (AI rates every tip): `https://ai-credit-saver.emergent.host/store/screenshot-1.png`
- Screenshot 2 (Turn credits into real money): `https://ai-credit-saver.emergent.host/store/screenshot-2.png`
- App icon 512: `https://ai-credit-saver.emergent.host/icon-512.png`

## Prerequisites (your side)
1. **Google Play Developer account** — one-time $25 at https://play.google.com/console
2. Node.js + JDK 17 + Android SDK on your machine (Android Studio installs these).
3. Your deployed URL: `https://ai-credit-saver.emergent.host`

## Build the Android app (Bubblewrap)
```bash
npm i -g @bubblewrap/cli
bubblewrap init --manifest https://ai-credit-saver.emergent.host/manifest.json
# answer prompts: package id e.g. host.emergent.tipjar, app name TipJar,
# signing key (let it generate one — KEEP the .keystore + passwords safe!)
bubblewrap build
# produces app-release-signed.aab  (upload this to Play Console)
```

## Verify domain ownership (removes the browser URL bar)
Bubblewrap prints an `assetlinks.json`. Host it at:
`https://ai-credit-saver.emergent.host/.well-known/assetlinks.json`
(Ask Emergent Support to place this file, or add it to the deployed build.)

## Publish
1. Play Console → Create app → upload the `.aab`.
2. Fill store listing (icon 512, feature graphic, screenshots, description).
3. Complete content rating, data safety, and **note**: sports-betting-tip apps must comply with
   Google Play's Gambling policy — declare it as tips/information (no real-money wagering inside the
   app) and add an 18+ rating. Real-money credit purchase/redemption may need extra review.
4. Submit for review.

## Updating later
Because it's a TWA, most updates ship automatically when you redeploy the website — no new AAB
needed unless you change the icon, package id, or Android shell.
