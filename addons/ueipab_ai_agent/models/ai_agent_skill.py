from odoo import models, fields, api


class AiAgentSkill(models.Model):
    _name = 'ai.agent.skill'
    _description = 'AI Agent Skill'
    _order = 'name'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Codigo', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text('Descripcion')

    # AI Configuration
    system_prompt = fields.Text('Prompt del Sistema', required=True)
    model_name = fields.Char('Modelo AI', default='claude-haiku-4-5-20251001')
    max_turns = fields.Integer('Max Turnos', default=5)
    timeout_hours = fields.Integer('Timeout (horas)', default=48)

    # WhatsApp template
    greeting_template = fields.Text('Plantilla Saludo Inicial')

    # Link to source model
    source_model = fields.Char('Modelo Origen')

    # Stats
    conversation_count = fields.Integer('Conversaciones', compute='_compute_stats')
    resolved_count = fields.Integer('Resueltas', compute='_compute_stats')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El codigo del skill debe ser unico.'),
    ]

    @api.depends_context('lang')
    def _compute_stats(self):
        for skill in self:
            conversations = self.env['ai.agent.conversation'].search([
                ('skill_id', '=', skill.id),
            ])
            skill.conversation_count = len(conversations)
            skill.resolved_count = len(conversations.filtered(lambda c: c.state == 'resolved'))
