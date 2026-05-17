#!/usr/bin/env python3
"""
DMARC Report Processor for FreeScout finanzas@ mailbox (mailbox_id=5).

Daily workflow:
  1. Find active DMARC aggregate-report conversations in FreeScout (MySQL read)
  2. Parse XML attachments from disk (Google=ZIP, Yahoo/Microsoft=GZ)
  3. Classify source IPs: good / third-party / suspicious
  4. Post a human-readable HTML note to each conversation (FS API)
  5. Close each conversation (FS API)
  6. Send a consolidated digest email to ALERT_EMAIL via Odoo XML-RPC

Usage:
  python3 dmarc_report_processor.py           # live
  python3 dmarc_report_processor.py --dry-run # no writes

Cron: /etc/cron.d/dmarc_processor
  30 10 * * * root /usr/bin/python3 /opt/odoo-dev/scripts/dmarc_report_processor.py >> /var/log/dmarc_processor.log 2>&1
"""

import os
import sys
import gzip
import io
import ipaddress
import json
import socket
import xmlrpc.client
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import pymysql
import requests

# ── Config ───────────────────────────────────────────────────────────────────

FS_API_URL    = "https://freescout.ueipab.edu.ve/api"
FS_API_KEY    = "30d0665f9f0ba392c736659b1989b1e1"
FS_MAILBOX_ID = 5   # finanzas@ueipab.edu.ve
FS_USER_ID    = 1   # admin

MYSQL = dict(
    host="localhost", db="free297",
    user="free297", password="1gczp1S@3!",
    cursorclass=pymysql.cursors.DictCursor,
)
ATTACHMENT_BASE = "/var/www/freescout/storage/app/attachment"

ODOO = {
    "url": "https://odoo.ueipab.edu.ve",
    "db": "DB_UEIPAB",
    "user": "tdv.devs@gmail.com",
    "api_key": "6e65cfeb1762f224f675b8d26c1dfe0c",
}
ALERT_EMAIL = "gustavo.perdomo@ueipab.edu.ve"
FROM_EMAIL  = "finanzas@ueipab.edu.ve"

# Known-legitimate sending IP ranges (IPv4 + Google IPv6)
_KNOWN_GOOD_RAW = [
    ("209.85.0.0/16",      "Google Workspace"),
    ("74.125.0.0/16",      "Google Workspace"),
    ("66.102.0.0/20",      "Google"),
    ("172.217.0.0/16",     "Google"),
    ("108.177.0.0/17",     "Google"),
    ("142.250.0.0/15",     "Google"),
    ("64.23.157.121/32",   "Servidor UEIPAB (Odoo/FreeScout)"),
    # Google IPv6 blocks
    ("2001:4860::/32",     "Google IPv6"),
    ("2607:f8b0::/32",     "Google IPv6"),
    ("2a00:1450::/32",     "Google IPv6 (EU)"),
    ("2800:3f0::/32",      "Google IPv6 (LATAM)"),
    ("2404:6800::/32",     "Google IPv6 (APAC)"),
]
KNOWN_GOOD_NETS = [(ipaddress.ip_network(n), lbl) for n, lbl in _KNOWN_GOOD_RAW]

# Known third-party senders that mis-align From: header (blocked by DMARC, worth noting)
KNOWN_THIRD_PARTY = {
    "50.31.44.87": "SendGrid / Akdemia (em.akdemia.com) — From: ueipab.edu.ve pero MAIL FROM: akdemia → DMARC misalign",
}

DRY_RUN = "--dry-run" in sys.argv


# ── IP Classification ────────────────────────────────────────────────────────

def classify_ip(ip_str):
    """Return (class, label): class is 'good' | 'third_party' | 'unknown'."""
    if ip_str in KNOWN_THIRD_PARTY:
        return "third_party", KNOWN_THIRD_PARTY[ip_str]
    try:
        ip = ipaddress.ip_address(ip_str)
        for net, label in KNOWN_GOOD_NETS:
            if ip in net:
                return "good", label
    except ValueError:
        pass
    return "unknown", None


