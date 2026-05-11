import re
from odoo import models, fields, api

BONUS_MIN_CONVERSATIONS = 3
BONUS_MIN_FEEDBACK = 1


class HrNoticeAcknowledgmentCalibration(models.Model):
    _inherit = 'hr.notice.acknowledgment'

    calibration_conversation_count = fields.Integer(
        'Conversaciones de Prueba', compute='_compute_calibration_stats', store=False)
    calibration_feedback_count = fields.Integer(
        'Sugerencias Enviadas', compute='_compute_calibration_stats', store=False)
    bonus_eligible = fields.Boolean(
        'Elegible para Bono', compute='_compute_calibration_stats', store=False)

    @api.depends('wa_number', 'notice_key')
    def _compute_calibration_stats(self):
        Feedback = self.env['ai.agent.feedback'].sudo()
        Conversation = self.env['ai.agent.conversation'].sudo()

        for rec in self:
            if rec.notice_key != 'glenda_calibracion_v1' or not rec.wa_number:
                rec.calibration_conversation_count = 0
                rec.calibration_feedback_count = 0
                rec.bonus_eligible = False
                continue

            digits = re.sub(r'\D', '', rec.wa_number)
            # Match conversations by phone digits
            all_convs = Conversation.search([
                ('skill_id.code', '=', 'general_inquiry'),
            ])
            conv_count = sum(
                1 for c in all_convs
                if re.sub(r'\D', '', c.phone or '') == digits
            )
            fb_count = Feedback.search_count([
                ('wa_number', '!=', False),
                ('employee_id', '=', rec.employee_id.id),
            ]) if rec.employee_id else Feedback.search_count([
                ('wa_number', '!=', False),
            ])
            # More precise: filter by digits client-side
            all_fb = Feedback.search([('employee_id', '=', rec.employee_id.id)]) if rec.employee_id else Feedback.browse()
            fb_count = len(all_fb)

            rec.calibration_conversation_count = conv_count
            rec.calibration_feedback_count = fb_count
            rec.bonus_eligible = (
                conv_count >= BONUS_MIN_CONVERSATIONS and
                fb_count >= BONUS_MIN_FEEDBACK
            )
