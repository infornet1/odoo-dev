#!/usr/bin/env python3
"""
UEIPAB Attendance System — Instagram Stories (4 slides) v3
Comunica a los empleados cómo funciona el sistema de asistencia automatizado.
"""

import glob, os
from PIL import Image, ImageDraw, ImageFont

OUT_DIR  = "/home/ftpuser/odoo-dev"
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

# ── Brand Colors ─────────────────────────────────────────────
NAVY  = (26,  44,  91)
BLUE  = (36, 113, 163)
LBLUE = (173, 210, 235)
LIGHT = (240, 244, 250)
WHITE = (255, 255, 255)
GREEN = (40, 167,  69)
LGRN  = (212, 237, 218)
DGRN  = (21,  87,  36)
AMBER = (255, 193,   7)
LAMB  = (255, 243, 205)
DAMB  = (133, 100,   4)
RED   = (220,  53,  69)
LRED  = (253, 232, 232)
DRED  = (114,  28,  36)
LGRAY = (233, 236, 239)
GRAY  = (108, 117, 125)

W, H = 1080, 1920
FOOTER_Y    = 1830
CONTENT_END = 1820


# ── Font ─────────────────────────────────────────────────────
def F(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


# ── Logo ─────────────────────────────────────────────────────
LOGO = None
_paths = glob.glob('/home/ftpuser/odoo-dev/Instituto*Bello*.png')
if _paths:
    LOGO = Image.open(_paths[0]).convert("RGBA")

def paste_logo(img, max_w=400, max_h=150, cy=100):
    if not LOGO:
        return
    ratio = min(max_w / LOGO.width, max_h / LOGO.height)
    nw, nh = int(LOGO.width * ratio), int(LOGO.height * ratio)
    r = LOGO.resize((nw, nh), Image.LANCZOS)
    img.paste(r, ((W - nw) // 2, cy - nh // 2), r)


# ── Draw helpers ─────────────────────────────────────────────
def ctext(d, text, y, f, color):
    bb = d.textbbox((0, 0), text, font=f)
    x  = (W - (bb[2] - bb[0])) // 2
    d.text((x, y - bb[1]), text, font=f, fill=color)
    return bb[3] - bb[1]

def ltext(d, text, x, y, f, color):
    bb = d.textbbox((0, 0), text, font=f)
    d.text((x, y - bb[1]), text, font=f, fill=color)
    return bb[3] - bb[1]

def wrap_lines(d, text, f, max_w):
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
    return lines

def card(d, x, y, cw, ch, fill, r=20, outline=None, ow=2):
    d.rounded_rectangle([x, y, x + cw, y + ch], radius=r,
                         fill=fill, outline=outline, width=ow)

def pill(d, text, y, f, text_col, bg_col, px=40, py=18, r=None):
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + px * 2, th + py * 2
    x0 = (W - pw) // 2
    if r is None:
        r = ph // 2
    d.rounded_rectangle([x0, y, x0 + pw, y + ph], radius=r, fill=bg_col)
    d.text((x0 + px, y + py - bb[1]), text, font=f, fill=text_col)
    return y + ph

def vgrad(img, top, bot):
    d = ImageDraw.Draw(img)
    for row in range(img.height):
        t = row / img.height
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        d.line([(0, row), (img.width, row)], fill=c)

def new_slide():
    img = Image.new("RGB", (W, H), NAVY)
    vgrad(img, NAVY, (15, 28, 65))
    return img

def std_header(img, d):
    d.rectangle([0, 0, W, 10], fill=BLUE)
    paste_logo(img, max_w=380, max_h=145, cy=100)
    d.rectangle([80, 205, W - 80, 210], fill=BLUE)
    return 230

def std_footer(img, d):
    d.rectangle([0, FOOTER_Y, W, H], fill=NAVY)
    ctext(d, "Instituto Privado Andrés Bello, C.A.", FOOTER_Y + 15, F(27), (160, 185, 220))
    ctext(d, "recursoshumanos@ueipab.edu.ve",         FOOTER_Y + 52, F(25), (120, 160, 205))
    d.rectangle([0, H - 8, W, H], fill=BLUE)

def section_header(d, text, y, bg=BLUE, fg=WHITE, h=105, fsz=44):
    d.rectangle([0, y, W, y + h], fill=bg)
    ctext(d, text, y + h // 2 - 14, F(fsz, bold=True), fg)
    return y + h

def bottom_cta(d, line1, line2, y_start, slide_num=None,
               bg=(36, 58, 110), fg=WHITE, accent=LBLUE):
    """Fill bottom area with a CTA/info block + optional slide dots."""
    h = CONTENT_END - y_start - 10
    if h < 60:
        return
    card(d, 50, y_start, W - 100, h, bg, r=22, outline=BLUE, ow=2)
    inner = y_start + (h * 2 // 5) - 20
    ctext(d, line1, inner,      F(32, bold=True), fg)
    ctext(d, line2, inner + 46, F(29),            accent)
    if slide_num is not None:
        dot_cy = y_start + h - 40
        dot_r, gap = 13, 44
        total = 4
        total_w = total * dot_r * 2 + (total - 1) * gap
        x0 = (W - total_w) // 2
        for i in range(total):
            cx = x0 + i * (dot_r * 2 + gap) + dot_r
            col = WHITE if i + 1 == slide_num else (80, 115, 165)
            d.ellipse([cx - dot_r, dot_cy - dot_r, cx + dot_r, dot_cy + dot_r], fill=col)


# ══════════════════════════════════════════════════════════════
# SLIDE 1 — PORTADA
# ══════════════════════════════════════════════════════════════
def make_s1():
    img = new_slide()
    d   = ImageDraw.Draw(img)
    y   = std_header(img, d)

    ctext(d, "SISTEMA DE REGISTRO", y + 15, F(56, bold=True), WHITE)
    ctext(d, "DE ASISTENCIA",       y + 85, F(66, bold=True), WHITE)
    y += 185

    y = pill(d, "  Tu asistencia, ahora automatizada  ",
             y, F(35), WHITE, BLUE, px=36, py=22) + 35

    # ── PRIMARY: Kiosko card ──────────────────────────────────
    kh = 255
    card(d, 50, y, W - 100, kh, (22, 42, 88), r=22, outline=AMBER, ow=5)
    # "OBLIGATORIO" badge top-right
    badge_w, badge_h = 230, 42
    bx = W - 50 - badge_w - 16
    by = y + 14
    d.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=21, fill=AMBER)
    d.text((bx + 18, by + 8), "OBLIGATORIO", font=F(24, bold=True), fill=NAVY)
    # Card title
    d.text((95, y + 18), "KIOSKO DE ASISTENCIA", font=F(40, bold=True), fill=AMBER)
    d.text((95, y + 70), "Método principal — todos los empleados", font=F(29), fill=LBLUE)
    # Divider inside card
    d.rectangle([80, y + 110, W - 80, y + 113], fill=(50, 80, 150))
    # Details
    d.text((95, y + 122), "Ubicación:  Oficina de Administración", font=F(27), fill=WHITE)
    d.rectangle([80, y + 162, W - 80, y + 164], fill=(40, 65, 130))
    d.text((95, y + 172), "Registra tu entrada y salida cada día", font=F(28), fill=WHITE)
    d.text((95, y + 212), "en el Kiosko. Es el registro oficial.", font=F(28), fill=WHITE)

    y += kh + 25

    # ── Contingency separator ─────────────────────────────────
    sep_h = 50
    card(d, 50, y, W - 100, sep_h, (36, 58, 110), r=14)
    ctext(d, "MÉTODOS DE CONTINGENCIA (si el Kiosko no está disponible)", y + 12,
          F(24, bold=True), LBLUE)
    y += sep_h + 14

    # ── Contingency card 0: Odoo Dashboard ───────────────────
    card(d, 50, y, W - 100, 128, LIGHT, r=18, outline=(30, 80, 140), ow=3)
    d.text((95, y + 14), "TODOS (con acceso a Odoo)", font=F(32, bold=True), fill=(30, 80, 140))
    d.text((95, y + 54), "Dashboard → Botón Check In / Check Out", font=F(28, bold=True), fill=NAVY)
    d.text((95, y + 92), "Marca tu entrada y salida digitalmente", font=F(25), fill=GRAY)
    y += 144

    # ── Contingency card 1: Docentes ──────────────────────────
    card(d, 50, y, W - 100, 120, LGRN, r=18, outline=DGRN, ow=3)
    d.text((95, y + 14), "DOCENTES", font=F(32, bold=True), fill=DGRN)
    d.text((95, y + 52), "Control de Asistencias", font=F(28, bold=True), fill=NAVY)
    d.text((95, y + 88), "Pasa lista — sincronización automática", font=F(25), fill=GRAY)
    y += 136

    # ── Contingency card 2: Admin / Mant. ────────────────────
    card(d, 50, y, W - 100, 120, LAMB, r=18, outline=DAMB, ow=3)
    d.text((95, y + 14), "ADMIN & MANTENIMIENTO", font=F(32, bold=True), fill=DAMB)
    d.text((95, y + 52), "Red WiFi del plantel", font=F(28, bold=True), fill=NAVY)
    d.text((95, y + 88), "Conéctate 2+ horas antes de las 2 PM", font=F(25), fill=GRAY)
    y += 136

    # ── Reporte info box ──────────────────────────────────────
    y += 8
    card(d, 50, y, W - 100, 175, (36, 60, 120), r=20, outline=BLUE, ow=2)
    ctext(d, "Reporte quincenal por correo institucional:", y + 16, F(28, bold=True), WHITE)
    ctext(d, "Día 16  →  Quincena 1  (días 1 al 15)",      y + 58, F(27), LBLUE)
    ctext(d, "Día  1  →  Quincena 2  (día 16 al fin)",     y + 94, F(27), LBLUE)
    ctext(d, "Verifica y confirma tu registro cada quincena", y + 138, F(25), (160, 200, 235))
    y += 193

    bottom_cta(d,
               "Descubre cómo funciona el sistema",
               "Desliza para ver los detalles ->",
               y + 15, slide_num=1)

    std_footer(img, d)
    path = os.path.join(OUT_DIR, "asistencia_story_s1.png")
    img.save(path)
    print(f"Guardado: {path}")


# ══════════════════════════════════════════════════════════════
# SLIDE 2 — CÓMO SE REGISTRA TU ASISTENCIA
# ══════════════════════════════════════════════════════════════
def make_s2():
    img = new_slide()
    d   = ImageDraw.Draw(img)
    y   = std_header(img, d)

    y = section_header(d, "CÓMO SE REGISTRA TU ASISTENCIA", y,
                        bg=BLUE, h=108, fsz=40) + 18

    # ── Kiosko reminder ───────────────────────────────────────
    y = pill(d, "  ★  Kiosko (Oficina Admin) = MÉTODO OBLIGATORIO  ★  ",
             y, F(27, bold=True), AMBER, (22, 42, 88), px=28, py=16) + 18

    # ── Contingency separator ─────────────────────────────────
    card(d, 50, y, W - 100, 44, (36, 58, 110), r=12)
    ctext(d, "MÉTODOS DE CONTINGENCIA (si el Kiosko no está disponible)", y + 10,
          F(23, bold=True), LBLUE)
    y += 58

    # ── Contingency 1: Odoo Dashboard ─────────────────────────
    # Header 58px + gap 12px + 3 steps×40=120px + gap 8px + note 38px + pad 14px = 250px
    BLU2 = (30, 80, 140)
    card(d, 50, y, W - 100, 250, LIGHT, r=20, outline=BLU2, ow=4)
    d.rounded_rectangle([50, y, W - 50, y + 58], radius=20, fill=BLU2)
    ctext(d, "TODOS CON ACCESO A ODOO", y + 14, F(36, bold=True), WHITE)
    ty = y + 70
    steps_o = [
        ("1.", "Abre el Dashboard de RRHH en Odoo"),
        ("2.", "Haz clic en el botón verde  Check In  al llegar"),
        ("3.", "Al salir haz clic en  Check Out"),
    ]
    for num, step in steps_o:
        d.text((80, ty), num, font=F(29, bold=True), fill=BLU2)
        d.text((140, ty), step, font=F(29), fill=NAVY)
        ty += 40
    card(d, 75, ty + 8, W - 150, 38, (210, 228, 248), r=10)
    ctext(d, "Captura IP, geolocalización y hora automáticamente", ty + 16, F(24), BLU2)
    y += 265

    # ── Contingency 2: Docentes ───────────────────────────────
    # Header 58px + gap 12px + 4 lines×38=152px + gap 10px + note 36px + pad 10px = 278px
    card(d, 50, y, W - 100, 278, LGRN, r=20, outline=DGRN, ow=4)
    d.rounded_rectangle([50, y, W - 50, y + 58], radius=20, fill=DGRN)
    ctext(d, "DOCENTES", y + 14, F(36, bold=True), WHITE)
    ty = y + 70
    steps_d = [
        ("1.", "Registra tu clase en Control de Asistencias"),
        ("",   "como lo haces normalmente"),
        ("2.", "El sistema sincroniza automáticamente"),
        ("",   "Horario: 7:00 AM - 1:30 PM"),
    ]
    for num, step in steps_d:
        if num:
            d.text((80, ty), num, font=F(29, bold=True), fill=DGRN)
        d.text((140, ty), step, font=F(29), fill=NAVY)
        ty += 38
    card(d, 75, ty + 10, W - 150, 36, (195, 232, 205), r=10)
    ctext(d, "Sin acción adicional de tu parte", ty + 18, F(24, bold=True), DGRN)
    y += 295

    # ── Contingency 3: Admin / Mant. ──────────────────────────
    # Header 58px + gap 12px + 4 lines×38=152px + gap 10px + note 36px + pad 10px = 278px
    card(d, 50, y, W - 100, 278, LAMB, r=20, outline=DAMB, ow=4)
    d.rounded_rectangle([50, y, W - 50, y + 58], radius=20, fill=DAMB)
    ctext(d, "ADMIN & MANTENIMIENTO", y + 14, F(33, bold=True), WHITE)
    ty = y + 70
    steps_a = [
        ("1.", "Conéctate al WiFi del plantel (red UEIPAB)"),
        ("2.", "Permanece conectado 2+ horas"),
        ("",   "La conexión debe ser antes de las 2 PM"),
        ("3.", "El sistema registra tu presencia"),
    ]
    for num, step in steps_a:
        if num:
            d.text((80, ty), num, font=F(29, bold=True), fill=DAMB)
        d.text((140, ty), step, font=F(29), fill=NAVY)
        ty += 38
    card(d, 75, ty + 10, W - 150, 36, (250, 240, 195), r=10)
    ctext(d, "Control de Asistencias tiene prioridad siempre", ty + 18, F(24), DAMB)
    y += 295

    # ── Sync note ─────────────────────────────────────────────
    card(d, 50, y, W - 100, 92, (36, 60, 120), r=16, outline=BLUE, ow=2)
    ctext(d, "Sincronización automática — lunes a viernes", y + 14, F(28, bold=True), WHITE)
    ctext(d, "Procesado cada noche tras el cierre del día",  y + 54, F(26), LBLUE)
    y += 108

    bottom_cta(d,
               "Cada quincena recibirás tu resumen",
               "Continúa para ver el reporte ->",
               y + 15, slide_num=2)

    std_footer(img, d)
    path = os.path.join(OUT_DIR, "asistencia_story_s2.png")
    img.save(path)
    print(f"Guardado: {path}")


# ══════════════════════════════════════════════════════════════
# SLIDE 3 — EL REPORTE QUINCENAL
# ══════════════════════════════════════════════════════════════
def make_s3():
    img = new_slide()
    d   = ImageDraw.Draw(img)
    y   = std_header(img, d)

    y = section_header(d, "TU REPORTE QUINCENAL", y,
                        bg=BLUE, h=108, fsz=46) + 18

    ctext(d, "Cada 15 días recibes un email de",     y,      F(33), WHITE)
    ctext(d, "Recursos Humanos con tu resumen",       y + 44, F(33), WHITE)
    y += 100

    # ── Email preview ─────────────────────────────────────────
    ep_h = 680
    card(d, 40, y, W - 80, ep_h, WHITE, r=24, outline=BLUE, ow=4)
    d.rounded_rectangle([40, y, W - 40, y + 74], radius=24, fill=NAVY)
    ctext(d, "Reporte de Asistencia Quincenal", y + 22, F(30, bold=True), WHITE)

    ey = y + 90
    d.text((68, ey),  "Para:", font=F(26, bold=True), fill=GRAY)
    d.text((170, ey), "Tu correo institucional",       font=F(26), fill=NAVY)
    ey += 36
    d.text((68, ey),  "De:",   font=F(26, bold=True), fill=GRAY)
    d.text((170, ey), "recursoshumanos@ueipab.edu.ve", font=F(26), fill=BLUE)
    ey += 50

    d.rectangle([60, ey, W - 60, ey + 2], fill=LGRAY)
    ey += 10

    cols = [65, 218, 420, 605, 760, 895]
    hdrs = ["Fecha", "Día", "Entrada", "Salida", "Hrs", ""]
    for cx, ht in zip(cols, hdrs):
        d.text((cx, ey), ht, font=F(24, bold=True), fill=GRAY)
    ey += 36

    rows = [
        ("01/06", "Lun", "07:55", "17:02", "9.1", "OK", LGRN, DGRN, None),
        ("02/06", "Mar", "08:03", "- - -", " - ", "!",  LAMB, DAMB, None),
        ("03/06", "Mié", "- - -", "- - -", " - ", "X",  LRED, DRED, None),
        ("04/06", "Jue", "08:01", "17:10", "9.2", "OK", LGRN, DGRN, None),
        ("05/06", "Vie", "- - -", "- - -", " - ", "-",  LGRAY, GRAY, "Feriado"),
    ]
    for fecha, dia, entr, sal, hrs, status, row_bg, st_col, note in rows:
        d.rectangle([60, ey, W - 60, ey + 40], fill=row_bg)
        display_fecha = fecha if not note else f"{fecha}*"
        d.text((cols[0], ey + 6), display_fecha, font=F(24), fill=NAVY if not note else GRAY)
        d.text((cols[1], ey + 6), dia,    font=F(24), fill=NAVY if not note else GRAY)
        d.text((cols[2], ey + 6), entr,   font=F(24), fill=NAVY)
        d.text((cols[3], ey + 6), sal,    font=F(24), fill=NAVY)
        d.text((cols[4], ey + 6), hrs,    font=F(24), fill=NAVY)
        d.text((cols[5], ey + 4), status, font=F(26, bold=True), fill=st_col)
        ey += 41

    d.text((65, ey + 4), "* 05/06 = Feriado (día no hábil)", font=F(22), fill=GRAY)
    ey += 36

    d.rectangle([60, ey, W - 60, ey + 2], fill=LGRAY)
    ey += 12

    d.rounded_rectangle([100, ey, W - 100, ey + 62], radius=31, fill=GREEN)
    ctext(d, "Confirmar recepción del reporte", ey + 17, F(27, bold=True), WHITE)

    y += ep_h + 22

    # ── Legend ────────────────────────────────────────────────
    ctext(d, "Significado de los íconos:", y, F(33, bold=True), WHITE)
    y += 52

    legend = [
        (LGRN,  DGRN, "OK",  "Registro completo (entrada + salida)"),
        (LAMB,  DAMB, " ! ", "Salida no registrada — requiere corrección"),
        (LRED,  DRED, " X ", "Ausencia o día sin registro"),
        (LGRAY, GRAY, " - ", "Día no hábil, feriado o fin de semana"),
    ]
    for bg, fg, icon, desc in legend:
        card(d, 50, y, W - 100, 72, bg, r=14, outline=fg, ow=2)
        d.text((82, y + 16), icon, font=F(30, bold=True), fill=fg)
        for i, line in enumerate(wrap_lines(d, desc, F(28), W - 250)):
            d.text((160, y + 16 + i * 32), line, font=F(28), fill=NAVY)
        y += 82

    bottom_cta(d,
               "Revisa el email y confirma recepción",
               "El botón verde registra tu acuse de recibo",
               y + 18, slide_num=3)

    std_footer(img, d)
    path = os.path.join(OUT_DIR, "asistencia_story_s3.png")
    img.save(path)
    print(f"Guardado: {path}")


# ══════════════════════════════════════════════════════════════
# SLIDE 4 — QUÉ DEBES HACER
# ══════════════════════════════════════════════════════════════
def make_s4():
    img = new_slide()
    d   = ImageDraw.Draw(img)
    y   = std_header(img, d)

    y = section_header(d, "QUÉ DEBES HACER", y,
                        bg=BLUE, h=108, fsz=50) + 30

    steps = [
        (1, GREEN, LGRN, DGRN,
         "Revisa el email de RRHH",
         "Llega desde recursoshumanos@ueipab.edu.ve los días 1 y 16 de cada mes"),
        (2, BLUE, LIGHT, NAVY,
         "Verifica tu registro",
         "Confirma que todas tus entradas y salidas estén correctas"),
        (3, AMBER, LAMB, DAMB,
         "Reporta si hay un error",
         "Usa el enlace en el email para solicitar una corrección a RRHH"),
        (4, GREEN, LGRN, DGRN,
         "Confirma la recepción",
         "Haz clic en el botón verde — queda registrado con fecha y hora"),
    ]
    for num, bg_num, bg_card, fg_card, title, desc in steps:
        card(d, 50, y, W - 100, 185, bg_card, r=20, outline=fg_card, ow=3)
        d.ellipse([72, y + 30, 136, y + 94], fill=bg_num)
        nf  = F(42, bold=True)
        nbb = d.textbbox((0, 0), str(num), font=nf)
        nx  = 104 - (nbb[2] - nbb[0]) // 2
        ny  = y + 62 - (nbb[3] - nbb[1]) // 2 - nbb[1]
        d.text((nx, ny), str(num), font=nf, fill=WHITE)
        d.text((155, y + 22), title, font=F(34, bold=True), fill=fg_card)
        ty = y + 70
        for line in wrap_lines(d, desc, F(28), W - 240):
            d.text((155, ty), line, font=F(28), fill=NAVY)
            ty += 36
        y += 203

    y += 20

    # ── Important date ────────────────────────────────────────
    card(d, 50, y, W - 100, 230, (60, 18, 28), r=22, outline=RED, ow=4)
    d.rounded_rectangle([50, y, W - 50, y + 62], radius=22, fill=RED)
    ctext(d, "IMPORTANTE — A PARTIR DEL 1 DE JUNIO 2026", y + 15, F(27, bold=True), WHITE)
    ty = y + 80
    msg = ("Las ausencias injustificadas podrán generar "
           "descuentos en tu nómina. Reporta cualquier "
           "error ANTES del cierre de cada quincena.")
    for line in wrap_lines(d, msg, F(29), W - 150):
        ctext(d, line, ty, F(29), WHITE)
        ty += 40
    y += 250

    # ── Contact ───────────────────────────────────────────────
    card(d, 50, y, W - 100, 120, (36, 60, 120), r=20, outline=BLUE, ow=2)
    ctext(d, "Consultas y correcciones:",          y + 15, F(30, bold=True), WHITE)
    ctext(d, "recursoshumanos@ueipab.edu.ve", y + 60, F(30), LBLUE)
    y += 140

    bottom_cta(d,
               "Tu asistencia ya está siendo registrada",
               "Sistema activo desde mayo 2026",
               y + 18, slide_num=4)

    std_footer(img, d)
    path = os.path.join(OUT_DIR, "asistencia_story_s4.png")
    img.save(path)
    print(f"Guardado: {path}")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generando stories de asistencia UEIPAB...")
    make_s1()
    make_s2()
    make_s3()
    make_s4()
    print(f"Listo. 4 slides en {OUT_DIR}")
