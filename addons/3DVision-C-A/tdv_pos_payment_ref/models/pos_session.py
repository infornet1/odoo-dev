from odoo import models, fields, api

class PosSession(models.Model):
  _inherit = 'pos.session'

  def _loader_params_pos_payment_method(self):
    res = super()._loader_params_pos_payment_method()
    if res.get("search_params") and res["search_params"].get("fields"):
      res["search_params"]["fields"].append("is_ref_payment")
    return res

  def _create_bank_payment_moves(self, data):
    """Override to pass POS payment references in context"""
    # print(f"DEBUG: _create_bank_payment_moves llamado con data: {data}")
    
    # Obtener solo las referencias de la orden actual que se está procesando
    current_order_id = data.get('order_id')
    # print(f"DEBUG: current_order_id: {current_order_id}")
    
    if not current_order_id:
      # print("DEBUG: No hay order_id en data, usando método alternativo")
      # Si no hay order_id, buscar en todas las órdenes de la sesión
      pos_payment_refs = {}
      for order in self.order_ids:
        for payment in order.payment_ids:
          if payment.reference and payment.payment_method_id.is_ref_payment:
            pos_payment_refs[payment.id] = payment.reference
      
      # print(f"DEBUG: Referencias de todas las órdenes: {pos_payment_refs}")
      
      if pos_payment_refs:
        self = self.with_context(pos_payment_references=pos_payment_refs)
      
      return super()._create_bank_payment_moves(data)
    
    # Buscar la orden actual
    current_order = self.env['pos.order'].browse(current_order_id)
    if not current_order.exists():
      # print(f"DEBUG: Orden {current_order_id} no existe")
      return super()._create_bank_payment_moves(data)
    
    # Obtener solo las referencias de esta orden específica
    pos_payment_refs = {}
    for payment in current_order.payment_ids:
      # print(f"DEBUG: Payment {payment.id}: reference={payment.reference}, is_ref_payment={payment.payment_method_id.is_ref_payment}")
      if payment.reference and payment.payment_method_id.is_ref_payment:
        pos_payment_refs[payment.id] = payment.reference
    
    # print(f"DEBUG: Referencias de orden {current_order_id}: {pos_payment_refs}")
    
    # Pasar las referencias en el contexto
    if pos_payment_refs:
      self = self.with_context(pos_payment_references=pos_payment_refs)
    
    return super()._create_bank_payment_moves(data)

  def _create_split_account_payment(self, payment, amounts):
    """Override to pass POS payment reference in context"""
    # print(f"DEBUG: _create_split_account_payment llamado para payment {payment.id}")
    # print(f"DEBUG: Payment reference: {payment.reference}, is_ref_payment: {payment.payment_method_id.is_ref_payment}")
    
    # Buscar la referencia de este payment específico
    pos_payment_refs = {}
    if payment.reference and payment.payment_method_id.is_ref_payment:
      pos_payment_refs[payment.id] = payment.reference
      # print(f"DEBUG: Referencia encontrada para payment {payment.id}: {payment.reference}")
      # Pasar la referencia en el contexto SOLO si este payment tiene referencia
      self = self.with_context(pos_payment_references=pos_payment_refs)
    else:
      # print(f"DEBUG: Payment {payment.id} NO tiene referencia o no requiere referencia")
      # Limpiar el contexto para asegurar que no se use referencias de otros payments
      self = self.with_context(pos_payment_references={})
    
    return super()._create_split_account_payment(payment, amounts)

