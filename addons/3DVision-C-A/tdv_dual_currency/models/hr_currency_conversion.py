import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class HrContract(models.Model):
    _inherit = 'hr.contract'

    wage_in_ves = fields.Monetary(
        string='Salario en moneda secundaria',
        compute='_compute_wage_in_ves',
        inverse='_inverse_wage_in_ves',
        store=True,
        readonly=False, # Permitir edición cuando enable_secondary_currency es True
        currency_field='conversion_currency_id'
    )
    
    conversion_currency_id = fields.Many2one(
        'res.currency', 
        related='company_id.currency_conversion_id',
        readonly=True,
        store=True # Necesario para que el related funcione correctamente en depends
    )
    
    enable_secondary_currency = fields.Boolean(
        string='Editar salario en moneda secundaria',
        default=False
    )

    @api.depends('wage', 'company_id.currency_id', 'company_id.currency_conversion_id', 'enable_secondary_currency')
    def _compute_wage_in_ves(self):
        """
        Calcula wage_in_ves basado en wage SOLO cuando enable_secondary_currency es False.
        Si enable_secondary_currency es True, wage_in_ves es editable y este compute no debe sobrescribirlo.
        """
        today = fields.Date.today()
        for contract in self:
            if not contract.enable_secondary_currency:
                # Modo edición en moneda principal: Calcular secundaria
                company = contract.company_id
                currency_from = company.currency_id
                currency_to = company.currency_conversion_id
                
                if currency_from and currency_to and currency_from != currency_to:
                    contract.wage_in_ves = currency_from._convert(
                        contract.wage or 0.0,
                        currency_to,
                        company,
                        today
                    )
                elif currency_from == currency_to:
                    contract.wage_in_ves = contract.wage or 0.0
                else:
                    # No se puede convertir si faltan monedas
                    contract.wage_in_ves = 0.0 
            # Si enable_secondary_currency es True, el valor es el ingresado o el calculado por el inverse/onchange

    @api.depends('wage_in_ves', 'company_id.currency_id', 'company_id.currency_conversion_id', 'enable_secondary_currency')
    def _inverse_wage_in_ves(self):
        """
        Calcula wage basado en wage_in_ves SOLO cuando enable_secondary_currency es True.
        Este método se llama cuando wage_in_ves es modificado (o cuando enable_secondary_currency cambia y activa el recompute).
        """
        today = fields.Date.today()
        for contract in self:
            if contract.enable_secondary_currency:
                # Modo edición en moneda secundaria: Calcular principal
                company = contract.company_id
                currency_from = company.currency_conversion_id
                currency_to = company.currency_id

                if currency_from and currency_to and currency_from != currency_to:
                    contract.wage = currency_from._convert(
                        contract.wage_in_ves or 0.0,
                        currency_to,
                        company,
                        today
                    )
                elif currency_from == currency_to:
                     contract.wage = contract.wage_in_ves or 0.0
                else:
                    # No se puede convertir si faltan monedas
                    contract.wage = 0.0
            # Si enable_secondary_currency es False, wage es el valor principal y no debe ser sobreescrito por este inverse

    @api.onchange('enable_secondary_currency')
    def _onchange_enable_secondary_currency(self):
        """
        Actualiza visualmente el campo no editable cuando se cambia el modo de edición.
        No afecta a la persistencia, solo a la interfaz.
        """
        _logger.info("=== ONCHANGE enable_secondary_currency START ===")
        _logger.info(f"Onchange triggered. enable_secondary_currency: {self.enable_secondary_currency}, wage: {self.wage}, wage_in_ves: {self.wage_in_ves}")

        # Si faltan datos clave, no hacer nada
        if not self.company_id or not self.company_id.currency_id or not self.company_id.currency_conversion_id:
            return
            
        today = fields.Date.today()
        company = self.company_id
        currency_main = company.currency_id
        currency_secondary = company.currency_conversion_id

        # No convertir si las monedas son las mismas
        if currency_main == currency_secondary:
            if self.enable_secondary_currency:
                self.wage = self.wage_in_ves or 0.0
            else:
                self.wage_in_ves = self.wage or 0.0
            return

        if self.enable_secondary_currency:
            # Se acaba de activar: Calcular wage desde wage_in_ves
            new_wage = currency_secondary._convert(
                self.wage_in_ves or 0.0,
                currency_main,
                company,
                today
            )
            _logger.info(f"Onchange calculated new wage: {new_wage}")
            self.wage = new_wage
        else:
            # Se acaba de desactivar: Calcular wage_in_ves desde wage
            new_wage_in_ves = currency_main._convert(
                self.wage or 0.0,
                currency_secondary,
                company,
                today
            )
            _logger.info(f"Onchange calculated new wage_in_ves: {new_wage_in_ves}")
            self.wage_in_ves = new_wage_in_ves
        _logger.info(f"Onchange finished. wage: {self.wage}, wage_in_ves: {self.wage_in_ves}")
        _logger.info("=== ONCHANGE enable_secondary_currency END ===")

    @api.onchange('wage', 'wage_in_ves')
    def _onchange_wage_fields(self):
        """
        Maneja la actualización automática del campo complementario cuando
        se modifica wage o wage_in_ves, dependiendo del modo activo.
        """
        _logger.info("=== ONCHANGE wage/wage_in_ves START ===")
        _logger.info(f"Onchange wage/wage_in_ves triggered. enable_secondary_currency: {self.enable_secondary_currency}")
        _logger.info(f"Current values - wage: {self.wage}, wage_in_ves: {self.wage_in_ves}")

        if not self.company_id or not self.company_id.currency_id or not self.company_id.currency_conversion_id:
            return

        today = fields.Date.today()
        company = self.company_id
        currency_main = company.currency_id
        currency_secondary = company.currency_conversion_id

        # No convertir si las monedas son las mismas
        if currency_main == currency_secondary:
            if self.enable_secondary_currency:
                self.wage = self.wage_in_ves or 0.0
            else:
                self.wage_in_ves = self.wage or 0.0
            return

        try:
            if not self.enable_secondary_currency:
                # Modo edición principal: actualizar wage_in_ves
                if self.wage:
                    new_wage_in_ves = currency_main._convert(
                        self.wage,
                        currency_secondary,
                        company,
                        today
                    )
                    _logger.info(f"Calculated new wage_in_ves: {new_wage_in_ves}")
                    self.wage_in_ves = new_wage_in_ves
            else:
                # Modo edición secundaria: actualizar wage
                if self.wage_in_ves:
                    new_wage = currency_secondary._convert(
                        self.wage_in_ves,
                        currency_main,
                        company,
                        today
                    )
                    _logger.info(f"Calculated new wage: {new_wage}")
                    self.wage = new_wage

        except Exception as e:
            _logger.error(f"Error en conversión de moneda: {str(e)}")

        _logger.info(f"Final values - wage: {self.wage}, wage_in_ves: {self.wage_in_ves}")
        _logger.info("=== ONCHANGE wage/wage_in_ves END ===")

    def write(self, vals):
        """ Sobrescribir write para asegurar el cálculo correcto de wage antes de guardar
            cuando se edita en moneda secundaria.
        """
        today = fields.Date.today()
        # Iterar sobre los contratos que se están guardando
        for contract in self:
            # Determinar el estado final de enable_secondary_currency
            enable_secondary = vals.get('enable_secondary_currency', contract.enable_secondary_currency)
            
            if enable_secondary:
                # Si se está en modo edición secundaria, calcular wage desde wage_in_ves
                company = contract.company_id
                currency_from = company.currency_conversion_id
                currency_to = company.currency_id
                
                # Usar el valor de wage_in_ves que se está guardando, o el actual si no cambia
                wage_in_ves_val = vals.get('wage_in_ves', contract.wage_in_ves)
                
                calculated_wage = 0.0
                if currency_from and currency_to and currency_from != currency_to:
                    calculated_wage = currency_from._convert(
                        wage_in_ves_val or 0.0,
                        currency_to,
                        company,
                        today
                    )
                elif currency_from == currency_to:
                     calculated_wage = wage_in_ves_val or 0.0
                
                _logger.info(f"WRITE: enable_secondary=True. Calculated wage: {calculated_wage}. Vals before: {vals}")
                # Forzar la actualización de wage si estamos en modo secundario
                vals['wage'] = calculated_wage
                _logger.info(f"WRITE: Vals after forcing wage: {vals}")
                    
        return super(HrContract, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """ Sobrescribir create para asegurar el cálculo correcto de wage antes de crear
            cuando se edita en moneda secundaria.
        """
        today = fields.Date.today()
        # Obtener la compañía por defecto o del contexto si es necesario
        # Esto puede necesitar ajuste dependiendo de cómo se llame al create
        company_id = self.env.company.id 

        for vals in vals_list:
            enable_secondary = vals.get('enable_secondary_currency', False)
            
            if enable_secondary:
                # Intentar obtener la compañía de los valores, o usar la por defecto
                current_company_id = vals.get('company_id', company_id)
                company = self.env['res.company'].browse(current_company_id)
                
                currency_from = company.currency_conversion_id
                currency_to = company.currency_id
                wage_in_ves_val = vals.get('wage_in_ves', 0.0)
                
                calculated_wage = 0.0
                if currency_from and currency_to and currency_from != currency_to:
                    calculated_wage = currency_from._convert(
                        wage_in_ves_val or 0.0,
                        currency_to,
                        company,
                        today
                    )
                elif currency_from == currency_to:
                    calculated_wage = wage_in_ves_val or 0.0
                
                _logger.info(f"CREATE: enable_secondary=True. Calculated wage: {calculated_wage}. Vals before: {vals}")
                # Forzar el valor de wage en vals
                vals['wage'] = calculated_wage
                _logger.info(f"CREATE: Vals after forcing wage: {vals}")
                
        return super(HrContract, self).create(vals_list)