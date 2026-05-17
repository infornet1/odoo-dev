# Glenda vía Telegram — Plan de Implementación

**Status:** Idea / Planning
**Fecha:** 2026-05-17
**Módulo objetivo:** `ueipab_ai_agent` (extensión de canal)

---

## Resumen ejecutivo

Agregar Telegram como segundo canal de atención para Glenda. El API de Telegram Bot es **100% gratuito** (sin costo por mensaje); el único costo variable es Claude Haiku (~$0.001–$0.003/conv), mismo que ya se paga por WhatsApp. El canal de WA no desaparece — Telegram sería un carril paralelo para usuarios que prefieran ese canal o que lleguen desde el sitio web del colegio.

---

## Comparativa de canales

| Criterio | WhatsApp (MassivaMóvil) | Telegram Bot API |
|----------|------------------------|-----------------|
| Costo por mensaje | Incluido en suscripción mensual | **Gratuito** |
| Costo suscripción | ~$XX/mes (MassivaMóvil) | $0 |
| Costo IA (Claude) | ~$0.001–0.003/conv | Igual |
| Penetración VE | ~95% | ~25–35% (creciendo) |
| Entrega en tiempo real | Poll cada 5 min (o webhook) | **Webhook instantáneo** |
| Primer contacto | Requiere template aprobado por Meta | Libre, sin restricciones |
| Ventana 24h | Sí — después de 24h sin respuesta del usuario, solo templates | **No existe esta restricción** |
| Multimedia | Imágenes, audio, documentos | Igual + inline buttons |
| Outbound proactivo | Sí (si ya enviaste en 24h / con template) | Solo si usuario inició el bot |
| API calidad | Buena (MassivaMóvil abstrae) | Excelente (oficial, bien documentada) |

---

## Casos de uso apropiados para Telegram

### ✅ Usar Telegram
1. **Consultas inbound desde el sitio web** — botón "Chatea con Glenda en Telegram" en la web del colegio
2. **Canal de noticias/anuncios del colegio** — canal de Telegram (broadcast, no bidireccional)
3. **Usuarios tech-savvy** que prefieren Telegram sobre WA
4. **Reducir consumo de créditos WA** para conversaciones de baja prioridad
5. **Sin ventana 24h** — Glenda puede continuar una conversación en Telegram aunque pasen días sin respuesta del cliente, sin cambiar a templates

### ❌ NO reemplaza WA para
1. **Outbound proactivo** — recordatorio de facturas, comprobantes de pago, payslip ack — los representantes están en WA; no hay forma de iniciarles contacto en Telegram sin que ellos primero inicien el bot
2. **Conversaciones existentes** — la base de datos de partners usa teléfonos móviles, no Telegram ID
3. **Usuarios mayores/no-tech** — WhatsApp es el canal dominante para padres en Venezuela

---

## Arquitectura técnica

### Flujo de mensajes

```
Telegram user → Telegram servers → webhook POST /ai-agent/telegram
                                   → ai.agent.telegram.service
                                   → ai.agent.conversation (skill=general_inquiry)
                                   → Claude Haiku
                                   → Telegram Bot API (send_message)
                                   → Usuario
```

### Componentes nuevos

#### 1. `models/ai_agent_telegram_service.py`
```python
class AiAgentTelegramService(models.AbstractModel):
    _name = 'ai.agent.telegram.service'

    def send_message(self, chat_id, text):
        """Envía mensaje de texto vía Telegram Bot API."""
        token = self.env['ir.config_parameter'].sudo().get_param('ai_agent.telegram_bot_token')
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=15,
        )

    def set_webhook(self, url):
        """Registra el webhook de Telegram apuntando a la URL pública de Odoo."""
        token = self.env['ir.config_parameter'].sudo().get_param('ai_agent.telegram_bot_token')
        requests.post(
            f'https://api.telegram.org/bot{token}/setWebhook',
            json={'url': url, 'allowed_updates': ['message']},
        )
```

#### 2. Controlador webhook — `controllers/telegram_webhook.py`
```python
@http.route('/ai-agent/telegram/webhook', type='json', auth='public', methods=['POST'], csrf=False)
def telegram_webhook(self, **kwargs):
    data = request.get_json_data()
    message = data.get('message', {})
    chat_id = str(message.get('chat', {}).get('id', ''))
    text = message.get('text', '')
    # Delegar a ai.agent.conversation._handle_telegram_message(chat_id, text)
```

