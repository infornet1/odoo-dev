#!/usr/bin/env python3
"""
Glenda AI Agent — Instagram Stories (4 slides)
Introduce Glenda to UEIPAB staff + calibration programme announcement.

Slides:
  S1 — ¡Bienvenida, Glenda!  (who she is)
  S2 — ¿Qué puede hacer?    (capabilities)
  S3 — Programa de calibración (join the programme)
  S4 — Bono de participación  (formula + CTA)
"""

import glob
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

OUT_DIR  = "/home/ftpuser/odoo-dev"
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

# ── Brand colors ──────────────────────────────────────────────────────────────
NAVY   = (26,  44,  91)       # UEIPAB primary
DNAVY  = (15,  25,  60)       # darker navy for gradients
VIOLET = (88,  44, 131)       # Glenda accent
LVIOLT = (237, 225, 255)      # light violet card bg
DVIOLT = (55,  20,  90)       # dark violet text on light
TEAL   = (0,  150, 136)       # AI/tech green-teal
LTEAL  = (210, 245, 240)      # light teal card bg
DTEAL  = (0,   80,  70)       # dark teal text
GOLD   = (212, 175,  55)      # premium gold (from flyer)
LGOLD  = (255, 248, 210)      # light gold card bg
DGOLD  = (120,  95,   5)      # dark gold text
GREEN  = (40,  167,  69)
LGRN   = (212, 237, 218)
DGRN   = (21,   87,  36)
RED    = (200,  50,  50)
LRED   = (253, 232, 232)
DRED   = (100,  20,  20)
WHITE  = (255, 255, 255)
LIGHT  = (240, 244, 250)
LGRAY  = (220, 225, 235)
GRAY   = (100, 110, 125)

W, H        = 1080, 1920
FOOTER_Y    = 1845
PAD         = 60

