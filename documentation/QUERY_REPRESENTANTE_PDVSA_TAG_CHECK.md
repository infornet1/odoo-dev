# QueryRepresentantePDVSAFalseTagCheck

**Created:** 2026-04-15
**Environment:** Production (`DB_UEIPAB`) — read-only query via XML-RPC
**Models:** `res.partner`, `account.move`, `account.move.line`

---

## Purpose

Ad-hoc receivables report for customers tagged as **Representante PDVSA** (`res.partner.category_id`), showing outstanding invoice balances segmented by `fiscal_check` flag. Includes total product line quantity per customer.

---

## Filter Criteria

| Field | Model | Value |
|-------|-------|-------|
| `category_id` | `res.partner` | `Representante PDVSA` (tag id=26, same in both envs) |
| `move_type` | `account.move` | `out_invoice`, `out_receipt` |
| `state` | `account.move` | `posted` |
| `fiscal_check` | `account.move` | `True` or `False` (run separately) |
| `payment_state` | `account.move` | not `paid` |
| `display_type` | `account.move.line` | `product` only (excludes section/note lines) |

---

## Output Fields

| Column | Source | Notes |
|--------|--------|-------|
| Customer Name | `res.partner.name` | Alphabetically sorted |
| Tax ID | `res.partner.vat` | Venezuelan cedula (V-prefix) |
| QTY | `account.move.line.quantity` | Sum of product lines across all unpaid invoices per customer |
| Amount Due | `account.move.amount_residual_signed` | Signed field — correctly nets credit notes and partial payments |

> **Why `amount_residual_signed` and not `amount_residual`?**
> `amount_residual` is always positive (absolute value). `amount_residual_signed` carries the sign
> of the move from the customer's perspective, so credit notes and overpayments correctly offset
> outstanding balances. Using `amount_residual` caused a $24,662 overstatement on SARELY BELLORIN
> in the initial run.

---

## Results (2026-04-15, Production)

### fiscal_check = TRUE (Es Fiscal)

| Customer Name | Tax ID | QTY | Amount Due |
|---|---|---|---|
| ALBERTO GONZALEZ | V14641877 | 1.00 | 128.30 |
| ALIRIO ROSAS | V18340737 | 1.00 | 128.30 |
| ANA GUEVARA | V14552083 | 1.00 | 197.38 |
| CARLOS JOSE LAYA MEJIAS | V14640559 | 1.00 | 197.38 |
| CARLOS NAVARRO | V12437797 | 1.00 | 0.38 |
| CARLOS SALAZAR | V12075876 | 2.00 | 256.60 |
| DAMIRIS HEREDIA | V11726859 | 1.00 | 128.30 |
| DANIEL DOMINGUEZ | V17592159 | 2.00 | 256.60 |
| DANIELA RONDON | V18229071 | 1.00 | 0.01 |
| DANNEYSE LA CRUZ | V12679751 | 1.00 | 128.30 |
| DAVID EVANS | V14133887 | 2.00 | 394.76 |
| ELIAS MUNOZ | V17010349 | 1.00 | 197.38 |
| ELVIS GOMEZ | V18827337 | 1.00 | 167.77 |
| JESUS LA CRUZ | V18454199 | 1.00 | 128.30 |
| JONATHAN RAMIREZ | V20546183 | 1.00 | 128.30 |
| JOSE TABASCA | V12017339 | 1.00 | 128.30 |
| JOSMAR FIGUEROA | V15846608 | 2.00 | 256.66 |
| JOYCE MOGOLLON | V17008520 | 1.00 | 128.30 |
| LILIANNA REYES | V17558736 | 2.00 | 197.46 |
| LUIS CONDALES | V14133407 | 1.00 | 128.38 |
| MARIA APONTE | V18478620 | 5.00 | 845.42 |
| NELLYS ARAY | V17871749 | 1.00 | 128.30 |
| RAMLY REQUENA | V14187612 | 1.00 | 127.76 |
| RAQUEL LOPEZ | V18808658 | 1.00 | 128.30 |
| REINSON GUTIERREZ | V16311885 | 4.00 | 611.74 |
| RONALD BUTTO | V17382543 | 2.00 | 256.60 |
| ROSALIA YANEZ | V16572749 | 1.00 | 131.07 |
| ROXIMAR HERNANDEZ | V16078298 | 2.00 | 256.60 |
| RUTHBELIS MARIN | V13610559 | 1.00 | 0.23 |
| SARELY BELLORIN | V14641839 | 1.00 | 197.83 |
| VIRGILIO CASTRO | V13920446 | 2.00 | 256.88 |
| YAIRO BLONDELL | V14725186 | 1.00 | 197.38 |
| ZORIMAR SANTAELLA | V13498097 | 2.00 | 256.60 |
| **TOTAL** | | **49.00** | **6,671.87** |

