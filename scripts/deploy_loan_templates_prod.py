# -*- coding: utf-8 -*-
"""
deploy_loan_templates_prod.py — Deploy HR Loan email templates to production.

Creates / patches three templates in DB_UEIPAB:
  1. "Adelanto de Salario – Notificación" (NEW — id=75 in testing, new id in prod)
  2. template id=37  "Payslip Email - Employee Delivery"  — add loan deduction row
  3. template id=50  "Adelanto de Prestaciones Sociales"  — add loan deduction block

Run from dev server:
    python3 /opt/odoo-dev/scripts/deploy_loan_templates_prod.py

Requires: psycopg2, access to production PostgreSQL (host 10.124.0.3 via SSH tunnel
or direct connection from dev server using ueipab17_postgres_1 credentials).
"""

import json
import re
import psycopg2

PROD_DSN = dict(host='10.124.0.3', dbname='DB_UEIPAB', user='odoo', password='odoo8069', port=5432)

# ---------------------------------------------------------------------------
# Template 1: Adelanto de Salario – Notificación  (NEW in production)
# ---------------------------------------------------------------------------

ADELANTO_SALARIO_BODY = {"en_US": "<div style=\"font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#f4f4f4;margin:0;padding:20px\">\n  <div style=\"max-width:680px;margin:0 auto;background-color:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.1);overflow:hidden\">\n\n    <!-- HEADER -->\n    <div style=\"background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);color:white;padding:30px;text-align:center\">\n      <h1 style=\"margin:0;font-size:26px;font-weight:600\">\u{1F4B0} Adelanto de Salario</h1>\n      <p style=\"margin:6px 0 0;font-size:15px;opacity:0.9\">Instituto Privado Andrés Bello, CA</p>\n    </div>\n\n    <div style=\"padding:30px\">\n\n      <p style=\"font-size:16px;color:#333;margin-bottom:20px\">\n        Estimado/a <strong t-out=\"object.employee_id.name\"></strong>,\n      </p>\n      <p style=\"font-size:14px;color:#555;line-height:1.6;margin-bottom:24px\">\n        Le informamos que se ha procesado un <strong>adelanto de salario</strong> a su favor.\n        A continuación encontrará el detalle del mismo.\n      </p>\n\n      <!-- INFO ROWS -->\n      <div style=\"background:#f0f4fa;border-radius:8px;padding:20px;margin-bottom:24px\">\n\n        <div style=\"display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #d0dce8\">\n          <span style=\"font-weight:600;color:#1a2c5b;font-size:13px\">\u{1F4CB} Nro. Adelanto:</span>\n          <span style=\"color:#333;font-size:13px\"><t t-out=\"object.name\"></t></span>\n        </div>\n        <div style=\"display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #d0dce8\">\n          <span style=\"font-weight:600;color:#1a2c5b;font-size:13px\">\u{1F464} Empleado:</span>\n          <span style=\"color:#333;font-size:13px\"><t t-out=\"object.employee_id.name\"></t></span>\n        </div>\n        <div style=\"display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #d0dce8\">\n          <span style=\"font-weight:600;color:#1a2c5b;font-size:13px\">\u{1F194} Cédula:</span>\n          <span style=\"color:#333;font-size:13px\">\n            <t t-out=\"object.employee_id.identification_id or 'N/A'\"></t>\n          </span>\n        </div>\n        <div style=\"display:flex;justify-content:space-between;padding:7px 0\">\n          <span style=\"font-weight:600;color:#1a2c5b;font-size:13px\">\u{1F4C5} Fecha:</span>\n          <span style=\"color:#333;font-size:13px\">\n            <t t-out=\"object.date\" t-options='{\"widget\":\"date\",\"format\":\"dd/MM/yyyy\"}'></t>\n          </span>\n        </div>\n\n      </div>\n\n      <!-- AMOUNT BOX -->\n      <div style=\"background:linear-gradient(135deg,#1a2c5b,#2471a3);border-radius:8px;padding:22px;margin-bottom:24px;text-align:center;color:white\">\n        <p style=\"margin:0 0 6px;font-size:13px;opacity:0.85;text-transform:uppercase;letter-spacing:.5px\">Monto Adelantado</p>\n        <p style=\"margin:0 0 4px;font-size:32px;font-weight:700\">\n          Bs. <t t-out=\"'{:,.2f}'.format(object.advance_bs_amount or (object.loan_amount * (object.advance_exchange_rate or 1.0)))\"></t>\n        </p>\n      </div>\n\n      <!-- EXCHANGE RATE REFERENCE -->\n      <div style=\"background:#fff9e6;border:2px dashed #ffc107;border-radius:8px;padding:12px;margin-bottom:24px;text-align:center\">\n        <div style=\"font-size:12px;color:#856404;margin-bottom:4px\">Tasa de Cambio Aplicada (Referencia)</div>\n        <div style=\"font-size:18px;font-weight:bold;color:#d39e00\">\n          Bs. <t t-esc=\"'{:,.4f}'.format(object.advance_exchange_rate or 1.0)\"/>\n        </div>\n      </div>\n\n      <!-- REPAYMENT SCHEDULE -->\n      <div style=\"background:#1a2c5b;color:white;padding:10px 16px;border-radius:6px 6px 0 0;font-size:14px;font-weight:600\">\n        \u{1F4C5} Plan de Recuperación\n      </div>\n      <table style=\"width:100%;border-collapse:collapse;margin-bottom:24px;font-size:13px\">\n        <thead>\n          <tr style=\"background:#2471a3;color:white\">\n            <th style=\"padding:8px 12px;text-align:left\">#</th>\n            <th style=\"padding:8px 12px;text-align:left\">Fecha de Descuento</th>\n            <th style=\"padding:8px 12px;text-align:right\">Monto</th>\n          </tr>\n        </thead>\n        <tbody>\n          <t t-foreach=\"object.loan_lines\" t-as=\"line\">\n            <tr style=\"border-bottom:1px solid #e0e0e0\">\n              <td style=\"padding:8px 12px;color:#555\">\n                <t t-out=\"line_index + 1\"></t>\n              </td>\n              <td style=\"padding:8px 12px;color:#333\">\n                <t t-out=\"line.date\" t-options='{\"widget\":\"date\",\"format\":\"dd/MM/yyyy\"}'></t>\n              </td>\n              <td style=\"padding:8px 12px;text-align:right;font-weight:600;color:#1a2c5b\">\n                Bs. <t t-out=\"'{:,.2f}'.format(line.amount * (object.advance_exchange_rate or 1.0))\"></t>\n              </td>\n            </tr>\n          </t>\n        </tbody>\n      </table>\n\n      <!-- LEGAL DECLARATION -->\n      <div style=\"background:#f8f9fa;border:1px solid #dee2e6;border-radius:6px;padding:16px;margin-bottom:24px;font-size:12px;color:#555;line-height:1.7\">\n        <strong style=\"color:#1a2c5b\">DECLARACIÓN DEL TRABAJADOR</strong><br>\n        El suscrito trabajador declara haber recibido de la\n        <strong>UNIDAD EDUCATIVA INSTITUTO PRIVADO ANDRES BELLO, CA</strong>\n        la cantidad de\n        <strong>Bs. <t t-out=\"'{:,.2f}'.format(object.advance_bs_amount or (object.loan_amount * (object.advance_exchange_rate or 1.0)))\"></t></strong>\n        por concepto de <strong>ADELANTO DE SALARIO</strong>, el cual será descontado\n        de su nómina según el plan de recuperación indicado. Al confirmar la recepción\n        digital, el trabajador acusa recibo del monto recibido y acepta las condiciones\n        de recuperación establecidas.\n      </div>\n\n      <!-- INFO NOTE -->\n      <div style=\"background:#e8f4f8;border-left:4px solid #2471a3;padding:14px 18px;margin-bottom:24px;border-radius:4px\">\n        <p style=\"font-size:13px;color:#1a2c5b;margin:0 0 6px\"><strong>ℹ️ ¿Dudas o consultas?</strong></p>\n        <p style=\"font-size:13px;color:#555;margin:0\">\n          Si tiene alguna duda por favor escribir a\n          <a href=\"mailto:recursoshumanos@ueipab.edu.ve\" style=\"color:#2471a3;text-decoration:none\">recursoshumanos@ueipab.edu.ve</a>\n        </p>\n      </div>\n\n    </div><!-- /padding -->\n\n    <!-- ACK BUTTON -->\n    <div style=\"background:linear-gradient(135deg,#28a745,#20c997);padding:28px 30px;text-align:center\">\n      <p style=\"margin:0 0 12px;color:white;font-size:15px;font-weight:600\">\n        ✅ Confirme la recepción digital de este adelanto\n      </p>\n      <p style=\"margin:0 0 18px;color:rgba(255,255,255,0.88);font-size:13px\">\n        Al hacer clic, acusa conformidad digital de que ha recibido el adelanto indicado.\n      </p>\n      <a t-att-href=\"object.loan_ack_url\" style=\"display:inline-block;background:white;color:#28a745;padding:14px 40px;                 font-size:15px;font-weight:bold;text-decoration:none;border-radius:8px;                 box-shadow:0 4px 15px rgba(0,0,0,0.2)\">\n        Confirmar Recepción del Adelanto\n      </a>\n      <p style=\"margin:14px 0 0;color:rgba(255,255,255,0.75);font-size:12px\">\n        Su confirmación quedará registrada con fecha, hora e IP.\n      </p>\n    </div>\n\n    <!-- FOOTER -->\n    <div style=\"background:#f8f9fa;padding:18px 30px;text-align:center;font-size:12px;color:#888;border-top:1px solid #e0e0e0\">\n      <p style=\"margin:0\">Instituto Privado Andrés Bello • <strong style=\"color:#1a2c5b\">recursoshumanos@ueipab.edu.ve</strong></p>\n      <p style=\"margin:6px 0 0;color:#aaa\">Este es un documento generado automáticamente.</p>\n    </div>\n\n  </div>\n</div>\n        "}

