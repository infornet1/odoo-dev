# Customers Sheet vs Odoo Representante — VAT Audit

**Date:** 2026-02-15
**Status:** PENDING REVIEW (follow up Feb 18, 2026)
**Action:** Waiting for invoicing/customer support team feedback

---

## Summary

| Category | Count |
|----------|-------|
| Match (both Odoo + Sheet) | 175 |
| Odoo-only (not in sheet) | 140 |
| Sheet-only (not in Odoo Representante) | 17 |

---

## Priority 1: Active Sheet Entries Missing Representante Tag (10)

These contacts are ACTIVE in the Customers sheet with recent invoices but have NO Representante tag in Odoo production.

| VAT | Name | Odoo ID | Inv 90d | Sheet Row | Sheet Status |
|-----|------|---------|---------|-----------|--------------|
| V13030596 | MARIA LANZ | #2664 | 3 | 115 | ACTIVE |
| V13453627 | VICTOR VILLAMIZAR | #2906 | 3 | 164 | ACTIVE |
| V14188332 | ROSA MARCANO | #2822 | 6 | 152 | ACTIVE |
| V16250166 | KELLY MONTAGUTH | #2590 | 3 | 102 | ACTIVE |
| V17382543 | RONALD BUTTO | #2818 | 6 | 150 | ACTIVE |
| V17882231 | HECTOR CALLES | #2467 | 3 | 71 | ACTIVE |
| V18476850 | MARIA MARTIN | #3658 | 4 | 116 | ACTIVE |
| V18794732 | MIGUEL GONZALEZ | #2698 | 3 | 126 | ACTIVE |
| V25427177 | WILMEILYS CONTRERAS | #2919 | 3 | 167 | ACTIVE |

**Suggested action:** Add Representante tag to these 9 contacts in both Odoo environments.

---

## Priority 2: Odoo Representante with Invoices but NOT in Sheet (2)

These contacts are tagged Representante in Odoo and have recent invoicing activity but are missing from the Customers sheet.

| VAT | Name | Odoo ID | Inv 90d |
|-----|------|---------|---------|
| V14818060 | YULIMAR GUEVARA | #2951 | 1 |
| V18205513 | ANNELYS SANTOYO | #2169 | 1 |

**Suggested action:** Add these 2 to the Customers sheet.

---

## Priority 3: Inactive Sheet Entries Tagged "Inactivo" in Odoo (6)

These are INACTIVE in the Customers sheet and already tagged "Inactivo" in Odoo. No action needed.

| VAT | Name | Odoo ID | Sheet Row |
|-----|------|---------|-----------|
| E84478521 | DALIA AL LAHYANI | #2295 | 182 |
| V10940421 | MARIA RODRIGUEZ | #2672 | 185 |
| V10941251 | ZULEIMA FERNANDEZ | #2970 | 189 |
| V11265833 | TULIO MONTES | #2891 | 187 |
| V15014379 | CARMEN ROJAS | #2252 | 180 |
| V16249615 | VANESSA OSUNA | #2899 | 188 |
| V19638019 | KILZIA CHACOA | #2592 | 184 |

---

## Priority 4: Sheet Entry NOT in Odoo at All (1)

| VAT | Name | Sheet Row | Sheet Status |
|-----|------|-----------|--------------|
| V14553353 | MARLENE MAITA | 186 | INACTIVE |

Contact does not exist in Odoo. Likely a withdrawn family — no action unless support team says otherwise.

---

## Priority 5: Odoo-Only Without Recent Invoices (138)

138 contacts tagged Representante in Odoo with 0 invoices in last 90 days and NOT in Customers sheet. These are likely former families. Full list available via the audit script.

**Question for support team:** Should these be re-tagged as "Inactivo" or kept as Representante?

---

## Questions for Support Team

1. **Priority 1 (9 untagged):** Should these be tagged as Representante or Representante PDVSA?
2. **Priority 2 (2 missing from sheet):** Should YULIMAR GUEVARA and ANNELYS SANTOYO be added to the Customers sheet?
3. **Priority 5 (138 no invoices):** Should contacts with no recent invoicing activity be re-tagged as "Inactivo"?
