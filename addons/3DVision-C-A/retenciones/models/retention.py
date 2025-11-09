from odoo import models, api, fields, _
from odoo.exceptions import UserError
import re


STATES = [("draft", "Draft"), ("posted", "Posted"), ("cancel", "Cancel")]
TYPES = [("iva", "IVA"), ("islr", "ISLR"), ("iae", "IAE")]
IAE_TYPES = [("S", "Service"), ("C", "Purchase")]
PARTNER_TYPES = [("customer", "Customer"), ("vendor", "Vendor")]


class Retention(models.Model):
    _name = "retention"
    _description = "Retentions"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

#============================ DEFAULT FUNCTIONS ================================
    def _default_period(self):
        return fields.date.today().strftime("%Y%m")

    def _default_currency(self):
        currency_id = self.env.ref("base.VEF")
        return (
            currency_id if currency_id.active else self.env.company.currency_id
        )

#============================ BASIC FIELDS =====================================
    name = fields.Char("Name", default="", store=True)
    period = fields.Char("Period", default=_default_period)
    correlative = fields.Char("Correlative")
    date = fields.Date("Date", default=fields.Date.today(), required=True)
    type = fields.Selection(TYPES, "Type", required=True, default="iva")
    partner_type = fields.Selection(
        PARTNER_TYPES,
        string="Tipo de Retención",
        required=True,
        default="vendor"
    )
    state = fields.Selection(STATES, "State", default="draft", required=True)
    current = fields.Boolean("Current", default=True)
    amount_total = fields.Monetary(
        string="Total Detained",
        compute="_compute_amount_total",
        store=True
    )
    is_legal_entity = fields.Boolean(
        related='partner_id.is_legal_entity',
        readonly=False
    )

