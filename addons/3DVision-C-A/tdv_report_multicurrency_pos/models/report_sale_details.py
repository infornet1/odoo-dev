from odoo import models,fields
import math

"""
Este modelo se hereda para solucionar el error del doble moneda en el
reporte de la sesion del pos
"""

class ReportSaleDetailsInherit(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        # Ejecutar metodo original primero
        res = super(ReportSaleDetailsInherit, self).get_sale_details(date_start, date_stop, config_ids, session_ids)
        
        # Obtener la compañia y las monedas
        company = self.env.company
        primary_currency = company.currency_id
        second_currency = company.second_currency_id

        # Calcular la tasa de conversión
        conversion_rate = 1.0
        if second_currency:

            report_date = res['date_start'].date() if res.get('date_start') else fields.Date.today()
            conversion_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=primary_currency,
                to_currency=second_currency,
                company=company,
                date=report_date,
            )
            print("Tasa de conversión: %s", conversion_rate)
        else:
            print("No se ha configurado una segunda moneda.")

        # Obtener la lista de payments
        payments = res.get('payments', [])
        session_name = res.get('session_name', False)


        for payment in payments:
            # Inicializar campos necesarios con valores por defecto
            payment.setdefault('money_counted', 0.0)
            payment.setdefault('final_count', 0.0)
            payment.setdefault('money_difference', 0.0)
            
            # Formatear el texto del nombre del pago
            ultimo_espacio = payment["name"].rfind(" ")

            if ultimo_espacio != -1:
                if not session_name:
                    session_name = payment["name"][ultimo_espacio + 1:]
                    print("LA SESSION NAME ES: ",session_name)
                
                payment["name"] = payment["name"][:ultimo_espacio]
                
            # Verificar si tiene journal_id
            if 'journal_id' not in payment or not payment['journal_id']:
                continue
        
            journal = self.env['account.journal'].browse(payment['journal_id'])
            
            # Obtener pagos POS
            pos_payments = self.env['pos.payment'].search([
                ('session_id', '=', payment['session']),
                ('payment_method_id', '=', payment['id']),
            ])

            # Sumar amount_full_precision
            amount_full_precision = sum(pos_payments.mapped('amount_full_precision'))
            payment['amount_full_precision'] = amount_full_precision

            # Solo procesar si no es efectivo o es efectivo en Bs
            if not payment.get('cash', False) or payment.get('name') == 'EFECTIVO Bs':
                # Buscar asiento contable
                ref_value_english = "Closing difference in %s (%s)" % (payment["name"], session_name)
                ref_value_spanish = "Diferencia de cierre en %s (%s)" % (payment["name"], session_name)
                
                account_move = self.env['account.move'].search([
                    ('ref', 'in', [ref_value_english, ref_value_spanish])
                ], limit=1)


                print("---------------------ENTRANDO EN EL IF---------------------")
                print("ref_value_english: ", ref_value_english)
                print("ref_value_spanish: ", ref_value_spanish)
                print("Asiento encontrado: ", account_move)
                # print("Session name: ", session_name)
                print(payment)

