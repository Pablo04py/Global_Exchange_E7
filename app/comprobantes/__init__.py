"""Envío por email de las facturas electrónicas aprobadas (SCRUM-23).

Cuando una `FacturaElectronica` (app `facturacion`, SCRUM-56) queda `APROBADA`
por SIFEN, se encola el envío de su KuDE a los usuarios asociados al cliente.
El comando `procesar_envios` (servicio `mailer`) descarga el KuDE de Factura
Segura y lo envía; si el SMTP o Factura Segura no responden, lo reintenta
durante una hora.
"""
