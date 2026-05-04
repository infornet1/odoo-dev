# -*- coding: utf-8 -*-
"""
deploy_loan_templates_prod.py — Deploy HR Loan email templates to production.

Creates / patches three templates in DB_UEIPAB:
  1. "Adelanto de Salario – Notificación" (NEW — copied from testing id=75)
  2. template id=37  "Payslip Email - Employee Delivery"  — add loan deduction row
  3. template id=50  "Adelanto de Prestaciones Sociales"  — add loan deduction block

Run from dev server:
    python3 /opt/odoo-dev/scripts/deploy_loan_templates_prod.py
"""

import json
import psycopg2

TEST_DSN  = dict(host='localhost', dbname='testing',   user='odoo', password='odoo8069', port=5433)
PROD_DSN  = dict(host='10.124.0.3', dbname='DB_UEIPAB', user='odoo', password='odoo8069', port=5432)

# ---------------------------------------------------------------------------
# Loan deduction block for Payslip Email (template id=37)
# Appended inside ❌ Deducciones tbody before closing </tbody>
# ---------------------------------------------------------------------------

PAYSLIP_LOAN_BLOCK = (
    '\n                          <t t-set="loan_ded" t-value="0"/>'
    '\n                          <t t-foreach="o.line_ids" t-as="line">'
    '\n                            <t t-if="line.code == \'VE_LOAN_DED_V2\'">'
    '\n                              <t t-set="loan_ded" t-value="line.total"/>'
    '\n                            </t>'
    '\n                          </t>'
    '\n                          <t t-if="loan_ded != 0">'
    '\n                          <tr>'
    '\n                            <td style="padding:4px 8px;font-size:12px;color:#333;">Recuperación Anticipo Salarial</td>'
    '\n                            <td style="padding:4px 8px;font-size:12px;color:#c0392b;text-align:right;">'
    '\n                              Bs. <t t-esc="\'{{:,.2f}}\'.format(abs(loan_ded) * (o.exchange_rate_used or 1))"/>'
    '\n                            </td>'
    '\n                          </tr>'
    '\n                          </t>'
)

# ---------------------------------------------------------------------------
# Loan deduction block for Adelanto de Prestaciones (template id=50)
# ---------------------------------------------------------------------------

PRESTACIONES_LOAN_BLOCK = (
    '\n                          <t t-set="liquid_loan" t-value="0"/>'
    '\n                          <t t-foreach="o.line_ids" t-as="line">'
    '\n                            <t t-if="line.code == \'LIQUID_LOAN_DED_V2\'">'
    '\n                              <t t-set="liquid_loan" t-value="line.total"/>'
    '\n                            </t>'
    '\n                          </t>'
    '\n                          <t t-if="liquid_loan != 0">'
    '\n                          <tr style="border-bottom:1px solid #d0dce8;">'
    '\n                            <td style="padding:7px 0;font-size:13px;color:#555;">Recuperación Anticipo</td>'
    '\n                            <td style="padding:7px 0;font-size:13px;color:#c0392b;text-align:right;font-weight:600;">'
    '\n                              Bs. <t t-esc="\'{{:,.2f}}\'.format(abs(liquid_loan) * (o.exchange_rate_used or 1))"/>'
    '\n                            </td>'
    '\n                          </tr>'
    '\n                          </t>'
)


def insert_before_tbody_close(html, block):
    """Insert block before the last </tbody> in html."""
    idx = html.rfind('</tbody>')
    if idx == -1:
        return html + block
    return html[:idx] + block + '\n' + html[idx:]


def run():
    test_conn = psycopg2.connect(**TEST_DSN)
    prod_conn = psycopg2.connect(**PROD_DSN)
    tc = test_conn.cursor()
    pc = prod_conn.cursor()

    # ------------------------------------------------------------------
    # 1. Create "Adelanto de Salario – Notificación" (copy from testing id=75)
    # ------------------------------------------------------------------
    pc.execute("SELECT id FROM mail_template WHERE name->>'en_US' = 'Adelanto de Salario – Notificación'")
    row = pc.fetchone()
    if row:
        print(f"Template 'Adelanto de Salario – Notificación' already exists (id={row[0]}) — skipped")
    else:
        tc.execute("""
            SELECT subject::text, email_from, email_to, email_cc, body_html::text
            FROM mail_template WHERE id = 75
        """)
        src = tc.fetchone()
        if not src:
            print("WARNING: Template id=75 not found in testing — skipping")
        else:
            subject, email_from, email_to, email_cc, body_html = src
            pc.execute("""
                INSERT INTO mail_template
                    (name, subject, email_from, email_to, email_cc,
                     body_html, model_id, active,
                     create_uid, write_uid, create_date, write_date)
                SELECT
                    %s::jsonb, %s::jsonb, %s, %s, %s,
                    %s::jsonb,
                    id, true, 1, 1, NOW(), NOW()
                FROM ir_model WHERE model = 'hr.loan'
                RETURNING id
            """, (
                json.dumps({'en_US': 'Adelanto de Salario – Notificación'}),
                subject,
                email_from, email_to, email_cc,
                body_html,
            ))
            new_id = pc.fetchone()[0]
            print(f"Created 'Adelanto de Salario – Notificación' id={new_id} ✓")

    # ------------------------------------------------------------------
    # 2. Patch template id=37 (Payslip Email - Employee Delivery)
    # ------------------------------------------------------------------
    pc.execute("SELECT body_html::text FROM mail_template WHERE id = 37")
    row = pc.fetchone()
    if not row:
        print("WARNING: Template id=37 not found — skipping")
    else:
        body = json.loads(row[0])
        if 'VE_LOAN_DED_V2' in body.get('en_US', ''):
            print("Template id=37: loan block already present — skipped")
        else:
            for lang in ('en_US', 'es_VE'):
                if lang in body:
                    body[lang] = insert_before_tbody_close(body[lang], PAYSLIP_LOAN_BLOCK)
            pc.execute(
                "UPDATE mail_template SET body_html=%s::jsonb, write_date=NOW() WHERE id=37",
                (json.dumps(body),)
            )
            print("Template id=37: loan block inserted ✓")

    # ------------------------------------------------------------------
    # 3. Patch template id=50 (Adelanto de Prestaciones Sociales)
    # ------------------------------------------------------------------
    pc.execute("SELECT body_html::text FROM mail_template WHERE id = 50")
    row = pc.fetchone()
    if not row:
        print("WARNING: Template id=50 not found — skipping")
    else:
        body = json.loads(row[0])
        if 'LIQUID_LOAN_DED_V2' in body.get('en_US', ''):
            print("Template id=50: loan block already present — skipped")
        else:
            for lang in ('en_US', 'es_VE'):
                if lang in body:
                    body[lang] = insert_before_tbody_close(body[lang], PRESTACIONES_LOAN_BLOCK)
            pc.execute(
                "UPDATE mail_template SET body_html=%s::jsonb, write_date=NOW() WHERE id=50",
                (json.dumps(body),)
            )
            print("Template id=50: loan block inserted ✓")

    prod_conn.commit()
    tc.close(); test_conn.close()
    pc.close(); prod_conn.close()
    print("\ndeploy_loan_templates_prod.py completed.")
    print("Next: docker restart ueipab17  (flush Odoo template cache)")


if __name__ == '__main__':
    run()