ADELANTO_SALARIO_SUBJECT = {"en_US": "\U0001f4b0 ADELANTO DE SALARIO │ Nro.: {{object.name}} │ {{object.employee_id.name}}"}

# ---------------------------------------------------------------------------
# Loan deduction block for Payslip Email (template id=37)
# Inserted inside the ❌ Deducciones table before the closing </tbody>
# ---------------------------------------------------------------------------

PAYSLIP_EMAIL_LOAN_BLOCK = """
                          <t t-set="loan_ded" t-value="0"/>
                          <t t-foreach="o.line_ids" t-as="line">
                            <t t-if="line.code == 'VE_LOAN_DED_V2'">
                              <t t-set="loan_ded" t-value="line.total"/>
                            </t>
                          </t>
                          <t t-if="loan_ded != 0">
                          <tr>
                            <td style="padding:4px 8px;font-size:12px;color:#333;">Recuperación Anticipo Salarial</td>
                            <td style="padding:4px 8px;font-size:12px;color:#c0392b;text-align:right;">
                              Bs. <t t-esc="'{:,.2f}'.format(abs(loan_ded) * (o.exchange_rate_used or 1))"/>
                            </td>
                          </tr>
                          </t>"""

# ---------------------------------------------------------------------------
# Loan deduction block for Adelanto Prestaciones (template id=50)
# ---------------------------------------------------------------------------