#============================ RELATED FIELDS ===================================
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True
    )
    debit_account_id = fields.Many2one("account.account", "Debit Account")
    credit_account_id = fields.Many2one("account.account", "Credit Account")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain="[('type','=','general')]"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=_default_currency,
        required=True
    )
    journal_currency = fields.Many2one(
        comodel_name="res.currency",
        string="Journal Currency",
        related="journal_id.currency_id"
    )
    line_ids = fields.One2many(
        comodel_name="retention.line",
        inverse_name="retention_id",
        string="Retention Lines",
        store=True
    )
    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        compute="_compute_invoice_ids"
    )
    signature = fields.Image(
        string="Signature",
        default=lambda self: self.env.company.retention_signature
    )

    has_journal_entries = fields.Boolean(compute="_compute_has_journal_entries")

    has_journal_entries = fields.Boolean(compute="_compute_has_journal_entries")

    def _compute_display_name(self):
        for retention in self:
            if retention.name:
                retention.display_name = retention.name
            else:
                retention.display_name = _(
                    "%s Retention Draft %s" % (retention.type.upper(), retention.period
                ))

    @api.onchange("date", "type")
    def onchange_date_or_type(self):
        self.period = self.date.strftime("%Y%m")

        
        if self.partner_type == 'vendor':
            SEARCH_DOMAIN = [
                ("type", "=", self.type),
                ("partner_type", "=", self.partner_type),
                ("company_id", "=", self.company_id.id),
                ("state", "!=", "cancel"),
                ("correlative", "!=", False),
            ]

            correlatives = (self.env['retention'].search(SEARCH_DOMAIN) - self) \
                .mapped(
                    lambda r: int(
                        r.correlative[6:] if len(
                            r.correlative or "") == 14 else "0"
                    )
            )

            if correlatives:
                self.correlative = self.period + \
                    str(max(correlatives) + 1).zfill(8)
            else:
                self.correlative = self.period + "1".zfill(8)
        else:
            
            self.correlative = ""

    @api.onchange("currency_id", "date")
    def onchange_currency(self):
        for retention in self:
            retention.line_ids.mapped(
                lambda l: l.onchange_invoice_or_currency())

    @api.depends("line_ids.amount_detained", "type")
    def _compute_amount_total(self):
        for retention in self:
            retention.amount_total = sum(
                retention.mapped("line_ids.amount_detained")
            )

    @api.depends("line_ids")
    def _compute_invoice_ids(self):
        for retention in self:
            retention.invoice_ids = retention.line_ids.invoice_id

    def _validate_to_confirm(self):
        if self.partner_type == 'customer' and not self.correlative:
            raise UserError(_("El campo Correlativo es obligatorio para la retencion. Por favor, ingréselo."))
        moves = self.line_ids.mapped("invoice_id")
        for move in moves:
            retention_moves = (
                self.env["retention.line"]
                .search(
                    [
                        ("id", "not in", self.line_ids.ids),
                        ("type", "=", self.type),
                    ]
                )
                .mapped("move_id")
            )

            try:
                assert all(
                    [bool(line.ret_tax_id) for line in self.line_ids]
                ), _("The Retention Tax is required in all lines")
                assert self.journal_id, _(
                    "The journal is required to post the entry"
                )
                assert move not in retention_moves, _(
                    "The bill %s has already been a retention" % move.name
                )

                if self.type == "iae":
                    assert all(self.line_ids.mapped("iae_type")), _(
                        "The Transaction is required to IAE retentions"
                    )
                elif self.type == "iva":
                    assert all(self.line_ids.mapped("registry_type")), _(
                        "The registry type is required to IVA retentions"
                    )

                for reversal_move in move.reversal_move_id:
                    assert reversal_move not in retention_moves, _(
                        "The Credit Note %s must be in the retention"
                        % reversal_move.name
                    )

            except Exception as e:
                raise UserError(_(str(e)))

            return True

    def button_confirm(self):
        self._validate_to_confirm()

        if not self.name:
            self.name = self.env["ir.sequence"].next_by_code(self.type)

        self.line_ids.mapped(lambda l: l._create_account_move())
        self.state = "posted"
        self.current = False

    @api.model
    def _validate_retentions_to_print(self, retentions):
        try:
            assert len(set(retentions.mapped("type"))) == 1, _(
                "Too many retention types"
            )
            for retention in retentions:
                assert (
                    retention.company_id.vat
                    or retention.company_id.company_registry
                ), _("Missing company ID in %s" % retention.name)
                assert (
                    retention.partner_id.vat or retention.partner_id.ced_rif
                ), _("Missing partner ID in %s" % retention.name)

                if retention.type == "iae":
                    assert retention.company_id.ruc, _(
                        "The RUC of the company is missing in %s"
                        % retention.name
                    )
                    assert retention.partner_id.ruc, _(
                        "The provider's RUC is missing in %s" % retention.name
                    )
                    assert retention.company_id.taxpayer_license, _(
                        "The LAE of the company is missing in %s"
                        % retention.name
                    )
                    assert retention.partner_id.taxpayer_license, _(
                        "The provider's IAE is missing in %s" % retention.name
                    )

                for line in retention.line_ids:
                    move = line.invoice_id
                    # Para proveedores
                    if move.move_type in ['in_invoice', 'in_refund'] and getattr(move, 'fiscal_check', False):
                        assert line.control_number, _("Falta el número de control en la factura %s" % move.name)
                        assert line.invoice_ref, _("Falta el correlativo fiscal en la factura %s" % move.name)
                    # Para clientes
                    if move.move_type in ['out_invoice', 'out_refund'] and getattr(move, 'fiscal_check', False):
                        assert line.control_number, _("Falta el número de control en la factura %s" % move.name)
                        assert line.invoice_ref, _("Falta el correlativo fiscal en la factura %s" % move.name)

                    if retention.type == "iae":
                        assert line.iae_type, _(
                            "Missing transaction type on invoice %s"
                            % line.invoice_id.name
                        )

        except Exception as e:
            raise UserError(str(e))

    def print_retention(self):
        self._validate_retentions_to_print(self)
        report = "retenciones.action_report_retention"
        return self.env.ref(report).report_action(self)

    def print_text_retention(self):
        self._validate_retentions_to_print(self)
        ret_types = set(self.mapped("type")).pop()
        return self.env.ref(
            f"retenciones.action_report_text_{ret_types}_retention"
        ).report_action(self)

    # def print_text_retention(self):
    #     self._validate_retentions_to_print(retentions=self, validate_type=True)

    #     if (ret_types == "islr" and len(set(self.mapped(lambda r: r.period[:6]))) > 1):
    #         raise UserError(_("Too many Periods for print"))


    def button_open_journal_entry(self):
        self.ensure_one()
        res = {}
        domain = [("id", "in", self.line_ids.move_id.mapped("id"))]
        move_ids = self.line_ids.mapped("move_id")

        if move_ids:
            res.update(
                {
                    "name": _("Journal Entry"),
                    "type": "ir.actions.act_window",
                    "res_model": "account.move",
                    "context": {"create": False},
                    "view_mode": "tree,form",
                    "domain": domain,
                }
            )
        return res

    def get_retention_text_lines(self):
        return "\n".join(self.line_ids.mapped(lambda l: l.get_text_info())) + "\n"

    def button_draft(self):
        self.line_ids.mapped(lambda l: l._draft_move())
        self.state = "draft"
        self.current = True

    def button_cancel(self):
        self.line_ids.mapped(lambda l: l._cancel_move())
        self.state = "cancel"

    @api.model
    def sanitize_string(self, string):
        return re.sub(r"[-_.,#\\]", "", string)

    @api.constrains("correlative")
    def _constrains_correlative(self):
        for retention in self:
            try:
                if retention.correlative:
                    assert (
                        len(retention.correlative) == 14
                    ), "The length of the correlative must be 14 characters"
                    assert (
                        retention.correlative.isdigit()
                    ), "The correlative must be a number"
            except Exception as e:
                raise UserError(str(e))

    @api.onchange("partner_type")
    def _onchange_partner_type(self):
        self.partner_id = False
        return {
            'domain': {
                'partner_id': [
                    ('customer_rank' if self.partner_type == 'customer' else 'supplier_rank', '>', 0)
                ]
            }
        }

    @api.model
    def create_or_add_to_retention(self, partner_type, retention_kind, period, invoice):
        retention = self.env['retention'].search([
            ('type', '=', partner_type),
            ('partner_type', '=', retention_kind),
            ('period', '=', period),
            ('state', '=', 'draft'),
        ], limit=1)
        if not retention:
            retention = self.create({
                'type': partner_type,
                'partner_type': retention_kind,
                'period': period,
                'date': fields.Date.today(),
                'state': 'draft',
            })
        # Verifica si la factura ya está asociada
        if not self.env['retention.line'].search([('retention_id', '=', retention.id), ('invoice_id', '=', invoice.id)]):
            self.env['retention.line'].create({
                'retention_id': retention.id,
                'invoice_id': invoice.id,
            })
        return retention


    @api.depends("line_ids")
    def _compute_has_journal_entries(self):
        for retention in self:
            retention.has_journal_entries = any(retention.line_ids.mapped("move_id"))