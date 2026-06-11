# -*- coding: utf-8 -*-
"""Setup 2026-2027 enrollment catalog for ueipab_sales.

Idempotent — safe to re-run. Creates/updates:
  - 17 products (clone config of product.template id=8 MENSUALIDAD)
  - Sales settings: quotation templates ON, portal payment OFF (signature stays)
  - 12 sale.order.template (3 llamados x 4 family cases)

Run:  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
        < /opt/odoo-dev/scripts/setup_ueipab_sales_catalog.py
Prod: same via ueipab17 / DB_UEIPAB (after testing validation only).
"""
BCV_NOTE = ("NOTA IMPORTANTE: Todos los montos están expresados en USD. "
            "Debe ser pagado a la tasa BCV del día.")

# ── 1. Products ──────────────────────────────────────────────────────────────
# (code, name, price, description_sale)
PRODUCTS = [
    # Inscripción — one per llamado
    ('INS2627-L1', 'Inscripción 2026-2027 · 1er Llamado (Promoción Especial)',
     187.51, 'Válido 11/06/2026 – 31/07/2026 · Incluye convenio de pago a tarifa preferencial'),
    ('INS2627-L2', 'Inscripción 2026-2027 · 2do Llamado (Promoción Vacacional)',
     207.93, 'Válido 01/08/2026 – 31/08/2026 · Requiere solvencia al 31/07/2026'),
    ('INS2627-L3', 'Inscripción 2026-2027 · 3er Llamado (Regular)',
     218.88, 'Válido 01/09/2026 – 30/09/2026 · Requiere solvencia total 2025-2026'),
    # Mensualidad — promo (convenio 1er llamado); hermanos % stack on promo
    ('MEN2627-PROMO',    'Mensualidad 2026-2027 · Convenio 1er Llamado',            197.38,
     'Tarifa preferencial con convenio firmado hasta el 31/07/2026'),
    ('MEN2627-PROMO-H2', 'Mensualidad 2026-2027 · Convenio · 2 hermanos (-5%)',     187.51,
     'Tarifa preferencial convenio, por estudiante (2 hermanos)'),
    ('MEN2627-PROMO-H3', 'Mensualidad 2026-2027 · Convenio · 3 hermanos (-8%)',     181.59,
     'Tarifa preferencial convenio, por estudiante (3 hermanos)'),
    ('MEN2627-PROMO-H4', 'Mensualidad 2026-2027 · Convenio · 4+ hermanos (-11%)',   175.67,
     'Tarifa preferencial convenio, por estudiante (4 o más hermanos)'),
    # Mensualidad — base (2do/3er llamado)
    ('MEN2627-BASE', 'Mensualidad 2026-2027 · Tarifa regular',          218.88, 'Tarifa aprobada (Opción A) desde septiembre 2026'),
    ('MEN2627-PP',   'Mensualidad 2026-2027 · Pronto pago (-5%)',       207.93, 'Descuento por pronto pago sobre tarifa regular'),
    ('MEN2627-H2',   'Mensualidad 2026-2027 · 2 hermanos (-5%)',        207.94, 'Por estudiante (2 hermanos), tarifa regular'),
    ('MEN2627-H3',   'Mensualidad 2026-2027 · 3 hermanos (-8%)',        201.37, 'Por estudiante (3 hermanos), tarifa regular'),
    ('MEN2627-H4',   'Mensualidad 2026-2027 · 4+ hermanos (-11%)',      194.80, 'Por estudiante (4+ hermanos), tarifa regular'),
    # Anuales — per student
    ('SEG2627',   'Seguro Escolar 2026-2027 (Seguros Caracas)', 30.58, 'Costo anual por estudiante'),
    ('ING2627-P', 'Guía de Inglés 2026-2027 · precio promo',    35.00, 'Válido hasta el 31/07/2026'),
    ('ING2627-R', 'Guía de Inglés 2026-2027 · precio regular',  40.00, 'Desde el 01/08/2026'),
    ('OLI2627',   'Olimpiadas 2026-2027',                       10.00, 'Costo anual por estudiante'),
    ('ENC2627',   'Enciclopedia 2026-2027',                     36.00, 'Costo anual por estudiante'),
]

