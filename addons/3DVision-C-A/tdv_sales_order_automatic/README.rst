

**TDV_SALES_ORDER_AUTOMATIC**

Automatización de entregas y facturación es una herramienta diseñada para simplificar y agilizar los procesos de gestión de pedidos, entregas y facturación en el sistema Odoo. Este addon permite automatizar varias tareas relacionadas con la confirmación de órdenes de venta, la validación de entregas y la generación de facturas, lo que reduce la carga de trabajo manual y mejora la eficiencia operativa de las empresas.

**Características Principales:**

- **Automatización de Confirmación de Órdenes de Venta**: El addon automatiza la confirmación de órdenes de venta según la configuración definida, lo que elimina la necesidad de intervención manual en este proceso.
- **Automatización de Validación de Entregas**: Permite la validación automática de entregas asociadas a las órdenes de venta, agilizando el proceso de envío de productos a los clientes.
- **Generación Automática de Facturas**: Facilita la generación automática de facturas basadas en la confirmación de entregas, lo que garantiza una facturación oportuna y precisa de los productos entregados.
- **Envío Automático de Facturas**: Además de la generación automática de facturas, el addon ofrece la posibilidad de enviar automáticamente las facturas a los clientes por correo electrónico, siempre que esté habilitada esta funcionalidad y se disponga de la dirección de correo electrónico del cliente.

**ResConfigSettings**

La clase **ResConfigSettings** hereda del modelo **res.config.settings** de Odoo y agrega campos booleanos a la página de configuración:

**Campos:**

- **is_create_invoice_delivery_validate** (boolean): Controla la creación y publicación automática de facturas al validar una entrega.
- **is_auto_send_invoice** (boolean): Habilita el envío automático de facturas al cliente al validar una entrega.
- **is_auto_confirm** (boolean): Habilita la confirmación automática de órdenes de venta.
- **is_auto_delivery** (boolean): Habilita la validación automática de órdenes de entrega.

Estos campos permiten automatizar los procesos de facturación y entrega en Odoo, lo que ahorra tiempo y reduce la carga de trabajo manual para los usuarios.

**SalesOrder**

Agrega funcionalidad para automatizar los procesos de confirmación de órdenes de venta, entrega y facturación.

**Métodos:**

- **action_confirm()**: Sobrescribe el método de confirmación de órdenes de venta para incluir la automatización de procesos.
  - Actualiza las cantidades entregadas para las líneas de servicio.
  - Verifica la configuración de auto confirmación y auto entrega desde los parámetros de configuración.
  - Valida automáticamente las entregas asociadas si la auto confirmación de entrega está habilitada.
  - Crea y publica las facturas si la auto confirmación está habilitada.
- **\_validate_confirmation_automatic()**: Valida automáticamente las entregas asociadas a la orden de venta.
- **set_service_product_qty_delivered()**: Actualiza la cantidad entregada para las líneas de servicio.
- **\_create_and_post_invoices()**: Crea y publica las facturas para la orden de venta.

Estos métodos permiten automatizar los procesos de confirmación de órdenes de venta, entrega y facturación en Odoo, reduciendo la intervención manual y mejorando la eficiencia operativa.

**StockPicking**

Sobrescribe el método **button_validate()** para automatizar la creación y envío de facturas al validar una entrega.

**Métodos:**

- **button_validate()**: Sobrescribe el método para validar la entrega y automatizar la creación y envío de facturas.
  - Verifica la configuración de auto validación de factura y auto envío de factura desde los parámetros de configuración.
  - Si la auto validación de factura está habilitada, verifica si algún producto tiene política de factura 'al entregar' o si no hay facturas asociadas a la orden de venta.
  - Llama a la función **\_create_invoices** en la venta asociada para crear la factura.
  - Publica la factura creada y, si el envío automático de facturas está habilitado y el cliente tiene una dirección de correo electrónico, envía la factura al cliente.

Este método automatiza la creación y envío de facturas al validar una entrega en Odoo, lo que simplifica el proceso de facturación y mejora la eficiencia operativa.
