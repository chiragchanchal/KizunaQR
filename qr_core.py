"""
Kizuna QR -- QR CORE module.

Self-contained rendering of a REAL QR matrix into a large, styled PNG.
No mocks: every dark pixel below derives from the actual qrcode library
matrix, so preview and download bytes are identical.

Public API
----------
render_qr(content, scheme="hinokami", fg=None, bg=None, round_mods=False,
          emblem=True, ec="H") -> bytes     # PNG bytes
PRESETS -- dict mapping scheme name -> {fg, bg, accent}
"""

import io
from qrcode import QRCode, constants
from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Preset palettes -- muted Demon Slayer restraint, no neon.
# ---------------------------------------------------------------------------
PRESETS = {
    "hinokami":  {"fg": "#1B2030", "bg": "#F4EFE6", "accent": "#C13B2F"},
    "muzan":     {"fg": "#191919", "bg": "#E8E6E1", "accent": "#4B3F5E"},
    "urokodaki": {"fg": "#16201F", "bg": "#EAF0EC", "accent": "#8B8A6E"},
    "keepsake":  {"fg": "#22222A", "bg": "#F2EFE7", "accent": "#A8794A"},
    "zenitsu":   {"fg": "#2B2013", "bg": "#F8ECD4", "accent": "#ECA43B"},
    "inosuke":   {"fg": "#1C252B", "bg": "#E6EEF2", "accent": "#4D768A"},
    "rengoku":   {"fg": "#2D1612", "bg": "#F9EAE1", "accent": "#D14F33"},
    "tengen":    {"fg": "#281C2D", "bg": "#F4EAF6", "accent": "#9E416F"},
    "giyu":      {"fg": "#17202B", "bg": "#E5EEF5", "accent": "#315975"},
    "shinobu":   {"fg": "#231B2D", "bg": "#F2E8F8", "accent": "#7B5091"},
}


def _hex(color):
    """Normalize a hex color string to an (r, g, b, 255) RGBA tuple."""
    if color is None:
        return (0, 0, 0, 255)
    s = color.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def _is_finder(m, r, c):
    """True if the 7x7 block at (r,c) is a canonical finder pattern."""
    n = len(m)
    if r + 7 > n or c + 7 > n:
        return False
    for dr in range(7):
        for dc in range(7):
            in_inner = (1 <= dr <= 5) and (1 <= dc <= 5)
            in_center = (2 <= dr <= 4) and (2 <= dc <= 4)
            expected = (not in_inner) or in_center  # outer frame + center dark
            if m[r + dr][c + dc] != expected:
                return False
    return True

from pathlib import Path

DEFAULT_LOGO_PATH = Path(__file__).parent / "static" / "logo.png"


