# TDV POS Currency Price List

## Descripción

Este addon permite controlar los métodos de pago en divisa del POS basándose en las listas de precios configuradas. Cuando se usa una lista de precio específica, el sistema bloquea manualmente los métodos de pago y fuerza el uso de un popup especial para distribuir el monto total entre los métodos de pago en divisa.

## Funcionalidades

- **Control por Lista de Precio**: Solo se activa cuando se usa una lista de precio configurada
- **Bloqueo de Métodos de Pago**: Los métodos de pago especiales se bloquean visualmente
- **Popup de Distribución**: Permite distribuir el monto total entre los métodos de pago en divisa
- **Validación en Tiempo Real**: Verifica que la suma distribuida sea igual al total de la orden

## Configuración

### 1. Habilitar la Funcionalidad

En la configuración del POS, ir a la pestaña "Control de Divisa por Lista de Precio" y marcar la casilla "Habilitar Control por Lista de Precio".

### 2. Configurar Listas de Precio

Seleccionar las listas de precio que habilitarán el control de divisa. Solo cuando se use una de estas listas se activará la funcionalidad.

### 3. Configurar Métodos de Pago

Seleccionar los métodos de pago que aparecerán en el popup de divisa. Estos métodos se bloquearán manualmente y solo se podrán usar a través del popup.

## Uso

1. **Configurar el POS** con las listas de precio y métodos de pago deseados
2. **Usar una lista de precio configurada** en el POS
3. **Ir a la pantalla de pago** - se mostrará la nota y el botón azul
4. **Hacer clic en "Métodos de Pago en Divisa"** para abrir el popup
5. **Distribuir el monto total** entre los métodos de pago disponibles
6. **Confirmar** la distribución

## Archivos Principales

- `models/pos_config.py`: Extensión del modelo de configuración del POS
- `views/pos_config_view.xml`: Vista para configurar las opciones
- `static/src/js/Popups/DivisaPaymentMethodsPopup.js`: Lógica del popup
- `static/src/xml/divisa_payment_methods_popup.xml`: Template del popup
- `static/src/js/patch_payment_screen.js`: Parche de la pantalla de pago
- `static/src/xml/patch_payment_screen.xml`: Template del parche
- `static/src/js/models.js`: Extensiones del modelo POS

## Dependencias

- `point_of_sale`
- `tdv_multi_currency_pos_fixed`

## Versión

17.0.0.0

## Autor

3DVision C.A.