def rdns(ip_str):
    """Best-effort reverse DNS."""
    try:
        return socket.gethostbyaddr(ip_str)[0]
    except Exception:
        return ip_str


# ── FreeScout MySQL reads ────────────────────────────────────────────────────

def find_unprocessed_dmarc_convs(conn):
    """Active conversations in finanzas@ whose subject looks like a DMARC report."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, subject, created_at, number
            FROM conversations
            WHERE mailbox_id = %s
              AND status = 1
              AND (
                    subject LIKE 'Report domain: ueipab.edu.ve%%'
                 OR subject LIKE 'Report Domain: ueipab.edu.ve%%'
                 OR subject LIKE '%%[Preview] Report Domain: ueipab.edu.ve%%'
                 OR subject LIKE 'Report domain: ueipab.edu.ve%%'
              )
            ORDER BY created_at DESC
            """,
            (FS_MAILBOX_ID,),
        )
        return cur.fetchall()


def get_dmarc_attachments(conn, conv_id):
    """Return attachment rows (file_dir, file_name, mime_type) for a conversation."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.file_dir, a.file_name, a.mime_type, a.thread_id
            FROM attachments a
            JOIN threads t ON a.thread_id = t.id
            WHERE t.conversation_id = %s
              AND a.mime_type IN (
                    'application/zip',
                    'application/gzip',
                    'application/x-gzip',
                    'application/x-zip-compressed',
                    'application/octet-stream'
              )
            ORDER BY a.id ASC
            """,
            (conv_id,),
        )
        return cur.fetchall()


# ── Attachment reading ───────────────────────────────────────────────────────

