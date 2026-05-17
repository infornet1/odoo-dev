# Glenda vía Telegram — Plan de Implementación

**Status:** Production — Fase 1 + 2 deployed 2026-05-17
**Fecha:** 2026-05-17 (v2 — updated with exact file changes)
**Bot registrado:** `@gledas_ueipab` ✅
**Módulo objetivo:** `ueipab_ai_agent` (extensión de canal)

---

## Resumen ejecutivo

Agregar Telegram como segundo canal para Glenda. El bot `@gledas_ueipab` ya está registrado.
El costo adicional es **$0** (Telegram API es gratuito); solo el costo de Claude Haiku ya pagado.
WhatsApp no desaparece — Telegram es un carril paralelo para usuarios inbound desde la web del colegio.

---

## Comparativa de canales

| Criterio | WhatsApp (MassivaMóvil) | Telegram Bot API |
|----------|------------------------|-----------------|
| Costo por mensaje | Incluido en suscripción | **Gratuito** |
| Suscripción mensual | ~$XX/mes | $0 |
| Costo IA (Claude) | ~$0.002/conv | Igual |
| Penetración VE | ~95% | ~25–35% (creciendo) |
| Respuesta | Poll cada 5 min (cron Odoo) | **Webhook instantáneo** |
| Primer contacto | Requiere template Meta | Libre, sin restricciones |
| Ventana 24h | Sí | **No existe** |
| Imágenes (comprobantes) | Sí (URL MassivaMóvil) | Sí (file_id → download) |
| Outbound proactivo | Sí (con template o dentro de 24h) | Solo si usuario inició el bot primero |

---

## Casos de uso

### ✅ Telegram es ideal para
1. **Consultas inbound desde el sitio web** — botón "Chatea con Glenda" → Telegram
2. **Usuarios tech-savvy** que prefieren Telegram
3. **Reducir consumo de créditos WA** para consultas generales
4. **Conversaciones sin límite de 24h** — Glenda puede seguir aunque pasen días

### ❌ NO reemplaza WA para
1. **Outbound proactivo** (facturas, payslip ack, recordatorios) — representantes viven en WA
2. **Usuarios mayores** — WhatsApp es dominante en Venezuela para ese segmento

---

## Arquitectura técnica

### Flujo de mensajes

```
Usuario Telegram
    │  (mensaje de texto, imagen, /start)
    ▼
Telegram servers
    │  POST /ai-agent/telegram/webhook  (webhook, instantáneo)
    ▼
TelegramWebhookController  (nuevo)
    │  extrae chat_id, text, photo
    ▼
ai.agent.conversation._get_or_create_telegram_conversation()  (nuevo)
    │  crea/recupera conversación con channel='telegram'
    ▼
conv.action_process_reply()  (modificado — channel-aware)
    │  llama _send_to_user() en vez de wa_service directamente
    ▼
ai.agent.telegram.service.send_message(chat_id, text)  (nuevo)
    │  POST api.telegram.org/bot{TOKEN}/sendMessage
    ▼
Usuario Telegram
```

### Pivote arquitectónico clave: `_send_to_user()`

El cambio central es reemplazar las **7 llamadas directas** a `wa_service.send_message()` en
`ai_agent_conversation.py` por un helper `_send_to_user(text)` que despacha por canal:

```python
def _send_to_user(self, text):
    """Despacha al canal correcto — WA o Telegram."""
    ICP = self.env['ir.config_parameter'].sudo()
    if ICP.get_param('ai_agent.dry_run', 'True').lower() == 'true':
        _logger.info("DRY_RUN [%s]: %s", self.channel, text[:80])
        return 0
    if self.channel == 'telegram':
        self.env['ai.agent.telegram.service'].send_message(self.telegram_chat_id, text)
        return 0  # Telegram tiene su propio message_id, no lo usamos
    else:
        wa = self.env['ai.agent.whatsapp.service']
        result = wa.send_message(self.phone, text)
        return result.get('message_id', 0)
```

