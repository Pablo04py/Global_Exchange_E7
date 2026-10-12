"""Comando para preparar un turno de caja abierto y probar el cierre (solo desarrollo).

Uso (desde la raíz del repositorio):
    docker compose exec web python manage.py preparar_demo_cierre <username>

Prepara un turno abierto para probar el cierre sin pasar por las pantallas de
asignación y apertura: crea una caja de demostración y usa los servicios reales
de la app `caja` para asignarla al cajero (`asignar_cajero`, SCRUM-36) y abrirla
(`apertura_caja`, SCRUM-37) con un fondo inicial en guaraníes y en cada moneda
habilitada. Después la caja puede cerrarse desde `/arqueos/cerrar/`.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from caja.models import Caja
from caja.services import MONEDA_LOCAL, apertura_caja, asignar_cajero
from operaciones.models import Moneda

MONTO_INICIAL_DEMO = Decimal('5000000')  # guaraníes
FONDO_DIVISA_DEMO = Decimal('1000')      # por cada moneda habilitada


class Command(BaseCommand):
    """Crea una caja de demostración, la asigna al cajero y la abre."""

    help = "Crea una caja de demostración con un turno ABIERTO para un cajero (solo con DEBUG=True)."

    def add_arguments(self, parser):
        """Define los argumentos del comando.

        Args:
            parser: Parser de argumentos de Django.
        """
        parser.add_argument('username', help="Usuario con rol Cajero al que se le abre la caja.")

    def handle(self, *args, **options):
        """Crea la caja, la asigna y la abre con los servicios de la app `caja`.

        Raises:
            CommandError: Si `DEBUG` está desactivado, el usuario no existe, no
                tiene rol Cajero o la asignación/apertura no es posible (por
                ejemplo, porque ya tiene un turno asignado o abierto).
        """
        if not settings.DEBUG:
            raise CommandError("Este comando solo puede ejecutarse con DEBUG=True.")

        Usuario = get_user_model()
        try:
            cajero = Usuario.objects.get(username=options['username'])
        except Usuario.DoesNotExist:
            raise CommandError(f"No existe el usuario '{options['username']}'.")
        if 'Cajero' not in (cajero.roles or []):
            raise CommandError(f"El usuario '{cajero.username}' no tiene el rol Cajero.")

        numero = 1
        while Caja.objects.filter(codigo=f"DEMO-{numero}").exists():
            numero += 1
        fondo = {MONEDA_LOCAL: MONTO_INICIAL_DEMO}
        fondo.update({m.codigo.upper(): FONDO_DIVISA_DEMO for m in Moneda.objects.filter(habilitada=True)})

        try:
            with transaction.atomic():  # si algo falla no queda la caja ni la asignación a medias
                caja = Caja.objects.create(nombre=f"Caja Demo {numero}", codigo=f"DEMO-{numero}")
                asignar_cajero(caja, cajero, asignado_por=cajero)
                apertura_caja(cajero, fondo)
        except ValidationError as error:
            raise CommandError(' '.join(error.messages))

        self.stdout.write(self.style.SUCCESS(
            f"Turno ABIERTO en '{caja}' para '{cajero.username}'. Ya puede cerrarse en /arqueos/cerrar/."
        ))
