# Image / AI Testing (TipJar)

AI tip analysis uses Gemini (gemini-3.1-pro-preview) via EMERGENT_LLM_KEY.

## Rules
- Use base64-encoded JPEG/PNG/WEBP only. No SVG/BMP/HEIC.
- Do NOT use blank/solid-color images; must contain real visual features.
- First frame only for animated formats. Resize oversized images.

## Endpoint
- POST /api/tips/analyze  (multipart: file=<image>, text=<string>) (auth) ->
  {home_team, away_team, match_time, country, league, market, odds, rating(1-10), analysis, image_path}
- POST /api/tips {raw_text, image_path, home_team, away_team, match_time, country, league, market, odds, ai_rating, ai_analysis} (auth) -> saved tip

Note: If AI fails, endpoint returns a neutral fallback (rating 5) so the flow never blocks.