Con este helper, `action_process_reply()` y `_send_reminder()` no necesitan saber nada de Telegram.

---

## Archivos a crear / modificar

### NUEVOS

#### `models/ai_agent_telegram_service.py`
Wrapper HTTP para la Telegram Bot API. Funciones:
- `send_message(chat_id, text)` — envío de texto con `parse_mode='HTML'`
- `get_file_url(file_id)` — obtiene URL descargable para imágenes (comprobantes)
- `set_webhook(url)` — registra el webhook (llamar una sola vez al desplegar)
- `answer_pre_checkout_query()` — reservado para Fase 3 (inline buttons)

Config params:
- `ai_agent.telegram_bot_token` — token de @BotFather
- `ai_agent.telegram_enabled` — booleano kill-switch

#### `controllers/telegram_webhook.py`
Endpoint público que recibe los updates de Telegram:

```python
@http.route('/ai-agent/telegram/webhook', type='json', auth='public',
            methods=['POST'], csrf=False)
def telegram_webhook(self, **kwargs):
    data = request.get_json_data()
    message = data.get('message') or data.get('edited_message', {})
    if not message:
        return {}
    chat_id   = str(message['chat']['id'])
    text      = message.get('text', '')
    first_name = message.get('from', {}).get('first_name', '')
    photo     = message.get('photo')   # lista de tamaños; usar el último (mayor)
    document  = message.get('document')

    request.env['ai.agent.conversation'].sudo()\
        ._handle_telegram_inbound(chat_id, text, first_name, photo, document)
    return {}
```

### MODIFICADOS

#### `models/ai_agent_conversation.py`

**1. Campos nuevos:**
```python
channel = fields.Selection([
    ('whatsapp', 'WhatsApp'),
    ('telegram', 'Telegram'),
], default='whatsapp', string='Canal')

telegram_chat_id = fields.Char('Telegram Chat ID')
```

**2. Campo `phone` — quitar `required=True`** (Telegram no tiene teléfono).
   Agregar `_check_identifier` constraint: al menos uno de `phone` o `telegram_chat_id` debe estar presente.

**3. Método nuevo `_send_to_user(text)`** — ver arriba.

**4. Reemplazar 7 callsites** de `wa_service.send_message(self.phone, text)`:

| Línea aprox. | Contexto | Cambio |
|---|---|---|
| 345 | Greeting al iniciar | `self._send_to_user(greeting)` |
| 461 | Action reply (balance, etc.) | `self._send_to_user(...)` |
| 511 | Farewell al resolver | `self._send_to_user(farewell)` |
| 569 | Respuesta normal de Claude | `self._send_to_user(response_text)` |
| 623 | Balance breakdown | `self._send_to_user(balance_msg)` |
| 1420 | Reminder | `self._send_to_user(reminder_text)` |
| 1472 | Farewell por timeout | `self._send_to_user(farewell)` |

**5. Método nuevo `_handle_telegram_inbound(chat_id, text, first_name, photo, document)`:**
```python
def _handle_telegram_inbound(self, chat_id, text, first_name, photo, document):
    """Punto de entrada para mensajes Telegram. Análogo a _cron_poll_messages para WA."""
    if not self._telegram_enabled():
        return
    # Imagen → descargar y pasar como attachment a action_process_reply
    attachment = None
    if photo:
        file_id = photo[-1]['file_id']  # mayor resolución
        url = self.env['ai.agent.telegram.service'].get_file_url(file_id)
        attachment = {'url': url, 'source': 'telegram'}
    # Crear o recuperar conversación
    conv = self._get_or_create_telegram_conversation(chat_id, first_name)
    if not conv:
        return
    conv.action_process_reply(
        message_text=text or '[imagen]',
        extra_attachments=[attachment] if attachment else None,
    )
```

