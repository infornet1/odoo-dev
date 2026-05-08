#!/usr/bin/env python3
"""
Cashea Campaign v2 — Instagram Post + Story (SIN PRECIO)
Versión genérica: no menciona $197,38 — válida para cualquier mes/tarifa.
"""

import glob, os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR   = "/home/ftpuser/odoo-dev"
OUT_POST  = os.path.join(OUT_DIR, "cashea_instagram_post_v2.png")
OUT_STORY = os.path.join(OUT_DIR, "cashea_instagram_story_v2.png")

BLACK  = (17,  17,  17)
YELLOW = (255, 214,  0)
WHITE  = (255, 255, 255)
GRAY   = (200, 200, 200)
DGRAY  = (110, 110, 110)

LOGO_PATHS = (glob.glob('/home/ftpuser/odoo-dev/Instituto*Bello*.png') +
              glob.glob('/tmp/school_logo.png'))
school_logo = Image.open(LOGO_PATHS[0]).convert("RGBA") if LOGO_PATHS else None

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

def centered_text(draw, text, y, width, fnt, color):
    bb = draw.textbbox((0,0), text, font=fnt)
    draw.text(((width-(bb[2]-bb[0]))//2, y), text, font=fnt, fill=color)

def stripe(draw, y, h, w, color):
    draw.rectangle([0, y, w, y+h], fill=color)

def rounded_rect(draw, xy, radius, fill, outline=None, outline_width=0):
    draw.rounded_rectangle(xy, radius=radius, fill=fill,
                            outline=outline, width=outline_width)

def logo_cashea_pill(img, x, y, height=56):
    fnt = font(int(height*0.55), bold=True)
    tmp = Image.new("RGBA", img.size, (0,0,0,0))
    d   = ImageDraw.Draw(tmp)
    bb  = d.textbbox((0,0), "cashea", font=fnt)
    pw  = (bb[2]-bb[0]) + height
    d.rounded_rectangle([x, y, x+pw, y+height], radius=height//2, fill=YELLOW+(255,))
    d.text((x+height//2, y+(height-(bb[3]-bb[1]))//2-bb[1]),
           "cashea", font=fnt, fill=BLACK+(255,))
    img.alpha_composite(tmp)
    return pw

def paste_logo(img, logo, max_w, max_h, x, y, center_x=False):
    if logo is None: return
    ratio  = min(max_w/logo.width, max_h/logo.height)
    new_w, new_h = int(logo.width*ratio), int(logo.height*ratio)
    resized = logo.resize((new_w, new_h), Image.LANCZOS)
    px = (img.width-new_w)//2 if center_x else x
    img.paste(resized, (px, y), resized if resized.mode=="RGBA" else None)

# ═══════════════════════════════════════════════════════════════════════════════
# POST v2  1080×1080 — sin precio
# ═══════════════════════════════════════════════════════════════════════════════
W, H = 1080, 1080
img = Image.new("RGB", (W, H), BLACK)
d   = ImageDraw.Draw(img)

stripe(d, 0, 12, W, YELLOW)

# logos
paste_logo(img, school_logo, max_w=360, max_h=80, x=60, y=44)
rgba = img.convert("RGBA")
logo_cashea_pill(rgba, x=W-300, y=44, height=68)
img = rgba.convert("RGB"); d = ImageDraw.Draw(img)

stripe(d, 136, 4, W, YELLOW)

# hero texto — genérico
centered_text(d, "¡NUEVA FORMA DE PAGAR EN EL COLEGIO!", 170, W, font(28, bold=True), YELLOW)
centered_text(d, "Divide tu mensualidad", 234, W, font(64, bold=True), WHITE)
centered_text(d, "en cuotas quincenales", 308, W, font(64, bold=True), WHITE)
centered_text(d, "sin intereses",          382, W, font(64, bold=True), YELLOW)

# pill genérica (sin precio)
rounded_rect(d, [130, 470, W-130, 556], radius=48, fill=YELLOW)
centered_text(d, "0% de interés · 0 recargos extra", 484, W, font(44, bold=True), BLACK)

centered_text(d, "Paga cómodo · A tu ritmo · Sin sorpresas", 578, W, font(30), GRAY)

# tabla niveles (% en lugar de $)
tx, ty, tw = 80, 632, W-160
row_h = 58
rounded_rect(d, [tx, ty, tx+tw, ty+38], radius=8, fill=YELLOW)
d.text((tx+16, ty+9),        "NIVEL",          font=font(20,True), fill=BLACK)
d.text((tx+tw//2-50, ty+9),  "INICIAL",        font=font(20,True), fill=BLACK)
d.text((tx+tw-210, ty+9),    "CUOTA DÍA 14",   font=font(20,True), fill=BLACK)

levels = [
    ("🌱  Semilla  (nuevo)",      "60%  inicial", "resto en 14 días"),
    ("🌿  Raíz  (5 pagos)",       "50%  inicial", "resto en 14 días"),
    ("🍃  Hoja  (10 pagos)",      "40%  inicial", "más cuotas"),
    ("🌳  Tronco y superiores",   "desde 25%",    "aún más flex. ⭐"),
]
for i,(lvl,ini,cuota) in enumerate(levels):
    ry = ty+38+i*row_h
    d.rectangle([tx,ry,tx+tw,ry+row_h], fill=(30,30,30) if i%2==0 else (22,22,22))
    d.rectangle([tx,ry,tx+4,ry+row_h],  fill=YELLOW)
    d.text((tx+16, ry+16),        lvl,   font=font(22),       fill=WHITE)
    d.text((tx+tw//2-55, ry+16),  ini,   font=font(22,True),  fill=YELLOW)
    d.text((tx+tw-190, ry+16),    cuota, font=font(20),        fill=GRAY)

bot = ty+38+len(levels)*row_h
d.rectangle([tx, bot, tx+tw, bot+3], fill=YELLOW)

centered_text(d, "¡Descarga Cashea y empieza hoy!", bot+18, W, font(30,True), WHITE)
centered_text(d, "Google Play  ·  App Store (iPhone)  ·  cashea.app", bot+60, W, font(25), YELLOW)

stripe(d, H-12, 12, W, YELLOW)
centered_text(d, "Instituto Privado Andrés Bello — UEIPAB", H-50, W, font(24,True), GRAY)

img.save(OUT_POST, "PNG", optimize=True)
print(f"✓ Post v2 guardado  : {OUT_POST}  ({W}×{H})")


# ═══════════════════════════════════════════════════════════════════════════════
# STORY v2  1080×1920 — sin precio
# ═══════════════════════════════════════════════════════════════════════════════
W, H = 1080, 1920
img = Image.new("RGB", (W, H), BLACK)
d   = ImageDraw.Draw(img)

stripe(d, 0, 14, W, YELLOW)

# cabecera logos
paste_logo(img, school_logo, max_w=420, max_h=90, x=0, y=80, center_x=True)
rgba = img.convert("RGBA")
logo_cashea_pill(rgba, x=(W-260)//2, y=192, height=72)
img = rgba.convert("RGB"); d = ImageDraw.Draw(img)

stripe(d, 284, 5, W, YELLOW)

# hero genérico
centered_text(d, "¡NUEVA FORMA DE PAGAR", 318, W, font(46,True), YELLOW)
centered_text(d, "EN EL COLEGIO!",         372, W, font(46,True), YELLOW)

centered_text(d, "Divide tu mensualidad", 440, W, font(70,True), WHITE)
centered_text(d, "en cuotas cómodas",     520, W, font(70,True), WHITE)
centered_text(d, "sin intereses",          600, W, font(70,True), YELLOW)

# pill genérica grande
rounded_rect(d, [80, 698, W-80, 796], radius=52, fill=YELLOW)
centered_text(d, "0% de interés · 0 recargos extra", 714, W, font(50,True), BLACK)

centered_text(d, "Paga a tu ritmo · Sin sorpresas · Con Cashea", 822, W, font(32), GRAY)

stripe(d, 876, 5, W, YELLOW)

# sección niveles
centered_text(d, "DEPENDIENDO DE TU NIVEL",       900, W, font(34,True), YELLOW)
centered_text(d, "tu inicial puede ser aún menor", 946, W, font(30),      GRAY)

tx, ty, tw = 60, 994, W-120
row_h = 84

rounded_rect(d, [tx, ty, tx+tw, ty+50], radius=10, fill=YELLOW)
d.text((tx+20, ty+13),         "NIVEL",          font=font(26,True), fill=BLACK)
d.text((tx+tw//2-60, ty+13),   "INICIAL %",      font=font(26,True), fill=BLACK)
d.text((tx+tw-230, ty+13),     "CUOTA DÍA 14",   font=font(26,True), fill=BLACK)

levels_full = [
    ("🌱 Semilla",   "Nuevo usuario",      "60%", "resto en 14 días"),
    ("🌿 Raíz",      "5 pagos o $120",     "50%", "resto en 14 días"),
    ("🍃 Hoja",      "10 pagos o $400",    "40%", "más cuotas"),
    ("🌳 Tronco",    "20 pagos o $800",    "25%", "más cuotas"),
    ("🌲 Árbol",     "40 pagos o $2.000",  "20%", "más cuotas"),
    ("🌻 Araguaney", "80 pagos o $4.000",  "0%*", "máx. flex."),
]
for i,(lvl,req,pct,cuota) in enumerate(levels_full):
    ry = ty+50+i*row_h
    d.rectangle([tx,ry,tx+tw,ry+row_h], fill=(28,28,28) if i%2==0 else (20,20,20))
    d.rectangle([tx,ry,tx+5,ry+row_h],  fill=YELLOW)
    d.text((tx+18, ry+12),       lvl,   font=font(28,True), fill=WHITE)
    d.text((tx+18, ry+48),       req,   font=font(22),      fill=DGRAY)
    d.text((tx+tw//2-40, ry+22), pct,   font=font(34,True), fill=YELLOW)
    d.text((tx+tw-218,   ry+26), cuota, font=font(24),      fill=GRAY)

bot = ty+50+len(levels_full)*row_h
d.rectangle([tx, bot, tx+tw, bot+4], fill=YELLOW)

# nota asterisco araguaney
d.text((tx+20, bot+10), "* 0% inicial con socios selectos (Nivel Araguaney)",
       font=font(22), fill=DGRAY)

# nota motivacional
note_y = bot+52
rounded_rect(d, [tx, note_y, tx+tw, note_y+90], radius=12,
             fill=(28,28,28), outline=YELLOW, outline_width=2)
centered_text(d, "Cada cuota a tiempo sube tu nivel.", note_y+12, W, font(28,True), WHITE)
centered_text(d, "¡Entre más usas Cashea, menos pagas!", note_y+50, W, font(26), YELLOW)

# CTA
cta_y = note_y + 110
rounded_rect(d, [100, cta_y, W-100, cta_y+78], radius=39, fill=YELLOW)
centered_text(d, "📲 Descarga Cashea ahora", cta_y+16, W, font(38,True), BLACK)
centered_text(d, "Google Play  ·  App Store  ·  cashea.app",
              cta_y+98, W, font(27), GRAY)

stripe(d, H-14, 14, W, YELLOW)
centered_text(d, "Instituto Privado Andrés Bello — UEIPAB", H-58, W, font(27,True), GRAY)

img.save(OUT_STORY, "PNG", optimize=True)
print(f"✓ Story v2 guardado : {OUT_STORY}  ({W}×{H})")
print("\nArchivos v2 listos (sin precio — versión abierta).")
