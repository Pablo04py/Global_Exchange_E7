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

---

### Registro #3 - 11/09/2026
* **Tarea / Historia**: Hito 4 - Sprint 2 (Visualización de Tasas, Simulador de Conversión, Cierre de Sesión SSO y Estandarización UI/UX)
* **Autor**: Pablo Portillo
* **Herramienta / Modelo**: Gemini
* **Contexto / Objetivo**: Resolver la persistencia de sesión SSO con Keycloak 24, unificar la arquitectura del simulador y visualizador de cotizaciones sobre el diagrama de clases de operaciones, homologar las plantillas al diseño base (`layouts/base.html`), e implementar la suite de pruebas unitarias (PUD) y tagging Git Flow (SCC).
* **Prompts Determinantes Utilizados**:

  1. **Sincronización de claims y Cierre de Sesión SSO en Keycloak 24:**
     > *"¿Eso se puede configurar también desde Keycloak para que se sincronice con Django? [...] Al darle al botón de cerrar sesión se queda la sesión activa en Keycloak."*
     > 
     > **Decisión**: Se habilitó el mapeador *Add to userinfo* dentro del ámbito roles en Keycloak y se exportó la configuración actualizada a `realm-export.json.example`. Para corregir la sesión persistente, se creó la vista personalizada `KeycloakOIDCLogoutView` en `usuarios/views.py` enviando el parámetro `id_token_hint` a `OIDC_OP_LOGOUT_ENDPOINT`, garantizando la destrucción del token SSO remoto.

  2. **Arquitectura, ORM y Enrutamiento de Cotizaciones y Simulador:**
     > *"Debo hacer visualización de tasas y simulador conversión en base al diagrama de clases. ¿Debo hacer un módulo por separado o hacerlo en uno solo? [...] FieldError / AttributeError en /operaciones/simulador/."*
     > 
     > **Decisión**: Se consolidó la lógica de lectura y simulación en una estructura unificada aprovechando los métodos del dominio (`calcular_precio_compra` y `calcular_precio_venta` en `TasaDeCambio`). Se solucionó el error 404 vinculando la subruta en `core/urls.py` mediante `include('cotizaciones.urls')`, y se adaptaron los QuerySets de las vistas para mapear correctamente la relación simple con el modelo `Moneda`.

  3. **Estandarización de Interfaz (UI/UX) y Pruebas Unitarias (PUD):**
     > *"Quiero que la estética de los formularios tenga la misma que el dashboard herede de base.html."*
     > 
     > **Decisión**: Se refactorizaron los archivos de plantilla (`form_moneda.html`, `form_tasa.html`, `lista_monedas.html`, `lista_tasas.html` y `simulador.html`) extendiendo de `layouts/base.html`, integrando la iconografía de Tabler e Inter font. Se estructuró la suite de pruebas en `cotizaciones/tests.py` validando la precisión decimal de las conversiones.

* **Resultado / Decisión**: Culminación exitosa del Sprint 2 del Hito 4. Se verificó el paso correcto de las pruebas unitarias con `manage.py test`, se completó el flujo de integración en Git (`feature/sprint2-cotizaciones-simulador` hacia `develop`) y se publicó el tag de entrega `v1.2.0-sprint2`.