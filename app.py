"""Kizuna QR -- FastAPI backend.

Serves the single-page frontend and generates styled QR PNGs via the
real-matrix renderer in qr_core.render_qr.
"""

import base64
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import qr_core

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
STATIC_HTML = STATIC_DIR / "index.html"

app = FastAPI(title="Kizuna QR")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class GenerateRequest(BaseModel):
    content: str = Field(..., max_length=2048)
    scheme: str = "hinokami"
    fg: str | None = None
    bg: str | None = None
    round: bool = False
    emblem: bool = True
    frame: str = "none"
    emblem_data_url: str | None = None
    ec: str = "H"
    text: str | None = None
    text_font: str = "inter"
    text_pos: str = "bottom"
    text_theme: str = "accent"



@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = STATIC_HTML.read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.post("/generate")
def generate(req: GenerateRequest) -> JSONResponse:
    content = (req.content or "").strip()
    if not content:
        return JSONResponse(status_code=400, content={"error": "content is empty"})
        
    if req.emblem_data_url and len(req.emblem_data_url) > 1_500_000:
        return JSONResponse(status_code=400, content={"error": "Logo image too large. Max allowed is ~1MB."})

    try:
        png = qr_core.render_qr(
            content,
            scheme=req.scheme,
            fg=req.fg,
            bg=req.bg,
            round_mods=req.round,
            emblem=req.emblem,
            frame=req.frame,
            logo_b64=req.emblem_data_url,
            ec=req.ec,
            text=req.text,
            text_font=req.text_font,
            text_pos=req.text_pos,
            text_theme=req.text_theme,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:  # noqa: BLE001 -- never crash, return 500
        return JSONResponse(status_code=500, content={"error": "server error"})

    b64 = base64.b64encode(png).decode("ascii")
    return JSONResponse(status_code=200, content={"data": "data:image/png;base64," + b64})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