PRESTACIONES_LOAN_BLOCK = """
                          <t t-set="liquid_loan" t-value="0"/>
                          <t t-foreach="o.line_ids" t-as="line">
                            <t t-if="line.code == 'LIQUID_LOAN_DED_V2'">
                              <t t-set="liquid_loan" t-value="line.total"/>
                            </t>
                          </t>
                          <t t-if="liquid_loan != 0">
                          <tr style="border-bottom:1px solid #d0dce8;">
                            <td style="padding:7px 0;font-size:13px;color:#555;">Recuperación Anticipo</td>
                            <td style="padding:7px 0;font-size:13px;color:#c0392b;text-align:right;font-weight:600;">
                              Bs. <t t-esc="'{:,.2f}'.format(abs(liquid_loan) * (o.exchange_rate_used or 1))"/>
                            </td>
                          </tr>
                          </t>"""


def run():
    conn = psycopg2.connect(**PROD_DSN)
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # 1. Create "Adelanto de Salario – Notificación" template (NEW)
    # ------------------------------------------------------------------
    cur.execute("SELECT id FROM mail_template WHERE name->>'en_US' = 'Adelanto de Salario – Notificación'")
    row = cur.fetchone()
    if row:
        print(f"Template 'Adelanto de Salario – Notificación' already exists (id={row[0]}) — skipped")
    else:
        cur.execute("""
            INSERT INTO mail_template
                (name, subject, email_from, email_to, email_cc,
                 body_html, model_id, active, create_uid, write_uid, create_date, write_date)
            SELECT
                %s::jsonb, %s::jsonb,
                '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
                '{{object.employee_id.work_email}}',
                'recursoshumanos@ueipab.edu.ve',
                %s::jsonb,
                id, true, 1, 1, NOW(), NOW()
            FROM ir_model WHERE model = 'hr.loan'
            RETURNING id
        """, (
            json.dumps({"en_US": "Adelanto de Salario – Notificación"}),
            json.dumps(ADELANTO_SALARIO_SUBJECT),
            json.dumps(ADELANTO_SALARIO_BODY),
        ))
        new_id = cur.fetchone()[0]
        print(f"Created 'Adelanto de Salario – Notificación' template id={new_id}")

    # ------------------------------------------------------------------
    # 2. Patch template id=37 (Payslip Email - Employee Delivery)
    # ------------------------------------------------------------------
    cur.execute("SELECT body_html::text FROM mail_template WHERE id = 37")
    row = cur.fetchone()
    if not row:
        print("WARNING: Template id=37 not found — skipping Payslip Email patch")
    else:
        body = json.loads(row[0])
        en_body = body.get('en_US', '')
        if 'VE_LOAN_DED_V2' in en_body:
            print("Template id=37: loan block already present — skipped")
        else:
            # Insert before closing </tbody> of deducciones table
            patched = en_body.replace('</tbody>\n                        </table>',
                                       PAYSLIP_EMAIL_LOAN_BLOCK + '\n</tbody>\n                        </table>', 1)
            body['en_US'] = patched
            if 'es_VE' in body:
                body['es_VE'] = body['es_VE'].replace(
                    '</tbody>\n                        </table>',
                    PAYSLIP_EMAIL_LOAN_BLOCK + '\n</tbody>\n                        </table>', 1)
            cur.execute(
                "UPDATE mail_template SET body_html = %s::jsonb, write_date = NOW() WHERE id = 37",
                (json.dumps(body),)
            )
            print("Template id=37: loan block inserted ✓")

    # ------------------------------------------------------------------
    # 3. Patch template id=50 (Adelanto de Prestaciones Sociales)
    # ------------------------------------------------------------------
    cur.execute("SELECT body_html::text FROM mail_template WHERE id = 50")
    row = cur.fetchone()
    if not row:
        print("WARNING: Template id=50 not found — skipping Adelanto Prestaciones patch")
    else:
        body = json.loads(row[0])
        en_body = body.get('en_US', '')
        if 'LIQUID_LOAN_DED_V2' in en_body:
            print("Template id=50: loan block already present — skipped")
        else:
            # Insert before closing </tbody> of the deductions table
            patched = en_body.replace('</tbody>\n                        </table>',
                                       PRESTACIONES_LOAN_BLOCK + '\n</tbody>\n                        </table>', 1)
            body['en_US'] = patched
            if 'es_VE' in body:
                body['es_VE'] = body['es_VE'].replace(
                    '</tbody>\n                        </table>',
                    PRESTACIONES_LOAN_BLOCK + '\n</tbody>\n                        </table>', 1)
            cur.execute(
                "UPDATE mail_template SET body_html = %s::jsonb, write_date = NOW() WHERE id = 50",
                (json.dumps(body),)
            )
            print("Template id=50: loan block inserted ✓")

    conn.commit()
    cur.close()
    conn.close()
    print("\ndeploy_loan_templates_prod.py completed.")
    print("Next step: docker restart ueipab17  (flush Odoo template cache)")


if __name__ == '__main__':
    run()
