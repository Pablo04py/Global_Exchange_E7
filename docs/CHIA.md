# Registro de Prompts e Interacciones con IA (CHIA)

## Proyecto: Global Exchange (IS2 - 2026/2)

---

### 📌 Guía de Registro (CHIA)

* **Propósito**: Garantizar la trazabilidad y auditabilidad del uso de IA en las decisiones del proyecto.
* **Qué registrar**: Solamente prompts y decisiones **determinantes** (arquitectura, infraestructura, resolución de bloqueos críticos o configuración de testing). Se omiten consultas triviales.

---

### 📋 Plantilla de Registro (Ejemplo Reusable)

### Registro #N - [DD/MM/AAAA]
* **Tarea / Historia**: `SCRUM-XX` (Nombre de la Historia de Usuario)
* **Autor**: [Nombre del Desarrollador]
* **Herramienta / Modelo**: [Gemini / ChatGPT / Claude / etc.]
* **Contexto / Objetivo**: [Breve descripción del problema o la necesidad técnica]
* **Prompt Utilizado**:
  > *"[Escribir aquí el prompt o la instrucción clave enviada a la IA]"*
* **Resultado / Decisión**: [Decisión técnica tomada, cambios aplicados o solución obtenida]

---

### Registro #1 - 20/02/2026
* **Tarea / Historia**: `SCRUM-46` (Gestión de Documentación y Prompts de IA)
* **Autor**: Fabio
* **Herramienta / Modelo**: Gemini
* **Contexto / Objetivo**: Crear la estructura inicial del documento `CHIA.md` y definir las pautas para el registro de prompts del equipo.
* **Prompt Utilizado**:
  > *"Crear una plantilla en Markdown para registrar la interacción con modelos de IA en el proyecto, definiendo criterios para documentar prompts determinantes, contextos y decisiones tomadas."*
* **Resultado / Decisión**: Se aprobó el formato estandarizado para `docs/CHIA.md`, estableciendo la obligación de documentar únicamente los intercambios clave para la arquitectura y resolución de bloqueos.

---

### Registro #2 - 31/08/2026
* **Tarea / Historia**: `SCRUM-44` (Framework de Pruebas Unitarias)
* **Autor**: Fabio
* **Herramienta / Modelo**: Gemini
* **Contexto / Objetivo**: Diseñar la arquitectura de pruebas automáticas para el proyecto, organizar la estructura del directorio y definir los tests unitarios de las apps `main` y `usuarios`.
* **Prompt Utilizado**:
  > *"Establecer una estructura limpia de tests con el patrón espejo en app/tests/ para la app main y usuarios sin modificar el código fuente, probando vistas, URLs, endpoints AJAX, el modelo Usuario, el decorador requiere_rol y el backend OIDC de Keycloak."*
* **Resultado / Decisión**: Se descartaron los archivos `tests.py` individuales dentro de cada app y se adoptó la suite centralizada en `app/tests/`. Se implementaron exitosamente las pruebas unitarias para `main/test_views.py`, `usuarios/test_models.py`, `usuarios/test_decorators.py` y `usuarios/test_backends.py`, verificando su ejecución mediante `docker compose exec web python manage.py test tests`.