**6. Método nuevo `_get_or_create_telegram_conversation(chat_id, first_name)`:**
Similar a `_get_or_create_general_inquiry_conversation()` pero:
- Busca por `telegram_chat_id` en vez de `phone`
- No bloquea por "farewell" de conversación previa (Telegram no tiene la misma dinámica)
- Crea conversación con `channel='telegram'`, `phone=''`, `telegram_chat_id=chat_id`
- Notifica CEO si partner identificado tiene saldo (mismo `_notify_ceo`)

#### `__manifest__.py`
Agregar a `data` y asegurar que los nuevos archivos están en los paths correctos.

#### `models/__init__.py`
```python
from . import ai_agent_telegram_service
```

#### `controllers/__init__.py`
```python
from . import telegram_webhook
```

---

## Plan por fases

### Fase 1 — Bot funcional (2 días) ← Empezar aquí

**Objetivo:** Enviar "Hola" al bot → Glenda responde por Telegram con el mismo conocimiento institucional que WA.

**Tareas:**
1. Obtener token de @BotFather (del bot `@gledas_ueipab`) → `ir.config_parameter` `ai_agent.telegram_bot_token`
2. Crear `ai_agent_telegram_service.py` con `send_message()` y `get_file_url()`
3. Crear `controllers/telegram_webhook.py`
4. Agregar campos `channel` + `telegram_chat_id` a `ai.agent.conversation`
5. Agregar `_send_to_user()` y reemplazar los 7 callsites
6. Implementar `_handle_telegram_inbound()` + `_get_or_create_telegram_conversation()`
7. Verificar nginx: `location /ai-agent/` ya cubre `/ai-agent/telegram/webhook` ✅
8. Llamar `set_webhook(f"{base_url}/ai-agent/telegram/webhook")` una vez
9. Upgradear módulo: `odoo -u ueipab_ai_agent`
10. Test: enviar "Hola" al bot → Glenda responde en Telegram

**Imágenes (comprobantes de pago):**
Manejar desde Fase 1 porque los clientes envían fotos de recibos. El flow es:
`photo[-1].file_id` → `get_file_url()` → URL temporal Telegram → Claude vision (igual que WA).

**Entregable:** Bot vivo, respondiendo en español venezolano, mismo conocimiento que WA.

---

### Fase 2 — Identificación de partner (1 día)

**Objetivo:** Glenda conoce quién está escribiendo → puede mostrar saldo, datos específicos.

**Estrategia de identificación:**
Telegram no tiene número de teléfono accesible sin permiso explícito del usuario.
Opciones (en orden de preferencia):

1. **Deep link desde el sitio web** — `t.me/gledas_ueipab?start=TOKEN` donde TOKEN es el token del partner en Odoo (`res.partner.token_notice_ack` o campo nuevo). Al hacer `/start TOKEN`, Glenda identifica al partner automáticamente.

2. **Solicitar cédula en conversación** — misma lógica que el flujo actual de `general_inquiry` (Glenda pregunta "¿Cuál es tu número de cédula?"). Compatible desde Fase 1 sin cambios adicionales.

3. **Botón "Compartir número"** (Fase 3) — Telegram permite botón `request_contact` que envía número de teléfono con consentimiento del usuario → cruzar con `res.partner.mobile`.

**Persistencia:** guardar `partner_id` en la conversación al identificar.

---

### Fase 3 — Features avanzados (2-3 días, opcional)

- **Inline buttons** — opciones rápidas: "Ver mi saldo", "Inscripción 2026-2027", "Contactar Pagos"
- **Comando `/saldo`** — balance directo si partner identificado
- **Botón "Compartir número"** — identificación sin cédula
- **CEO Command Center** — `_notify_ceo` ya funciona (no depende del canal); solo verificar que el resumen mencione "canal Telegram"
- **Canal de anuncios** — canal broadcast separado del bot (administrador envía a todos los suscriptores); requiere Telegram Channel API (diferente a bot)

---

## Configuración requerida

### ir.config_parameter a crear

