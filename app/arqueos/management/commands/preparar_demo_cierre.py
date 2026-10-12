"""Comando para preparar un turno de caja abierto y probar el cierre (solo desarrollo).

Uso (desde la raíz del repositorio):
    docker compose exec web python manage.py preparar_demo_cierre <username>

Hace lo mismo que la apertura de caja (SCRUM-37) para probar el cierre sin
pasar por esa pantalla: crea una caja de demostración y un turno
(`SesionCaja`) en estado `ABIERTA` para el cajero indicado, con un fondo
inicial en guaraníes y en cada moneda habilitada (`SaldoInicialCaja`). Después
la caja puede cerrarse desde `/arqueos/cerrar/` con el saldo registrado real.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caja.models import Caja, EstadoCaja, EstadoSesionCaja, SaldoInicialCaja, SesionCaja
from operaciones.models import Moneda

MONTO_INICIAL_DEMO = Decimal('5000000')  # guaraníes
FONDO_DIVISA_DEMO = Decimal('1000')      # por cada moneda habilitada


class Command(BaseCommand):
    """Crea una caja de demostración con un turno abierto para un cajero."""

    help = "Crea una caja de demostración con un turno ABIERTO para un cajero (solo con DEBUG=True)."

    def add_arguments(self, parser):
        """Define los argumentos del comando.

        Args:
            parser: Parser de argumentos de Django.
        """
        parser.add_argument('username', help="Usuario con rol Cajero al que se le abre la caja.")

    def handle(self, *args, **options):
        """Crea la caja y el turno abierto.

        Raises:
            CommandError: Si `DEBUG` está desactivado, el usuario no existe, no
                tiene rol Cajero o ya tiene un turno asignado o abierto.
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
        if SesionCaja.objects.filter(
            cajero=cajero, estado__in=[EstadoSesionCaja.ASIGNADA, EstadoSesionCaja.ABIERTA]
        ).exists():
            raise CommandError(f"El usuario '{cajero.username}' ya tiene una caja asignada o abierta.")

        numero = Caja.objects.filter(codigo__startswith='DEMO-').count() + 1
        caja = Caja.objects.create(
            nombre=f"Caja Demo {numero}", codigo=f"DEMO-{numero}", estado=EstadoCaja.EN_USO
        )
        turno = SesionCaja.objects.create(
            caja=caja,
            cajero=cajero,
            asignado_por=cajero,
            estado=EstadoSesionCaja.ABIERTA,
            monto_inicial=MONTO_INICIAL_DEMO,
            fecha_apertura=timezone.now(),
        )
        for moneda in Moneda.objects.filter(habilitada=True):
            SaldoInicialCaja.objects.create(sesion=turno, moneda=moneda, monto=FONDO_DIVISA_DEMO)
        self.stdout.write(self.style.SUCCESS(
            f"Turno ABIERTO en '{caja}' para '{cajero.username}'. Ya puede cerrarse en /arqueos/cerrar/."
        ))
