# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class FiscalPrinterController(http.Controller):

    @http.route('/fiscal_printer/test_connection', type='json', auth='user')
    def test_connection(self, printer_id, data):
        """
        Test the connection to the fiscal printer
        """
        print(f"Testing connection to printer {printer_id} with data {data}")
        try:
            # Get the printer record
            printer = request.env['x.pos.fiscal.printer'].browse(printer_id)
            if not printer.exists():
                return {'success': False, 'error': 'Impresora no encontrada'}
            else:
                print(f"Printer {printer.name} found")

                # Update printer data
                update_data = {}
                if 'connection_type' in data:
                    update_data['connection_type'] = data['connection_type']
                if 'usb_vendor_id' in data:
                    update_data['usb_vendor_id'] = data['usb_vendor_id']
                if 'usb_product_id' in data:
                    update_data['usb_product_id'] = data['usb_product_id']
                if 'flag_21' in data:
                    update_data['flag_21'] = data['flag_21']
                if 'flag_50' in data:
                    update_data['flag_50'] = data['flag_50']
                if 'flag_63' in data:
                    update_data['flag_63'] = data['flag_63']
                if 'current_z_report' in data:
                    update_data['current_z_report'] = int(
                        data['current_z_report'])
                if 'num_factura' in data:
                    update_data['last_invoice_number'] = data['num_factura']
                if 'num_factura_cn' in data:
                    update_data['last_cn_invoice_number'] = data['num_factura_cn']

                # Add registration number if available
                if data.get('registration_number'):
                    update_data['serial'] = data['registration_number']
                    print(
                        f"Registration number: {data['registration_number']}")

                printer.write(update_data)

            # Simulate connection test
            # In a real implementation, you would:
            # 1. Open the serial port
            # 2. Send a test command
            # 3. Check for response
            # 4. Close the connection

            message = f'Conexión exitosa a {printer.name}'
            if data.get('registration_number'):
                message += f' - Número de Registro: {data["registration_number"]}'

            return {
                'success': True,
                'message': message,
                'printer_info': {
                    'name': printer.name,
                    'serial': printer.serial,
                    'registration_number': data.get('registration_number'),
                }
            }

        except Exception as e:
            _logger.error(f"Error testing printer connection: {str(e)}")
            return {
                'success': False,
                'error': f'Error al probar conexión: {str(e)}'
            }

    @http.route('/fiscal_printer/connect', type='json', auth='user')
    def connect_printer(self, printer_id, serial_port, connection_type, api_url=None):
        """
        Connect to the fiscal printer
        """
        try:
            # Get the printer record
            printer = request.env['x.pos.fiscal.printer'].browse(printer_id)
            if not printer.exists():
                return {'success': False, 'error': 'Impresora no encontrada'}

            # Here you would implement the actual printer connection
            # For now, we'll simulate a successful connection
            _logger.info(
                f"Connecting to printer {printer.name} on port {serial_port}")

            # Simulate connection process
            # In a real implementation, you would:
            # 1. Open the serial port
            # 2. Initialize the printer
            # 3. Set up communication parameters
            # 4. Verify printer status

            # Update printer status (you might want to add a status field to your model)
            # printer.write({'status': 'connected'})

            return {
                'success': True,
                'message': f'Impresora {printer.name} conectada exitosamente',
                'printer_info': {
                    'name': printer.name,
                    'serial': printer.serial,
                    'port': serial_port,
                    'type': connection_type,
                    'api_url': api_url
                }
            }

        except Exception as e:
            _logger.error(f"Error connecting to printer: {str(e)}")
            return {
                'success': False,
                'error': f'Error al conectar impresora: {str(e)}'
            }

    @http.route('/fiscal_printer/print_receipt', type='json', auth='user')
    def print_receipt(self, printer_id, receipt_data):
        """
        Print a receipt on the fiscal printer
        """
        try:
            # Get the printer record
            printer = request.env['x.pos.fiscal.printer'].browse(printer_id)
            if not printer.exists():
                return {'success': False, 'error': 'Impresora no encontrada'}

            # Here you would implement the actual receipt printing
            # For now, we'll simulate printing
            _logger.info(f"Printing receipt on printer {printer.name}")

            # Simulate printing process
            # In a real implementation, you would:
            # 1. Format the receipt data
            # 2. Send commands to the printer
            # 3. Handle printer responses
            # 4. Log the transaction

            return {
                'success': True,
                'message': 'Recibo impreso exitosamente',
                'transaction_id': 'TXN_' + str(int(request.env['ir.sequence'].next_by_code('fiscal.printer.transaction')))
            }

        except Exception as e:
            _logger.error(f"Error printing receipt: {str(e)}")
            return {
                'success': False,
                'error': f'Error al imprimir recibo: {str(e)}'
            }