def read_dmarc_xml(file_dir, file_name, mime_type):
    """Decompress and return the XML string from a DMARC attachment on disk."""
    path = os.path.join(ATTACHMENT_BASE, (file_dir or "").rstrip("/"), file_name)
    if not os.path.exists(path):
        print(f"    [WARN] File not found: {path}")
        return None

    with open(path, "rb") as f:
        data = f.read()

    # Google sends a ZIP containing an XML file
    if file_name.endswith(".zip") or mime_type in ("application/zip", "application/x-zip-compressed"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml_names = [n for n in z.namelist() if n.lower().endswith(".xml")]
            if not xml_names:
                return None
            return z.read(xml_names[0]).decode("utf-8", errors="replace")

    # Yahoo / Microsoft send GZ
    try:
        return gzip.decompress(data).decode("utf-8", errors="replace")
    except Exception:
        return None


# ── XML parsing ──────────────────────────────────────────────────────────────

def parse_dmarc_xml(xml_str):
    _E = ET.Element  # shorthand for safe fallback element

    def _find(el, tag):
        result = el.find(tag)
        return result if result is not None else _E("x")

    root = ET.fromstring(xml_str)
    meta   = _find(root, "report_metadata")
    policy = _find(root, "policy_published")
    dr     = _find(meta, "date_range")

    begin_ts = int(dr.findtext("begin") or 0)
    end_ts   = int(dr.findtext("end")   or 0)

    records = []
    for rec in root.findall("record"):
        row  = _find(rec, "row")
        pol  = _find(row, "policy_evaluated")
        auth = _find(rec, "auth_results")
        ids  = _find(rec, "identifiers")

        ip          = row.findtext("source_ip", "")
        count       = int(row.findtext("count", "0"))
        disposition = pol.findtext("disposition", "")
        dkim_res    = pol.findtext("dkim", "")
        spf_res     = pol.findtext("spf",  "")

        dkim_el = auth.find("dkim")
        spf_el  = auth.find("spf")
        auth_dkim_domain   = dkim_el.findtext("domain",   "") if dkim_el is not None else ""
        auth_dkim_selector = dkim_el.findtext("selector", "") if dkim_el is not None else ""
        auth_spf_domain    = spf_el.findtext("domain",    "") if spf_el  is not None else ""

        ip_class, ip_label = classify_ip(ip)

        records.append({
            "ip":               ip,
            "count":            count,
            "disposition":      disposition,
            "dkim":             dkim_res,
            "spf":              spf_res,
            "header_from":      ids.findtext("header_from",  ""),
            "envelope_from":    ids.findtext("envelope_from", ""),
            "auth_dkim_domain": auth_dkim_domain,
            "auth_dkim_selector": auth_dkim_selector,
            "auth_spf_domain":  auth_spf_domain,
            "ip_class":         ip_class,
            "ip_label":         ip_label,
        })

    return {
        "org":       meta.findtext("org_name", ""),
        "report_id": meta.findtext("report_id", ""),
        "date_begin": datetime.fromtimestamp(begin_ts, tz=timezone.utc) if begin_ts else None,
        "date_end":   datetime.fromtimestamp(end_ts,   tz=timezone.utc) if end_ts   else None,
        "policy":    policy.findtext("p", ""),
        "records":   records,
    }


# ── HTML note for FreeScout ──────────────────────────────────────────────────

def build_html_note(parsed):
    records   = parsed["records"]
    date_str  = parsed["date_begin"].strftime("%Y-%m-%d") if parsed["date_begin"] else "?"
    good_n    = sum(r["count"] for r in records if r["ip_class"] == "good" and r["disposition"] == "none")
    blocked_n = sum(r["count"] for r in records if r["disposition"] == "reject")
    # Only alert when the unknown IP actually passed DMARC auth (dkim or spf aligned).
    # disposition=none on a failed-auth record just means the receiving MTA overrode p=reject locally.
    passing_unknown = [r for r in records if r["ip_class"] == "unknown" and (r["dkim"] == "pass" or r["spf"] == "pass")]

    alert_html = ""
    if passing_unknown:
        ips = ", ".join(r["ip"] for r in passing_unknown)
        alert_html = f'<p style="background:#f8d7da;padding:6px 10px;border-radius:4px"><strong>⚠️ ALERTA:</strong> IPs desconocidas pasando DMARC: <code>{ips}</code> — Investigar inmediatamente.</p>'

    rows = ""
    for r in records:
        if r["ip_class"] == "good" and r["disposition"] == "none":
            icon, bg = "✅", ""
        elif r["disposition"] == "reject":
            icon, bg = "🚫", "background:#fff8e1"
        elif r["ip_class"] == "unknown" and (r["dkim"] == "pass" or r["spf"] == "pass"):
            icon, bg = "⚠️", "background:#f8d7da"   # unknown IP, auth actually passed — investigate
        elif r["ip_class"] == "unknown":
            icon, bg = "🔍", "background:#fff3cd"   # unknown IP, auth failed but MTA didn't reject
        else:
            icon, bg = "🔍", "background:#fff3cd"

        label = r["ip_label"] or rdns(r["ip"])
        auth_note = ""
        if r["auth_dkim_domain"] and r["auth_dkim_domain"] != "ueipab.edu.ve":
            auth_note = f'<br><small style="color:#666">DKIM: {r["auth_dkim_domain"]}/{r["auth_dkim_selector"]}</small>'

        rows += f"""
        <tr style="{bg}">
          <td style="padding:3px 8px">{icon}</td>
          <td style="padding:3px 8px;font-family:monospace">{r["ip"]}</td>
          <td style="padding:3px 8px">{label}{auth_note}</td>
          <td style="padding:3px 8px;text-align:center;font-weight:bold">{r["count"]}</td>
          <td style="padding:3px 8px;color:{'green' if r['dkim']=='pass' else '#c0392b'}">{r["dkim"]}</td>
          <td style="padding:3px 8px;color:{'green' if r['spf']=='pass' else '#c0392b'}">{r["spf"]}</td>
          <td style="padding:3px 8px">{r["disposition"]}</td>
        </tr>"""

    period = ""
    if parsed["date_begin"] and parsed["date_end"]:
        period = f'{parsed["date_begin"].strftime("%Y-%m-%d %H:%M")} → {parsed["date_end"].strftime("%Y-%m-%d %H:%M")} UTC'

    return f"""
<div style="font-family:sans-serif;font-size:13px;max-width:800px">
  <h3 style="margin:0 0 8px;color:#1a2c5b">📊 DMARC Aggregate Report — {parsed['org']} — {date_str}</h3>
  <p style="margin:0 0 8px">
    Política: <strong>{parsed['policy']}</strong> &nbsp;|&nbsp;
    Legítimos: <strong style="color:green">{good_n}</strong> &nbsp;|&nbsp;
    Bloqueados (spoofing): <strong style="color:#856404">{blocked_n}</strong>
  </p>
  {alert_html}
  <table border="1" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:12px">
    <thead style="background:#1a2c5b;color:white">
      <tr>
        <th style="padding:4px 8px">Estado</th>
        <th style="padding:4px 8px">IP Origen</th>
        <th style="padding:4px 8px">Identificación</th>
        <th style="padding:4px 8px">Correos</th>
        <th style="padding:4px 8px">DKIM</th>
        <th style="padding:4px 8px">SPF</th>
        <th style="padding:4px 8px">Disposición</th>
      </tr>
    </thead>
    <tbody>{rows}
    </tbody>
  </table>
  <p style="font-size:11px;color:#666;margin-top:6px">
    Report-ID: {parsed['report_id']} &nbsp;|&nbsp; Período: {period}
  </p>
  <p style="font-size:11px;color:#999;margin:2px 0">
    Procesado automáticamente · dmarc_report_processor.py
  </p>
</div>"""


# ── FreeScout API writes ─────────────────────────────────────────────────────

def fs_add_note(conv_id, html_body):
    url = f"{FS_API_URL}/conversations/{conv_id}/threads"
    r = requests.post(
        url,
        json={"type": "note", "text": html_body, "user": FS_USER_ID},
        headers={"X-FreeScout-API-Key": FS_API_KEY},
        timeout=15,
    )
    return r.status_code == 201


def fs_close_conversation(conv_id):
    url = f"{FS_API_URL}/conversations/{conv_id}"
    r = requests.put(
        url,
        json={"status": "closed", "byUser": FS_USER_ID},
        headers={"X-FreeScout-API-Key": FS_API_KEY},
        timeout=15,
    )
    return r.status_code in (200, 204)


# ── OdooBot Discuss alert (CEO Command Center) ───────────────────────────────

def notify_ceo_discuss(suspicious_by_report):
    """
    Post an instant alert to the CEO's OdooBot DM channel in Odoo Discuss.
    Replicates ai_agent_conversation._notify_ceo_discuss() via XML-RPC.
    Only called when unknown IPs are passing DMARC (suspicious_passing list non-empty).
    """
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
        uid    = common.authenticate(ODOO["db"], ODOO["user"], ODOO["api_key"], {})
        models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")

        # ── 1. CEO partner_id ────────────────────────────────────────────────
        ceo_users = models.execute_kw(
            ODOO["db"], uid, ODOO["api_key"],
            "res.users", "search_read",
            [[["email", "=", ALERT_EMAIL]]],
            {"fields": ["partner_id"], "limit": 1},
        )
        if not ceo_users:
            print(f"  [WARN] OdooBot DM: CEO user not found for {ALERT_EMAIL}")
            return False
        ceo_partner_id = ceo_users[0]["partner_id"][0]

        # ── 2. OdooBot partner_id (base.partner_root) ────────────────────────
        bot_ref = models.execute_kw(
            ODOO["db"], uid, ODOO["api_key"],
            "ir.model.data", "search_read",
            [[["module", "=", "base"], ["name", "=", "partner_root"]]],
            {"fields": ["res_id"], "limit": 1},
        )
        if not bot_ref:
            print("  [WARN] OdooBot DM: partner_root not found")
            return False
        bot_partner_id = bot_ref[0]["res_id"]

        # ── 3. Find existing CEO ↔ OdooBot DM channel ────────────────────────
        # Odoo 17: model renamed mail.channel → discuss.channel
        CHAN_MODEL   = "discuss.channel"
        MEMBER_MODEL = "discuss.channel.member"

        ceo_ch = set(models.execute_kw(
            ODOO["db"], uid, ODOO["api_key"],
            CHAN_MODEL, "search",
            [[["channel_type", "=", "chat"],
              ["channel_member_ids.partner_id", "=", ceo_partner_id]]],
        ))
        bot_ch = set(models.execute_kw(
            ODOO["db"], uid, ODOO["api_key"],
            CHAN_MODEL, "search",
            [[["channel_type", "=", "chat"],
              ["channel_member_ids.partner_id", "=", bot_partner_id]]],
        ))
        shared = ceo_ch & bot_ch

        if shared:
            channel_id = min(shared)   # oldest / canonical channel
        else:
            # Create fresh DM channel
            channel_id = models.execute_kw(
                ODOO["db"], uid, ODOO["api_key"],
                CHAN_MODEL, "create",
                [{"channel_type": "chat", "name": ""}],
            )
            models.execute_kw(
                ODOO["db"], uid, ODOO["api_key"],
                MEMBER_MODEL, "create",
                [[
                    {"channel_id": channel_id, "partner_id": ceo_partner_id},
                    {"channel_id": channel_id, "partner_id": bot_partner_id},
                ]],
            )
            print(f"  OdooBot DM: created new channel #{channel_id}")

        # ── 4. Build message ─────────────────────────────────────────────────
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"⚠️ DMARC Alert — {today}"]
        lines.append("")
        lines.append("IPs desconocidas pasando DMARC para ueipab.edu.ve:")
        for submitter, ips in suspicious_by_report.items():
            for ip in ips:
                lines.append(f"  • {ip}  ({rdns(ip)})  — reporte de {submitter}")
        lines.append("")
        lines.append("Reporte completo enviado a tu correo. Revisar FreeScout finanzas@ para detalle.")

        html_body = "<br/>".join(lines)

        # ── 5. Post to channel ───────────────────────────────────────────────
        models.execute_kw(
            ODOO["db"], uid, ODOO["api_key"],
            CHAN_MODEL, "message_post",
            [channel_id],
            {
                "body":            html_body,
                "message_type":    "comment",
                "subtype_xmlid":   "mail.mt_comment",
            },
        )
        print(f"  OdooBot DM alert posted to channel #{channel_id}")
        return True

    except Exception as exc:
        print(f"  [ERROR] OdooBot DM notify failed: {exc}")
        return False


