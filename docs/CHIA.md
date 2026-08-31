# Registro de Prompts e Interacciones con IA (CHIA)

## Proyecto: Global Exchange (IS2 - 2026/2)

---

### 📌 Guía de Registro (CHIA)

* **Propósito**: Garantizar la trazabilidad y auditabilidad del uso de IA en las decisiones del proyecto.
* **Qué registrar**: Solamente prompts y decisiones **determinantes** (arquitectura, infraestructura, resolución de bloqueos críticos o configuración de testing). Se omiten consultas triviales.

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
* **Contexto / Objetivo**: Implementar la suite de pruebas unitarias, resolver fallos de red en Docker y corregir el mock de APIs externas.
* **Prompts Determinantes Utilizados**:

  1. **Ajuste de importación en el test unitario:**
     > *"ModuleNotFoundError: No module named 'apps' al ejecutar python manage.py test tests dentro del contenedor."*
     > 
     > **Decisión**: Se simplificó la ruta del parche en `app/tests/test_example.py` utilizando `@patch('requests.get')`, logrando la ejecución exitosa de la suite con resultado **`OK`**.