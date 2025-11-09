# -*- coding: utf-8 -*-

from odoo import models, fields, api


class FiscalPrinterModel(models.Model):
    _name = "x.pos.fiscal.printer"
    _description = "Impresora fiscal"

    name = fields.Char("Nombre")
    serial = fields.Char("Serial")
    serial_port = fields.Char("Puerto serial")
    usb_vendor_id = fields.Char("ID de fabricante USB")
    usb_product_id = fields.Char("ID de producto USB")
    # campo seleccion con los flags de la impresora fiscal, 00, 30
    flag_21 = fields.Selection(
        [('00', '00'), ('30', '30')], string="Flag 21", default='00')
    flag_50 = fields.Char("Flag 50", default='00')
    flag_63 = fields.Char("Flag 63", default='00')

    # seleccion de conexion, serial, usb, api
    connection_type = fields.Selection([('serial', 'Serial'), ('usb', 'USB'), ('usb_serial', 'USB Serial'), (
        'file', 'Archivo'), ('api', 'API')], string="Tipo de conexión", default='usb_serial', required=True)

    # url de la api
    api_url = fields.Char("URL de la API")

    display_current_z_report = fields.Char(
        "Z report", compute='_compute_current_z_report', inverse='_inverse_current_z_report', default="00000000", store=True)
    current_z_report = fields.Integer("Z report actual", default=1)
    last_invoice_number = fields.Char("Último número de factura", default=0)
    last_cn_invoice_number = fields.Char(
        "Último número de factura de crédito", default=0)

    printer_error = fields.Char("Error de la impresora", default='No error')
    company_id = fields.Many2one(
        "res.company", string="Empresa", default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency", string="Moneda para imprimir", default=lambda self: self.env.company.currency_id)

    credit_payment_method = fields.Selection([
        ('01', '01'),
        ('02', '02'),
        ('03', '03'),
        ('04', '04'),
        ('05', '05'),
        ('06', '06'),
        ('07', '07'),
        ('08', '08'),
        ('09', '09'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
    ], string="Método de pago de crédito", default='01')

    @api.depends('current_z_report')
    def _compute_current_z_report(self):
        """
        Compute the current Z report number, ensuring it is stored in the required 8-digit format.
        """
        for record in self:
            record.display_current_z_report = str(
                record.current_z_report).zfill(8)

    def _inverse_current_z_report(self):
        """
        Inverse the current Z report number, ensuring it is stored in the required 8-digit format.
        """
        for record in self:
            record.display_current_z_report = str(
                record.display_current_z_report).zfill(8)
            record.current_z_report = int(record.display_current_z_report)

    def test_printer(self):
        """Test the printer connection"""
        # This method will be called by the button
        # The actual logic is handled by JavaScript
        return {
            'type': 'ir.actions.client',
            'tag': 'fiscal_printer_test',
            'params': {
                'printer_id': self.id,
                'serial_port': self.serial_port,
                'connection_type': self.connection_type,
                'usb_vendor_id': self.usb_vendor_id,
                'usb_product_id': self.usb_product_id,
            }
        }

    def print_x_report(self):
        """Connect to the printer"""
        # This method will be called by the button
        # The actual logic is handled by JavaScript
        return {
            'type': 'ir.actions.client',
            'tag': 'fiscal_printer_connect',
            'params': {
                'printer_id': self.id,
                'serial_port': self.serial_port,
                'connection_type': self.connection_type,
                'api_url': self.api_url,
                'usb_vendor_id': self.usb_vendor_id,
                'usb_product_id': self.usb_product_id,
                'report_type': 'x',
            }
        }

    def print_z_report(self):
        """Connect to the printer"""
        # This method will be called by the button
        # The actual logic is handled by JavaScript
        return {
            'type': 'ir.actions.client',
            'tag': 'fiscal_printer_connect',
            'params': {
                'printer_id': self.id,
                'serial_port': self.serial_port,
                'connection_type': self.connection_type,
                'api_url': self.api_url,
                'usb_vendor_id': self.usb_vendor_id,
                'usb_product_id': self.usb_product_id,
                'report_type': 'z',
            }
        }
