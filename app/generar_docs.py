"""Genera la documentación HTML del código fuente con pdoc.

Uso (desde la raíz del repositorio):
    docker compose run --rm web python generar_docs.py

El resultado queda en ``docs/api/index.html``.
"""
import os
import re
import shutil
from pathlib import Path

import django
import pdoc
import pdoc.render

BASE_DIR = Path(__file__).resolve().parent          # carpeta app/
SALIDA = BASE_DIR.parent / "docs" / "api"           # docs/api/ en la raíz del repo

# Apps del proyecto a documentar. Los patrones con "!" excluyen módulos (regex).
MODULOS = [
    "core", "usuarios", "clientes", "mpagos",
    "cotizaciones", "operaciones", "main",
    r"!.*\.migrations",
]

# pdoc escribe los títulos de sección de los docstrings en inglés (Args, Returns...).
# Se traducen en el HTML generado; en el código se mantienen en inglés porque
# son las palabras clave del formato Google que pdoc necesita reconocer.
TRADUCCIONES = {
    "Arguments": "Parámetros",
    "Args": "Parámetros",
    "Returns": "Retorna",
    "Raises": "Excepciones",
    "Attributes": "Atributos",
    "Examples": "Ejemplos",
    "Example": "Ejemplo",
}


def traducir_secciones(carpeta):
    """Traduce al español los títulos de sección del HTML generado por pdoc."""
    patron = re.compile(r"(<h6[^>]*>)(" + "|".join(TRADUCCIONES) + r")(:?</h6>)")
    archivos = list(Path(carpeta).rglob("*.html")) + [Path(carpeta) / "search.js"]  # search.js: índice del buscador
    for archivo in archivos:
        html = archivo.read_text(encoding="utf-8")
        nuevo = patron.sub(lambda m: m.group(1) + TRADUCCIONES[m.group(2)] + m.group(3), html)
        if nuevo != html:
            archivo.write_text(nuevo, encoding="utf-8")


def main():
    """Configura Django, limpia la salida anterior y genera la documentación."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    if SALIDA.exists():
        shutil.rmtree(SALIDA)

    pdoc.render.configure(docformat="google", footer_text="Global Exchange - IS2")
    pdoc.pdoc(*MODULOS, output_directory=SALIDA)
    traducir_secciones(SALIDA)
    print(f"Documentación generada en {SALIDA}")


if __name__ == "__main__":
    main()