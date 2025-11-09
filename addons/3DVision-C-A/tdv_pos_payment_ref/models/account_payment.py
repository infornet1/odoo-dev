from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def create(self, vals_list):
        """Override to store POS payment reference"""
        payments = super().create(vals_list)
        
        # Buscar referencias de POS en el contexto
        pos_payment_refs = self.env.context.get('pos_payment_references', {})
        # print(f"DEBUG: pos_payment_references en contexto: {pos_payment_refs}")
        
        # Solo procesar si hay referencias en el contexto Y hay payments
        if pos_payment_refs and payments:
            # Si solo hay una referencia en el contexto, es porque viene de _create_split_account_payment
            # y esa referencia es específica para este payment
            if len(pos_payment_refs) == 1:
                pos_payment_id, ref = list(pos_payment_refs.items())[0]
                for payment in payments:
                    if payment.ref and 'POS payment' in payment.ref:
                        # print(f"DEBUG: Asignando referencia específica {ref} (pos_payment_id: {pos_payment_id})")
                        payment.ref = f"{payment.ref} - {ref}"
                        # print(f"DEBUG: Payment ref actualizado: {payment.ref}")
            else:
                # Si hay múltiples referencias, usar el método de asignación secuencial
                ref_list = []
                for pos_payment_id, ref in pos_payment_refs.items():
                    ref_list.append((pos_payment_id, ref))
                
                # Ordenar por ID para mantener el orden
                ref_list.sort(key=lambda x: x[0])
                # print(f"DEBUG: Referencias ordenadas: {ref_list}")
                
                ref_index = 0
                for payment in payments:
                    # Solo procesar payments que vengan del POS y que tengan referencias disponibles
                    if payment.ref and 'POS payment' in payment.ref and ref_index < len(ref_list):
                        pos_payment_id, ref = ref_list[ref_index]
                        # print(f"DEBUG: Asignando referencia {ref} (pos_payment_id: {pos_payment_id}) al payment {ref_index + 1}")
                        payment.ref = f"{payment.ref} - {ref}"
                        # print(f"DEBUG: Payment ref actualizado: {payment.ref}")
                        ref_index += 1
                    elif payment.ref and 'POS payment' in payment.ref:
                        print(f"DEBUG: Payment sin referencia asignada (no hay más referencias disponibles)")
        else:
            print(f"DEBUG: No hay referencias en el contexto o no hay payments - contexto vacío: {not pos_payment_refs}")
            
        return payments

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, **kwargs):
        """Override to include reference in memo field of accounting entries"""
        res = super()._prepare_move_line_default_vals(write_off_line_vals, **kwargs)
        
        #print(f"DEBUG: Payment ref en _prepare_move_line_default_vals: {self.ref}")
        
        # Buscar si este payment tiene una referencia de POS
        pos_payment_ref = None
        if self.ref and '-' in self.ref:
            # Extraer la referencia después del último guión
            pos_payment_ref = self.ref.split(' - ')[-1]
            # print(f"DEBUG: Referencia extraída: {pos_payment_ref}")
        
        if pos_payment_ref:
            # print(f"DEBUG: Agregando referencia al memo: {pos_payment_ref}")
            # Agregar la referencia al memo de todas las líneas del asiento
            for line in res:
                if line.get('name'):
                    # print(f"DEBUG: Memo antes: {line['name']}")
                    line['name'] = f"{line['name']} - {pos_payment_ref}"
                    # print(f"DEBUG: Memo después: {line['name']}")
                else:
                    line['name'] = pos_payment_ref
                    # print(f"DEBUG: Memo nuevo: {line['name']}")
        else:
            print("DEBUG: No se encontró referencia de POS")
                    
        return res
