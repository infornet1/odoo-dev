#!/usr/bin/env python3
"""
Cashea Campaign — Instagram Post + Story
Genera dos imágenes PNG listas para publicar:
  - Post  : 1080×1080 px (feed cuadrado)
  - Story : 1080×1920 px (historia vertical 9:16)

Paleta: Cashea amarillo #FFD600 / negro #111111 / blanco #FFFFFF
"""

import glob
import math
import os
from PIL import Image, ImageDraw, ImageFont

# ── rutas de salida ──────────────────────────────────────────────────────────
OUT_DIR  = "/home/ftpuser/odoo-dev"
OUT_POST  = os.path.join(OUT_DIR, "cashea_instagram_post.png")
OUT_STORY = os.path.join(OUT_DIR, "cashea_instagram_story.png")

# ── paleta ───────────────────────────────────────────────────────────────────
BLACK   = (17,  17,  17)
YELLOW  = (255, 214,  0)
WHITE   = (255, 255, 255)
GRAY    = (200, 200, 200)
DGRAY   = (120, 120, 120)
LGRAY   = (245, 245, 245)
GREEN   = (0,  160,  64)
YLIGHT  = (255, 240, 140)   # amarillo muy claro para fondos sutiles

# ── logo del colegio ─────────────────────────────────────────────────────────
LOGO_PATHS = (
    glob.glob('/home/ftpuser/odoo-dev/Instituto*Bello*.png') +
    glob.glob('/tmp/school_logo.png')
)
school_logo = Image.open(LOGO_PATHS[0]).convert("RGBA") if LOGO_PATHS else None

# ── fuentes ──────────────────────────────────────────────────────────────────
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

# ── helpers ──────────────────────────────────────────────────────────────────

def rounded_rect(draw, xy, radius, fill, outline=None, outline_width=0):
    """Dibuja un rectángulo con esquinas redondeadas."""
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                            outline=outline, width=outline_width)

