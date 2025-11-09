<h1>tdv_sales_book</h1>

Este módulo permite registrar, gestional las facturas de venta de acuerdo con las normativas fiscales locales. 

## Models

**sales_book_line:** Gestiona las lineas del libro de venta fiscal. Cada linea representa una factura y contiene toda la informacion necesaria para el cumpliento de las normativas fiscales
Este módelo se encarga de Relacionar cada línea con una factura especifica. Ademas de calcular y almacenar los totales de impuestos, tanto gravados como exentos.
Asegurarse de que todas las lineas tengan una fecha de factura válida.

**sales_book:** Gestiona el libro de ventas, registrando y reportando las facturas de venta conforme a las normativas fiscales.
Este módelo se encarga de calcular y almacenar los totales no gravados, exentos, de impuestos y totales de las facturas.Agrupar los totales de impuestos diferenciando entre entidades naturales y jurídicas.
Asegura que las fechas de inicio y fin estén presentes y sean válidas para el registro.

## Report

**sales_book_report:** Reporte en formato XLSX para el libro de ventas. El cual hereda de report.report_xlsx.abstract y utiliza diversos estilos y formatos para estructurar el informe. Incluye la configuración inicial, la escritura de encabezados, la población de datos de las líneas del libro de ventas y un resumen al final.
![sales_book excel](https://github.com/3D-Vision-C-A/tdv_sales_book/assets/96964600/35af5db4-3f4f-4823-9a51-0181224bbb7c)

*Acción de reporte para generar un libro de ventas en formato XLSX*
![sales_book report](https://github.com/3D-Vision-C-A/tdv_sales_book/assets/96964600/57e1616d-2e9d-4edf-8f8b-c1473328ee9c)


*Gestionar el Libro de Ventas, proporcionando una interfaz organizada tanto en formato de lista.* 
![sales_book 2](https://github.com/3D-Vision-C-A/tdv_sales_book/assets/96964600/e1d146a5-7066-48e4-8595-cca78a06b164)
