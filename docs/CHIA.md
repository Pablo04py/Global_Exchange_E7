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

### Registro #3 - 31/08/2026
* *Tarea / Historia*: SCRUM-28 (Integración de autenticación OIDC con Keycloak y control de acceso por roles)
* *Autor*: Giovanni
* *Herramienta / Modelo*: Claude
* *Contexto / Objetivo*: Integrar Django con Keycloak como proveedor de identidad (IdP) vía OIDC, sincronizar roles de Keycloak hacia el modelo de Usuario local, e implementar un mecanismo de control de acceso por rol para las vistas.

* *Prompts Determinantes Utilizados*:

  1. *Elección del mecanismo de sincronización Usuario-Keycloak:*
     > "Explicame cual es mejor, recorda que este proyecto lo hacemos en modo scrum, usamos github flow y hacemos releases..."
     >
     > *Decisión*: Se optó por mantener una tabla Usuario local liviana en Django (con keycloak_id, username, email), sincronizada automáticamente en cada login ("shadow user" pattern), en lugar de no persistir ningún dato de usuario y depender 100% de llamadas en vivo a Keycloak. Justificación: permite Foreign Keys reales desde otros modelos (Transaccion, Caja, etc.), compatibilidad con el admin de Django, y evita duplicar lógica de autenticación que Keycloak ya resuelve.

  2. *Diseño del backend de autenticación custom (usuarios/backends.py):*
     > "Y en actualizar_roles, guardás de verdad... esto en donde va en settings o en models.py"
     >
     > *Decisión*: Se extendió OIDCAuthenticationBackend de mozilla-django-oidc, sobrescribiendo create_user/update_user para sincronizar datos personales y roles (realm_access.roles del token) hacia el modelo Usuario en cada login, persistiendo los roles en un campo ArrayField de PostgreSQL.

  3. *Diseño del control de acceso por rol (decorador requiere_rol):*
     > "Ya, como hago las relaciones en Star UML como conecto los Foreign Keys y eso" (sesión de diseño previa) → "explicame para entender, así puedo usar en otros proyectos"
     >
     > *Decisión*: Se implementó un decorador propio (usuarios/decorators.py) que verifica request.user.roles contra una lista de roles permitidos, en lugar de usar el sistema de permisos nativo de Django (is_staff/Group), ya que los roles viven y se gestionan en Keycloak, no en la base de datos de Django.

  4. *Resolución de configuración de hostname de Keycloak (KC_HOSTNAME_STRICT, KC_HOSTNAME):*
     > "Sigue tirándome lo mismo, le doy a login y va a 8180 no es porque hardcodeamos..."
     >
     > *Decisión*: Se identificó que Keycloak (desde v22+) requiere KC_HOSTNAME con puerto explícito y KC_HOSTNAME_STRICT: false en modo desarrollo para evitar rechazos 401 en el endpoint userinfo por discrepancia entre el issuer del token y la URL real de acceso.

  5. *Exportación/importación automática del realm de Keycloak:*
     > "Decime a mi como hacer lo de la exportación automática del realm de Keycloak rápido paso a paso"
     >
     > *Decisión*: Se configuró command: start-dev --import-realm junto con un volumen montado hacia /opt/keycloak/data/import, versionando docker/keycloak/realm-export.json en el repositorio, para que la configuración del realm (roles, client, mappers) se reconstruya automáticamente ante cualquier reseteo de volúmenes de Docker, evitando pérdida de configuración manual repetida.

* *Resultado*: Login funcional vía Keycloak (OIDC), con roles sincronizados y control de acceso por rol operativo en las vistas de clientes y operaciones. Configuración de Keycloak reproducible automáticamente para todo el equipo.

### Registro #4 - 11/09/2026
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
### Registro #5 - 24/09/2026
* **Tarea / Historia**: `SCRUM-47` (Documentación automática del código)
* **Autor**: Alejandro Giménez
* **Herramienta / Modelo**: Claude
* **Contexto / Objetivo**: Verificar la rama feature/SCRUM-47 y dejar la documentación automática lista para integrar en develop.
* **Prompts Determinantes Utilizados**:

  1. **Revisión de la rama:**
     > *"Quiero que verifiques si funciona correctamente para poder mergear... teniendo en cuenta los criterios IDE, PDO y CHIA."*
     >
     > **Decisión**: Se descartó el HTML generado a mano en `app/docs/` porque estaba desactualizado y no podía regenerarse. Se agregó pdoc a `app/requirements.txt`.

  2. **Documentación automática con Django:**
     > *"Ayudame a hacer la documentación automática y dejarlo listo para mergear."*
     >
     > **Decisión**: Se creó `app/generar_docs.py`, que ejecuta `django.setup()` antes de pdoc (sin eso fallan los imports de los modelos) y excluye las migraciones. La salida va a `docs/api/`, y se montó `./docs` en el contenedor `web`. Se agregaron tareas de VS Code en `.vscode/tasks.json`.