# ── Digest email via Odoo ────────────────────────────────────────────────────

def send_digest_email(all_reports, has_alerts):
    today = datetime.now().strftime("%Y-%m-%d")
    status_color = "#c0392b" if has_alerts else "#27ae60"
    status_text  = "⚠️ REQUIERE ATENCIÓN" if has_alerts else "✅ Todo en orden"

    alert_blocks = ""
    for rpt in all_reports:
        for ip in rpt.get("suspicious_passing", []):
            alert_blocks += f"<p style='color:#c0392b'>⚠️ <strong>{rpt['submitter']}</strong>: IP desconocida pasando DMARC → <code>{ip}</code> ({rdns(ip)})</p>"
        for note in rpt.get("third_party_notes", []):
            alert_blocks += f"<p style='color:#856404'>🔍 <strong>{rpt['submitter']}</strong>: {note}</p>"

    rows_html = ""
    for rpt in all_reports:
        flag = "⚠️" if rpt.get("suspicious_passing") else ("🔍" if rpt.get("third_party_notes") else "✅")
        rows_html += f"""
        <tr>
          <td style="padding:5px 10px">{rpt['submitter']}</td>
          <td style="padding:5px 10px">{rpt['date']}</td>
          <td style="padding:5px 10px;text-align:center;color:green"><strong>{rpt['good']}</strong></td>
          <td style="padding:5px 10px;text-align:center;color:#856404"><strong>{rpt['blocked']}</strong></td>
          <td style="padding:5px 10px;text-align:center">{flag}</td>
        </tr>"""

    body = f"""
<div style="font-family:sans-serif;font-size:14px;max-width:720px">
  <h2 style="color:#1a2c5b;margin:0 0 12px">📊 DMARC Daily Digest — {today}</h2>

  <p style="margin:0 0 8px">
    Estado: <strong style="color:{status_color}">{status_text}</strong>
  </p>
  <p style="margin:0 0 12px;font-size:13px;color:#555">
    DNS activo: <code>DMARC p=reject; pct=100</code> &nbsp;|&nbsp; <code>SPF ~all</code>
    <em>(pendiente: actualizar a <code>-all</code> ~27 May si no hay quejas de entrega)</em>
  </p>

  {alert_blocks}

  <table border="1" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:13px">
    <thead style="background:#1a2c5b;color:white">
      <tr>
        <th style="padding:6px 10px">Proveedor</th>
        <th style="padding:6px 10px">Fecha reporte</th>
        <th style="padding:6px 10px">Correos legítimos</th>
        <th style="padding:6px 10px">Bloqueados</th>
        <th style="padding:6px 10px">Alerta</th>
      </tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>

  <p style="font-size:12px;color:#666;margin-top:14px">
    Cada reporte fue procesado, anotado y cerrado en FreeScout finanzas@ automáticamente.<br>
    Para ver el detalle completo, revisa las conversaciones cerradas en FreeScout.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:14px 0">
  <p style="font-size:11px;color:#aaa">
    Generado por <em>dmarc_report_processor.py</em> · UEIPAB &nbsp;|&nbsp;
    Suspender alertas: editar ALERT_EMAIL en el script.
  </p>
</div>"""

    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
        uid    = common.authenticate(ODOO["db"], ODOO["user"], ODOO["api_key"], {})
        models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")

        mail_id = models.execute_kw(
            ODOO["db"], uid, ODOO["api_key"],
            "mail.mail", "create", [{
                "subject":    f"[DMARC] {today} — {'⚠️ Alerta' if has_alerts else '✅ OK'} — ueipab.edu.ve",
                "body_html":  body,
                "email_from": FROM_EMAIL,
                "email_to":   ALERT_EMAIL,
                "state":      "outgoing",
            }],
        )
        return mail_id
    except Exception as e:
        print(f"  [ERROR] Could not queue digest email: {e}")
        return None


