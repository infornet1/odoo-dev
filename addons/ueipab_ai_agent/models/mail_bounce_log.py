from odoo import models, fields


class MailBounceLog(models.Model):
    _inherit = 'mail.bounce.log'

    ai_conversation_id = fields.Many2one(
        'ai.agent.conversation', string='Conversacion AI', readonly=True)
    ai_conversation_state = fields.Selection(
        related='ai_conversation_id.state', string='Estado Conversacion', readonly=True)

    def action_start_whatsapp(self):
        """Open the Start Conversation wizard pre-filled for this bounce log."""
        self.ensure_one()
        skill = self.env['ai.agent.skill'].search([('code', '=', 'bounce_resolution')], limit=1)
        phone = ''
        if self.partner_id:
            phone = self.partner_id.mobile or self.partner_id.phone or ''

        return {
            'type': 'ir.actions.act_window',
            'name': 'Iniciar Conversacion WhatsApp',
            'res_model': 'ai.agent.start.conversation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_skill_id': skill.id if skill else False,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
                'default_phone': phone,
                'default_source_model': 'mail.bounce.log',
                'default_source_id': self.id,
            },
        }