# Reseteo de session_name para evitar errores en futuras iteraciones
                session_name = False

                if account_move:
                    print("---------------------ENTRANDO EN ACCOUNT MOVE 1---------------------")
                    # Procesar con asiento contable encontrado
                    payment_method = self.env['pos.payment.method'].browse(payment['id'])
                    
                    is_loss = any(l.account_id == payment_method.journal_id.loss_account_id 
                                for l in account_move.line_ids)
                    is_profit = any(l.account_id == payment_method.journal_id.profit_account_id 
                                  for l in account_move.line_ids)
                    
                    # Establecer valores base
                    payment['final_count'] = payment.get('total', 0.0)
                    payment['money_difference'] = -account_move.amount_total if is_loss else account_move.amount_total
                    payment['money_counted'] = payment['final_count'] + payment['money_difference']
                    
                    # Conversión a Bolívares si es necesario
                    if journal.currency_id and journal.currency_id.name == 'VEF':
                        payment['convert_rate'] = True
                        payment['final_count'] = round(payment['final_count'] * conversion_rate, 2)
                        payment['money_difference'] = round(payment['money_difference'] * conversion_rate, 2)
                        payment['money_counted'] = round(payment['money_counted'] * conversion_rate, 2)
                    
                    # Configurar movimientos de caja
                    payment['cash_moves'] = []
                    if is_profit:
                        move_name = 'Difference observed during the counting (Profit)'
                        payment['cash_moves'].append({'name': move_name, 'amount': payment['money_difference']})
                    elif is_loss:
                        move_name = 'Difference observed during the counting (Loss)'
                        payment['cash_moves'].append({'name': move_name, 'amount': payment['money_difference']})
                    
                    payment['count'] = True
                    
                else:
                    # Procesar sin asiento contable
                    if journal.currency_id and journal.currency_id.name == 'VEF':
                        payment['total_copy'] = payment.get('amount_full_precision', 0.0)
                        payment['final_count'] = round(payment['total_copy'] * conversion_rate, 2)
                        payment['money_counted'] = payment['final_count']
                        payment['convert_rate'] = True
                        
                    else:
                        payment['final_count'] = payment.get('amount_full_precision', 0.0)
                        payment['money_counted'] = payment['final_count']
                        payment['convert_rate'] = False
                    # Calcular diferencia después de establecer todos los valores
                    payment['money_difference'] = payment['final_count'] - payment['money_counted']

                    # Para manejar la diferencia de caja
                    if not math.isclose(payment['money_difference'], 0.0, abs_tol=1e-10):
                        print("Existe una diferencia, aplicar diferencia de caja: ", payment['money_difference'])
                        payment['cash_moves'] = []
                        if payment['money_difference'] < 0:
                            print(payment['money_difference'])
                            move_name = 'Difference observed during the counting (Loss)'
                            payment['cash_moves'].append({'name': move_name, 'amount': payment['money_difference']})
                        else:
                            move_name = 'Difference observed during the counting (Profit)'
                            payment['cash_moves'].append({'name': move_name, 'amount': payment['money_difference']})
                    else:
                        if payment.get('cash_moves'):
                            print("Eliminar porque la diferencia es 0")
                            del payment['cash_moves']
                    
                        print("No hay diferencia, todo está correcto.")

                    payment['count']= True
                    res['sessions_group'] = list(set(payment['session'] for payment in res['payments']))
                    res['rate'] = conversion_rate

                    print("El payment pos-procesado: ",payment)


        # Filtrar cualquier payment que se llame "Efectivo" (ignorando mayúsculas/minúsculas)
        res["payments"] = [p for p in res["payments"] if p["name"].lower() != "efectivo"]

        print(res)
        res['currency']['symbol'] = ''
            
        return res


########################### Version anterior (contiene el error con el reporte X)

# class ReportSaleDetailsInherit(models.AbstractModel):
#     _inherit = "report.point_of_sale.report_saledetails"

#     def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
#         # Ejecutar metodo original primero / almacenar todos los datos en res
#         res = super(ReportSaleDetailsInherit, self).get_sale_details(date_start, date_stop, config_ids, session_ids)
#         # Obtener la compañia y las monedas
#         company = self.env.company
#         primary_currency = self.env.company.currency_id
#         second_currency = self.env.company.second_currency_id

#         # Calcular la tasa de conversión
#         if second_currency:
#             conversion_rate = self.env['res.currency']._get_conversion_rate(
#                 from_currency=primary_currency,
#                 to_currency=second_currency,
#                 company=company,
#                 date=fields.Date.today(),
#             )
#             print("Tasa de conversión de la segunda moneda:", conversion_rate)
#         else:
#             conversion_rate = None
#             print("No se ha configurado una segunda moneda.")

    
#         # Obtener la lista de payments y el valor de la session
#         payments = res.get('payments', [])
#         session_name = res.get('session_name', False)
        