def centered_text(draw, text, y, width, fnt, color):
    """Texto centrado horizontalmente."""
    bb = draw.textbbox((0, 0), text, font=fnt)
    tw = bb[2] - bb[0]
    draw.text(((width - tw) // 2, y), text, font=fnt, fill=color)

def logo_cashea_pill(img, x, y, height=56):
    """Dibuja la pastilla 'cashea' amarilla con texto negro."""
    fnt = font(int(height * 0.55), bold=True)
    tmp = Image.new("RGBA", img.size, (0,0,0,0))
    d   = ImageDraw.Draw(tmp)
    bb  = d.textbbox((0,0), "cashea", font=fnt)
    tw  = bb[2] - bb[0]
    pw  = tw + height          # padding horizontal = height/2 each side
    ph  = height
    d.rounded_rectangle([x, y, x+pw, y+ph], radius=ph//2,
                        fill=YELLOW + (255,))
    d.text((x + height//2, y + (ph - (bb[3]-bb[1]))//2 - bb[1]),
           "cashea", font=fnt, fill=BLACK + (255,))
    img.alpha_composite(tmp)
    return pw   # returns width of pill

def paste_logo(img, logo, max_w, max_h, x, y, center_x=False):
    """Pega el logo del colegio escalado, opcionalmente centrado en x."""
    if logo is None:
        return
    ratio = min(max_w / logo.width, max_h / logo.height)
    new_w = int(logo.width  * ratio)
    new_h = int(logo.height * ratio)
    resized = logo.resize((new_w, new_h), Image.LANCZOS)
    px = (img.width - new_w) // 2 if center_x else x
    if resized.mode == "RGBA":
        img.paste(resized, (px, y), resized)
    else:
        img.paste(resized, (px, y))

def stripe(draw, y, height, width, color):
    draw.rectangle([0, y, width, y + height], fill=color)

# ═══════════════════════════════════════════════════════════════════════════════
# POST  1080 × 1080
# ═══════════════════════════════════════════════════════════════════════════════

W, H = 1080, 1080
img = Image.new("RGB", (W, H), BLACK)
d   = ImageDraw.Draw(img)

# ── fondo: círculo decorativo amarillo difuso (top-right) ──
overlay = Image.new("RGBA", (W, H), (0,0,0,0))
od = ImageDraw.Draw(overlay)
od.ellipse([-100, -200, 700, 600], fill=YELLOW+(28,))   # muy suave
img.paste(Image.new("RGB", img.size, BLACK), (0,0))
img = Image.new("RGB", (W, H), BLACK)
d   = ImageDraw.Draw(img)

# franja amarilla superior
stripe(d, 0, 12, W, YELLOW)

# ── logos cabecera ──────────────────────────────────────────────────────────
# logo colegio (izquierda)
paste_logo(img, school_logo, max_w=380, max_h=80, x=60, y=44)

# pastilla cashea (derecha)
rgba_img = img.convert("RGBA")
pill_w = logo_cashea_pill(rgba_img, x=W - 300, y=44, height=68)
img = rgba_img.convert("RGB")
d   = ImageDraw.Draw(img)

# ── divider ─────────────────────────────────────────────────────────────────
stripe(d, 136, 4, W, YELLOW)

# ── bloque central ──────────────────────────────────────────────────────────
# etiqueta superior
centered_text(d, "¡NUEVA FORMA DE PAGAR EN EL COLEGIO!", 168, W,
              font(28, bold=True), YELLOW)

# título principal
centered_text(d, "Divide tu mensualidad", 230, W, font(62, bold=True), WHITE)
centered_text(d, "en cuotas quincenales", 302, W, font(62, bold=True), WHITE)

# pill precio
px0, py0 = 190, 390
px1, py1 = W - 190, 490
rounded_rect(d, [px0, py0, px1, py1], radius=50, fill=YELLOW)
centered_text(d, "Mensualidad: $197,38", py0 + 14, W, font(52, bold=True), BLACK)

# subtítulo sin interés
centered_text(d, "Sin intereses · Sin recargos · 0% extra", 514, W,
              font(32, bold=False), GRAY)

# ── tabla rápida niveles ─────────────────────────────────────────────────────
tx, ty, tw = 80, 575, W - 160
row_h = 60
# encabezado
rounded_rect(d, [tx, ty, tx+tw, ty+36], radius=8, fill=YELLOW)
d.text((tx+16, ty+8), "NIVEL", font=font(20, bold=True), fill=BLACK)
d.text((tx+tw//2 - 70, ty+8), "INICIAL", font=font(20, bold=True), fill=BLACK)
d.text((tx+tw - 180, ty+8), "CUOTA 14 DÍAS", font=font(20, bold=True), fill=BLACK)

levels = [
    ("🌱  Semilla  (nuevo)", "$118,43", "$78,95"),
    ("🌿  Raíz  (5 pagos)",  "$98,69",  "$98,69"),
    ("🍃  Hoja  (10 pagos)", "$78,95",  "más cuotas"),
    ("🌳  Tronco y superiores", "desde $49,35", "aún mejor ⭐"),
]
for i, (lvl, ini, cuota) in enumerate(levels):
    row_y = ty + 36 + i * row_h
    bg = (30, 30, 30) if i % 2 == 0 else (22, 22, 22)
    d.rectangle([tx, row_y, tx+tw, row_y+row_h], fill=bg)
    # thin yellow left border
    d.rectangle([tx, row_y, tx+4, row_y+row_h], fill=YELLOW)
    d.text((tx+16, row_y+16), lvl, font=font(23), fill=WHITE)
    d.text((tx+tw//2 - 60, row_y+16), ini, font=font(23, bold=True), fill=YELLOW)
    d.text((tx+tw - 175, row_y+16), cuota, font=font(21), fill=GRAY)

# línea cierre tabla
bottom_y = ty + 36 + len(levels) * row_h
d.rectangle([tx, bottom_y, tx+tw, bottom_y+3], fill=YELLOW)

# ── CTA descarga ─────────────────────────────────────────────────────────────
centered_text(d, "¡Descarga Cashea y empieza hoy!", bottom_y + 22, W,
              font(30, bold=True), WHITE)
centered_text(d, "Google Play  ·  App Store (iPhone)  ·  cashea.app",
              bottom_y + 64, W, font(25), YELLOW)

# franja amarilla inferior
stripe(d, H - 12, 12, W, YELLOW)

# ── pie ──────────────────────────────────────────────────────────────────────
centered_text(d, "Instituto Privado Andrés Bello — UEIPAB", H - 52, W,
              font(24, bold=True), GRAY)

img.save(OUT_POST, "PNG", optimize=True)
print(f"✓ Post guardado  : {OUT_POST}  ({W}×{H})")


# ═══════════════════════════════════════════════════════════════════════════════
# STORY  1080 × 1920
# ═══════════════════════════════════════════════════════════════════════════════

W, H = 1080, 1920
img = Image.new("RGB", (W, H), BLACK)
d   = ImageDraw.Draw(img)

# franja superior
stripe(d, 0, 14, W, YELLOW)

# ── zona segura top (sin cubrir handle de historia) ─────────────────────────
# logos — centrados
paste_logo(img, school_logo, max_w=420, max_h=90, x=0, y=80, center_x=True)

rgba_img = img.convert("RGBA")
pill_w = logo_cashea_pill(rgba_img, x=(W - 260)//2, y=190, height=72)
img = rgba_img.convert("RGB")
d   = ImageDraw.Draw(img)

stripe(d, 282, 5, W, YELLOW)

# ── aviso grande ─────────────────────────────────────────────────────────────
centered_text(d, "¡GRAN NOTICIA PARA NUESTRA", 316, W, font(44, bold=True), YELLOW)
centered_text(d, "COMUNIDAD!", 370, W, font(44, bold=True), YELLOW)

centered_text(d, "Ahora puedes pagar tu", 440, W, font(68, bold=True), WHITE)
centered_text(d, "mensualidad en", 518, W, font(68, bold=True), WHITE)
centered_text(d, "cuotas sin interés", 596, W, font(68, bold=True), WHITE)

# pill precio grande
rounded_rect(d, [100, 692, W-100, 800], radius=54, fill=YELLOW)
centered_text(d, "Mensualidad: $197,38", 706, W, font(58, bold=True), BLACK)

centered_text(d, "con Cashea · Sin intereses · 0% extra", 826, W,
              font(34), GRAY)

stripe(d, 886, 5, W, YELLOW)

# ── tabla niveles completa ───────────────────────────────────────────────────
centered_text(d, "DEPENDIENDO DE TU NIVEL", 910, W, font(32, bold=True), YELLOW)
centered_text(d, "tu inicial puede ser aún más bajo", 954, W, font(30), GRAY)

tx, ty, tw = 60, 1000, W - 120
row_h = 82

# encabezado tabla
rounded_rect(d, [tx, ty, tx+tw, ty+48], radius=10, fill=YELLOW)
d.text((tx+20, ty+12), "NIVEL", font=font(26, bold=True), fill=BLACK)
d.text((tx+tw//2 - 60, ty+12), "INICIAL", font=font(26, bold=True), fill=BLACK)
d.text((tx+tw - 230, ty+12), "CUOTA DÍA 14", font=font(26, bold=True), fill=BLACK)

levels_full = [
    ("🌱 Semilla",  "Nuevo usuario",     "$118,43", "$78,95"),
    ("🌿 Raíz",     "5 pagos o $120",    "$98,69",  "$98,69"),
    ("🍃 Hoja",     "10 pagos o $400",   "$78,95",  "más cuotas"),
    ("🌳 Tronco",   "20 pagos o $800",   "$49,35",  "más cuotas"),
    ("🌲 Árbol",    "40 pagos o $2.000", "$39,48",  "más cuotas"),
    ("🌻 Araguaney","80 pagos o $4.000", "desde 0%", "máx. flex."),
]
for i, (lvl, req, ini, cuota) in enumerate(levels_full):
    row_y = ty + 48 + i * row_h
    bg = (28, 28, 28) if i % 2 == 0 else (20, 20, 20)
    d.rectangle([tx, row_y, tx+tw, row_y+row_h], fill=bg)
    d.rectangle([tx, row_y, tx+5, row_y+row_h], fill=YELLOW)
    d.text((tx+18, row_y+14), lvl, font=font(28, bold=True), fill=WHITE)
    d.text((tx+18, row_y+50), req, font=font(22), fill=DGRAY)
    d.text((tx+tw//2 - 70, row_y+26), ini, font=font(30, bold=True), fill=YELLOW)
    d.text((tx+tw - 210, row_y+26), cuota, font=font(26), fill=GRAY)

bottom_y = ty + 48 + len(levels_full) * row_h
d.rectangle([tx, bottom_y, tx+tw, bottom_y+4], fill=YELLOW)

# ── nota subir de nivel ───────────────────────────────────────────────────────
note_y = bottom_y + 20
rounded_rect(d, [tx, note_y, tx+tw, note_y+100], radius=12,
             fill=(28,28,28), outline=YELLOW, outline_width=2)
centered_text(d, "Cada cuota a tiempo sube tu nivel.", note_y+14, W,
              font(28, bold=True), WHITE)
centered_text(d, "¡Entre más usas Cashea, menos pagas!", note_y+52, W,
              font(26), YELLOW)

# ── CTA ─────────────────────────────────────────────────────────────────────
cta_y = note_y + 124
rounded_rect(d, [100, cta_y, W-100, cta_y+80], radius=40, fill=YELLOW)
centered_text(d, "📲 Descarga Cashea ahora", cta_y+18, W,
              font(38, bold=True), BLACK)

centered_text(d, "Google Play  ·  App Store  ·  cashea.app",
              cta_y + 100, W, font(28), GRAY)

# franja inferior
stripe(d, H - 14, 14, W, YELLOW)
centered_text(d, "Instituto Privado Andrés Bello — UEIPAB",
              H - 62, W, font(28, bold=True), GRAY)

img.save(OUT_STORY, "PNG", optimize=True)
print(f"✓ Story guardado : {OUT_STORY}  ({W}×{H})")
print("\nArchivos listos para publicar en Instagram.")