# ── Main ─────────────────────────────────────────────────────────────────────

def extract_submitter(subject):
    """Pull the provider name from the DMARC report subject line."""
    for prefix in [
        "Report domain: ueipab.edu.ve Submitter: ",
        "Report Domain: ueipab.edu.ve Submitter: ",
    ]:
        idx = subject.find(prefix)
        if idx != -1:
            rest = subject[idx + len(prefix):]
            return rest.split()[0] if rest else subject
    # Fallback: strip [Preview] and grab after "Submitter:"
    if "Submitter:" in subject:
        return subject.split("Submitter:")[-1].strip().split()[0]
    return subject[:40]


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] dmarc_report_processor starting {'(DRY RUN)' if DRY_RUN else '(LIVE)'}")

    conn = pymysql.connect(**MYSQL)
    try:
        convs = find_unprocessed_dmarc_convs(conn)
    finally:
        conn.close()

    if not convs:
        print("No unprocessed DMARC conversations found. Exiting.")
        return

    print(f"Found {len(convs)} unprocessed DMARC conversation(s)")

    all_reports = []
    has_alerts  = False

    for conv in convs:
        conv_id    = conv["id"]
        subject    = conv["subject"]
        submitter  = extract_submitter(subject)
        conv_date  = str(conv["created_at"])[:10]

        print(f"\n  Conv {conv_id} | {submitter} | {conv_date}")
        print(f"  Subject: {subject[:80]}")

        conn = pymysql.connect(**MYSQL)
        try:
            attachments = get_dmarc_attachments(conn, conv_id)
        finally:
            conn.close()

        if not attachments:
            print("  [SKIP] No DMARC attachments found")
            continue

        report_summary = {
            "conv_id":           conv_id,
            "submitter":         submitter,
            "date":              conv_date,
            "good":              0,
            "blocked":           0,
            "suspicious_passing": [],
            "third_party_notes": [],
        }

        parsed_reports = []
        for att in attachments:
            file_dir  = att["file_dir"] or ""
            file_name = att["file_name"]
            mime_type = att["mime_type"]

            # Skip attachments not matching DMARC filename convention
            if "ueipab.edu.ve" not in file_name and not file_name.endswith(".xml.gz"):
                continue

            print(f"  Attachment: {file_name} ({mime_type})")
            xml_str = read_dmarc_xml(file_dir, file_name, mime_type)
            if not xml_str:
                continue

            try:
                parsed = parse_dmarc_xml(xml_str)
            except Exception as e:
                print(f"  [ERROR] XML parse failed: {e}")
                continue

            parsed_reports.append(parsed)

            for r in parsed["records"]:
                if r["ip_class"] == "good" and r["disposition"] == "none":
                    report_summary["good"] += r["count"]
                if r["disposition"] == "reject":
                    report_summary["blocked"] += r["count"]
                if r["ip_class"] == "unknown" and (r["dkim"] == "pass" or r["spf"] == "pass"):
                    report_summary["suspicious_passing"].append(r["ip"])
                    has_alerts = True
                if r["ip_class"] == "third_party":
                    report_summary["third_party_notes"].append(r["ip_label"])
                    # Third-party blocked is noteworthy but not critical
                    print(f"  [NOTE] Third-party sender: {r['ip']} — {r['ip_label']}")

        if not parsed_reports:
            print("  [SKIP] Could not parse any XML from this conversation")
            continue

        # Build one combined note per conversation (may have multiple attachments)
        for parsed in parsed_reports:
            html_note = build_html_note(parsed)
            if DRY_RUN:
                print(f"  [DRY RUN] Would post note to conv {conv_id}")
            else:
                ok = fs_add_note(conv_id, html_note)
                print(f"  Note posted: {'✓' if ok else '✗'}")

        if DRY_RUN:
            print(f"  [DRY RUN] Would close conv {conv_id}")
        else:
            ok = fs_close_conversation(conv_id)
            print(f"  Conversation closed: {'✓' if ok else '✗'}")

        all_reports.append(report_summary)

        # Summary line per conversation
        print(
            f"  ✅ legit={report_summary['good']}  "
            f"🚫 blocked={report_summary['blocked']}  "
            f"⚠️ suspicious={report_summary['suspicious_passing']}"
        )

    # ── Notifications ────────────────────────────────────────────────────────
    if not all_reports:
        print("\nNo reports processed — no notifications sent.")
        return

    # Collect suspicious IPs grouped by submitter (for Discuss message)
    suspicious_by_submitter = {}
    for rpt in all_reports:
        if rpt.get("suspicious_passing"):
            suspicious_by_submitter[rpt["submitter"]] = rpt["suspicious_passing"]

    if DRY_RUN:
        print(f"\n[DRY RUN] Would send digest email — has_alerts={has_alerts}")
        if suspicious_by_submitter:
            print(f"[DRY RUN] Would post OdooBot DM alert — {suspicious_by_submitter}")
    else:
        # Always: daily digest email
        mail_id = send_digest_email(all_reports, has_alerts)
        if mail_id:
            print(f"\nDigest email queued → {ALERT_EMAIL} (mail.mail id={mail_id})")
        else:
            print("\n[WARN] Digest email failed to queue")

        # Critical only: OdooBot Discuss DM (CEO Command Center)
        if suspicious_by_submitter:
            print("\nPosting OdooBot DM alert (unknown IPs passing DMARC)...")
            notify_ceo_discuss(suspicious_by_submitter)

    print(f"\nDone. {len(all_reports)} report(s) processed.")


if __name__ == "__main__":
    main()