# ── Fonts ─────────────────────────────────────────────────────────────────────
def F(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

# ── Assets ────────────────────────────────────────────────────────────────────
LOGO = None
_logo_paths = glob.glob('/home/ftpuser/odoo-dev/Instituto*.png')
if _logo_paths:
    LOGO = Image.open(_logo_paths[0]).convert("RGBA")

FLYER = None
_flyer_path = '/home/ftpuser/odoo-dev/GlendasAI-Flyer.png'
if os.path.isfile(_flyer_path):
    FLYER = Image.open(_flyer_path).convert("RGBA")

# ── Draw helpers ──────────────────────────────────────────────────────────────
def make_base(top_color=NAVY, bot_color=DNAVY):
    """Create gradient background."""
    img = Image.new("RGBA", (W, H), top_color)
    d   = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    return img

def paste_logo(img, cy=105, max_w=400, max_h=140):
    if not LOGO:
        return
    ratio = min(max_w / LOGO.width, max_h / LOGO.height)
    nw, nh = int(LOGO.width * ratio), int(LOGO.height * ratio)
    r = LOGO.resize((nw, nh), Image.LANCZOS)
    img.paste(r, ((W - nw) // 2, cy - nh // 2), r)

def ctext(d, text, y, f, color=WHITE, shadow=None):
    """Center text, optional shadow."""
    bb = d.textbbox((0, 0), text, font=f)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    x  = (W - tw) // 2
    if shadow:
        d.text((x + 2, y - bb[1] + 2), text, font=f, fill=shadow)
    d.text((x, y - bb[1]), text, font=f, fill=color)
    return th

def ltext(d, text, x, y, f, color=WHITE):
    bb = d.textbbox((0, 0), text, font=f)
    d.text((x, y - bb[1]), text, font=f, fill=color)
    return bb[3] - bb[1]

def wrap_center(d, text, y, f, color=WHITE, max_w=960, line_gap=8):
    """Word-wrap centered text, return bottom y."""
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = ' '.join(cur + [w])
        bb = d.textbbox((0, 0), test, font=f)
        if bb[2] - bb[0] <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(' '.join(cur))
            cur = [w]
    if cur:
        lines.append(' '.join(cur))
    for line in lines:
        h = ctext(d, line, y, f, color)
        y += h + line_gap
    return y

def rrect(d, x1, y1, x2, y2, r, fill, outline=None, width=2):
    """Rounded rectangle."""
    d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill,
                         outline=outline, width=width)

def card(d, y, title, body_lines, bg, title_color, body_color,
         icon=None, border=None, x1=PAD, x2=W - PAD, corner=20):
    """Draw a card with title + body lines, return bottom y."""
    inner_pad = 24
    title_f   = F(38, bold=True)
    body_f    = F(33)

    # estimate height
    th = d.textbbox((0, 0), title, font=title_f)[3] + inner_pad
    bh = sum(d.textbbox((0, 0), l, font=body_f)[3] + 10 for l in body_lines)
    total_h = th + bh + inner_pad * 2

    rrect(d, x1, y, x2, y + total_h, corner, fill=bg,
          outline=border or bg, width=3)

    cy = y + inner_pad
    if icon:
        ltext(d, icon, x1 + inner_pad, cy, title_f, title_color)
        ltext(d, title, x1 + inner_pad + 55, cy, title_f, title_color)
    else:
        ltext(d, title, x1 + inner_pad, cy, title_f, title_color)
    cy += th

    for line in body_lines:
        ltext(d, line, x1 + inner_pad + (20 if icon else 0), cy, body_f, body_color)
        cy += d.textbbox((0, 0), line, font=body_f)[3] + 10

    return y + total_h + 18

def divider(d, y, color=GOLD, alpha=180):
    d.line([(PAD * 2, y), (W - PAD * 2, y)], fill=color + (alpha,) if len(color) == 3 else color, width=3)
    return y + 3

def footer(img, d):
    rrect(d, 0, FOOTER_Y - 10, W, H, 0, fill=DNAVY)
    ctext(d, "Instituto Privado Andrés Bello, C.A.", FOOTER_Y + 10, F(28), LGRAY)
    ctext(d, "recursoshumanos@ueipab.edu.ve", FOOTER_Y + 50, F(28), LGRAY)

def dot_nav(d, current, total=4, y=1795):
    dot_r, gap = 12, 36
    total_w = (total - 1) * gap
    x0 = (W - total_w) // 2
    for i in range(total):
        cx = x0 + i * gap
        color = WHITE if i == current else GRAY
        d.ellipse([cx - dot_r, y - dot_r, cx + dot_r, y + dot_r], fill=color)

# ── SLIDE 1 — Bienvenida ──────────────────────────────────────────────────────
def slide1():
    img = make_base(NAVY, (10, 18, 50))
    d   = ImageDraw.Draw(img)

    paste_logo(img, cy=110)

    # Thin gold separator line under logo
    d.line([(PAD * 2, 175), (W - PAD * 2, 175)], fill=GOLD, width=2)

    # Paste flyer image below logo (cropped/resized to fit width)
    if FLYER:
        fw = W - PAD * 2
        ratio = fw / FLYER.width
        fh = int(FLYER.height * ratio)
        fh = min(fh, 340)
        resized = FLYER.resize((fw, fh), Image.LANCZOS)
        img.paste(resized, (PAD, 190), resized)
        flyer_bot = 190 + fh + 20
    else:
        flyer_bot = 200

    d.line([(PAD * 2, flyer_bot), (W - PAD * 2, flyer_bot)], fill=GOLD, width=2)

    y = flyer_bot + 30
    y += ctext(d, "UNA NUEVA ERA EN ANDRÉS BELLO", y, F(44, bold=True), GOLD,
               shadow=(0, 0, 0)) + 12
    y += ctext(d, "La inteligencia artificial llega a nuestro", y, F(36), LIGHT) + 8
    y += ctext(d, "equipo para servir mejor a las familias.", y, F(36), LIGHT) + 30

    # Big WA badge
    badge_h = 110
    rrect(d, PAD, y, W - PAD, y + badge_h, 24, fill=GREEN, outline=GOLD, width=3)
    wa_icon_x = PAD + 30
    ltext(d, "WA", wa_icon_x, y + 28, F(48, bold=True), WHITE)
    ltext(d, "+58 414 832 1989", wa_icon_x + 100, y + 28, F(46, bold=True), WHITE)
    ltext(d, "Escríbele directamente a Glenda", wa_icon_x + 100, y + 76, F(30), LGRN)
    y += badge_h + 25

    # Powered-by line
    rrect(d, PAD + 60, y, W - PAD - 60, y + 64, 16, fill=(20, 20, 50))
    ctext(d, "Impulsada por Claude AI  ·  Anthropic", y + 14, F(30), LGOLD)
    y += 90

    dot_nav(d, 0)
    footer(img, d)

    path = os.path.join(OUT_DIR, "glenda_story_s1.png")
    img.convert("RGB").save(path, quality=95)
    print(f"  Saved: {path}")

# ── SLIDE 2 — Capacidades ─────────────────────────────────────────────────────
def slide2():
    img = make_base(NAVY, (10, 20, 70))
    d   = ImageDraw.Draw(img)

    paste_logo(img, cy=110)
    d.line([(PAD * 2, 175), (W - PAD * 2, 175)], fill=GOLD, width=2)

    y = 205
    y += ctext(d, "¿QUÉ PUEDE HACER", y, F(54, bold=True), WHITE,
               shadow=(0, 0, 0)) + 4
    y += ctext(d, "GLENDA?", y, F(72, bold=True), GOLD,
               shadow=(0, 0, 0)) + 28

    capabilities = [
        ("24/7", "Consulta General",
         ["Aranceles, inscripciones,", "métodos de pago — a toda hora"],
         LTEAL, DTEAL, TEAL),
        ("📋", "Soporte de Facturación",
         ["Redirige consultas de saldo", "y pagos al equipo de Pagos"],
         LVIOLT, DVIOLT, VIOLET),
        ("✅", "Recordatorio de Nómina",
         ["Notifica a empleados para", "confirmar recibo de pago"],
         LGOLD, DGOLD, GOLD),
        ("📊", "Recolección de Datos RRHH",
         ["Recopila info de empleados", "vía WhatsApp de forma segura"],
         LGRN, DGRN, GREEN),
        ("📧", "Resolución de Rebotes",
         ["Contacta representantes con", "emails incorrectos y los actualiza"],
         LRED, DRED, RED),
    ]

    for icon, title, body, bg, tc, border in capabilities:
        y = card(d, y, f"{icon}  {title}", body, bg, tc, tc,
                 border=border + (180,) if isinstance(border, tuple) else border)

    dot_nav(d, 1)
    footer(img, d)

    path = os.path.join(OUT_DIR, "glenda_story_s2.png")
    img.convert("RGB").save(path, quality=95)
    print(f"  Saved: {path}")

# ── SLIDE 3 — Programa de calibración ────────────────────────────────────────
def slide3():
    img = make_base((20, 10, 60), (10, 5, 35))
    d   = ImageDraw.Draw(img)

    paste_logo(img, cy=110)
    d.line([(PAD * 2, 175), (W - PAD * 2, 175)], fill=GOLD, width=2)

    y = 210
    y += ctext(d, "PROGRAMA DE", y, F(52, bold=True), WHITE, shadow=(0,0,0)) + 4
    y += ctext(d, "CALIBRACIÓN DE GLENDA", y, F(46, bold=True), GOLD, shadow=(0,0,0)) + 10
    y += ctext(d, "Tu experiencia hace a Glenda más inteligente", y, F(34), LIGHT) + 28

    # Invite banner
    rrect(d, PAD, y, W - PAD, y + 90, 20, fill=VIOLET, outline=GOLD, width=3)
    ctext(d, "¡Buscamos voluntarios del equipo UEIPAB!", y + 16, F(36, bold=True), WHITE)
    ctext(d, "Participa y ayuda a entrenar a Glenda", y + 54, F(30), LVIOLT)
    y += 108

    steps = [
        ("1", "Interactúa con Glenda",
         ["Conversa con ella por WhatsApp", "una vez a la semana"],
         LVIOLT, DVIOLT),
        ("2", "Documenta tu experiencia",
         ["Anota qué funcionó bien y qué", "podría mejorar (5 min máx)"],
         LGOLD, DGOLD),
        ("3", "Comparte retroalimentación",
         ["Envíala a RRHH — tu input", "mejora el sistema para todos"],
         LGRN, DGRN),
    ]

    def step_card(d, y, num, title, body, bg, tc, card_h=170):
        x1, x2, inner = PAD, W - PAD, 24
        rrect(d, x1, y, x2, y + card_h, 20, fill=bg, outline=tc, width=3)
        cy = y + inner
        circ_r = 34
        d.ellipse([x1 + inner, cy, x1 + inner + circ_r * 2, cy + circ_r * 2], fill=tc)
        cx_circ = x1 + inner + circ_r
        bn = d.textbbox((0, 0), num, font=F(42, bold=True))
        d.text((cx_circ - (bn[2] - bn[0]) // 2, cy + 4 - bn[1]), num,
               font=F(42, bold=True), fill=WHITE)
        tx = x1 + inner + circ_r * 2 + 20
        ltext(d, title, tx, cy + 4, F(38, bold=True), tc)
        cy += circ_r * 2 + 14
        for line in body:
            ltext(d, line, x1 + inner + 10, cy, F(31), tc)
            cy += d.textbbox((0, 0), line, font=F(31))[3] + 8
        return y + card_h + 18

    for num, title, body, bg, tc in steps:
        y = step_card(d, y, num, title, body, bg, tc, card_h=175)

    # Who can participate box
    rrect(d, PAD, y, W - PAD, y + 100, 20, fill=(30, 20, 70), outline=VIOLET, width=2)
    ctext(d, "¿Quién puede participar?", y + 14, F(34, bold=True), GOLD)
    ctext(d, "Todo el personal UEIPAB — docentes, admin y mantenimiento", y + 52, F(28), LIGHT)
    ctext(d, "No se requiere conocimiento técnico previo.", y + 80, F(26), LGRAY)
    y += 118

    # Bono preview teaser
    rrect(d, PAD, y, W - PAD, y + 90, 20, fill=GREEN, outline=GOLD, width=3)
    ctext(d, "Recibes un bono por cada sesión documentada", y + 16, F(32, bold=True), WHITE)
    ctext(d, "Ver fórmula en la siguiente diapositiva  →", y + 54, F(28), LGRN)
    y += 108

    dot_nav(d, 2)
    footer(img, d)

    path = os.path.join(OUT_DIR, "glenda_story_s3.png")
    img.convert("RGB").save(path, quality=95)
    print(f"  Saved: {path}")

# ── SLIDE 4 — Bono + CTA ──────────────────────────────────────────────────────
def slide4():
    img = make_base((5, 45, 25), (2, 22, 10))
    d   = ImageDraw.Draw(img)

    paste_logo(img, cy=110)
    d.line([(PAD * 2, 175), (W - PAD * 2, 175)], fill=GOLD, width=2)

    y = 208
    y += ctext(d, "BONO DE", y, F(54, bold=True), WHITE, shadow=(0,0,0)) + 4
    y += ctext(d, "PARTICIPACIÓN", y, F(64, bold=True), GOLD, shadow=(0,0,0)) + 8
    y += ctext(d, "Cada sesión documentada te recompensa", y, F(32), LIGHT) + 28

    # ── Formula box ──
    fbox_h = 340
    rrect(d, PAD, y, W - PAD, y + fbox_h, 24, fill=LGOLD, outline=GOLD, width=4)

    fy = y + 22
    ctext(d, "FÓRMULA DEL BONO", fy, F(36, bold=True), DGOLD)
    fy += 48
    d.line([(PAD + 40, fy), (W - PAD - 40, fy)], fill=GOLD, width=2)
    fy += 20

    # Formula as: Bono = Salario Base ÷ 21.75
    ctext(d, "Bono =", fy, F(44, bold=True), DNAVY)
    fy += 52
    # Fraction visual: numerator / divider line / denominator
    num_text = "Salario Base"
    den_text = "21.75 dias"
    bb_n = d.textbbox((0, 0), num_text, font=F(46, bold=True))
    bb_d = d.textbbox((0, 0), den_text, font=F(42, bold=True))
    max_w = max(bb_n[2], bb_d[2]) + 40
    cx = W // 2
    # numerator
    ctext(d, num_text, fy, F(46, bold=True), DNAVY)
    fy += bb_n[3] + 10
    # fraction line
    d.line([(cx - max_w // 2, fy), (cx + max_w // 2, fy)], fill=NAVY, width=5)
    fy += 14
    # denominator
    ctext(d, den_text, fy, F(42, bold=True), DNAVY)
    fy += bb_d[3] + 16
    d.line([(PAD + 40, fy), (W - PAD - 40, fy)], fill=GOLD, width=1)
    fy += 14
    ctext(d, "por cada sesión semanal documentada", fy, F(28), DGOLD)
    y += fbox_h + 20

    # Summary line
    rrect(d, PAD + 40, y, W - PAD - 40, y + 64, 16, fill=(10, 60, 35))
    ctext(d, "Tu aporte semanal = 1 día de salario", y + 14, F(32, bold=True), GOLD)
    y += 82

    # What you receive
    y = card(d, y, "¿Qué recibes?",
             ["+ Bono por cada sesión documentada",
              "+ Acceso anticipado a nuevas funciones",
              "+ Reconocimiento como pionero/a UEIPAB"],
             LGRN, DGRN, GREEN)

    # Sign up box
    rrect(d, PAD, y, W - PAD, y + 200, 24, fill=GREEN, outline=GOLD, width=3)
    ctext(d, "CÓMO INSCRIBIRTE", y + 18, F(36, bold=True), WHITE)
    d.line([(PAD + 50, y + 66), (W - PAD - 50, y + 66)], fill=LGRN, width=2)
    ctext(d, "Escribe a RRHH expresando tu interés:", y + 80, F(31), LGRN)
    ctext(d, "recursoshumanos@ueipab.edu.ve", y + 122, F(36, bold=True), GOLD)
    ctext(d, "Asunto: Programa Calibración Glenda", y + 166, F(27), WHITE)
    y += 218

    # Urgency banner
    rrect(d, PAD, y, W - PAD, y + 74, 18, fill=RED, outline=GOLD, width=2)
    ctext(d, "Cupos limitados — ¡Inscríbete hoy!", y + 18, F(34, bold=True), WHITE)
    y += 92

    dot_nav(d, 3)
    footer(img, d)

    path = os.path.join(OUT_DIR, "glenda_story_s4.png")
    img.convert("RGB").save(path, quality=95)
    print(f"  Saved: {path}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating Glenda AI Stories...")
    slide1()
    slide2()
    slide3()
    slide4()
    print("Done — 4 slides saved to", OUT_DIR)
