#!/usr/bin/env python3
"""
Cashea Campaign — Envío Masivo (via Odoo Shell)

Envía la campaña de lanzamiento Cashea a todos los clientes activos con email.
Por defecto corre en DRY_RUN. Cambiar DRY_RUN = False para envío real.

Prerrequisito:
    1. Crear la plantilla primero:
       docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
         < /opt/odoo-dev/scripts/create_cashea_campaign_template.py

Uso:
    # DRY_RUN — ver destinatarios sin enviar
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
      < /opt/odoo-dev/scripts/send_cashea_campaign.py

    # Envío real (cambiar DRY_RUN = False abajo)
    # o pasar variable de entorno:
    #   DRY_RUN=false docker exec -i odoo-dev-web ...
"""

import os
import sys
import time
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────────────

# Cambiar a False cuando estés listo para el envío real
DRY_RUN = os.environ.get('DRY_RUN', 'true').lower() not in ('false', '0', 'no')

# ID de la plantilla creada por create_cashea_campaign_template.py
# Actualizar si la plantilla fue recreada con un ID diferente
TEMPLATE_ID = int(os.environ.get('CASHEA_TEMPLATE_ID', '81'))

# Límite de destinatarios (0 = todos). Útil para prueba inicial con 5 o 10.
LIMIT = int(os.environ.get('CASHEA_LIMIT', '0'))

# Pausa entre envíos (segundos) para no saturar el servidor de correo
SEND_DELAY = float(os.environ.get('CASHEA_DELAY', '0.5'))

# ──────────────────────────────────────────────────────────────────────────────
# Inicio
# ──────────────────────────────────────────────────────────────────────────────

print("=" * 70)
print(f"CAMPAÑA CASHEA — {'*** DRY RUN (simulación) ***' if DRY_RUN else '*** ENVÍO REAL ***'}")
print(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Template  : id={TEMPLATE_ID}")
if LIMIT:
    print(f"Límite    : {LIMIT} destinatarios")
print("=" * 70)

# ──────────────────────────────────────────────────────────────────────────────
# Verificar plantilla
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n[1] Verificando plantilla id={TEMPLATE_ID}...")
Template = env['mail.template']
tmpl = Template.browse(TEMPLATE_ID)
if not tmpl.exists():
    print(f"    ERROR: Plantilla id={TEMPLATE_ID} no encontrada.")
    print("    Ejecuta create_cashea_campaign_template.py primero.")
    sys.exit(1)
print(f"    OK — '{tmpl.name}'")
print(f"    Asunto: {tmpl.subject}")

# ──────────────────────────────────────────────────────────────────────────────
# Obtener destinatarios — clientes activos con email (no internos)
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n[2] Buscando destinatarios...")
domain = [
    ('active', '=', True),
    ('email', '!=', False),
    ('customer_rank', '>', 0),
    ('email', 'not ilike', '@ueipab.edu.ve'),  # excluir emails internos
]
partners = env['res.partner'].search(domain, order='name asc')

if LIMIT and LIMIT > 0:
    partners = partners[:LIMIT]

print(f"    {len(partners)} destinatario(s) encontrado(s)")

if not partners:
    print("    Sin destinatarios. Verificar dominio de búsqueda.")
    sys.exit(0)

# Mostrar muestra
print(f"\n    Primeros {min(10, len(partners))} destinatarios:")
for p in partners[:10]:
    print(f"      [{p.id:5d}] {p.name:<42} {p.email}")
if len(partners) > 10:
    print(f"      ... y {len(partners)-10} más")

# ──────────────────────────────────────────────────────────────────────────────
# DRY_RUN — sólo mostrar resumen
# ──────────────────────────────────────────────────────────────────────────────

if DRY_RUN:
    print(f"\n{'─'*70}")
    print(f"DRY RUN — se enviarían {len(partners)} correos.")
    print("Para envío real, ejecutar con variable DRY_RUN=false:")
    print("  DRY_RUN=false docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \\")
    print("    < /opt/odoo-dev/scripts/send_cashea_campaign.py")
    print(f"{'─'*70}")
    sys.exit(0)

# ──────────────────────────────────────────────────────────────────────────────
# ENVÍO REAL
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n[3] Enviando correos ({len(partners)} destinatarios)...")
print(f"    Delay entre envíos: {SEND_DELAY}s\n")

sent = 0
errors = 0
start_ts = time.time()

for i, partner in enumerate(partners, 1):
    try:
        # Renderiza con Odoo 17 API y encola (force_send=False)
        rendered = tmpl._generate_template(
            [partner.id],
            render_fields=['subject', 'body_html', 'email_from']
        )
        r = rendered[partner.id]
        mail = env['mail.mail'].create({
            'subject': r['subject'],
            'body_html': r['body_html'],
            'email_from': r.get('email_from', '"Instituto Privado Andrés Bello" <pagos@ueipab.edu.ve>'),
            'email_to': partner.email,
            'auto_delete': False,
        })
        sent += 1
        print(f"  [{i:4d}/{len(partners)}] OK   {partner.name:<44} {partner.email}")
    except Exception as e:
        errors += 1
        err_msg = str(e)[:80]
        print(f"  [{i:4d}/{len(partners)}] ERR  {partner.name:<44} {partner.email}")
        print(f"               {err_msg}")

    if i < len(partners) and SEND_DELAY > 0:
        time.sleep(SEND_DELAY)

# Commit para persistir los mensajes encolados
env.cr.commit()

elapsed = time.time() - start_ts
print(f"\n{'='*70}")
print(f"CAMPAÑA CASHEA — COMPLETADA")
print(f"  Enviados  : {sent}")
print(f"  Errores   : {errors}")
print(f"  Duración  : {elapsed:.1f}s")
print(f"  Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nLos correos están encolados en mail.mail (estado 'outgoing').")
print(f"El servidor de correo los enviará en el siguiente ciclo del cron.")
print("=" * 70)
