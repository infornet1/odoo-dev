#!/usr/bin/env python3
"""
Newsletter: ¡Oro Regional en Robótica Kurios! — Email Blast
============================================================
Celebra el 1er lugar (medalla de oro, Desafío #14) del Instituto Privado
"Andrés Bello" en el Torneo Regional de Robótica Kurios — Zona Oriente,
disputado el sábado 20 de junio en el Colegio Integral El Manglar
(Nueva Barcelona, Edo. Anzoátegui).

Campeones: Isaac Carrillo · Jadasa Mayz · Andrés Córdoba

FROM:      soporte@ueipab.edu.ve   (Instituto Andrés Bello)
REPLY-TO:  soporte@ueipab.edu.ve
SUBJECT:   ¡EL ANDRÉS BELLO SE ADUEÑA DEL ORO EN EL REGIONAL DE ROBÓTICA KURIOS!🏅🤖

Recipients are the hard-coded community list below — every address is sent
its OWN individual email (one mail.mail per address, deduped case-insensitive).

Media is served from /var/www/dev/flyers/kurios/ → https://dev.ueipab.edu.ve/flyers/kurios/

Usage:
    python3 scripts/send_robotics_kurios_newsletter.py            # dry-run (lists recipients)
    python3 scripts/send_robotics_kurios_newsletter.py --preview  # CEO only (real send)
    python3 scripts/send_robotics_kurios_newsletter.py --live     # full community blast
"""

import argparse
import json
import logging
import os
import re
import socket
import ssl
import sys
import time
import xmlrpc.client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

PROD_CFG   = os.environ.get('KURIOS_PROD_CFG', '/opt/odoo-dev/config/production.json')

ODOO_URL   = 'https://odoo.ueipab.edu.ve'
LOGO_URL   = f'{ODOO_URL}/web/image/res.company/1/logo'        # 1080×1080 square logo
MEDIA_BASE = 'https://dev.ueipab.edu.ve/flyers/kurios'

EMAIL_FROM = 'Colegio Andrés Bello - Soporte <soporte@ueipab.edu.ve>'
REPLY_TO   = 'soporte@ueipab.edu.ve'
SUBJECT    = 'Orgullo tigrense: nuestros 7 equipos en el Regional de Robótica Kurios 🤖💙'

CEO_EMAIL  = 'gustavo.perdomo@ueipab.edu.ve'
CEO_NAME   = 'Gustavo Perdomo'

MAIL_QUEUE_CRON_ID = 3
SEND_DELAY         = 0.15    # tiny pause between individual mail.mail creates
BATCH_SIZE         = 10      # emails released per batch
BATCH_INTERVAL     = 140     # seconds to wait between batches

# Resume/idempotency: every successfully-queued address is persisted here so a
# crash + re-run never re-sends. Override path with KURIOS_STATE.
STATE_FILE = os.environ.get('KURIOS_STATE', '/tmp/kurios_sent_state.json')

# ── Community recipient list (raw — every address gets its own email) ───────────

