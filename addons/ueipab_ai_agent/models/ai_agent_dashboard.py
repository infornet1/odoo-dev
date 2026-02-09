import logging
import re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AiAgentDashboard(models.TransientModel):
    _name = 'ai.agent.dashboard'
    _description = 'AI Agent - Panel de Control'

    # ── Estado General ──────────────────────────────────────────────
    dry_run = fields.Boolean('Modo Prueba', default=True)
    active_db = fields.Char('Entorno Activo')
    credits_ok = fields.Boolean('Creditos OK', readonly=True)

    # ── Creditos y Consumo ──────────────────────────────────────────
    wa_remaining_sends = fields.Integer('WA Envios Restantes', readonly=True, default=-1)
    wa_total_sends = fields.Integer('WA Limite Envios', readonly=True, default=-1)
    wa_sends_threshold = fields.Integer('WA Umbral Alerta', default=50)

    claude_total_spend = fields.Float('Claude Gasto USD', readonly=True, digits=(10, 4))
    claude_spend_limit_usd = fields.Float('Claude Limite USD', digits=(10, 2), default=4.50)
    claude_total_input_tokens = fields.Integer('Tokens Entrada', readonly=True)
    claude_total_output_tokens = fields.Integer('Tokens Salida', readonly=True)
    claude_input_rate = fields.Float('Tasa Input ($/token)', digits=(10, 6), default=0.000001)
    claude_output_rate = fields.Float('Tasa Output ($/token)', digits=(10, 6), default=0.000005)

    # ── Tareas Programadas ──────────────────────────────────────────
    cron_poll_active = fields.Boolean('Poll WhatsApp Activo')
    cron_poll_nextcall = fields.Datetime('Poll Proxima Ejecucion', readonly=True)
    cron_timeout_active = fields.Boolean('Timeouts Activo')
    cron_timeout_nextcall = fields.Datetime('Timeouts Proxima Ejecucion', readonly=True)
    cron_credits_active = fields.Boolean('Credit Guard Activo')
    cron_credits_nextcall = fields.Datetime('Credit Guard Proxima Ejecucion', readonly=True)

    # ── Horario de Contacto ─────────────────────────────────────────
    schedule_weekday_start = fields.Char('Lun-Vie Inicio', default='06:30')
    schedule_weekday_end = fields.Char('Lun-Vie Fin', default='20:30')
    schedule_weekend_start = fields.Char('Sab-Dom Inicio', default='09:30')
    schedule_weekend_end = fields.Char('Sab-Dom Fin', default='19:00')

    # ── Cuenta WhatsApp ─────────────────────────────────────────────
    whatsapp_active_account = fields.Selection([
        ('primary', 'Primaria'),
        ('backup', 'Respaldo'),
    ], string='Cuenta Activa', readonly=True)
    whatsapp_primary_phone = fields.Char('Telefono Primario', readonly=True)
    whatsapp_backup_phone = fields.Char('Telefono Respaldo', readonly=True)
    whatsapp_flagged_phone = fields.Char('Numero Afectado', readonly=True)
    whatsapp_flagged_date = fields.Char('Fecha Desvinculacion', readonly=True)

    # ── Identidad del Agente ────────────────────────────────────────
    agent_display_name = fields.Char('Nombre del Agente', default='Asistente Virtual')
    institution_display_name = fields.Char('Nombre Institucion', default='UEIPAB')
    whatsapp_send_interval = fields.Integer('Anti-spam (seg)', default=120)

    # ── Estadisticas ────────────────────────────────────────────────
    active_conversations_count = fields.Integer('Conversaciones Activas', readonly=True)
    pending_bounce_count = fields.Integer('Bounces Pendientes', readonly=True)
    total_messages_sent = fields.Integer('Mensajes Enviados', readonly=True)

    # ── Param key mapping ───────────────────────────────────────────
    _PARAM_MAP = {
        'dry_run': ('ai_agent.dry_run', 'bool'),
        'active_db': ('ai_agent.active_db', 'str'),
        'whatsapp_send_interval': ('ai_agent.whatsapp_send_interval', 'int'),
        'wa_sends_threshold': ('ai_agent.wa_sends_threshold', 'int'),
        'claude_spend_limit_usd': ('ai_agent.claude_spend_limit_usd', 'float'),
        'claude_input_rate': ('ai_agent.claude_input_rate', 'float'),
        'claude_output_rate': ('ai_agent.claude_output_rate', 'float'),
        'schedule_weekday_start': ('ai_agent.schedule_weekday_start', 'str'),
        'schedule_weekday_end': ('ai_agent.schedule_weekday_end', 'str'),
        'schedule_weekend_start': ('ai_agent.schedule_weekend_start', 'str'),
        'schedule_weekend_end': ('ai_agent.schedule_weekend_end', 'str'),
        'agent_display_name': ('ai_agent.agent_display_name', 'str'),
        'institution_display_name': ('ai_agent.institution_display_name', 'str'),
    }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()

        # ── Load editable params ────────────────────────────────────
        for field_name, (param_key, param_type) in self._PARAM_MAP.items():
            if field_name not in fields_list:
                continue
            raw = ICP.get_param(param_key, False)
            if raw is False:
                continue
            if param_type == 'bool':
                res[field_name] = str(raw).lower() == 'true'
            elif param_type == 'int':
                try:
                    res[field_name] = int(raw)
                except (ValueError, TypeError):
                    pass
            elif param_type == 'float':
                try:
                    res[field_name] = float(raw)
                except (ValueError, TypeError):
                    pass
            else:
                res[field_name] = str(raw)

        # ── Read-only status ────────────────────────────────────────
        if 'credits_ok' in fields_list:
            res['credits_ok'] = ICP.get_param(
                'ai_agent.credits_ok', 'True'
            ).lower() == 'true'

        # ── WhatsApp account status ────────────────────────────────
        if 'whatsapp_active_account' in fields_list:
            active = ICP.get_param('ai_agent.whatsapp_active_account', 'primary')
            res['whatsapp_active_account'] = active if active in ('primary', 'backup') else 'primary'
        if 'whatsapp_primary_phone' in fields_list:
            res['whatsapp_primary_phone'] = ICP.get_param('ai_agent.whatsapp_primary_phone', '')
        if 'whatsapp_backup_phone' in fields_list:
            res['whatsapp_backup_phone'] = ICP.get_param('ai_agent.whatsapp_backup_phone', '')
        if 'whatsapp_flagged_phone' in fields_list:
            res['whatsapp_flagged_phone'] = ICP.get_param('ai_agent.whatsapp_flagged_phone', '')
        if 'whatsapp_flagged_date' in fields_list:
            res['whatsapp_flagged_date'] = ICP.get_param('ai_agent.whatsapp_flagged_date', '')

        # ── Cron controls ───────────────────────────────────────────
        cron_map = {
            'cron_poll': 'ueipab_ai_agent.ir_cron_poll_whatsapp_messages',
            'cron_timeout': 'ueipab_ai_agent.ir_cron_check_conversation_timeouts',
            'cron_credits': 'ueipab_ai_agent.ir_cron_check_credits',
        }
        for prefix, xml_id in cron_map.items():
            active_field = f'{prefix}_active'
            next_field = f'{prefix}_nextcall'
            try:
                cron = self.env.ref(xml_id, raise_if_not_found=False)
                if cron:
                    if active_field in fields_list:
                        res[active_field] = cron.active
                    if next_field in fields_list:
                        res[next_field] = cron.nextcall
            except Exception:
                pass

        # ── Live stats ──────────────────────────────────────────────
        if 'claude_total_spend' in fields_list or 'claude_total_input_tokens' in fields_list:
            input_rate = float(ICP.get_param('ai_agent.claude_input_rate', '0.000001'))
            output_rate = float(ICP.get_param('ai_agent.claude_output_rate', '0.000005'))
            self.env.cr.execute("""
                SELECT COALESCE(SUM(ai_input_tokens), 0),
                       COALESCE(SUM(ai_output_tokens), 0)
                FROM ai_agent_message
                WHERE ai_input_tokens > 0 OR ai_output_tokens > 0
            """)
            total_in, total_out = self.env.cr.fetchone()
            res['claude_total_input_tokens'] = total_in
            res['claude_total_output_tokens'] = total_out
            res['claude_total_spend'] = (total_in * input_rate) + (total_out * output_rate)

        if 'active_conversations_count' in fields_list:
            res['active_conversations_count'] = self.env['ai.agent.conversation'].search_count([
                ('state', 'in', ('active', 'waiting')),
            ])

        if 'pending_bounce_count' in fields_list:
            res['pending_bounce_count'] = self.env['mail.bounce.log'].search_count([
                ('state', '!=', 'resolved'),
            ])

        if 'total_messages_sent' in fields_list:
            res['total_messages_sent'] = self.env['ai.agent.message'].search_count([
                ('direction', '=', 'outbound'),
            ])

        return res

    def action_apply(self):
        """Save editable fields back to ir.config_parameter and cron states."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()

        # ── Write params ────────────────────────────────────────────
        for field_name, (param_key, param_type) in self._PARAM_MAP.items():
            value = getattr(self, field_name)
            if param_type == 'bool':
                ICP.set_param(param_key, str(value))
            elif param_type in ('int', 'float'):
                ICP.set_param(param_key, str(value))
            else:
                ICP.set_param(param_key, value or '')

        # ── Write cron active states ────────────────────────────────
        cron_map = {
            'cron_poll_active': 'ueipab_ai_agent.ir_cron_poll_whatsapp_messages',
            'cron_timeout_active': 'ueipab_ai_agent.ir_cron_check_conversation_timeouts',
            'cron_credits_active': 'ueipab_ai_agent.ir_cron_check_credits',
        }
        for field_name, xml_id in cron_map.items():
            try:
                cron = self.env.ref(xml_id, raise_if_not_found=False)
                if cron:
                    cron.sudo().write({'active': getattr(self, field_name)})
            except Exception as e:
                _logger.error("Failed to update cron %s: %s", xml_id, e)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Configuracion Guardada"),
                'message': _("Los parametros del AI Agent se han actualizado correctamente."),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_check_credits(self):
        """On-demand credit check: calls MassivaMóvil API + recalculates Claude spend."""
        self.ensure_one()

        # ── WhatsApp subscription check ─────────────────────────────
        wa_remaining = -1
        wa_total = -1
        wa_error = False
        try:
            wa_service = self.env['ai.agent.whatsapp.service']
            config = wa_service._get_config()
            url = config['base_url'].rstrip('/') + '/get/subscription'
            resp = requests.get(url, params={'secret': config['secret']}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get('data', {})
            usage = data.get('usage', {}).get('wa_send', {})
            used = int(usage.get('used', 0))
            limit_val = int(usage.get('limit', 0))
            wa_remaining = limit_val - used
            wa_total = limit_val
        except Exception as e:
            wa_error = True
            _logger.error("Dashboard credit check — WhatsApp API error: %s", e)

        # ── Claude spend recalculation ──────────────────────────────
        ICP = self.env['ir.config_parameter'].sudo()
        input_rate = float(ICP.get_param('ai_agent.claude_input_rate', '0.000001'))
        output_rate = float(ICP.get_param('ai_agent.claude_output_rate', '0.000005'))
        self.env.cr.execute("""
            SELECT COALESCE(SUM(ai_input_tokens), 0),
                   COALESCE(SUM(ai_output_tokens), 0)
            FROM ai_agent_message
            WHERE ai_input_tokens > 0 OR ai_output_tokens > 0
        """)
        total_in, total_out = self.env.cr.fetchone()
        spend = (total_in * input_rate) + (total_out * output_rate)

        self.write({
            'wa_remaining_sends': wa_remaining,
            'wa_total_sends': wa_total,
            'claude_total_spend': spend,
            'claude_total_input_tokens': total_in,
            'claude_total_output_tokens': total_out,
        })

        if wa_error:
            msg = _("Error al consultar WhatsApp API. Claude: $%.4f USD") % spend
            notif_type = 'warning'
        else:
            msg = _("WhatsApp: %d/%d envios restantes. Claude: $%.4f USD") % (
                wa_remaining, wa_total, spend)
            notif_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Creditos Verificados"),
                'message': msg,
                'type': notif_type,
                'sticky': False,
            },
        }

    def action_switch_whatsapp_account(self):
        """Manually switch active WhatsApp account between primary and backup."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        current = ICP.get_param('ai_agent.whatsapp_active_account', 'primary')
        target = 'backup' if current == 'primary' else 'primary'

        # Read target phone + unique_id from params
        target_phone = ICP.get_param(f'ai_agent.whatsapp_{target}_phone', '')
        target_unique = ICP.get_param(f'ai_agent.whatsapp_{target}_unique_id', '')

        if not target_phone or not target_unique:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': _("No se encontro la configuracion de la cuenta %s. "
                                 "Ejecute el Health Monitor primero.") % target,
                    'type': 'danger',
                    'sticky': False,
                },
            }

        ICP.set_param('ai_agent.whatsapp_account_id', target_unique)
        ICP.set_param('ai_agent.whatsapp_account_phone', target_phone)
        ICP.set_param('ai_agent.whatsapp_active_account', target)

        _logger.info("Manual WA account switch: %s → %s (%s)", current, target, target_phone)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Cuenta WhatsApp Cambiada"),
                'message': _("Cuenta activa: %s (%s)") % (target.upper(), target_phone),
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_refresh(self):
        """Reload the dashboard form with fresh data."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ai.agent.dashboard',
            'view_mode': 'form',
            'target': 'inline',
            'flags': {'mode': 'edit'},
        }

    @api.constrains('schedule_weekday_start', 'schedule_weekday_end',
                     'schedule_weekend_start', 'schedule_weekend_end')
    def _check_schedule_format(self):
        pattern = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
        for rec in self:
            for fname in ('schedule_weekday_start', 'schedule_weekday_end',
                          'schedule_weekend_start', 'schedule_weekend_end'):
                val = getattr(rec, fname)
                if val and not pattern.match(val):
                    raise ValidationError(
                        _("El campo '%s' debe tener formato HH:MM (ej: 06:30). Valor: %s")
                        % (fname, val)
                    )
