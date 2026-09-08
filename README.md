# Kizuna QR

A Demon Slayer–inspired styled QR generator. Every pixel of the rendered
PNG derives from the **real** QR matrix (no mocks), so the on-screen
preview and the downloaded file are the same bytes. Styled options include
rounded modules, custom finder/eye styling, and a modest center emblem,
with high error correction (H/Q) to keep the code scannable under the
overlay.

## Run

```bash
uvicorn app:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

## API

- `GET /` — serves the single-page frontend.
- `POST /generate` — JSON body `{content, scheme, fg, bg, round, emblem, ec}`.
  Returns `{"data": "data:image/png;base64,<b64>"}` on success; `400 {"error": ...}`
  for empty/invalid content; `500 {"error": ...}` on unexpected failure.

## Preset palettes

Demo/preset colors include **Hinokami**, **Muzan**, **Urokodaki**, and
**Keepsake** (muted Demon Slayer restraint, no neon). The frontend also
supports a **Custom** palette with your own foreground/background hex colors.
