from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = 'pos.config'

    restrict_partner_by_tag = fields.Boolean(
        string='Restrict Partners by Tag',
        help='Allows limiting visible partners in POS based on selected tags.'
    )
    allowed_partner_tag_ids = fields.Many2many(
        'res.partner.category',
        'pos_config_partner_category_rel',
        'pos_config_id',
        'category_id',
        string='Allowed Partner Tags',
        help='Only partners with these tags will be available in the POS.'
    )

    # Field to store the ID of the POS_CLIENTE tag
    pos_client_category_id = fields.Many2one(
        'res.partner.category',
        compute='_compute_pos_client_category_id',
        string='POS Client Category',
        store=False,
    )

    @api.depends('company_id')
    def _compute_pos_client_category_id(self):
        # Search for the 'POS_CLIENTE' tag
        category = self.env['res.partner.category'].search([('name', '=', 'POS_CLIENTE')], limit=1)
        for config in self:
            config.pos_client_category_id = category.id if category else False

    def _pos_ui_models_to_load(self):
        models = super()._pos_ui_models_to_load()
        if 'res.partner' not in models:
            models.append('res.partner')
        return models

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['context'] = self._get_pos_ui_partner_context()
        return result

    def _get_pos_ui_partner_context(self):
        self.ensure_one()
        context = self.env.context.copy()
        if self.restrict_partner_by_tag and self.allowed_partner_tag_ids:
            context['pos_restrict_partner_by_tag'] = True
            context['pos_allowed_partner_tag_ids'] = self.allowed_partner_tag_ids.ids
        return context

    # Ensure this field is loaded in the frontend
    @api.model
    def _get_pos_ui_pos_config(self, params):
        configs = super()._get_pos_ui_pos_config(params)
        pos_client_category = self.env['res.partner.category'].search([('name', '=', 'POS_CLIENTE')], limit=1)
        pos_client_category_id = pos_client_category.id if pos_client_category else False

        # Add the tag ID to each config dictionary
        for config in configs:
             config['pos_client_category_id'] = pos_client_category_id

        return configs

    def get_limited_partners_loading(self):
        domain = [
            '|',
                ('company_id', '=', self.company_id.id),
                ('company_id', '=', False)
        ]
        if self.restrict_partner_by_tag and self.allowed_partner_tag_ids:
            domain.append(('category_id', 'in', self.allowed_partner_tag_ids.ids))
        partners = self.env['res.partner'].search(domain, limit=100)
        return [(p.id,) for p in partners]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        # Call the original create method first to create the partner
        partner = super().create(vals)

        # Tag assignment is handled in frontend JS

        return partner

    @api.model
    def _pos_ui_search_domain(self, config):
        domain = super()._pos_ui_search_domain(config)
        if config.restrict_partner_by_tag and config.allowed_partner_tag_ids:
            domain += [('category_id', 'in', config.allowed_partner_tag_ids.ids)]
        return domain 