### fiscal_check = FALSE (No Fiscal)

| Customer Name | Tax ID | QTY | Amount Due |
|---|---|---|---|
| ANNELYS SANTOYO | V18205513 | 2.00 | 394.76 |
| CARLOS NAVARRO | V12437797 | 1.00 | 197.38 |
| DANIEL VASQUEZ | V17237134 | 1.00 | 197.38 |
| GREGORY PEREIRA | V12873319 | 1.00 | 128.30 |
| ILDEMARO ARRIOJA | V15934607 | 1.00 | 128.30 |
| JEAN CARLOS CANO | V14468555 | 1.00 | 197.38 |
| JEAN CARLOS SEQUEA | V13498322 | 1.00 | 197.38 |
| LILIANNA REYES | V17558736 | 2.00 | 56.00 |
| MARIA ALEJANDRA GONZALEZ | V14688499 | 1.00 | 197.38 |
| RUTHBELIS MARIN | V13610559 | 1.00 | 197.38 |
| **TOTAL** | | **12.00** | **1,891.64** |

### Combined Summary

| fiscal_check | Customers | Invoices | Amount Due |
|---|---|---|---|
| True | 33 | 49 | $6,671.87 |
| False | 10 | 12 | $1,891.64 |
| **Combined** | **43** | **61** | **$8,563.51** |

> Customers appearing in both groups (mix of fiscal/non-fiscal unpaid invoices):
> CARLOS NAVARRO, LILIANNA REYES, RUTHBELIS MARIN

---

## Python Script (XML-RPC)

```python
import xmlrpc.client
from collections import defaultdict

ODOO_URL  = 'https://odoo.ueipab.edu.ve'
ODOO_DB   = 'DB_UEIPAB'
ODOO_USER = 'tdv.devs@gmail.com'
ODOO_PASS = '<api_key>'   # see /opt/odoo-dev/scripts/ai_agent_resolution_bridge.py

common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid    = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', allow_none=True)

def search_read(model, domain, fields):
    return models.execute_kw(ODOO_DB, uid, ODOO_PASS, model, 'search_read',
                             [domain], {'fields': fields})

# Tag id=26 = Representante PDVSA (same in testing and production)
partners    = search_read('res.partner', [('category_id', '=', 26)], ['id', 'name', 'vat'])
partner_ids = [p['id'] for p in partners]
partner_map = {p['id']: (p['name'], p['vat'] or '') for p in partners}

def run_report(fiscal_flag):
    moves = search_read('account.move',
        [
            ('partner_id',    'in', partner_ids),
            ('move_type',     'in', ['out_invoice', 'out_receipt']),
            ('state',         '=',  'posted'),
            ('fiscal_check',  '=',  fiscal_flag),
            ('payment_state', '!=', 'paid'),
        ],
        ['id', 'partner_id', 'amount_residual_signed']
    )
    if not moves:
        return 0.0

    move_ids = [m['id'] for m in moves]

    # Quantity: product lines only (excludes section/note display_type)
    lines = search_read('account.move.line',
        [('move_id', 'in', move_ids), ('display_type', '=', 'product')],
        ['move_id', 'quantity']
    )
    qty_per_move = defaultdict(float)
    for l in lines:
        qty_per_move[l['move_id'][0]] += l['quantity']

    data = defaultdict(lambda: {'amount': 0.0, 'qty': 0.0})
    for m in moves:
        pid = m['partner_id'][0]
        data[pid]['amount'] += m['amount_residual_signed']
        data[pid]['qty']    += qty_per_move.get(m['id'], 0.0)

    total_amt = total_qty = 0.0
    for pid, vals in sorted(data.items(), key=lambda x: partner_map[x[0]][0]):
        name, vat = partner_map[pid]
        print(f"{name:<35} {vat:<15} {vals['qty']:>8,.2f} {vals['amount']:>15,.2f}")
        total_amt += vals['amount']
        total_qty += vals['qty']
    print(f"{'TOTAL':<35} {'':<15} {total_qty:>8,.2f} {total_amt:>15,.2f}")
    return total_amt

run_report(True)
run_report(False)
```

---

## Notes

- **Tag ID 26** (`Representante PDVSA`) is consistent across testing and production environments.
- `fiscal_check` is a custom boolean field (`Es fiscal`) on `account.move`, added by a local customization.
- Near-zero balances (e.g. CARLOS NAVARRO $0.38, DANIELA RONDON $0.01) are likely rounding residuals — candidates for write-off.
- Re-run this query monthly or after each invoice cycle to track PDVSA receivables aging.
