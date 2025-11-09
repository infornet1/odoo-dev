# TDV POS Restrict Change

- Version: 17.0.1.0.0
- Author: 3DVision, C.A
- License: LGPL-3

## Descripción
Evita validar pagos en el Punto de Venta cuando existe cambio por devolver. Obliga a que el cambio sea exactamente 0, promoviendo buenas prácticas en caja.

## Dependencias
- point_of_sale
- tdv_multi_currency_pos_fixed

Este módulo es auto-instalable: si las dependencias están instaladas, se instala automáticamente.

## Uso
- Abra el POS y realice un cobro.
- Si los pagos superan el total (cambio > 0), se mostrará un mensaje y no permitirá validar la orden hasta ajustar los montos.

## Instalación
- Asegúrese de tener el directorio del módulo en la ruta de addons.
- Actualice la lista de aplicaciones y recargue los assets del POS.