#         for payment in payments:
#             # Formatear el texto
#             ultimo_espacio = payment["name"].rfind(" ")
#             payment["name"] = payment["name"][:ultimo_espacio]

#             # Obtener el texto moneda (USD o VEF) del diario
#             if 'journal_id' not in payment or not payment['journal_id']:
#                 continue
        
#             journal = self.env['account.journal'].browse(payment['journal_id'])

#             pos_payments = self.env['pos.payment'].search([
#                 ('session_id', '=', payment['session']),
#                 ('payment_method_id', '=', payment['id']),
#             ])

#             # Sumar el campo amount_full_precision de todos los pagos encontrados
#             amount_full_precision = sum(pos_payments.mapped('amount_full_precision'))

#             # Agregar el campo al diccionario de payment
#             payment['amount_full_precision'] = amount_full_precision


#             print("\n\n",payment,"\n\n")

#             if not payment.get('cash', False) or payment.get('name') == 'EFECTIVO Bs':  # Verificar si 'cash' es False
#                 # Busqueda de asiento en ingles
#                 ref_value = "Closing difference in %s (%s)" % (payment["name"],session_name)
#                 account_move = self.env['account.move'].search([("ref", "=", ref_value)], limit=1)

#                 if account_move:
#                     print("English")
#                 else:
#                     # Busqueda de asiento en español
#                     print("Spanish")
#                     ref_value = "Diferencia de cierre en %s (%s)" % (payment["name"],session_name)
#                     account_move = self.env['account.move'].search([("ref", "=", ref_value)], limit=1)

#                     journal = self.env['account.journal'].browse(payment['journal_id'])

#                     # Si es bolivares
#                     if not account_move and journal.currency_id.name == 'VEF':
#                         print("ENTRO EN EL IF DE VEF")

#                     # Obtener el monto total con decimales con desde el modelo pos.payment
#                         payment['total'] = payment['amount_full_precision']
#                         payment['final_count'] = payment['total'] * conversion_rate
                      
            
#                     else:
#                         print("ENTRO EN EL IF DE USD")
#                         payment['final_count'] = payment['amount_full_precision']
                    
#                     payment['money_difference'] = payment['final_count'] - payment['money_counted']

#                     print("Con el payment formateado: ",payment)

                    
#                     # Si es dolares     
#                     if account_move:

#                         payment_method = self.env['pos.payment.method'].browse(payment['id'])
#                         is_loss = any(l.account_id == payment_method.journal_id.loss_account_id for l in account_move.line_ids)
#                         is_profit = any(l.account_id == payment_method.journal_id.profit_account_id for l in account_move.line_ids)
                        
#                         # Obtener los montos en Dolares
#                         payment['final_count'] = payment['total']
#                         payment['money_difference'] = -account_move.amount_total if is_loss else account_move.amount_total
#                         payment['money_counted'] = payment['final_count'] + payment['money_difference']
                        
#                         # Conversion a Bolivares
#                         if journal.currency_id.name == 'VEF':
#                             payment['final_count'] = round((payment['final_count'] * conversion_rate),2)  
#                             payment['money_difference'] = round((payment['money_difference'] * conversion_rate),2) 
#                             payment['money_counted'] = round((payment['money_counted'] * conversion_rate),2)
                       
#                         payment['cash_moves'] = []
#                         if is_profit:
#                             move_name = 'Difference observed during the counting (Profit)'
#                             payment['cash_moves'] = [{'name': move_name, 'amount': payment['money_difference']}]
#                         elif is_loss:
#                             move_name = 'Difference observed during the counting (Loss)'
#                             payment['cash_moves'] = [{'name': move_name, 'amount': payment['money_difference']}]
#                         payment['count'] = True

#         res['currency']['symbol'] = ''
#         print(res)
#         return res
