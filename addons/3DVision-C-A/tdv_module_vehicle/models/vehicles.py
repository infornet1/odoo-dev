from odoo import models, fields

class Vehicle(models.Model):
    _name = 'vehicle'
    _description = 'MOdelo de Vehículo'

    name = fields.Char(string='Nombre')
    number_plate = fields.Char(string='Placa')
    color = fields.Char(string='Color')
    