def render_qr(content, scheme="hinokami", fg=None, bg=None, round_mods=False,
              emblem=True, ec="H", logo_path=None, logo_b64=None, frame="none",
              text=None, text_font="inter", text_pos="bottom", text_theme="accent"):
    """
    Render `content` into a styled PNG (bytes).

    Real qrcode matrix at generous 1280x1280 with a large quiet zone.
    Default error correction H (or Q) keeps it scannable under overlays.
    """
    if not content or not str(content).strip():
        raise ValueError("content is empty")

    ec_map = {"H": constants.ERROR_CORRECT_H, "Q": constants.ERROR_CORRECT_Q}
    if ec not in ec_map:
        raise ValueError("ec must be 'H' or 'Q'")

    preset = PRESETS.get(scheme, PRESETS["hinokami"])
    _fg = _hex(fg if fg else preset["fg"])
    _bg = _hex(bg if bg else preset["bg"])
    _accent = _hex(preset["accent"])

    # 1) Compute the REAL matrix. version=None lets the QR auto-grow; the
    #    lib raises DataOverflowError if content cannot be fit.
    qr = QRCode(version=None, error_correction=ec_map[ec],
                box_size=40, border=6)
    qr.add_data(str(content))
    try:
        qr.make(fit=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("QR content too long to encode: %s" % exc)

    matrix = qr.get_matrix()   # list[list[bool]] -> the REAL grid
    n = len(matrix)            # module count including the quiet zone
    box = 40
    size = n * box

    img = Image.new("RGBA", (size, size), _bg)
    d = ImageDraw.Draw(img)

    rr = box * 0.18 if round_mods else 0
    pad = max(1, int(box * 0.04)) if round_mods else 0

    def _cell(x0, y0, x1, y1, fill):
        if round_mods:
            d.rounded_rectangle([x0, y0, x1, y1], radius=rr, fill=fill)
        else:
            d.rectangle([x0, y0, x1, y1], fill=fill)

    # Locate the finder patterns FIRST (they are drawn square).
    eye_locations = [(0, 0), (0, n - 7), (n - 7, 0)]

    def _in_eye(r, c):
        for (er, ec) in eye_locations:
            if er <= r < er + 7 and ec <= c < ec + 7:
                return True
        return False

    # 2) Draw all dark modules from the real matrix.
    for r in range(n):
        for c in range(n):
            if not matrix[r][c]:
                continue
            if _in_eye(r, c):
                d.rectangle([c * box, r * box,
                             (c + 1) * box, (r + 1) * box], fill=_fg)
            else:
                x0 = c * box + pad
                y0 = r * box + pad
                x1 = (c + 1) * box - pad
                y1 = (r + 1) * box - pad
                _cell(x0, y0, x1, y1, _fg)

    # 3) Restore the canonical nested-squares eye on each finder.
    for (er, ec) in eye_locations:
        for dr in range(7):
            for dc in range(7):
                if (dr in (0, 6)) or (dc in (0, 6)):
                    if matrix[er + dr][ec + dc]:
                        d.rectangle([(ec + dc) * box, (er + dr) * box,
                                     (ec + dc + 1) * box, (er + dr + 1) * box],
                                    fill=_fg)
                elif 2 <= dr <= 4 and 2 <= dc <= 4:
                    if matrix[er + dr][ec + dc]:
                        d.rectangle([(ec + dc) * box, (er + dr) * box,
                                     (ec + dc + 1) * box, (er + dr + 1) * box],
                                    fill=_fg)

    # 4) Optional centered emblem: custom image logo or geometric mark (~14% width).
    if emblem:
        _draw_emblem(img, d, size, _accent, _fg, _bg, logo_path, logo_b64)

    # 5) Handle Custom Framing if requested
    if frame and frame != "none":
        margin = int(size * 0.15)
        
        if frame == "circular":
            import math
            circle_radius = int((size * math.sqrt(2)) / 2) + margin // 2
            framed_size = circle_radius * 2
            framed_img = Image.new("RGBA", (framed_size, framed_size), (0,0,0,0))
            fd = ImageDraw.Draw(framed_img)
            
            # background
            fd.ellipse([margin//4, margin//4, framed_size - margin//4, framed_size - margin//4], fill=_bg)
            
            # ring
            ring_width = max(4, int(size * 0.03))
            for i in range(ring_width):
                ratio = i / ring_width
                r = int(_fg[0] * (1 - ratio) + _accent[0] * ratio)
                g = int(_fg[1] * (1 - ratio) + _accent[1] * ratio)
                b = int(_fg[2] * (1 - ratio) + _accent[2] * ratio)
                fd.ellipse([margin//4 + i, margin//4 + i, framed_size - margin//4 - i, framed_size - margin//4 - i], outline=(r,g,b,255), width=2)
                
            framed_img.paste(img, (framed_size//2 - size//2, framed_size//2 - size//2))
            img = framed_img
            
        else:
            framed_size = size + margin * 2
            bg_color = (0,0,0,0) if frame in ("card", "sticker", "bubble") else _bg
            framed_img = Image.new("RGBA", (framed_size, framed_size), bg_color)
            fd = ImageDraw.Draw(framed_img)
            
            pad = margin // 2
            bw = max(3, int(size * 0.015))
            
            if frame == "card":
                shadow = int(margin * 0.2)
                # shadow
                fd.rounded_rectangle([pad + shadow, pad + shadow, framed_size - pad + shadow, framed_size - pad + shadow], radius=margin//2, fill=(0,0,0,40))
                # card background
                fd.rounded_rectangle([pad, pad, framed_size - pad, framed_size - pad], radius=margin//2, fill=_bg, outline=_accent, width=bw)
                
            elif frame == "sticker":
                inner_w = framed_size - 2 * pad
                scallops = 10
                radius = inner_w // (scallops * 2)
                actual_w = radius * 2 * scallops
                pad_x = (framed_size - actual_w) // 2
                pad_y = pad_x
                # draw scallops
                for i in range(scallops):
                    x = pad_x + i * 2 * radius + radius
                    fd.ellipse([x - radius, pad_y, x + radius, pad_y + radius*2], fill=_bg)
                    fd.ellipse([x - radius, framed_size - pad_y - radius*2, x + radius, framed_size - pad_y], fill=_bg)
                for i in range(scallops):
                    y = pad_y + i * 2 * radius + radius
                    fd.ellipse([pad_x, y - radius, pad_x + radius*2, y + radius], fill=_bg)
                    fd.ellipse([framed_size - pad_x - radius*2, y - radius, framed_size - pad_x, y + radius], fill=_bg)
                # center fill
                fd.rectangle([pad_x + radius, pad_y, framed_size - pad_x - radius, framed_size - pad_y], fill=_bg)
                fd.rectangle([pad_x, pad_y + radius, framed_size - pad_x, framed_size - pad_y - radius], fill=_bg)
                # outline
                for i in range(scallops):
                    x = pad_x + i * 2 * radius + radius
                    fd.arc([x - radius, pad_y, x + radius, pad_y + radius*2], 180, 0, fill=_fg, width=bw)
                    fd.arc([x - radius, framed_size - pad_y - radius*2, x + radius, framed_size - pad_y], 0, 180, fill=_fg, width=bw)
                for i in range(scallops):
                    y = pad_y + i * 2 * radius + radius
                    fd.arc([pad_x, y - radius, pad_x + radius*2, y + radius], 90, 270, fill=_fg, width=bw)
                    fd.arc([framed_size - pad_x - radius*2, y - radius, framed_size - pad_x, y + radius], 270, 90, fill=_fg, width=bw)
            
            elif frame == "bubble":
                fd.rounded_rectangle([pad, pad, framed_size - pad, framed_size - pad - margin], radius=margin, fill=_bg, outline=_fg, width=bw)
                tail_w = margin
                tail_h = margin
                center = framed_size // 2
                fd.polygon([(center - tail_w//2, framed_size - pad - margin),
                            (center, framed_size - pad),
                            (center + tail_w//2, framed_size - pad - margin)], fill=_bg)
                fd.line([(center - tail_w//2, framed_size - pad - margin), (center, framed_size - pad)], fill=_fg, width=bw)
                fd.line([(center, framed_size - pad), (center + tail_w//2, framed_size - pad - margin)], fill=_fg, width=bw)
                # clear overlapping line
                fd.line([(center - tail_w//2 + bw, framed_size - pad - margin), (center + tail_w//2 - bw, framed_size - pad - margin)], fill=_bg, width=bw+2)
            
            else:
                fd.rectangle([0, 0, framed_size, framed_size], fill=_bg)

            # Paste QR Code over background
            if frame == "bubble":
                framed_img.paste(img, (margin, margin - margin // 2), img if img.mode == "RGBA" else None)
            else:
                framed_img.paste(img, (margin, margin), img if img.mode == "RGBA" else None)
            
            if frame == "scan_me":
                fd.rounded_rectangle([pad, pad, framed_size - pad, framed_size - pad], radius=margin//2, outline=_fg, width=bw)
                banner_w = margin * 3
                banner_h = int(margin * 0.8)
                banner_x0 = framed_size // 2 - banner_w // 2
                banner_y0 = framed_size - pad - banner_h // 2
                banner_x1 = framed_size // 2 + banner_w // 2
                banner_y1 = framed_size - pad + banner_h // 2
                
                tail_w = int(margin * 0.4)
                tail_y = banner_y0 + banner_h // 3
                fd.polygon([(banner_x0, tail_y), (banner_x0 - tail_w, banner_y1), (banner_x0, banner_y1)], fill=_fg)
                fd.polygon([(banner_x1, tail_y), (banner_x1 + tail_w, banner_y1), (banner_x1, banner_y1)], fill=_fg)
                fd.rounded_rectangle([banner_x0, banner_y0, banner_x1, banner_y1], radius=max(2, int(margin*0.1)), fill=_accent)
                try:
                    from PIL import ImageFont
                    try:
                        font = ImageFont.truetype("arial.ttf", size=int(banner_h * 0.6))
                    except IOError:
                        font = ImageFont.load_default()
                    text_to_draw = text if text and text.strip() else "SCAN ME"
                    left, top, right, bottom = font.getbbox(text_to_draw)
                    tw = right - left
                    th = bottom - top
                    fd.text((framed_size//2 - tw//2, banner_y0 + (banner_h - th)//2 - int(banner_h*0.1)), text_to_draw, font=font, fill=_bg)
                except Exception:
                    pass

            elif frame == "viewfinder":
                L = margin * 1.5
                # corner marks
                fd.line([(pad, pad + L), (pad, pad), (pad + L, pad)], fill=_fg, width=bw, joint="curve")
                fd.line([(framed_size - pad - L, pad), (framed_size - pad, pad), (framed_size - pad, pad + L)], fill=_fg, width=bw, joint="curve")
                fd.line([(pad, framed_size - pad - L), (pad, framed_size - pad), (pad + L, framed_size - pad)], fill=_fg, width=bw, joint="curve")
                fd.line([(framed_size - pad - L, framed_size - pad), (framed_size - pad, framed_size - pad), (framed_size - pad, framed_size - pad - L)], fill=_fg, width=bw, joint="curve")
                
                # top camera accent
                cx = framed_size // 2
                cy = pad
                cw = margin // 3
                fd.rectangle([cx - cw, cy - cw//2, cx + cw, cy + cw//2], outline=_accent, width=max(2, bw//2))
                fd.ellipse([cx - cw//2, cy - cw//2, cx + cw//2, cy + cw//2], outline=_accent, width=max(2, bw//2))

            img = framed_img

    if text and text.strip():
        img = _draw_custom_text(img, text.strip(), text_font, text_pos, text_theme, size, _fg, _bg, _accent)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def _draw_emblem(img, d, size, accent, ink, bg_color, logo_path=None, logo_b64=None):
    """
    Draw image logo if available, or fall back to geometric emblem.
    Keeps bounding box modest (~10% of width) so scannability is strictly preserved.
    """
    import base64
    logo_img = None
    
    if logo_b64:
        try:
            # Handle data:image/png;base64,... prefix
            if "," in logo_b64:
                logo_b64 = logo_b64.split(",")[1]
            img_data = base64.b64decode(logo_b64)
            logo_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        except Exception:
            pass

    if not logo_img:
        target_logo = Path(logo_path) if logo_path else DEFAULT_LOGO_PATH
        if target_logo and target_logo.exists():
            try:
                logo_img = Image.open(target_logo).convert("RGBA")
            except Exception:
                pass
            
    if logo_img:
        try:
            max_dim = int(size * 0.08)
            c = size // 2
            badge_r = int(max_dim * 0.52)
            # Compact background badge circle
            d.ellipse([c - badge_r, c - badge_r, c + badge_r, c + badge_r],
                      fill=bg_color, outline=ink, width=max(2, size // 450))

            logo_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            lw, lh = logo_img.size
            pos = (c - lw // 2, c - lh // 2)
            img.paste(logo_img, pos, logo_img)
            return
        except Exception:
            pass  # Fall back to geometric emblem

    _draw_geometric_emblem(d, size, accent, ink)

def _draw_geometric_emblem(d, size, accent, ink):
    """Fallback geometric mark."""
    c = size // 2
    u = max(1, size // 128)
    sw = u * 3
    d.rounded_rectangle([c - sw // 2, c - u * 6, c + sw // 2, c + u * 6],
                        radius=sw // 2, fill=ink)
    for sign in (-1, 1):
        hx = u * 5
        pts = [(c + sign * u * 2 - hx, c - u * 3),
               (c + sign * u * 2, c - u * 6),
               (c + sign * u * 2 + hx, c - u * 3),
               (c + sign * u * 2, c + u)]
        d.polygon(pts, fill=ink)
    r = u * 3
    d.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=accent)

def _draw_custom_text(img, text, text_font, text_pos, text_theme, core_size, fg, bg, accent):
    if text_pos == "none":
        return img
        
    from PIL import ImageFont, ImageDraw
    
    font_files = {
        "inter": "arial.ttf",
        "playfair": "georgia.ttf",
        "caveat": "comic.ttf"
    }
    font_filename = font_files.get(text_font, "arial.ttf")
    
    fontsize = max(24, int(core_size * 0.06))
    try:
        font = ImageFont.truetype(font_filename, size=fontsize)
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", size=fontsize)
        except IOError:
            font = ImageFont.load_default()
            
    left, top, right, bottom = font.getbbox(text)
    tw = right - left
    th = bottom - top
    
    if text_theme == "accent":
        box_bg = accent
        text_color = bg
    elif text_theme == "dark":
        box_bg = fg
        text_color = bg
    else:
        box_bg = bg
        text_color = fg

    w, h = img.size
    
    if text_pos in ("top", "bottom"):
        pad = int(th * 1.5)
        new_h = h + pad + th
        new_img = Image.new("RGBA", (w, new_h), bg)
        if text_pos == "top":
            new_img.paste(img, (0, pad + th))
            tx = w // 2 - tw // 2
            ty = pad // 2
        else:
            new_img.paste(img, (0, 0))
            tx = w // 2 - tw // 2
            ty = h + pad // 2
            
        d = ImageDraw.Draw(new_img)
        if text_theme != "light":
            bar_y0 = 0 if text_pos == "top" else h
            bar_y1 = pad + th if text_pos == "top" else new_h
            d.rectangle([0, bar_y0, w, bar_y1], fill=box_bg)
            
        d.text((tx, ty), text, font=font, fill=text_color)
        return new_img
        
    elif text_pos == "pill":
        d = ImageDraw.Draw(img)
        pad_x = int(core_size * 0.05)
        pad_y = int(core_size * 0.03)
        pill_w = tw + pad_x * 2
        pill_h = th + pad_y * 2
        
        px = w // 2 - pill_w // 2
        py = h - int(core_size * 0.08) - pill_h // 2
        
        shadow_offset = int(core_size * 0.01)
        d.rounded_rectangle([px + shadow_offset, py + shadow_offset, px + pill_w + shadow_offset, py + pill_h + shadow_offset], radius=pill_h//2, fill=(0,0,0,50))
        d.rounded_rectangle([px, py, px + pill_w, py + pill_h], radius=pill_h//2, fill=box_bg, outline=fg, width=max(2, int(core_size*0.005)))
        d.text((px + pad_x, py + pad_y - int(th*0.1)), text, font=font, fill=text_color)
        return img
        
    return img




# ---------------------------------------------------------------------------
# Self-test: render, verify PNG, cross-check matrix dims, decode back.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np
    import cv2
    from PIL import Image as _Im

    print("=== Kizuna QR core self-test ===")

    def run(content, scheme, rounds, emb):
        try:
            png = render_qr(content, scheme=scheme, round_mods=rounds,
                            emblem=emb)
        except ValueError as e:
            print("FAIL ValueError %r -> %s" % (content, e))
            return False
        # a) valid PNG bytes
        magic = png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 0
        # b) independently recompute the matrix; confirm drawn pixel size
        q = QRCode(error_correction=constants.ERROR_CORRECT_H,
                   box_size=40, border=6)
        q.add_data(content)
        q.make(fit=True)
        m = q.get_matrix()
        im = _Im.open(io.BytesIO(png))
        dim_ok = im.size == (len(m) * 40, len(m) * 40)
        # c) decode the *rendered* PNG with a real decoder
        arr = np.frombuffer(png, dtype=np.uint8)
        imgcv = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        val, _, _ = cv2.QRCodeDetector().detectAndDecode(imgcv)
        decode_ok = val == content
        ok = magic and dim_ok and decode_ok
        print("input   : %r" % content)
        print("decoded : %r" % (val if decode_ok else "FAIL"))
        print("magic=%s dims=%s decode=%s" % (magic, dim_ok, decode_ok))
        print("matrix  : %d modules -> %s px" % (len(m), im.size))
        print("RESULT  : %s   [round=%s emblem=%s scheme=%s]"
              % ("PASS" if ok else "FAIL", rounds, emb, scheme))
        return ok

    r1 = run("https://example.com", "hinokami", False, True)
    r2 = run("Kizuna QR keepsake text", "urokodaki", True, True)
    r3 = run("keepsake plain text", "keepsake", False, False)
    print("=== ALL PASS ===" if (r1 and r2 and r3) else "=== SOME FAILED ===")
