from django.db import migrations


def cargar_comisiones(apps, schema_editor):

    ConfiguracionComision = apps.get_model(
        'operaciones',
        'ConfiguracionComision'
    )

    ConfiguracionComision.objects.update_or_create(
        categoria='MINORISTA',
        defaults={'porcentaje': '2.00'}
    )

    ConfiguracionComision.objects.update_or_create(
        categoria='CORPORATIVO',
        defaults={'porcentaje': '1.50'}
    )

    ConfiguracionComision.objects.update_or_create(
        categoria='VIP',
        defaults={'porcentaje': '1.00'}
    )


def eliminar_comisiones(apps, schema_editor):

    ConfiguracionComision = apps.get_model(
        'operaciones',
        'ConfiguracionComision'
    )

    ConfiguracionComision.objects.filter(
        categoria__in=[
            'MINORISTA',
            'CORPORATIVO',
            'VIP'
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            'operaciones',
            '0003_configuracioncomision_transaccion'
        ),
        # DEJÁ ACÁ LA DEPENDENCIA QUE DJANGO GENERÓ
    ]

    operations = [
        migrations.RunPython(
            cargar_comisiones,
            eliminar_comisiones
        ),
    ]