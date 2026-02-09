from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StartConversationWizard(models.TransientModel):
    _name = 'ai.agent.start.conversation.wizard'
    _description = 'Start AI Agent Conversation'

    skill_id = fields.Many2one('ai.agent.skill', required=True, string='Skill')
    partner_id = fields.Many2one('res.partner', required=True, string='Contacto')
    phone = fields.Char('Telefono WhatsApp', required=True)
    source_model = fields.Char('Modelo Origen')
    source_id = fields.Integer('ID Origen')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.phone = self.partner_id.mobile or self.partner_id.phone or ''

    def action_start(self):
        """Create conversation and send greeting."""
        self.ensure_one()

        if not self.phone:
            raise UserError(_("Debe indicar un numero de telefono WhatsApp."))

        # Normalize phone
        wa_service = self.env['ai.agent.whatsapp.service']
        normalized_phone = wa_service._normalize_phone(self.phone)

        # Check for existing active conversation
        existing = self.env['ai.agent.conversation'].search([
            ('partner_id', '=', self.partner_id.id),
            ('skill_id', '=', self.skill_id.id),
            ('state', 'in', ('draft', 'active', 'waiting')),
        ], limit=1)
        if existing:
            raise UserError(_(
                "Ya existe una conversacion activa para este contacto y skill (%s). "
                "Cierre o resuelva la conversacion existente primero."
            ) % existing.name)

        # Create conversation
        conversation = self.env['ai.agent.conversation'].create({
            'skill_id': self.skill_id.id,
            'partner_id': self.partner_id.id,
            'phone': normalized_phone,
            'source_model': self.source_model or '',
            'source_id': self.source_id or 0,
        })

        # Link to source record if it's a bounce log
        if self.source_model == 'mail.bounce.log' and self.source_id:
            bounce_log = self.env['mail.bounce.log'].browse(self.source_id)
            if bounce_log.exists():
                bounce_log.write({
                    'ai_conversation_id': conversation.id,
                    'whatsapp_contacted': True,
                    'whatsapp_contact_date': fields.Datetime.now(),
                })

        # Start the conversation (send greeting)
        conversation.action_start()

        # Return action to view the conversation
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conversacion AI',
            'res_model': 'ai.agent.conversation',
            'res_id': conversation.id,
            'view_mode': 'form',
            'target': 'current',
        }