RAW_RECIPIENTS = """
todalacomunidad@ueipab.edu.ve
adriangelacandiago16@gmail.com
mairealeflores2178@gmail.com;gonzalezavp21@gmail.com
alexisqnes@gmail.com;alexisqnes@hotmail.com
alirioj_20@hotmail.com
amadamelendez26@gmail.com
ambarhel@gmail.com
kamira1975@hotmail.com
anamariaguevara13@gmail.com;hernanvargas85@gmail.com;guevaraamx@gmail.com
analoreto_16@hotmail.com;anadel16@gmail.com
alzolarae@gmail.com;galvisanais@gmail.com
danielr85m85@gmail.com;acvg819@gmail.com
miregamboab@gmail.com;andresmhernandez@gmail.com
alegnah163@gmail.com
angelicagomes_01@hotmail.com;angelicagoms15@gmail.com
angelicaluzardo93@hotmail.com
ramoncabeza@gmail.com
1303anmirth@gmail.com
neumo.martinez@gmail.com
salazarmc@outlook.es
arelisdemorillo24@gmail.com;pastormorillo2021@gmail.com
garciaadc@gmail.com;figuerahd@gmail.com
Argniceloreto@gmail.com
astrid2704@hotmail.com;astridzabala@gmail.com
belisamc09@gmail.com;marcocanizalez1806@gmail.com
benito.torrealba@gmail.com;karla.gueli@gmail.com
betzimarpr@gmail.com
jbisleibymata@gmail.com
vayoletca@gmail.com
candy.one7@gmail.com
carpiosweetamelie@gmail.com
militzalaya.17@gmail.com;carlos-laya@hotmail.com;militzabolivar1782@gmail.com
tecsmecca@gmail.com
dorirms@gmail.com;cash1974@gmail.com
carmenpereira0712@gmail.com
carmentenias8@gmail.com;carmen-t.10@hotmail.com
gonzalezcju2543@gmail.com
azocarcatherine53@gmail.com
cfiguerasilva@gmail.com
cheni0702@gmail.com
gr.cristinai@gmail.com; cristina_igr@icloud.com
bellorindd@gmail.com;jenrit09@gmail.com
nanidomin9@gmail.com; mayra86852@gmail.com
ercilia.ulloa@gmail.com;daniel.vasquez25@gmail.com
danielagrondon553@gmail.com;carrillo.julio.pn@gmail.com
danielavillamizarc@gmail.com
danneyse@gmail.com
davidjevansmt@gmail.com
dayanacperdomo@yahoo.com
dencilvalera@gmail.com
doalbert@gmail.com
dorelvisher@gmail.com
edddajoserodrigueztineo@gmail.com
cisnerst@gmail.com;jjedgardo@hotmail.com
joachim@brusseel.be;edifelmarinv@gmail.com
eduardo.jose.rangel79@gmail.com;nathaliavilla04@gmail.com
eliasjose30@gmail.com;odaguis@gmail.com
elizabethvioletahayer@gmail.com;hayerelizabethvioleta@gmail.com
elviramatamqz@gmail.com;melviram511@gmail.com
keidysr89@gmail.com;elvisalexandergomezcampos@gmail.com
emilyquinterogandica@gmail.com
noiralybeltran@gmail.com
erickmontilla21@gmail.com;genesisg.guelia@gmail.com
fradicor@gmail.com
cpcnataliavillagran@gmail.com;freddyaquiles1976@gmail.com
giovanella.velasquez@gmail.com
damarinm@ueipab.edu.ve;gloriavictoriarespaldo@gmail.com
rubneida@gmail.com;pereirago@gmail.com;pereirago@onnestech.com.ve
gustavoenrique220@gmail.com;danielbeta@gmail.com
hjcallesq@gmail.com
velasquez.snv@gmail.com
ildemaroarrioja@gmail.com;ildemaro.arrioja@gmail.com;mariaroapo@gmail.com
irelys.marin@gmail.com
joselynherrera05@gmail.com;joselynh0511@gmail.com
machadoiriana@hotmail.com;jesusalfonzoa@gmail.com
isamarnarvaez91@gmail.com
jeancano@hotmail.com
yina1901rodriguez@gmail.com
munozjeanc@gmail.com;diurkapalma@gmail.com
sannelys1@gmail.com;lacruz.jesus1985@gmail.com
tillerotatiana@gmail.com;jesusr.18@gmail.com
jarp190891@gmail.com
jorgelb30@gmail.com
martinez.jorge53@gmail.com;emighely@gmail.com
bianessy29@gmail.com;joseangelcontrerasl@gmail.com
jhescalona12@gmail.com
johanaquilarquez@gmail.com;joserafael180681@gmail.com
jr1805173@gmail.com
jsolorzanoc@hotmail.com
josetabask1975@gmail.com;mariangelamfx198032@gmail.com
ramsoj18@gmail.com;adrianamarfer@gmail.com;ramsoj18@hotmail.com
mogollonjoy@gmail.com
gonzalez_kjl@hotmail.com;gonzalezkjl80@gmail.com;jpgonzalez@ueipab.edu.ve
guerrakariangela1@icloud.com;guerrakariangela@gmail.com
williamd0205@gmail.com;eilyndelgado2009@gmail.com
karlimer78@gmail.com
karlengab.2786@gmail.com
vkathy80@gmail.com;vkathy80@hotmail.com
keiladbb3@gmail.com
lewisdugarte@gmail.com;kellykarina22@gmail.com;ppcglogjunin@gmail.com
ingliliannareyes@gmail.com
maestrialismer.barrios@gmail.com
lourdescamayar@gmail.com
luiscondales@hotmail.com;dennyshalom@hotmail.com;luisalbert7910@gmail.com
luis.goite@gmail.com;velamaria.pqt@gmail.com
lorenariveraq@gmail.com;lmgh19061013@gmail.com
luismarcanof@gmail.com;lunamanuely1@gmail.com
herreramix246@gmail.com
maisuarezb@gmail.com
drigelio.jose@gmail.com;marialejandra1202@gmail.com
apontemarivic@gmail.com;apontemarivict@gmail.com
Bompartt@yahoo.es
mlanz45@gmail.com
mariamartin_n@hotmail.com
gabrielameneses07@gmail.com
ybagnieto8@gmail.com
marivic03051@gmail.com;pablocordoba4379@gmail.com
maderamariana@gmail.com
marilyn.romero3103@hotmail.com;marilyn.romero3103@gmail.com
vasquezmaryory72@gmail.com;juanmanuel.correia.b@gmail.com
mayrobissanchez@gmail.com;cornelioguzman@gmail.com
mgbgcolegio@gmail.com
noriannydmb@gmail.com;mervisjeg@gmail.com
miguel1987g@gmail.com
arq.miguelkarim@gmail.com
susanaquijada102@gmail.com
velasqueznt27@gmail.com; velasqueznt27@icloud.com
nchleotaud@gmail.com
natalia93rom@gmail.com
asesorias.empresas.y.u.2019@gmail.com
nellyslucy@gmail.com
neyladiaz4@gmail.com
tatinormaestre@gmail.com
gonzaleznak24@gmail.com
orlimarn@gmail.com
osnaydasantamaria@gmail.com
paolavelasco2202@gmail.com;paolavelasco2926@gmail.com
mdldvia24@gmail.com;ortegapedro.21@gmail.com
pedroso2967@gmail.com
cosmapca@gmail.com
raizajrendon@gmail.com
requenaramly@gmail.com
raquelelizabethenator@gmail.com
lisbeth.campos.0408@gmail.com;raulosunan@gmail.com
reyfts1112@gmail.com
robertovera365@outlook.com; yamelsancheztellechea@gmail.com
ronaldbutto@gmail.com
ronmel.acevedo83@gmail.com
rmarcano79@gmail.com
yanezrosalia429@gmail.com
roximarhr01@gmail.com
mruthd2@gmail.com
samiraparrah@gmail.com
sarely_bellorin28@hotmail.com;sarelybellorin@gmail.com
sharifaalrifai4@gmail.com;mikhaelark@gmail.com
maitasorelis@gmail.com
susana.taraboulsi@gmail.com
alcalata12@gmail.com
vanessa.dbv@gmail.com
vanehdezmarchan@gmail.com
vlvg1606@gmail.com;v.villamizar@outlook.com;fatima.dugarte@gmail.com
misleflores@gmail.com;plazmisle@gmail.com;vircaso@gmail.com
contreraswilmeilys@gmail.com
yblondell@gmail.com;keniadelvalle@gmail.com
yenseryenny@gmail.com
kityangeles@gmail.com
figueroays@gmail.com
yinfaka@gmail.com
nunezyoicis05@gmail.com
yoselinpenaguillen@gmail.com;victoriavicky720@gmail.com
romaneduardo53@gmail.com;ybenavides8@gmail.com
Lisa71736@gmail.com;yamilatabete1@hotmail.com;lianghaiying1984@gmail.com
zorimars@gmail.com
eduardosc412@gmail.com;karinadelvallealemancarranza@gmail.com
olysang.geo@gmail.com;olysamg@gmail.com
jennyferdelcarmenmanriqueperez@gmail.com
ruddyramirez312@gmail.com
alfonzoyn@gmail.com
hernanjbrito1@gmail.com
yeseniabotelho@gmail.com
dradayhannagonzalez@gmail.com
zulgeidismarcano@gmail.com
francis.azuaje8@gmail.com
marquezkimf@gmail.com
"""