ref = env['product.template'].browse(8)   # MENSUALIDAD — config to clone
assert ref.exists(), 'Reference product id=8 not found'
base_vals = {
    'detailed_type': ref.detailed_type,
    'categ_id': ref.categ_id.id,
    'taxes_id': [(6, 0, ref.taxes_id.ids)],
    'invoice_policy': ref.invoice_policy,
    'uom_id': ref.uom_id.id,
    'uom_po_id': ref.uom_po_id.id,
    'sale_ok': True,
    'purchase_ok': False,
}

created = updated = 0
for code, name, price, desc in PRODUCTS:
    vals = dict(base_vals, name=name, default_code=code,
                list_price=price, description_sale=desc)
    tmpl = env['product.template'].search([('default_code', '=', code)], limit=1)
    if tmpl:
        tmpl.write(vals)
        updated += 1
    else:
        env['product.template'].create(vals)
        created += 1
print('Products: %d created, %d updated' % (created, updated))

# ── 2. Sales settings ────────────────────────────────────────────────────────
settings = env['res.config.settings'].create({
    'group_sale_order_template': True,     # enable Quotation Templates feature
    'portal_confirmation_sign': True,      # keep signature option (read-only stage anyway)
    'portal_confirmation_pay': False,      # NO online payment requirement
})
settings.execute()
print('Settings applied: quotation templates ON, portal payment OFF')

# ── 3. Quotation templates (for the Sales team UI) ───────────────────────────
LLAMADOS = [
    ('1er Llamado (hasta 31/07/2026)', 'INS2627-L1',
     {1: 'MEN2627-PROMO', 2: 'MEN2627-PROMO-H2', 3: 'MEN2627-PROMO-H3', 4: 'MEN2627-PROMO-H4'},
     'ING2627-P'),
    ('2do Llamado (agosto 2026)', 'INS2627-L2',
     {1: 'MEN2627-BASE', 2: 'MEN2627-H2', 3: 'MEN2627-H3', 4: 'MEN2627-H4'},
     'ING2627-R'),
    ('3er Llamado (septiembre 2026)', 'INS2627-L3',
     {1: 'MEN2627-BASE', 2: 'MEN2627-H2', 3: 'MEN2627-H3', 4: 'MEN2627-H4'},
     'ING2627-R'),
]
CASES = [(1, '1 estudiante'), (2, '2 hermanos'), (3, '3 hermanos'), (4, '4+ hermanos')]
ANUALES = ['SEG2627', 'OLI2627', 'ENC2627']

def variant(code):
    p = env['product.product'].search([('default_code', '=', code)], limit=1)
    assert p, 'missing product %s' % code
    return p

t_created = t_updated = 0
for l_name, ins_code, men_map, ing_code in LLAMADOS:
    for qty, case_name in CASES:
        tpl_name = 'Inscripción 2026-2027 · %s · %s' % (l_name, case_name)
        line_codes = [ins_code, men_map[qty], 'SEG2627', ing_code, 'OLI2627', 'ENC2627']
        lines = [(0, 0, {
            'product_id': variant(c).id,
            'product_uom_qty': qty,
            'product_uom_id': variant(c).uom_id.id,
        }) for c in line_codes]
        vals = {
            'name': tpl_name,
            'sale_order_template_line_ids': lines,
            'note': BCV_NOTE,
        }
        tpl = env['sale.order.template'].search([('name', '=', tpl_name)], limit=1)
        if tpl:
            tpl.sale_order_template_line_ids.unlink()
            tpl.write(vals)
            t_updated += 1
        else:
            env['sale.order.template'].create(vals)
            t_created += 1
print('Templates: %d created, %d updated' % (t_created, t_updated))

env.cr.commit()
print('DONE — catalog setup committed.')
