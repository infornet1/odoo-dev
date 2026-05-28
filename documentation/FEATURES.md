# Active Features Summary

| # | Feature | Status | Module | Documentation |
|---|---------|--------|--------|---------------|
| 1 | Payroll Disbursement Report | Production | `ueipab_payroll_enhancements` | [Docs](PAYROLL_DISBURSEMENT_REPORT.md) |
| 2 | Venezuelan Liquidation V1/V2 | Production | `ueipab_payroll_enhancements` | [V2 Impl](LIQUIDATION_V2_IMPLEMENTATION.md) |
| 3 | Prestaciones Interest Report | Production | `ueipab_payroll_enhancements` | [Docs](PRESTACIONES_INTEREST_REPORT.md) |
| 4 | Venezuelan Payroll V2 | Production | `ueipab_payroll_enhancements` | [V2 Plan](VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md) |
| 5 | Relacion Liquidacion Report | Production | `ueipab_payroll_enhancements` | [Docs](RELACION_BREAKDOWN_REPORT.md) |
| 6 | Payslip Email Delivery | Production | `hr_payslip_monthly_report` | [Docs](SEND_MAIL_BUTTON_FIX_FINAL.md) |
| 7 | Batch Email Template Selector | Production | `ueipab_payroll_enhancements` | - |
| 8 | Comprobante de Pago Compacto | Production | `ueipab_payroll_enhancements` | [Docs](COMPROBANTE_DE_PAGO.md) |
| 9 | Acuerdo Finiquito Laboral | Production | `ueipab_payroll_enhancements` | [Docs](FINIQUITO_REPORT.md) |
| 10 | AR-I Portal | Production | `ueipab_ari_portal` | Portal `/my/ari` |
| 11 | Payslip Acknowledgment | Production | `ueipab_payroll_enhancements` | [Docs](PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 12 | Smart Invoice Script | Testing | Script | - |
| 13 | Recurring Invoicing | Planned | - | [Plan](RECURRING_INVOICING_IMPLEMENTATION_PLAN.md) |
| 14 | Duplicate Payslip Warning | Planned | `ueipab_payroll_enhancements` | - |
| 15 | Batch Email Progress Wizard | Production | `ueipab_payroll_enhancements` | [Docs](BATCH_EMAIL_WIZARD.md) |
| 16 | HRMS Dashboard Ack Widget | Production | `ueipab_hrms_dashboard_ack` | [Docs](PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 17 | Cybrosys Module Refactoring | Planned | Multiple | [Docs](CYBROSYS_MODULE_MODIFICATIONS.md) |
| 18 | Liquidacion Estimation Mode | Production | `ueipab_payroll_enhancements` | - |
| 19 | Payslip Ack Reminder System | Production | `ueipab_payroll_enhancements` | [Docs](PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 20 | V2 Payroll Accounting Config | Production | Database config | - |
| 21 | Invoice Currency Rate Bug | Documented | `tdv_multi_currency_account` | [Docs](INVOICE_CURRENCY_RATE_BUG.md) |
| 22 | Aguinaldos Disbursement Report | Production | `ueipab_payroll_enhancements` | - |
| 23 | Advance Payment System | Production | `ueipab_payroll_enhancements` | [Docs](ADVANCE_PAYMENT_SYSTEM.md) |
| 24 | WebSocket/Nginx Fix | Production | Infrastructure | [Docs](WEBSOCKET_NGINX_FIX.md) |
| 25 | Email Bounce Processor | Production | Script + `ueipab_bounce_log` | [Docs](BOUNCE_EMAIL_PROCESSOR.md) |
| 26 | AI Agent (WhatsApp + Claude) | Production | `ueipab_ai_agent` | [Docs](AI_AGENT_MODULE.md) |
| 27 | Akdemia Data Pipeline | Production | Script + Cron | [Docs](AKDEMIA_DATA_PIPELINE.md) |
| 28 | WhatsApp Health Monitor | Production | Script + `ueipab_ai_agent` | [Docs](AI_AGENT_MODULE.md) |
| 29 | Resolution Bridge | Production | Script + Cron | [Docs](AI_AGENT_MODULE.md) |
| 30 | Freescout API Migration | Production (Phase 2+3) | Scripts | [Plan](FREESCOUT_API_MIGRATION_PLAN.md) |
| 31 | HR Data Collection (Glenda) | Production | `ueipab_ai_agent` + `ueipab_hr_employee` | [Docs](GLENDA_HR_DATA_COLLECTION.md) |
| 32 | Payslip Ack Confirmation Email | Production | `ueipab_payroll_enhancements` | [Docs](PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 33 | Payroll Requisition Estimation Report | Production | `ueipab_payroll_enhancements` | [Docs](PAYROLL_REQUISITION_ESTIMATION_REPORT.md) |
| 34 | Adelanto de Prestaciones Sociales Email | Production | `ueipab_payroll_enhancements` | [Changelog](CHANGELOG.md) |
| 35 | Payslip Ack Reminder via Glenda (WA) | Production | `ueipab_ai_agent` | [Docs](PAYSLIP_ACK_REMINDER_GLENDA.md) |
| 36 | HR Salary Advance / Loan System | Testing | `ueipab_payroll_enhancements` + `ohrms_loan` + `ohrms_loan_accounting` | [Docs](HR_SALARY_ADVANCE_LOAN.md) |
| 37 | Attendance Biweekly Email Report | Production | `ueipab_attendance_report` | [Plan](ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) |
| 38 | Bono Día de las Madres 2026 | Production | `ueipab_payroll_enhancements` | [Docs](BONO_MADRES_2026.md) |
| 39 | Control Asistencia → Odoo Bridge | Production | Script + Cron | [Docs](CONTROL_ASISTENCIA_BRIDGE.md) |
| 40 | Mikrotik Hotspot → Odoo Bridge | Production | Script + Cron | [Docs](CHANGELOG.md) |
| 41 | Gestión Control Asistencia — Guía Visual | Production | `mail.template` + Stories PNG | [Docs](CHANGELOG.md) |
| 42 | Notice Acknowledgment System | Production | `ueipab_attendance_report` | [Docs](NOTICE_ACKNOWLEDGMENT_SYSTEM.md) |
| 43 | Glenda Calibration Programme | Production | `ueipab_attendance_report` + `ueipab_ai_agent` | [Docs](GLENDA_CALIBRATION_PROGRAMME.md) |
| 44 | Glenda BCV Rate Context | Production | `ueipab_ai_agent` + Script + Cron | [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 45 | Glenda Invoice Balance Query | Production | `ueipab_ai_agent` | [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 46 | Glenda Daily Executive Digest | Production | Script + Cron | [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 47 | Employee Private Info Request | Production | `ueipab_hr_employee` | [Docs](EMPLOYEE_INFO_REQUEST.md) |
| 48 | Liquidación V2 Forecast | Production | `ueipab_payroll_enhancements` | Nómina→Reports→Pronóstico Liquidación V2; PDF + Excel |
| 49 | PDVSA Continuity Campaign | Production | `ueipab_attendance_report` | [Docs](PDVSA_CONTINUITY_CAMPAIGN.md) — deadline 08-Jun-2026 |
| 50 | Representante Continuity Campaign | Pending (letter not ready) | `ueipab_attendance_report` | [Docs](REPRESENTANTE_CONTINUITY_CAMPAIGN.md) |
| 51 | Glenda Auto Draft Payment (WA) | Production | `ueipab_ai_agent` | [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 52 | Pagos@ Email Receipt Processor | Production | Script | `scripts/pagos_receipt_processor.py` — [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 53 | WA Invoice Reminder | Production | Script + Wizard | [Plan](WA_INVOICE_REMINDER_PLAN.md) |
| 54 | Glenda OdooBot Bridge | Production | `ueipab_ai_agent` | [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 55 | Glenda Silent Timeout + Quiet Hours | Production | `ueipab_ai_agent` | [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 56 | DMARC Report Processor | Production | Script + Cron | `scripts/dmarc_report_processor.py` — [CEO](CEO_COMMAND_CENTER.md) |
| 57 | Glenda Telegram Channel | Production | `ueipab_ai_agent` | [Docs](GLENDA_TELEGRAM_CHANNEL.md) — `@GlendaUeipabBot`; deep-link `EMP_{id}` |
| 58 | Absence Notification System | Production | Script + Cron + `ueipab_ai_agent` | `scripts/absence_processor.py`; see Key Technical Patterns |
| 59 | Glenda School Account Help | Production | `ueipab_ai_agent` + Script | `ACTION:SCHOOL_ACCOUNT_HELP`; see Key Technical Patterns |
| 60 | Budget Consultation 2026-2027 | **Closed** | `ueipab_ai_agent` + Script | Opción A won 2026-05-26; Glenda v57.19 updated; results blast fired 201 recipients |
| 61 | Glenda Kurios Robotics Link | Production | `ueipab_ai_agent` | Shares `https://info.kuriosedu.com/books/kmbs/#p=3` on request |
| 62 | Glenda MOA Spelling Bee 2026 | Production | `ueipab_ai_agent` | Jun 1 Primaria / Jun 2 Media General |
| 63 | Glenda Telegram Parent Announcement | Production | Script | `scripts/send_glenda_telegram_email.py` |
| 64 | Glenda WA→Telegram Speed Suggestion | Production | `ueipab_ai_agent` | WA slow-response → recommends Telegram; WA-channel only |
| 65 | Glenda Almacenes París — Distintivo Escolar | Production | `ueipab_ai_agent` | ~$8–$10/u |
| 66 | Attendance ACK → CC recursoshumanos@ | Production | `ueipab_attendance_report` | `attendance_ack.py` `_notify_rrhh()` — CC recursoshumanos@ on ACK |
| 67 | Glenda Seguro Escolar 2026-2027 | Production | `ueipab_ai_agent` | Seguros Caracas Alt.2; $30.58/alumno |
| 68 | Manual WA/Telegram Trigger from AI Agent | Production | `ueipab_ai_agent` | AI Agent → Operaciones → Iniciar Conversación; Canal toggle WA/Telegram (v57.5) |
| 69 | Glenda Family Billing Enrichment | Production | `ueipab_ai_agent` + Script | `school.family_billing_json`; `sync_family_billing.py` 07:30 VET; [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 70 | Glenda AI Supervisor | Production | Script + Cron | `scripts/glenda_supervisor.py`; scores 1–5; CEO email + OdooBot DM + WA if critical |
| 71 | Glenda Staff Operational Guide | Production | Script | `scripts/create_glenda_ops_guide_email.py` |
| 72 | Glenda Welcome Menu + Budget UX v52 | Production | `ueipab_ai_agent` | 5-option menu; balance gate; A vs B quotation; [Patterns](GLENDA_TECHNICAL_PATTERNS.md) |
| 73 | Glenda Prior Conversation History | Production | `ueipab_ai_agent` | `_get_prior_conversation_summary()` in `general_inquiry.py`; 1-2 convs (7-day window) |
| 74 | Freescout Pagos@ Bridge | Production | `ueipab_ai_agent` + scripts | `ai.agent.freescout.task` |
| 75 | Attendance Correction — "En Revisión" State | Production | `ueipab_attendance_report` v6.20 | Wizard popup (note + attachment) → FS conversation (employee as customer, mailbox 4) → smart button link; re-invite thread resets to pending; CC arcides.arzola@ on open |