| Clave | Valor | Descripción |
|-------|-------|-------------|
| `ai_agent.telegram_bot_token` | `<token de @BotFather>` | Token del bot `@gledas_ueipab` |
| `ai_agent.telegram_enabled` | `True` | Kill-switch |

### Webhook (ejecutar una vez post-deploy)

```python
# Desde Odoo shell (testing primero, luego prod)
env['ai.agent.telegram.service'].set_webhook(
    'https://dev.ueipab.edu.ve/ai-agent/telegram/webhook'  # testing
    # 'https://odoo.ueipab.edu.ve/ai-agent/telegram/webhook'  # prod
)
```

### Nginx
El bloque `location /ai-agent/` ya existe y cubre el nuevo endpoint. Sin cambios requeridos.

---

## Estimación de costos operativos

| Item | Costo mensual |
|------|---------------|
| Telegram Bot API | **$0** |
| Claude Haiku (50 convs/día × 30 × $0.002) | ~$3/mes |
| Infraestructura (ya existe) | $0 adicional |
| **Total adicional** | **~$3/mes** |

---

## Diferencias clave WA vs Telegram (para implementación)

| Aspecto | WhatsApp | Telegram |
|---------|----------|----------|
| Identificador usuario | `phone` (número) | `chat_id` (entero) |
| Imágenes | URL directa de MassivaMóvil | `file_id` → llamar `getFile` → URL temporal (válida 1h) |
| Entrada de mensajes | Poll cron cada 5 min | Webhook POST instantáneo |
| Primer mensaje del bot | Template aprobado por Meta | Texto libre |
| Restricción outbound | 24h window + templates | Solo si usuario inició el bot |
| `send_reminders` (timeouts) | general_inquiry=False (silencioso) | Mismo comportamiento |
| `whatsapp_message_id` | Necesario para dedup | No aplica (Telegram tiene su propio `message_id`) |
| Anti-spam (120s) | Aplicable entre sends | No necesario (Telegram no bloquea por frecuencia) |

---

## Limitaciones conocidas

1. **Sin outbound proactivo** — Telegram no permite iniciar conversación si el usuario no ha escrito primero
2. **Adopción incierta** — requiere promoción activa (QR en colegio, link en web)
3. **Identificación más lenta** — sin número de teléfono, la identificación requiere un paso extra vs WA
4. **file_id expira** — las URLs de imágenes de Telegram son temporales (~1h); el OCR debe hacerse inmediatamente

---

## Estado de deployment (2026-05-17)

| Item | Estado |
|------|--------|
| Bot `@GlendaUeipabBot` | ✅ Producción LIVE |
| Token configurado | ✅ `ai_agent.telegram_bot_token` en DB_UEIPAB |
| Webhook | ✅ `odoo.ueipab.edu.ve/ai-agent/telegram/webhook` |
| `channel` + `telegram_chat_id` fields | ✅ En `ai.agent.conversation` |
| `_send_to_user()` channel dispatch | ✅ 7 callsites migrados |
| `/start EMP_{id}` deep-link handler | ✅ Auto-identifica empleado |
| WA → Telegram invite (1er reply) | ✅ `ai_agent.telegram_invite_enabled=True` |
| Anuncio interno enviado | ✅ 47/47 empleados — 2026-05-17 |
| Script anuncio | ✅ `scripts/send_glenda_telegram_announcement.py` |

### Empleados con link genérico (cédula fallback)
- `maria.nieto@ueipab.edu.ve` — work_email en prod es `ybagnieto8@gmail.com` → **actualizar HR**
- `alberto.perdomo`, `yelitza.chirinos`, `jesus.rengel` — no creados en prod aún

---

## Próximos pasos (Fase 3)

- Inline buttons (`/saldo`, `Contactar Pagos`, opciones rápidas)
- Crear empleados faltantes en prod y reenviar con deep link
- Actualizar `work_email` de MARIA NIETO → `maria.nieto@ueipab.edu.ve`
- Publicar `t.me/GlendaUeipabBot` en el sitio web del colegio para representantes