* **Resultado / Decisión**: Culminación exitosa del Sprint 2 del Hito 4. Se verificó el paso correcto de las pruebas unitarias con `manage.py test`, se completó el flujo de integración en Git (`feature/sprint2-cotizaciones-simulador` hacia `develop`) y se publicó el tag de entrega `v1.2.0-sprint2`.

---

### Registro #6 - 27/09/2026
* **Tarea / Historia**: `SCRUM-19` (Historial de transacciones)
* **Autor**: _(completar)_
* **Herramienta / Modelo**: Claude
* **Contexto / Objetivo**: Implementar el historial de transacciones de solo consulta para clientes registrados, con filtros, paginación, pruebas unitarias y documentación, integrándolo a la arquitectura existente sin que exista todavía un modelo de transacciones.
* **Prompts Determinantes Utilizados**:

  1. **Análisis previo del proyecto:**
     > *"Antes de modificar cualquier archivo, quiero que analices y entiendas el proyecto existente [...] explícame qué habría que hacer para implementar la historia de usuario."*
     >
     > **Decisión**: Se constató que no existía ningún modelo de transacciones en `main`, `develop` ni en las ramas `feature/*`, y que Minorista/Corporativo/VIP no son roles de Keycloak sino `Cliente.categoria`. El acceso al historial se definió como "usuario autenticado con al menos un `Cliente` asociado (`UsuarioCliente`)", sin crear roles nuevos.

  2. **Modelo de transacciones (opción A):**
     > *"Ok me parece bien la opción A."*
     >
     > **Decisión**: Se creó `Transaccion` en la app `operaciones` como contrato para la historia de compra/venta: dueño = `usuario` (el cliente es el propio usuario registrado), FKs `PROTECT` (registro de auditoría), tipo desde el punto de vista del cliente (compra = paga PYG y recibe divisa), `cajero` opcional mientras la operación esté pendiente y `estado` simple (`PENDIENTE`/`CONFIRMADA`/`CANCELADA`), cuya lógica de transición queda para la historia "Estado de transacción".

  3. **Filtros, dispositivo y datos de prueba:**
     > *"Quiero que fecha y hora estén en la misma sección pero que se pueda configurar por separado [...] Si me gustaría generar transacciones de prueba."*
     >
     > **Decisión**: `FiltroHistorialForm` (GET) con filtros por fecha, hora, tipo, moneda, medio de pago, montos, factura, dispositivo, cajero y estado; sus opciones se construyen solo con datos del usuario para impedir consultar datos ajenos por URL. Paginación de 20 con `Paginator`. `operaciones.utils.detectar_dispositivo` (User-Agent, sin librerías nuevas) para uso de compra/venta. Comando `generar_transacciones_prueba` (solo con `DEBUG=True`) para datos visibles, diferenciado de los tests, que usan una base temporal.

  4. **Un cliente por usuario:**
     > *"Solo se puede tener un cliente por usuario, osea el termino cliente muere, ya que el usuario registrado solo puede ser minorista, mayorista, vip o corporativo"*
     >
     > **Decisión**: Se eliminó el campo `cliente` de `Transaccion` (reescribiendo la migración `0003`, aún no compartida) y el filtro/columna "Cliente" del historial; el aislamiento se hace con `usuario=request.user`. La regla de acceso (tener un `Cliente` asociado) no se modificó y se revisará cuando otra historia configure las categorías de cliente en Keycloak. En `main/views.py` solo se mantuvo la corrección del enlace del menú y la extracción de `resolve_user_role()`, sin agregar enlaces nuevos al menú "Sin Rol".

* **Resultado / Decisión**: 61 pruebas nuevas en `app/tests/operaciones/` (modelo, dispositivo, acceso/seguridad, solo lectura, filtros, paginación y comando), todas en verde. Las 8 fallas preexistentes de `tests/main` y `tests/operaciones/test_views.py` no se modificaron por estar fuera del alcance de SCRUM-19. Documentación regenerada con `generar_docs.py`.
