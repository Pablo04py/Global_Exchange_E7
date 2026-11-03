"""Comando que envía y reintenta los envíos de facturas por email pendientes.

Uso (desde la raíz del repositorio):
    docker compose exec web python manage.py procesar_envios
    docker compose exec web python manage.py procesar_envios --loop --intervalo 60

Con `--loop` queda corriendo indefinidamente; así lo ejecuta el servicio
`mailer` de docker-compose.
"""

import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from comprobantes.services import procesar_pendientes


class Command(BaseCommand):
    """Procesa los envíos de facturas `PENDIENTE` cuyo próximo intento ya llegó."""

    help = "Envía por email el KuDE de las facturas aprobadas pendientes y reintenta los fallidos (SCRUM-23)."

    def add_arguments(self, parser):
        """Define los argumentos del comando.

        Args:
            parser: Parser de argumentos de Django.
        """
        parser.add_argument('--loop', action='store_true', help="Repetir indefinidamente.")
        parser.add_argument('--intervalo', type=int, default=60,
                            help="Segundos entre pasadas con --loop (por defecto 60).")

    def handle(self, *args, **options):
        """Ejecuta una pasada, o una cada `--intervalo` segundos con `--loop`."""
        if not options['loop']:
            self._pasada()
            return

        self.stdout.write(f"Procesando envíos pendientes cada {options['intervalo']} s (Ctrl+C para salir).")
        try:
            while True:
                close_old_connections()  # evita conexiones caídas en un proceso de larga duración
                self._pasada()
                time.sleep(options['intervalo'])
        except KeyboardInterrupt:
            self.stdout.write("Detenido.")

    def _pasada(self):
        """Procesa los envíos pendientes e informa el resultado si hubo alguno."""
        resumen = procesar_pendientes()
        if resumen['procesados']:
            self.stdout.write(
                f"Procesados: {resumen['procesados']} | enviados: {resumen['enviados']} "
                f"| fallidos: {resumen['fallidos']}"
            )