#### 3. Identificador de contacto en `ai.agent.conversation`
- Mapa `telegram_chat_id` → `res.partner` vía:
  - Comando `/start <token>` donde token viene del link en el sitio web (preregistro)
  - O solicitar al usuario su cédula/teléfono y cruzar con Odoo
  - Fallback: crear partner placeholder `Consulta Telegram {chat_id}`

#### 4. Campo `channel` en `ai.agent.conversation`
```python
channel = fields.Selection([
    ('whatsapp', 'WhatsApp'),
    ('telegram', 'Telegram'),
    ('discuss', 'Odoo Discuss'),
], default='whatsapp')
```
- La capa de envío (`send_message`) se delega al servicio correcto según `channel`
- El skill `general_inquiry` es channel-agnostic (mismo sistema_prompt, misma lógica)

#### 5. Configuración
| Parámetro | Descripción |
|-----------|-------------|
| `ai_agent.telegram_bot_token` | Token del bot (de @BotFather) |
| `ai_agent.telegram_bot_username` | `@GlendaAndreBelloBot` (o similar) |
| `ai_agent.telegram_enabled` | Booleano kill-switch |

---

## Plan de implementación por fases

### Fase 1 — Bot básico (1-2 días)
- Crear bot en @BotFather → obtener token
- Implementar `ai_agent_telegram_service.py` con `send_message()`
- Controlador webhook `/ai-agent/telegram/webhook`
- Conectar a `_get_or_create_general_inquiry_conversation()` con `channel='telegram'`
- Hacer que `action_process_reply()` use el servicio correcto según `channel`
- Configurar webhook en producción (ya tenemos nginx + SSL)
- **Test:** enviar "Hola" al bot → Glenda responde vía Telegram

### Fase 2 — Identificación de contacto (1 día)
- Flujo `/start` con solicitud de cédula o teléfono → cruzar con `res.partner`
- Si encuentra partner: contexto completo (saldo, nivel, etc.)
- Si no encuentra: placeholder, igual puede responder preguntas generales
- Opción de deep link: `t.me/GlendaBot?start=TOKEN` desde el sitio web del colegio

### Fase 3 — Features adicionales (2-3 días)
- Inline buttons para opciones comunes (ver saldo, inscripción, contactar pagos)
- Comando `/saldo` para consulta rápida de balance (si partner identificado)
- Integración con CEO command center (notificar si debtor contacta por Telegram)
- Canal de anuncios broadcast (mensajes de administrador → todos los suscriptores)

---

## Estimación de costos operativos

| Item | Costo mensual |
|------|---------------|
| Telegram Bot API | **$0** |
| Claude Haiku (50 convs/día × 30 días × $0.002) | ~$3/mes |
| Servidor (ya existe) | $0 adicional |
| **Total adicional sobre infraestructura actual** | **~$3/mes** |

Comparado con WA donde cada conversación consume créditos de la suscripción MassivaMóvil, Telegram tiene costo marginal cero a nivel de canal.

---

## Limitaciones conocidas

1. **Sin outbound proactivo** — Telegram solo permite enviar mensajes si el usuario inició el bot primero (similar a la restricción de WA después de 24h, pero es permanente salvo que el usuario haya iniciado el chat)
2. **Adopción incierta** — padres venezolanos usan principalmente WA; Telegram requeriría promoción activa (QR en el colegio, link en la web, etc.)
3. **Telegram ID ≠ teléfono** — identificar al usuario requiere un flujo de registro explícito; no es automático como WA donde el número ES la identidad
4. **Media en Telegram** — los comprobantes de pago enviados por Telegram llegan como `photo` o `document`; hay que adaptar el handler de imágenes (actualmente solo procesa URLs de MassivaMóvil)

---

## Decisión recomendada

**Implementar Fase 1 + 2** como MVP. El esfuerzo es de 2-3 días de desarrollo y el costo operativo adicional es prácticamente cero. Permite:
- Reducir presión sobre créditos WA para consultas de baja prioridad
- Ofrecer un canal alternativo en el sitio web del colegio
- Probar la demanda real antes de invertir en Fase 3

**No reemplazar WA** — mantener ambos canales en paralelo. WA sigue siendo el canal primario para contacto proactivo y para la base de representantes existente.

---

## Pasos para arrancar (cuando se decida proceder)

1. `! @BotFather` en Telegram → `/newbot` → anotar token
2. Crear `ir.config_parameter` `ai_agent.telegram_bot_token` = `<token>`
3. Implementar las clases descritas en Fase 1
4. Configurar nginx: `location /ai-agent/telegram/` → proxy Odoo (ya existe el bloque `/ai-agent/`)
5. Llamar `set_webhook(f"{base_url}/ai-agent/telegram/webhook")` una vez
6. Probar con mensaje directo al bot