# Addresses with confirmed hard-bounce DSNs — skip to avoid noise
SKIP_EMAILS = {
    'olysamg@gmail.com',     # EMIRO GONZALEZ — failing since 2026-05-17 (conv #44815)
}

_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')


def _parse_recipients():
    """Flatten the raw blob into a deduped (case-insensitive) ordered email list."""
    seen, out = set(), []
    for token in _EMAIL_RE.findall(RAW_RECIPIENTS):
        e = token.strip()
        k = e.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


# ── Config + XML-RPC ───────────────────────────────────────────────────────────

def _load_prod_cfg():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    return cfg['url'], cfg['db'], cfg['user'], cfg['api_key']


_CONN = {}   # holds live {url, models, db, uid, key}

# Transient transport errors that mean "the socket died, just reconnect & retry"
_RETRYABLE = (ssl.SSLError, socket.error, OSError, ConnectionError,
              xmlrpc.client.ProtocolError, xmlrpc.client.Fault, EOFError)


def _connect():
    """(Re)establish the XML-RPC connection and store it in _CONN."""
    url, db, user, key = _load_prod_cfg()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, key, {})
    if not uid:
        raise RuntimeError('XML-RPC authentication failed')
    _CONN.update(url=url, db=db, uid=uid, key=key,
                 models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object'))
    return uid


def call(model, method, args=None, kw=None, tries=4):
    """execute_kw with auto-reconnect. Survives idle-killed sockets between batches."""
    last = None
    for attempt in range(1, tries + 1):
        try:
            return _CONN['models'].execute_kw(
                _CONN['db'], _CONN['uid'], _CONN['key'],
                model, method, args or [[]], kw or {})
        except _RETRYABLE as e:
            last = e
            log.warning("call %s.%s failed (attempt %d/%d): %s — reconnecting…",
                        model, method, attempt, tries, e)
            time.sleep(min(2 * attempt, 8))
            try:
                _connect()
            except Exception as ce:
                log.warning("reconnect failed: %s", ce)
    raise RuntimeError(f"call {model}.{method} failed after {tries} attempts: {last}")


# ── Resume state ───────────────────────────────────────────────────────────────

def _load_state():
    try:
        return set(x.lower() for x in json.load(open(STATE_FILE)))
    except (FileNotFoundError, ValueError):
        return set()


def _save_state(sent_set):
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(sorted(sent_set), f)
    os.replace(tmp, STATE_FILE)


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _full_img(src, alt):
    return (
        f'<a href="{MEDIA_BASE}/{src}" target="_blank" style="text-decoration:none;">'
        f'<img src="{MEDIA_BASE}/{src}" alt="{alt}" width="600" '
        f'style="width:100%;max-width:536px;height:auto;display:block;border-radius:12px;'
        f'border:1px solid #e3e8f0;"/></a>'
    )


def _video_block(poster, mp4, label, caption):
    """A 'flagged' featured-video card: clickable poster + prominent play button."""
    return f"""
  <tr>
    <td style="padding:6px 32px 4px;">
      <div style="display:inline-block;background:#ffd400;color:#1a1a6e;font-size:11px;
                  font-weight:bold;padding:4px 12px;border-radius:14px;letter-spacing:0.5px;">
        ⭐ DESTACADO &bull; 🎥 {label}
      </div>
    </td>
  </tr>
  <tr>
    <td style="padding:8px 32px 6px;position:relative;">
      <a href="{MEDIA_BASE}/{mp4}" target="_blank" style="text-decoration:none;display:block;">
        <img src="{MEDIA_BASE}/{poster}" alt="{caption}" width="600"
             style="width:100%;max-width:536px;height:auto;display:block;border-radius:12px;
                    border:3px solid #ffd400;"/>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center" style="padding:0 32px 6px;text-align:center;">
      <table role="presentation" cellpadding="0" cellspacing="0" align="center" style="margin:0 auto;">
        <tr><td align="center" style="border-radius:26px;background:#1a1a6e;
                   box-shadow:0 4px 12px rgba(26,26,110,0.32);">
          <a href="{MEDIA_BASE}/{mp4}" target="_blank"
             style="display:inline-block;background:linear-gradient(135deg,#1a1a6e,#2b6fd6);
                    color:#fff;text-decoration:none;font-size:14px;font-weight:bold;
                    padding:11px 34px;border-radius:26px;">
            ▶️ Reproducir video
          </a>
        </td></tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="padding:0 32px 18px;text-align:center;">
      <p style="margin:0;color:#888;font-size:12px;font-style:italic;">{caption}</p>
    </td>
  </tr>"""


# ── HTML builder ───────────────────────────────────────────────────────────────

def _build_html(is_preview: bool = False) -> str:
    preview_banner = (
        '<div style="background:#c0392b;color:#fff;text-align:center;padding:10px;'
        'font-size:13px;font-weight:bold;">'
        '⚠️ VISTA PREVIA — Solo para revisión. No enviado a la comunidad.</div>'
    ) if is_preview else ''

    # Photo album: 6–21 minus 8 & 14 (used as video posters) → 2-column grid
    album_ids = [6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21]
    album_rows = ''
    for i in range(0, len(album_ids), 2):
        pair = album_ids[i:i + 2]
        cells = ''
        for n in pair:
            cells += (
                f'<td width="50%" style="padding:5px;" valign="top">'
                f'<a href="{MEDIA_BASE}/{n}.jpeg" target="_blank">'
                f'<img src="{MEDIA_BASE}/{n}.jpeg" alt="Robótica Kurios foto {n}" width="258" '
                f'style="width:100%;height:auto;display:block;border-radius:9px;border:1px solid #e3e8f0;"/>'
                f'</a></td>'
            )
        if len(pair) == 1:
            cells += '<td width="50%" style="padding:5px;">&nbsp;</td>'
        album_rows += f'<tr>{cells}</tr>'

    # Promotional flyers a–f — single row (clickable thumbnails)
    flyer_files = ['a', 'b', 'c', 'd', 'e', 'f']
    flyer_titles = {
        'a': 'STEAM &amp; Fútbol — Historia Copa Mundial',
        'b': 'Inscripciones Abiertas 2026-2027',
        'c': 'Clases de Robótica (alianza Kurios)',
        'd': 'Curso de Dibujo y Pintura',
        'e': 'Bachillerato Virtual 100% online',
        'f': 'Cursos de Inglés After School (MOA)',
    }
    flyer_cells = ''
    for f in flyer_files:
        flyer_cells += (
            f'<td width="16%" style="padding:3px;" valign="top">'
            f'<a href="{MEDIA_BASE}/{f}.jpeg" target="_blank" title="{flyer_titles[f]}">'
            f'<img src="{MEDIA_BASE}/{f}.jpeg" alt="{flyer_titles[f]}" width="88" '
            f'style="width:100%;height:auto;display:block;border-radius:6px;border:1px solid #e3e8f0;"/>'
            f'</a></td>'
        )

    # All-teams gallery — one full-width poster per team + caption (no invented placement)
    teams = [
        ('desafio3.jpg',            'Desaf&iacute;o 3',     'Rael Tenorio &bull; Athena Cruz'),
        ('desafio4.jpg',            'Desaf&iacute;o 4',     'Luc&iacute;a Pereira &bull; Saileh Mu&ntilde;oz &bull; Miranda Cuellar'),
        ('desafio5.jpg',            'Desaf&iacute;o 5',     'Luc&iacute;a Gonz&aacute;lez &bull; H&eacute;ctor Calles &bull; Alexandra S&aacute;nchez'),
        ('desafio7a.jpg',           'Desaf&iacute;o 7 (A)', 'Santiago Mart&iacute;nez &bull; Pedro Chanchamire &bull; &Aacute;lvaro Laya'),
        ('desafio12.jpg',           'Desaf&iacute;o 12',    'Fabriccio Figueroa &bull; Mariana Far&iacute;as &bull; Luis Goite'),
        ('desafio-unidad111r.jpg',  'Unidad 111 R',         'Sabrina Torres &bull; Sebasti&aacute;n Delgado &bull; Ariela Figueroa'),
    ]
    team_blocks = ''
    for src, name, students in teams:
        team_blocks += f"""
  <tr>
    <td style="padding:14px 32px 2px;text-align:center;">
      <div style="display:inline-block;background:#1a1a6e;color:#fff;font-size:13px;
                  font-weight:bold;padding:5px 18px;border-radius:14px;">🤖 {name}</div>
    </td>
  </tr>
  <tr>
    <td style="padding:6px 32px 2px;text-align:center;">{_full_img(src, name + ' — ' + students)}</td>
  </tr>
  <tr>
    <td style="padding:0 32px 8px;text-align:center;">
      <p style="margin:0;font-size:13px;color:#444;line-height:1.5;">{students}</p>
    </td>
  </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>¡Oro Regional en Robótica Kurios!</title>
</head>
<body style="margin:0;padding:0;background:#eef1f8;font-family:Arial,Helvetica,sans-serif;">
{preview_banner}
<table cellpadding="0" cellspacing="0" width="100%" style="background:#eef1f8;">
<tr><td align="center" style="padding:24px 10px;">
<table cellpadding="0" cellspacing="0" width="600"
       style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden;
              box-shadow:0 4px 28px rgba(0,0,0,0.12);">

  <!-- ══ HEADER ══ -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a1a6e 0%,#2b6fd6 100%);
               padding:34px 32px 26px;text-align:center;">
      <img src="{LOGO_URL}" alt="Instituto Andr&eacute;s Bello" width="78" height="78"
           style="border-radius:50%;border:3px solid rgba(255,212,0,0.85);
                  display:block;margin:0 auto 12px;"/>
      <h1 style="margin:0;color:#fff;font-size:20px;font-weight:bold;line-height:1.3;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </h1>
      <p style="margin:4px 0 14px;color:rgba(255,255,255,0.82);font-size:13px;">
        El Tigre, Estado Anzo&aacute;tegui
      </p>
      <div style="display:inline-block;background:#ffd400;border-radius:22px;padding:9px 24px;">
        <span style="color:#1a1a6e;font-size:15px;font-weight:bold;">
          🏅🤖 ¡CAMPEONES REGIONALES DE ROB&Oacute;TICA KURIOS!
        </span>
      </div>
    </td>
  </tr>

  <!-- ══ HERO POSTER ══ -->
  <tr>
    <td style="padding:0;">
      <img src="{MEDIA_BASE}/2.jpeg" alt="Torneo Regional de Rob&oacute;tica y Tecnolog&iacute;a Kurios — Desaf&iacute;o 14"
           width="600" style="width:100%;height:auto;display:block;"/>
    </td>
  </tr>

  <!-- ══ HEADLINE ══ -->
  <tr>
    <td style="padding:26px 32px 6px;text-align:center;">
      <h2 style="margin:0;color:#1a1a6e;font-size:23px;font-weight:bold;line-height:1.25;">
        ¡Felicitaciones a TODOS nuestros<br/>equipos de Rob&oacute;tica Kurios! 🏆🤖
      </h2>
      <p style="margin:10px 0 0;color:#2b6fd6;font-size:13px;font-weight:bold;text-transform:uppercase;letter-spacing:0.6px;">
        El Tigre &bull; Zona Oriente &bull; S&aacute;bado 20 de junio
      </p>
    </td>
  </tr>

  <!-- ══ LEAD ══ -->
  <tr>
    <td style="padding:14px 32px 6px;">
      <p style="margin:0 0 14px;color:#444;font-size:14px;line-height:1.8;">
        El pasado <strong>s&aacute;bado 20 de junio</strong>, en el <strong>Colegio Integral El
        Manglar</strong> (Nueva Barcelona, Edo. Anzo&aacute;tegui), <strong>siete equipos</strong>
        del Instituto Privado <strong>&ldquo;Andr&eacute;s Bello&rdquo;</strong> dejaron en alto el
        nombre de nuestra instituci&oacute;n en el <strong>Torneo Regional de Rob&oacute;tica de la
        Zona Oriente</strong> &mdash; la competencia Kurios.
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.8;">
        Coronamos la jornada con la <strong>medalla de oro 🥇 del Desaf&iacute;o 14</strong>, pero
        nuestro orgullo es por <strong>cada uno</strong> de los estudiantes que compiti&oacute; con
        disciplina, ingenio y la mejor aplicaci&oacute;n de la metodolog&iacute;a <strong>STEAM</strong>.
        ¡Hoy los celebramos a <strong>todos</strong>! 💙
      </p>
    </td>
  </tr>

  <!-- ══ CHAMPIONS CARD ══ -->
  <tr>
    <td style="padding:18px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:linear-gradient(135deg,#fff8e1,#fff3c4);
                    border:2px solid #ffd400;border-radius:14px;">
        <tr>
          <td style="padding:20px 22px;text-align:center;">
            <p style="margin:0 0 4px;font-size:12px;color:#b37a00;font-weight:bold;
                      text-transform:uppercase;letter-spacing:1px;">⚙️ Nuestros Campeones</p>
            <p style="margin:0 0 10px;font-size:20px;color:#1a1a6e;font-weight:bold;line-height:1.4;">
              Isaac Carrillo<br/>Jadasa Mayz<br/>Andr&eacute;s C&oacute;rdoba
            </p>
            <div style="display:inline-block;background:#1a1a6e;border-radius:10px;padding:10px 18px;">
              <span style="color:#ffd400;font-size:15px;font-weight:bold;">
                🥇 Medalla de Oro &bull; 1er Lugar &bull; Desaf&iacute;o #14
              </span>
            </div>
            <p style="margin:12px 0 0;font-size:13px;color:#555;line-height:1.6;">
              Una de las pruebas de <strong>mayor dificultad t&eacute;cnica</strong> de la
              competencia Kurios — superada con el <strong>mejor tiempo del torneo</strong>. ⏱️
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ ALL-TEAMS GALLERY ══ -->
  <tr>
    <td style="padding:26px 32px 2px;text-align:center;border-top:1px solid #eef1f8;">
      <h3 style="margin:14px 0 4px;color:#1a1a6e;font-size:18px;font-weight:bold;">
        🤖 Conoce a todos nuestros equipos
      </h3>
      <p style="margin:0;color:#888;font-size:12px;">Seis equipos m&aacute;s que nos llenaron de orgullo en El Manglar.</p>
    </td>
  </tr>
{team_blocks}

  <!-- ══ PODIUM HIGHLIGHT ══ -->
  <tr>
    <td style="padding:22px 32px 6px;text-align:center;border-top:1px solid #eef1f8;">
      <h3 style="margin:14px 0 12px;color:#1a1a6e;font-size:17px;font-weight:bold;">
        🏆 Juntos en El Manglar
      </h3>
      {_full_img('1.jpeg', 'Collage Kurios Robotics 2026 — momentos de triunfo y trabajo en equipo')}
    </td>
  </tr>

  <!-- ══ CLOSING ══ -->
  <tr>
    <td style="padding:18px 32px 8px;">
      <p style="margin:0 0 12px;color:#444;font-size:14px;line-height:1.8;">
        Cada hora de preparaci&oacute;n, cada l&iacute;nea de c&oacute;digo y cada reto superado en la
        cancha reafirman nuestro compromiso de avanzar hacia la <strong>excelencia acad&eacute;mica y
        tecnol&oacute;gica</strong>. Gracias a los estudiantes, a las familias y a los profesores
        especialistas que lo hicieron posible.
      </p>
      <p style="margin:0;color:#1a1a6e;font-size:15px;line-height:1.7;font-weight:bold;text-align:center;">
        Desde la gran familia del Andr&eacute;s Bello, ¡felicitamos de coraz&oacute;n a
        <span style="color:#2b6fd6;">todos nuestros equipos</span>! 💙🏆🤖<br/>
        <span style="font-weight:normal;color:#555;font-size:13px;">
          ¡Gracias por hacernos vibrar de orgullo y demostrar que somos verdaderos triunfadores!
        </span>
      </p>
    </td>
  </tr>

  <!-- ══ PROMO FLYERS ROW ══ -->
  <tr>
    <td style="padding:22px 28px 6px;text-align:center;border-top:1px solid #eef1f8;">
      <h3 style="margin:16px 0 4px;color:#1a1a6e;font-size:16px;font-weight:bold;">
        ✨ Conoce nuestra oferta educativa
      </h3>
      <p style="margin:0 0 10px;color:#888;font-size:12px;">Inscripciones 2026-2027 abiertas &bull; ¡Cont&aacute;ctanos!</p>
    </td>
  </tr>
  <tr>
    <td style="padding:0 20px 18px;">
      <table cellpadding="0" cellspacing="0" width="100%"><tr>
        {flyer_cells}
      </tr></table>
    </td>
  </tr>

  <!-- ══ FOOTER ══ -->
  <tr>
    <td style="background:#1a1a6e;padding:20px 32px;text-align:center;">
      <p style="margin:0 0 6px;font-size:13px;color:#ffd400;font-weight:bold;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </p>
      <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.78);line-height:1.7;">
        El Tigre, Edo. Anzo&aacute;tegui &bull; RIF J-08008617-1<br/>
        📷 @ueipab &bull; 🌐 www.ueipab.edu.ve<br/>
        Consultas: <a href="mailto:soporte@ueipab.edu.ve"
                      style="color:#9ec5ff;">soporte@ueipab.edu.ve</a>
        &bull; 📱 0414-8321963 / 0424-8944898
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Send helpers ───────────────────────────────────────────────────────────────

def _create_mail(to_email, html):
    mail_id = call('mail.mail', 'create', [[{
        'subject':     SUBJECT,
        'email_from':  EMAIL_FROM,
        'reply_to':    REPLY_TO,
        'email_to':    to_email,
        'body_html':   html,
        'state':       'outgoing',
        'auto_delete': True,
    }]])
    log.info("Queued → %s (mail.mail id=%s)", to_email, mail_id)
    return mail_id


def _trigger_mail_queue():
    log.info("Triggering mail queue cron (id=%d)…", MAIL_QUEUE_CRON_ID)
    call('ir.cron', 'method_direct_trigger', [[MAIL_QUEUE_CRON_ID]])
    log.info("Mail queue triggered.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Robotics Kurios newsletter blast')
    parser.add_argument('--preview', action='store_true', help='Send only to CEO for review')
    parser.add_argument('--live', action='store_true', help='Send to the full community list')
    args = parser.parse_args()

    dry_run = not (args.preview or args.live)

    recipients = _parse_recipients()
    log.info("Parsed %d unique recipient addresses from community list.", len(recipients))

    if dry_run:
        log.info("DRY-RUN — no emails sent. Use --preview (CEO) or --live (full blast).")
        for e in recipients:
            tag = '  [SKIP-bounce]' if e.lower() in SKIP_EMAILS else ''
            log.info("  would send → %s%s", e, tag)
        log.info("Total deliverable: %d (skipping %d known bounce).",
                 len([e for e in recipients if e.lower() not in SKIP_EMAILS]),
                 len([e for e in recipients if e.lower() in SKIP_EMAILS]))
        return

    if args.live and not recipients:
        log.error("GUARD: --live blocked — recipient list is empty.")
        sys.exit(2)

    _connect()
    log.info("Connected to Odoo (%s / %s)", ODOO_URL, _CONN['db'])

    if args.preview:
        _create_mail(CEO_EMAIL, _build_html(is_preview=True))
        _trigger_mail_queue()
        log.info("Preview sent to %s", CEO_EMAIL)
        return

    html = _build_html(is_preview=False)
    already = _load_state()                  # addresses sent on a previous (possibly crashed) run
    deliverable = [e for e in recipients
                   if e.lower() not in SKIP_EMAILS and e.lower() not in already]
    skipped = len([e for e in recipients if e.lower() in SKIP_EMAILS])
    resumed = len([e for e in recipients if e.lower() in already])
    total = len(deliverable)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE if total else 0
    eta_min = max(0, total_batches - 1) * BATCH_INTERVAL / 60.0
    log.info("BLAST START — %d to send | %d already-sent (resume) | %d skipped | "
             "%d batches of %d | %ds between | ETA ~%.0f min",
             total, resumed, skipped, total_batches, BATCH_SIZE, BATCH_INTERVAL, eta_min)
    if total == 0:
        log.info("Nothing to send — state file already covers every address.")
        return

    sent_set = set(already)
    sent = 0
    for bi in range(total_batches):
        batch = deliverable[bi * BATCH_SIZE:(bi + 1) * BATCH_SIZE]
        for e in batch:
            _create_mail(e, html)            # one individual email per address
            sent_set.add(e.lower())
            _save_state(sent_set)            # persist after every send → crash-safe resume
            sent += 1
            time.sleep(SEND_DELAY)
        _trigger_mail_queue()                # release this batch from the queue
        log.info("◆ Batch %d/%d released — %d/%d this run (%d total incl. resume).",
                 bi + 1, total_batches, sent, total, len(sent_set))
        if bi < total_batches - 1:
            log.info("Waiting %ds before next batch…", BATCH_INTERVAL)
            time.sleep(BATCH_INTERVAL)

    log.info("DONE — queued this run: %d | resumed: %d | skipped: %d | grand total sent: %d",
             sent, resumed, skipped, len(sent_set))


if __name__ == '__main__':
    main()
