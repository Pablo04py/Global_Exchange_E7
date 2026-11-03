"""Envío por email de los comprobantes de transacciones pagadas (SCRUM-23).

Cuando una transacción pasa a `PAGADA` se genera el PDF del comprobante y se
envía a los usuarios asociados al cliente. Si el servidor SMTP no responde, el
envío queda encolado en `EnvioComprobante` y el comando `procesar_envios` lo
reintenta durante una hora.
"""
