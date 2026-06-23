#!/usr/bin/env python3
"""
AVISO IMPORTANTE SOBRE PAGOS — Email Blast
==========================================
Informa a la comunidad de padres y representantes del Instituto Privado
"Andrés Bello" que la cuenta del Banco de Venezuela NO está disponible
temporalmente para recibir pagos, y lista las cuentas alternativas
(transferencias + pago móvil) habilitadas.

FROM:      pagos@ueipab.edu.ve   (Instituto Andrés Bello — Administración)
REPLY-TO:  pagos@ueipab.edu.ve
SUBJECT:   AVISO IMPORTANTE SOBRE PAGOS 🚨

Recipients are the hard-coded community list below — every address is sent
its OWN individual email (one mail.mail per address, deduped case-insensitive).
Same battle-tested throttled-batch infrastructure as the Kurios newsletter
(10 emails / 140 s, SSL-idle reconnect retry, crash-safe resume state).

Usage:
    python3 scripts/send_payment_notice_email.py            # dry-run (lists recipients)
    python3 scripts/send_payment_notice_email.py --preview  # CEO only (real send)
    python3 scripts/send_payment_notice_email.py --to a@b.c # one explicit address
    python3 scripts/send_payment_notice_email.py --live     # full community blast
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

PROD_CFG   = os.environ.get('PAYMENT_NOTICE_PROD_CFG',
                            os.environ.get('KURIOS_PROD_CFG',
                                           '/opt/odoo-dev/config/production.json'))

ODOO_URL   = 'https://odoo.ueipab.edu.ve'
LOGO_URL   = f'{ODOO_URL}/web/image/res.company/1/logo'        # 1080×1080 square logo

# From/Reply-To: payment notice → pagos@ so parents reply to the right inbox.
# (SMTP auth on prod is soporte@; both share @ueipab.edu.ve so DKIM/SPF align.)
EMAIL_FROM = 'Instituto Andrés Bello - Administración <pagos@ueipab.edu.ve>'
REPLY_TO   = 'pagos@ueipab.edu.ve'
SUBJECT    = 'AVISO IMPORTANTE SOBRE PAGOS 🚨'

CEO_EMAIL  = 'gustavo.perdomo@ueipab.edu.ve'
CEO_NAME   = 'Gustavo Perdomo'

MAIL_QUEUE_CRON_ID = 3
SEND_DELAY         = 0.15    # tiny pause between individual mail.mail creates
BATCH_SIZE         = 10      # emails released per batch
BATCH_INTERVAL     = 140     # seconds to wait between batches

# Resume/idempotency: every successfully-queued address is persisted here so a
# crash + re-run never re-sends. Override path with PAYMENT_NOTICE_STATE.
STATE_FILE = os.environ.get('PAYMENT_NOTICE_STATE', '/tmp/payment_notice_sent_state.json')

# ── Payment data (single source — edit here, the HTML renders from these) ────────

RIF = 'J-08008617-1'

TRANSFERENCIAS = [
    ('Banco Plaza',     '0138-0032-47-0320013870'),
    ('Banco BanPlus',   '0174-0127-12-1274138559'),
    ('Banco Mercantil', '0105-0069-93-1069377856'),
    ('Banco Bancamiga', '0172-0702-44-7024976891'),
]

PAGO_MOVIL = [
    ('Opción A', '0414-1906296', 'Mercantil 0105 / Banplus 0174'),
    ('Opción B', '0414-2337463', 'Banco Plaza 0138'),
    ('Opción C', '0414-4375222', 'Bancamiga 0172'),
]

# Pagos en divisas (capturado de /costos-escolaridad). Tarjeta de crédito vía
# Banco Mercantil se omite intencionalmente.
DIVISAS = [
    ('Zelle',   '💲', 'pagos@ueipab.edu.ve', 'A nombre de INSTITUTO PRIVADO ANDRÉS BELLO, C.A.'),
    ('Binance', '🪙', '383 867 49',           'Binance Pay ID'),
]

# ── Community recipient list (raw — every address gets its own email) ───────────
# Identical to the Kurios community list (todalacomunidad@ included).

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


# ── HTML builder ───────────────────────────────────────────────────────────────

def _build_html(is_preview: bool = False) -> str:
    preview_banner = (
        '<div style="background:#c0392b;color:#fff;text-align:center;padding:10px;'
        'font-size:13px;font-weight:bold;">'
        '⚠️ VISTA PREVIA — Solo para revisión. No enviado a la comunidad.</div>'
    ) if is_preview else ''

    # Transferencias rows
    transf_rows = ''
    for banco, cuenta in TRANSFERENCIAS:
        transf_rows += f"""
        <tr>
          <td style="padding:9px 14px;border-bottom:1px solid #eef1f8;">
            <span style="color:#1a1a6e;font-size:14px;font-weight:bold;">{banco}</span>
          </td>
          <td style="padding:9px 14px;border-bottom:1px solid #eef1f8;text-align:right;">
            <span style="font-family:'Courier New',monospace;font-size:15px;color:#222;font-weight:bold;">{cuenta}</span>
          </td>
        </tr>"""

    # Pago móvil rows
    pm_rows = ''
    for label, phone, bancos in PAGO_MOVIL:
        pm_rows += f"""
        <tr>
          <td style="padding:9px 14px;border-bottom:1px solid #eef1f8;" valign="top">
            <span style="display:inline-block;background:#1a1a6e;color:#fff;font-size:11px;
                         font-weight:bold;padding:3px 10px;border-radius:10px;">{label}</span>
          </td>
          <td style="padding:9px 14px;border-bottom:1px solid #eef1f8;text-align:right;">
            <span style="font-family:'Courier New',monospace;font-size:16px;color:#222;font-weight:bold;">{phone}</span><br/>
            <span style="font-size:11px;color:#888;">{bancos}</span>
          </td>
        </tr>"""

    # Divisas rows (Zelle / Binance)
    div_rows = ''
    for nombre, icon, valor, nota in DIVISAS:
        div_rows += f"""
        <tr>
          <td style="padding:9px 14px;border-bottom:1px solid #eef1f8;" valign="top">
            <span style="color:#1a1a6e;font-size:14px;font-weight:bold;">{icon} {nombre}</span>
          </td>
          <td style="padding:9px 14px;border-bottom:1px solid #eef1f8;text-align:right;">
            <span style="font-family:'Courier New',monospace;font-size:15px;color:#222;font-weight:bold;">{valor}</span><br/>
            <span style="font-size:11px;color:#888;">{nota}</span>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Aviso importante sobre pagos</title>
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
               padding:30px 32px 22px;text-align:center;">
      <img src="{LOGO_URL}" alt="Instituto Andr&eacute;s Bello" width="72" height="72"
           style="border-radius:50%;border:3px solid rgba(255,212,0,0.85);
                  display:block;margin:0 auto 12px;"/>
      <h1 style="margin:0;color:#fff;font-size:19px;font-weight:bold;line-height:1.3;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </h1>
      <p style="margin:4px 0 14px;color:rgba(255,255,255,0.82);font-size:12px;">
        El Tigre, Estado Anzo&aacute;tegui &bull; RIF {RIF}
      </p>
      <div style="display:inline-block;background:#ffd400;border-radius:22px;padding:9px 24px;">
        <span style="color:#1a1a6e;font-size:15px;font-weight:bold;">
          🚨 AVISO IMPORTANTE SOBRE PAGOS
        </span>
      </div>
    </td>
  </tr>

  <!-- ══ INTRO ══ -->
  <tr>
    <td style="padding:24px 32px 6px;">
      <p style="margin:0 0 14px;color:#444;font-size:14px;line-height:1.8;">
        Estimados <strong>Padres y Representantes</strong> del Instituto Privado
        &ldquo;Andr&eacute;s Bello&rdquo;,
      </p>
      <p style="margin:0 0 14px;color:#444;font-size:14px;line-height:1.8;">
        Se les informa que, <strong>por el momento</strong>, la cuenta del
        <strong>Banco de Venezuela NO se encuentra disponible</strong> para recibir pagos.
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.8;">
        Les solicitamos cordialmente utilizar nuestras <strong>cuentas alternativas</strong>
        para sus transferencias y pagos m&oacute;viles.
      </p>
    </td>
  </tr>

  <!-- ══ BENEFICIARIO ══ -->
  <tr>
    <td style="padding:16px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f4f7fd;border:1px solid #d6e0f5;border-radius:12px;">
        <tr>
          <td style="padding:14px 18px;text-align:center;">
            <p style="margin:0 0 2px;font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;">A nombre de</p>
            <p style="margin:0;font-size:15px;color:#1a1a6e;font-weight:bold;">INSTITUTO PRIVADO ANDR&Eacute;S BELLO, C.A.</p>
            <p style="margin:4px 0 0;font-size:13px;color:#444;">RIF: <strong>{RIF}</strong></p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ TRANSFERENCIAS ══ -->
  <tr>
    <td style="padding:20px 32px 4px;">
      <p style="margin:0 0 8px;color:#1a1a6e;font-size:15px;font-weight:bold;">
        🏦 Transferencias <span style="font-weight:normal;color:#888;font-size:13px;">(Cuentas Corrientes)</span>
      </p>
      <table cellpadding="0" cellspacing="0" width="100%"
             style="border:1px solid #e3e8f0;border-radius:10px;overflow:hidden;">
        {transf_rows}
      </table>
    </td>
  </tr>

  <!-- ══ PAGO MÓVIL ══ -->
  <tr>
    <td style="padding:20px 32px 4px;">
      <p style="margin:0 0 8px;color:#1a1a6e;font-size:15px;font-weight:bold;">
        📲 Pago M&oacute;vil
      </p>
      <table cellpadding="0" cellspacing="0" width="100%"
             style="border:1px solid #e3e8f0;border-radius:10px;overflow:hidden;">
        {pm_rows}
      </table>
      <p style="margin:8px 2px 0;font-size:12px;color:#888;">RIF: <strong>{RIF}</strong></p>
    </td>
  </tr>

  <!-- ══ PAGOS EN DIVISAS ══ -->
  <tr>
    <td style="padding:20px 32px 4px;">
      <p style="margin:0 0 8px;color:#1a1a6e;font-size:15px;font-weight:bold;">
        🌎 Pagos en Divisas
      </p>
      <table cellpadding="0" cellspacing="0" width="100%"
             style="border:1px solid #e3e8f0;border-radius:10px;overflow:hidden;">
        {div_rows}
      </table>
    </td>
  </tr>

  <!-- ══ CLOSING ══ -->
  <tr>
    <td style="padding:20px 32px 8px;">
      <p style="margin:0 0 10px;color:#444;font-size:14px;line-height:1.8;">
        Agradecemos de antemano su <strong>colaboraci&oacute;n y apoyo</strong>.
      </p>
      <p style="margin:0;color:#1a1a6e;font-size:14px;font-weight:bold;">La Administraci&oacute;n</p>
    </td>
  </tr>

  <!-- ══ FOOTER ══ -->
  <tr>
    <td style="background:#1a1a6e;padding:20px 32px;text-align:center;">
      <p style="margin:0 0 6px;font-size:13px;color:#ffd400;font-weight:bold;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </p>
      <p style="margin:0;font-size:11px;color:rgba(255,255,255,0.78);line-height:1.7;">
        El Tigre, Edo. Anzo&aacute;tegui &bull; RIF {RIF}<br/>
        🌐 www.ueipab.edu.ve<br/>
        Consultas de pago: <a href="mailto:pagos@ueipab.edu.ve"
                              style="color:#9ec5ff;">pagos@ueipab.edu.ve</a>
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
    parser = argparse.ArgumentParser(description='Payment-notice community email blast')
    parser.add_argument('--preview', action='store_true', help='Send only to CEO for review')
    parser.add_argument('--live', action='store_true', help='Send to the full community list')
    parser.add_argument('--to', metavar='EMAIL',
                        help='Real send of the production notice to ONE explicit address '
                             '(reuses the resume state file → never double-sends)')
    args = parser.parse_args()

    dry_run = not (args.preview or args.live or args.to)

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

    if args.to:
        target = args.to.strip()
        already = _load_state()
        if target.lower() in already:
            log.info("Already sent to %s (in state file) — nothing to do.", target)
            return
        _create_mail(target, _build_html(is_preview=False))
        _trigger_mail_queue()
        already.add(target.lower())
        _save_state(already)
        log.info("Notice sent to %s (added to resume state).", target)
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
