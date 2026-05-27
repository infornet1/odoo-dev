# Budget Results Email Blast — Consulta Presupuestaria 2026-2027

**Created:** 2026-05-27
**Status:** Fired

---

## Purpose

Official announcement to all parents and institutional staff communicating:
- Voting process concluded successfully (64% participation, quorum met)
- Opción Nro. 1 (Mensualidad $218,88) selected by the majority
- Link to the official results document
- Early-bird enrollment reminder ($187.51 until July 31)

---

## Email Specs

| Field | Value |
|---|---|
| FROM | `Instituto Andrés Bello <soporte@ueipab.edu.ve>` |
| REPLY-TO | `pagos@ueipab.edu.ve` |
| SUBJECT | `✅ Resultados Consulta Presupuestaria 2026-2027 — Instituto Andrés Bello` |
| Results doc | [Google Doc](https://docs.google.com/document/d/1GSGzXLxGaaMvYtbyJuGki5KFodmpoy5OyHk0fm4e2fg/edit?usp=sharing) |
| Sent via | Production Odoo `mail.mail` → queue cron id=3 |

---

## Recipients

| Source | Count |
|---|---|
| Google Sheets — Customers tab, col J (emails) | ~195 |
| Extra institutional addresses (hardcoded) | 6 |
| **Total** | **~201** |

### Extra Institutional Recipients

| Name | Email |
|---|---|
| Docentes Primaria | docentesprimaria@ueipab.edu.ve |
| Docentes Secundaria | docentesecundaria@ueipab.edu.ve |
| Académico | academico@ueipab.edu.ve |
| Administración | administracion@ueipab.edu.ve |
| Jesús Rengel | jesus.rengel@ueipab.edu.ve |
| Yelitza Chirinos | yelitza.chirinos@ueipab.edu.ve |

---

## Email Content Summary

- **Header:** Navy/blue gradient, circular logo, "RESULTADOS — CONSULTA PRESUPUESTARIA 2026-2027"
- **Green banner:** ✅ ¡Votación completada con éxito!
- **Result card:** 📊 Opción Núm. 1 — $218,88 mensualidad / $207,93 pronto pago
- **Stats bar:** 64% participación · ✅ Quórum alcanzado
- **CTA button:** Ver Comunicado Oficial → Google Doc link
- **Gold reminder box:** Early-bird inscripción $187,51 hasta 31 julio → pagos@ueipab.edu.ve
- **Closing (centered):** Atentamente, La Administración, Instituto Privado Andrés Bello

---

## Script

**File:** `scripts/send_budget_results_email.py`

```bash
# Dry-run (no sends)
python3 scripts/send_budget_results_email.py

# Preview to CEO (gustavo.perdomo@ueipab.edu.ve)
python3 scripts/send_budget_results_email.py --preview

# Full blast — production
python3 scripts/send_budget_results_email.py --live
```

The script runs on the dev server but connects to production Odoo via XML-RPC
(`config/production.json`), creates `mail.mail` records in `DB_UEIPAB`, and triggers
the production mail queue cron (id=3). No deployment to the production server needed.

### Status Filter (col C)

Recipients are filtered by status column (col C) — only `ACTIVE` and `PIPELINE` rows
are included. Any other status is skipped. **This filter was added post-blast on
2026-05-27 after the initial run inadvertently included all rows.**

Always confirm the status filter with the user before firing any future blast.

---

## Related

- [Budget Consultation 2026-2027](BUDGET_VOTE_EMAIL.md)
- [Glenda v57.19 Knowledge Update](CHANGELOG.md) — confirmed pricing injected after vote close
- Spreadsheet: `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA` (Customers tab)
