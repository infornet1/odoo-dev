<h1>IGTF</h1>

<h4>Models</h4>

**account.journal**
Permite modificar y extender las funcionalidades del modelo account.journal 
is_igtf: Se define un campo booleano is_igtf. Este campo se etiqueta como "Is IGTF" en la interfaz de usuario

**account.move**
- amount_igtf es un campo monetario que representa el monto total de IGTF

*Método _get_igtf_amount_in_currency*
Este método calcula el monto total de IGTF en la moneda especificada. Utiliza los pagos conciliados (_get_reconciled_payments) asociados al movimiento contable para realizar la conversión de moneda y suma los montos de IGTF correspondientes.

*Método _compute_amount_igtf*
Este método es un decorador @api.depends que recalcula el campo amount_igtf cada vez que cambia amount_residual en un movimiento. Actualiza amount_igtf llamando a _get_igtf_amount_in_currency con la moneda de la compañía.

*Método _compute_tax_totals*
Este método calcula los totales de impuestos y agrega información específica sobre IGTF al widget de totales de impuestos (tax_totals). Calcula el monto total de IGTF en la moneda de la factura y actualiza el widget con estos detalles.

*Método _compute_payments_widget_reconciled_info*
Este método calcula la información de reconciliación para los widgets de pagos de facturas y agrega detalles de los movimientos de IGTF asociados a los pagos. Actualiza el widget de pagos de facturas con información detallada sobre los pagos de IGTF.

*Método action_register_payment*
Sobrescribe el método action_register_payment para actualizar el contexto con información adicional antes de registrar un pago. Calcula el monto residual en la moneda de la compañía y actualiza el contexto antes de devolver el resultado.

**account.payment**

-IGTF_TAX con valor 0.03, que representa el 3% de IGTF.
-is_igtf: Campo booleano que indica si el pago está asociado con IGTF.
-igtf_tax: Campo monetario calculado para el monto de IGTF (3%) basado en amount o igtf_tax_wizard.
-amount_igtf: Campo monetario calculado para el total del pago incluyendo IGTF.
-igtf_journal_id: Campo many2one para seleccionar el método de pago asociado con IGTF.

**Método _compute_igtf**
Método decorado con @api.depends que calcula igtf_tax y amount_igtf basado en si is_igtf es verdadero o falso. Si is_igtf es verdadero, calcula igtf_tax usando igtf_tax_wizard o el 3% de amount. Actualiza amount_igtf sumando amount y igtf_tax.

**Método action_post**
Sobrescribe el método action_post para realizar acciones adicionales después de contabilizar un pago.
Verifica si el pago está asociado con IGTF (is_igtf es verdadero) y si no pertenece a una sesión de punto de venta (pos_session_id no existe).
Verifica si la cuenta de IGTF está configurada para la compañía actual; de lo contrario, genera un error.
Crea un nuevo movimiento contable (account.move) para registrar el pago de IGTF utilizando la información del pago actual y la configuración de la cuenta de IGTF.
Actualiza el contexto con información adicional antes de devolver el resultado.

**res.company**

-igtf_account_id es un campo tipo Many2one que referencia al modelo account.account.

**res.config.setting**
-igtf_account_id es un campo tipo Many2one que está relacionado (related) con el campo igtf_account_id del modelo res.company.


