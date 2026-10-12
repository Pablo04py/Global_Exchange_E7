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
* **Autor**: Alejandro Gimenez
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
     > **Decisión**: Se creó `Transaccion` en la app `operaciones` como contrato para la historia de compra/venta: `cliente` (a nombre de quién se opera) y `usuario` (quién operó), FKs `PROTECT` (registro de auditoría), tipo desde el punto de vista del cliente (compra = paga PYG y recibe divisa), `cajero` opcional mientras la operación esté pendiente y `estado` simple (`PENDIENTE`/`CONFIRMADA`/`CANCELADA`), cuya lógica de transición queda para la historia "Estado de transacción".

  3. **Filtros, dispositivo y datos de prueba:**
     > *"Quiero que fecha y hora estén en la misma sección pero que se pueda configurar por separado [...] Si me gustaría generar transacciones de prueba."*
     >
     > **Decisión**: `FiltroHistorialForm` (GET) con filtros por fecha, hora, tipo, moneda, medio de pago, montos, factura, dispositivo, cajero, operado por y estado; sus opciones se construyen solo con datos del usuario para impedir consultar datos ajenos por URL. Paginación de 20 con `Paginator`. `operaciones.utils.detectar_dispositivo` (User-Agent, sin librerías nuevas) para uso de compra/venta. Comando `generar_transacciones_prueba` (solo con `DEBUG=True`) para datos visibles, diferenciado de los tests, que usan una base temporal.

  4. **Un cliente por usuario:**
     > *"Solo se puede tener un cliente por usuario, osea el termino cliente muere, ya que el usuario registrado solo puede ser minorista, mayorista, vip o corporativo"*
     >
     > **Decisión**: Se eliminó el campo `cliente` de `Transaccion` (reescribiendo la migración `0003`, aún no compartida) y el filtro/columna "Cliente" del historial; el aislamiento se hace con `usuario=request.user`. La regla de acceso (tener un `Cliente` asociado) no se modificó y se revisará cuando otra historia configure las categorías de cliente en Keycloak. En `main/views.py` solo se mantuvo la corrección del enlace del menú y la extracción de `resolve_user_role()`, sin agregar enlaces nuevos al menú "Sin Rol".

  5. **Vuelta al modelo del enunciado (varios usuarios por cliente):**
     > *"Un cliente puede tener uno o más usuarios asociados que pueden operar en su nombre [...] Crees que [...] muestre el historial y arriba haya un indicador de que cliente pertenece ese historial"*
     >
     > **Decisión**: Prevalece el enunciado sobre la regla del punto 4: se restauró `Transaccion.cliente` (reescribiendo la `0003`, aún no mergeada). El historial muestra todas las operaciones del **cliente activo** de la sesión (`ge_active_client`, el mismo que elige el selector del dashboard, RF9), incluidas las de otros usuarios del cliente, con columna y filtro "Operado por" e indicador "Historial de: <cliente>". Sin cliente activo válido se usa la misma regla del dashboard (primer cliente asociado). No se agregó una pantalla intermedia de selección porque la elección del cliente activo pertenece a otra historia.

* **Resultado / Decisión**: 72 pruebas nuevas en `app/tests/operaciones/` (modelo, dispositivo, acceso/seguridad, solo lectura, filtros, paginación y comando), todas en verde. Las 8 fallas preexistentes de `tests/main` y `tests/operaciones/test_views.py` no se modificaron por estar fuera del alcance de SCRUM-19. Documentación regenerada con `generar_docs.py`.

### Registro #7 - 02/10/2026
- **Tarea / Historia**: `SCRUM-20` (Integración de campos obligatorios de comisión y tasa en transacciones, y corrección integral de la suite de pruebas)
- **Autor**: Fabio Rodriguez
- **Herramienta / Modelo**: Gemini
- **Contexto / Objetivo**: Resolver fallos de integridad por restricciones `NOT NULL` en los nuevos campos de comisiones de `Transaccion`, corregir problemas de descubrimiento de paquetes de prueba (`__init__.py` faltantes), inconsistencias de mayúsculas en rutas de plantillas (`templates`) y validación de roles de usuario en los diferentes módulos del sistema (`operaciones`, `cotizaciones`, `main`, `mpagos` y `clientes`).
- **Prompts Determinantes Utilizados**:

1. **Corrección de restricciones `NOT NULL` en pruebas y comandos:**
     > *"IntegrityError: null value in column "porcentaje_comision" of relation "operaciones_transaccion" violates not-null constraint al ejecutar comandos de generación y test suites."*
     > 
     > **Decisión**: Se implementó un parche dinámico (`patch.object`) en los `setUp` y bases de pruebas para inyectar automáticamente los campos obligatorios faltantes (`porcentaje_comision`, `monto_comision`, `moneda_comision`, `categoria_cliente_aplicada`, `tasa_referencia`), asegurando la compatibilidad con el nuevo modelo de transacciones sin alterar la lógica base del sistema.

2. **Resolución de errores de entorno, case-sensitivity y roles de usuario:**
     > *"Solucionar errores de descubrimiento de paquetes (`TypeError` por falta de `__init__.py`), `TemplateDoesNotExist` por nombres de carpetas en mayúsculas y errores de acceso `HTTP 403` en vistas debido al uso del campo personalizado `roles` en lugar de los grupos clásicos de Django."*
     > 
     > **Decisión**: Se estandarizó la estructura de directorios (`__init__.py` y carpetas `templates` en minúsculas) y se actualizaron los usuarios de prueba en los casos de integración para registrar correctamente el campo `roles=['...']`, logrando estabilizar el entorno y alcanzar el **100% de la suite de pruebas en verde (`OK`)**.

---

### Registro #8 - 02/10/2026

* **Tarea / Historia**: Configuración de entorno de producción local y mejora de navegación
* **Herramienta de IA utilizada**: ChatGPT
* **Objetivo**: Preparar una configuración de producción local para Global Exchange utilizando Docker, Gunicorn y Nginx, manteniendo separado el entorno de desarrollo. Además, incorporar una forma directa de regresar al Dashboard desde cualquier pantalla.

#### 1. Configuración de producción local

> Se solicitó analizar cómo configurar el proyecto para ejecutarse en un entorno similar a producción, sin necesidad de desplegarlo en un dominio o VPS.

**Decisión:** Mantener `docker-compose.yml` para desarrollo y crear una configuración independiente mediante `docker-compose.prod.yml`.

La arquitectura propuesta fue:

Navegador → Nginx → Gunicorn → Django → PostgreSQL

Keycloak se mantuvo inicialmente ejecutándose de forma independiente en el puerto `8080`.

#### 2. Incorporación de Gunicorn

> Se solicitó reemplazar el servidor de desarrollo de Django por un servidor adecuado para producción.

**Decisión:** Agregar `gunicorn` a `requirements.txt` y ejecutar Django mediante:

```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 3


### Registro #9 - 02/10/2026

* **Tarea / Historia**: Corrección posterior a merge e integración de cambios en operaciones
* **Herramienta de IA utilizada**: ChatGPT
* **Objetivo**: Diagnosticar y reparar errores producidos luego de integrar cambios de distintas ramas en `develop`, verificar el funcionamiento de Django y revisar las migraciones pendientes de la aplicación `operaciones`.

#### 1. Error detectado luego del merge

Luego del merge, el contenedor de Django no podía iniciar correctamente.

El log mostraba:

```text
ImportError: cannot import name 'registrar_transaccion_cancelada'
from 'operaciones.services'



### Registro #10 - 11/10/2026
- **Tarea / Historia**: `SCRUM-36` (Asignación de Cajero)
- **Autor**: Fabio Rodriguez
- **Herramienta / Modelo**: Gemini
- **Contexto / Objetivo**: Implementación completa del módulo de asignación de cajeros (`caja`), arquitectura MVT, validaciones de lógica de negocio, resolución de errores de importación/plantillas en Docker y armado del test suite en `tests/caja/`.
- **Prompts Determinantes Utilizados**:

1. **Resolución de Importación Circular y Estructura MVT:**
     > *"ImportError: cannot import name 'Caja' from partially initialized module 'caja.models' (most likely due to a circular import)"*
     >
     > **Decisión**: Se eliminó la importación redundante en `app/caja/models.py` y se estructuró la regla de negocio `clean_cajero()` en `forms.py` para impedir doble asignación de sesión a un mismo cajero.

2. **Ajuste de Test Suite en Espejo para Entorno Docker:**
     > *"ModuleNotFoundError: No module named 'app' al ejecutar manage.py test tests.caja dentro del contenedor Docker."*
     >
     > **Decisión**: Se ajustaron los `imports` dentro de `tests/caja/test_models.py` y `tests/caja/test_views.py` sustituyendo el prefijo `app.` por `caja.models`, adaptándose a la raíz `/app` del contenedor web.

3. **Corrección de Aserciones de Formulario en Django 4.1+:**
     > *"AttributeError: 'HttpResponse' object has no attribute 'is_bound' en assertFormError"*
     >
     > **Decisión**: Se actualizó la aserción extrayendo la instancia del formulario enlazado directamente desde el contexto de la respuesta (`response.context['form']`), garantizando el chequeo correcto de los mensajes de error.

- **Resultado / Decisión**: Ejecución exitosa de la suite con resultado **`OK` (4/4 tests pasados)** y plantilla `asignar_cajero.html` integrada correctamente al diseño base del sistema.


## Interacción con IA - SCRUM-37: Apertura de Caja (Multimoneda Dinámica)

**Fecha:** 12 de Octubre de 2026  
**Desarrollador:** Fabio Cesar Rodriguez Vazquez  
**Rama:** `feature/SCRUM-37`  

### 1. Contexto y Objetivos
- **Objetivo:** Implementar la funcionalidad de Apertura de Caja (SCRUM-37) permitiendo al cajero autenticado declarar el fondo inicial en efectivo desglosado por moneda antes de iniciar operaciones.
- **Clarificación del Modelo de Negocio:** Se estableció y alineó la abstracción de flujos entre la realidad bancaria y los requerimientos del ERS (operaciones electrónicas en PYG e inventario físico de divisas en ventanilla).

### 2. Decisiones Técnicas y Arquitectura
- **Integración con Módulo de Operaciones:** En lugar de hardcodear monedas estáticas mediante `TextChoices`, se vinculó `SaldoInicialCaja` mediante una `ForeignKey` al modelo dinámico `operaciones.Moneda`.
- **Formulario Dinámico:** Se adaptó `AperturaCajaForm` para instanciar dinámicamente un campo de entrada decimal por cada moneda que esté en estado `habilitada=True` en la base de datos.
- **Flujo de Estados:**
  - La `SesionCaja` transiciona de `ASIGNADA` a `ABIERTA`.
  - La `Caja` pasa de `DISPONIBLE` a `EN_USO`.
  - Se persisten las entradas en `SaldoInicialCaja` por cada divisa.

### 3. Archivos Modificados / Creados
- `caja/models.py`: Incorporación del modelo `SaldoInicialCaja` relacionado a `SesionCaja` y `operaciones.Moneda`.
- `caja/forms.py`: Implementación de `AperturaCajaForm` con iteración dinámica sobre `Moneda.objects.filter(habilitada=True)`.
- `caja/views.py`: Implementación de `aperturar_caja_view` con validaciones de sesión pendiente y guardado de saldos iniciales.
- `caja/urls.py`: Adición del endpoint `aperturar/` bajo el namespace `caja`.
- `caja/templates/caja/aperturar_caja.html`: Plantilla base funcional con bucle para renderizar el formulario dinámico.
- `tests/caja/test_apertura.py`: Test unitarios que verifican la creación de saldos, cambio de estado de sesión/caja y casos borde.

### 4. Resultado de Verificación
- **Migraciones:** Regenerada la migración `0002_saldoinicialcaja.py` para reflejar la relación FK con `operaciones.Moneda`.
- **Tests Unitarios:** Ejecución exitosa de la suite completa con `docker compose exec web python manage.py test tests.caja`.

Registro #11 - 12/10/2026
- Tarea / Historia: Implementación de confirmación de pagos mediante Stripe y SIPAP
- Autor: Pablo Portillo
- Herramienta / Modelo: ChatGPT
- Contexto / Objetivo: Diseñar e implementar el proceso de confirmación de pagos de las operaciones de compra y venta de divisas de Global Exchange, incorporando integración real en entorno de pruebas con Stripe para pagos mediante tarjeta y una simulación de confirmación para transferencias SIPAP. La solución debía integrarse con la arquitectura Django existente, mantener el flujo de estados de las transacciones, registrar los cambios mediante el sistema de auditoría y evitar almacenar datos sensibles de tarjetas.
- Prompts Determinantes Utilizados:
  1. Análisis inicial del flujo de confirmación de pagos:
     "Tengo que implementar la confirmación de pago, integración con servicios SIPAP, Stripe, etc. Quiero hacerlo sobre la estructura que ya tenemos sin romper lo que hicieron mis compañeros."
     Decisión: Se determinó que la confirmación de pagos debía trabajar sobre la entidad Transaccion ya existente, evitando crear modelos paralelos para representar operaciones pagadas. Cada operación se crea inicialmente con estado PENDIENTE y el servicio de pago correspondiente es responsable únicamente de validar el pago y solicitar posteriormente el cambio de estado.
     El flujo general definido quedó:
     Usuario confirma operación
             ↓
     Se crea Transaccion
             ↓
     Estado PENDIENTE
             ↓
     Se procesa el medio de pago
             ↓
     Pago confirmado
             ↓
     Estado PAGADA
             ↓
     LogTransaccion
     
     Se mantuvo la transición PENDIENTE → PAGADA centralizada para evitar modificar directamente el estado desde cada integración de pago.
  2. Definición de la arquitectura de servicios de pago:
     "Quiero separar Stripe y SIPAP para que no quede toda la lógica metida en views.py."
     Decisión: Se creó el paquete:
     operaciones/pagos/
     ├── __init__.py
     ├── stripe_service.py
     └── sipap_service.py
     
     La lógica específica de cada proveedor se separó de operaciones/views.py. Las vistas coordinan las solicitudes HTTP mientras que los servicios se encargan de comunicarse o simular la comunicación con el proveedor correspondiente.
     Este diseño permite incorporar posteriormente otros procesadores de pago sin concentrar toda la lógica dentro de las vistas de operaciones.
  3. Integración de Stripe en entorno Sandbox:
     "Quiero que Stripe funcione de verdad pero solamente en modo de prueba, sin manejar dinero real."
     Decisión: Se integró el SDK oficial de Stripe utilizando exclusivamente claves de prueba. Las credenciales se almacenan mediante variables de entorno y se incorporaron configuraciones para:
     STRIPE_SECRET_KEY
     STRIPE_PUBLISHABLE_KEY
     STRIPE_WEBHOOK_SECRET
     
     El SDK Python de Stripe se incorporó a requirements.txt, ejecutándose dentro del contenedor Docker de Django.
     La arquitectura local quedó:
     Navegador
         ↓
     Django en Docker
         ↓
     Stripe API Test Mode
     
     Stripe CLI en Windows
         ↓
     Webhook local de Django
     
     Stripe CLI se utilizó únicamente durante el desarrollo para reenviar eventos de webhook desde Stripe hacia el servidor local.
  4. Registro seguro de tarjetas mediante Stripe Elements:
     "Quiero que cuando registre una tarjeta no se guarden los datos sensibles en nuestra base de datos."
     Decisión: Se implementó el registro de tarjetas utilizando Stripe Elements + SetupIntent, evitando que el número completo de tarjeta o el código CVC pasen por el backend de Global Exchange.
     Se extendió Cliente con:
     stripe_customer_id
     
     y MedioPago con información necesaria para vincular la tarjeta tokenizada:
     stripe_payment_method_id
     marca_tarjeta
     exp_mes
     exp_anio
     
     además del número enmascarado existente.
     El flujo quedó:
     Usuario registra tarjeta
             ↓
     Django crea/recupera Customer
             ↓
     Stripe crea SetupIntent
             ↓
     Stripe Elements captura tarjeta
             ↓
     Stripe genera PaymentMethod
             ↓
     Django guarda solamente
     stripe_payment_method_id
     + información enmascarada
     
     De esta manera Global Exchange no persiste el PAN completo ni el CVC de las tarjetas.
  5. Confirmación del pago con una tarjeta previamente registrada:
     "Si la tarjeta ya está guardada quiero poder seleccionarla para la operación pero que vuelva a pedir el CVC para pagar."
     Decisión: Se reutilizó el PaymentMethod almacenado en Stripe, solicitando nuevamente el CVC antes de confirmar cada pago.
     Al seleccionar una tarjeta registrada:
     Transaccion PENDIENTE
             ↓
     Usuario ingresa CVC
             ↓
     Django crea PaymentIntent
             ↓
     stripe.confirmCardPayment()
             ↓
     Stripe procesa el pago
     
     Se configuró:
     payment_method_options={    "card": {        "require_cvc_recollection": True    }}
     
     
     permitiendo solicitar nuevamente el código de seguridad sin almacenar este dato.
     Durante las pruebas se utilizó la tarjeta de Stripe:
     4242 4242 4242 4242
     
     correspondiente al entorno Test Mode.
  6. Corrección de errores durante la integración con Stripe:
     "Stripe me rechaza el PaymentIntent cuando intento confirmar el pago."
     Decisión: Durante la integración se detectó que la combinación utilizada inicialmente con:
     payment_method_types=['card']
     
     
     generaba conflictos con la configuración actual del PaymentIntent. Se eliminó dicha configuración explícita y se dejó que Stripe determinara los métodos compatibles con la operación.
     También se corrigió el tratamiento de objetos devueltos por el SDK de Stripe, evitando utilizar accesos incompatibles mediante .get() sobre determinados StripeObject y utilizando sus atributos o conversión apropiada.
     Estos ajustes permitieron completar exitosamente la creación y confirmación del PaymentIntent.
  7. Confirmación definitiva mediante Webhook de Stripe:
     "El pago ya me aparece exitoso en Stripe, pero quiero que el estado en nuestra base cambie solamente cuando Stripe confirme realmente el pago."
     Decisión: Se evitó confiar únicamente en la respuesta recibida por el navegador. La confirmación definitiva se realiza mediante el evento:
     payment_intent.succeeded
     
     recibido en el webhook de Django.
     El flujo final quedó:
     PaymentIntent
           ↓
     Stripe procesa el pago
           ↓
     payment_intent.succeeded
           ↓
     Webhook Django
           ↓
     Se identifica la Transaccion
           ↓
     cambiar_estado_transaccion()
           ↓
     PAGADA
           ↓
     LogTransaccion
     
     Se utilizó metadata del PaymentIntent para mantener la asociación entre el pago realizado en Stripe y la transacción correspondiente de Global Exchange.
     De esta forma, aunque el usuario cierre la pestaña o ocurra un problema en el navegador después del pago, Stripe continúa siendo la fuente de confirmación del resultado.
  8. Sincronización visual después del pago con Stripe:
     "Stripe confirma el pago pero la página sigue mostrando pendiente hasta que recargo."
     Decisión: Se creó un endpoint para consultar el estado de la transacción y se implementó un mecanismo de actualización mediante JavaScript después de que confirmCardPayment() retorna correctamente.
     El navegador consulta periódicamente el estado durante unos segundos:
     Stripe confirma PaymentIntent
             ↓
     Navegador espera
             ↓
     Consulta estado de Transaccion
             ↓
     Webhook procesa evento
             ↓
     Transaccion PAGADA
             ↓
     Página se actualiza
     
     Esto evita marcar el pago como confirmado antes de que el webhook haya actualizado realmente la base de datos.
  9. Implementación de confirmación mediante SIPAP simulado:
     "Ahora quiero hacer SIPAP pero como simulación, porque obviamente no tenemos acceso al servicio real."
     Decisión: Se implementó un servicio independiente para SIPAP que simula la respuesta de una transferencia bancaria exitosa, manteniendo el mismo contrato conceptual que tendría una integración externa real.
     El flujo implementado quedó:
     Transaccion PENDIENTE
             ↓
     Usuario selecciona SIPAP
             ↓
     Confirmación simulada
             ↓
     sipap_service
             ↓
     Respuesta exitosa
             ↓
     cambiar_estado_transaccion()
             ↓
     PAGADA
             ↓
     LogTransaccion
     
     La simulación se mantuvo separada de Stripe para que una futura integración real con SIPAP pueda reemplazar exclusivamente el servicio correspondiente sin modificar todo el flujo de operaciones.
  10. Centralización del cambio de estado y auditoría:
      "Quiero que tanto Stripe como SIPAP utilicen el sistema de estados que ya tenemos y que quede registrado."
      Decisión: Tanto Stripe como SIPAP terminan utilizando el servicio central:
      cambiar_estado_transaccion(...)
      
      
      en lugar de realizar modificaciones directas sobre transaccion.estado.
      El servicio valida que solamente pueda producirse una transición válida desde:
      PENDIENTE
      
      hacia:
      PAGADA
      CANCELADA
      
      y genera automáticamente el correspondiente LogTransaccion, preservando la auditoría de las operaciones.
  11. Adaptación de la interfaz según el medio de pago:
      "Quiero que en el detalle aparezca la confirmación correspondiente dependiendo de si es tarjeta o SIPAP."
      Decisión: Se adaptó detalle_transaccion.html para mostrar diferentes acciones dependiendo del tipo de medio de pago y del estado actual de la transacción.
      Conceptualmente:
      PENDIENTE
      ├── TARJETA
      │     └── CVC + Confirmación Stripe
      │
      └── SIPAP
            └── Confirmación SIPAP simulada
      
      PAGADA
      └── Pago confirmado correctamente
      
      CANCELADA
      └── Operación cancelada
      
      También se mantuvo la información del medio de pago y los datos principales de la transacción sin exponer información sensible de tarjetas.
  12. Integración de Stripe dentro del entorno Docker:
      "¿Cómo instalo Stripe si estoy trabajando con Docker?"
      Decisión: Se determinó que el paquete Python debía agregarse de forma persistente a:
      app/requirements.txt
      
      y posteriormente reconstruir el servicio:
      docker compose up -d --build web
      
      La instalación temporal mediante pip install dentro de un contenedor en ejecución se descartó como solución permanente, ya que se perdería al reconstruir el contenedor.
      Stripe CLI permanece instalado en el sistema anfitrión y se utiliza exclusivamente para el reenvío de webhooks durante desarrollo local.
- Archivos Creados / Modificados:
  - operaciones/pagos/__init__.py: creación del paquete encargado de las integraciones de pago.
  - operaciones/pagos/stripe_service.py: lógica de creación y procesamiento de pagos mediante Stripe.
  - operaciones/pagos/sipap_service.py: simulación del proceso de confirmación mediante SIPAP.
  - operaciones/views.py: endpoints para inicio de pagos, confirmaciones, webhook de Stripe, consulta de estado y coordinación de los servicios de pago.
  - operaciones/services.py: utilización del servicio central de transición de estado y generación de auditoría.
  - operaciones/urls.py: incorporación de rutas necesarias para Stripe, SIPAP, webhook y consulta de estado.
  - operaciones/templates/operaciones/detalle_transaccion.html: interfaz diferenciada para confirmación mediante tarjeta Stripe o transferencia SIPAP y visualización del resultado del pago.
  - operaciones/templates/operaciones/operar.html: adaptación del proceso de creación y resumen de operaciones para seleccionar los medios de pago disponibles.
  - mpagos/models.py: incorporación de identificadores y metadatos necesarios para tarjetas tokenizadas con Stripe.
  - mpagos/forms.py: adaptación del registro y selección de tarjetas compatibles con Stripe.
  - mpagos/views.py: integración del proceso de registro seguro de tarjetas mediante Stripe Elements y SetupIntent.
  - mpagos/templates/mpagos/form.html: integración visual de Stripe Elements para captura segura de los datos de tarjeta.
  - mpagos/urls.py: incorporación de endpoints utilizados durante el registro de tarjetas.
  - clientes/models.py: incorporación del identificador stripe_customer_id para relacionar clientes locales con Stripe Customer.
  - core/settings.py: lectura y configuración de las claves de Stripe mediante variables de entorno.
  - .env.example: incorporación de las variables necesarias para configurar Stripe sin versionar credenciales reales.
  - requirements.txt: incorporación del SDK Python de Stripe.
  - clientes/migrations/0004_cliente_stripe_customer_id.py: migración correspondiente a la asociación del cliente con Stripe.
  - mpagos/migrations/0003_...py: migración correspondiente a los nuevos campos utilizados por las tarjetas Stripe.
  - operaciones/migrations/0006_alter_transaccion_estado.py: actualización del modelo de estados utilizado por el flujo de confirmación de pagos.
- Resultado / Decisión: Se implementó un flujo de confirmación de pagos integrado con la arquitectura existente de Global Exchange. Las operaciones permanecen inicialmente en estado PENDIENTE y solamente pasan a PAGADA cuando el proveedor correspondiente confirma el pago. Para tarjetas se incorporó Stripe en entorno Test Mode utilizando Stripe Elements, SetupIntent, PaymentIntent y Webhooks, sin almacenar números completos de tarjeta ni códigos CVC. La confirmación definitiva se realiza mediante payment_intent.succeeded, evitando depender únicamente de la respuesta del navegador. Para SIPAP se implementó una simulación desacoplada que reproduce el comportamiento esperado de un servicio externo y puede ser sustituida posteriormente por una integración real. Ambos mecanismos reutilizan cambiar_estado_transaccion() y LogTransaccion, conservando un único flujo de estados y auditoría para todas las operaciones y evitando crear implementaciones paralelas dentro del sistema.

---

### Registro #12 - 12/10/2026

* **Tarea / Historia**: Implementación de sistema de notificaciones por actualización de tasas de cambio
* **Autor**: Pablo Portillo
* **Herramienta / Modelo**: ChatGPT
* **Contexto / Objetivo**: Diseñar e implementar un sistema de notificaciones internas en Global Exchange para informar a los usuarios cuando un Analista Cambiario o Administrador General registra una nueva tasa de cambio. La funcionalidad debía integrarse con la arquitectura Django existente, reutilizar la campana del `layouts/base.html`, persistir el estado de lectura de cada usuario y mostrar un aviso al ingresar al Dashboard sin alterar el funcionamiento de los módulos existentes.

* **Prompts Determinantes Utilizados**:

  1. **Análisis de arquitectura y definición de la fuente de cotizaciones:**
     > *"Quiero seguir desarrollando y debo implementar notificaciones cuando hay cambios en las tasas de las divisas. Mi idea es que cuando el analista cambiario cambia una divisa esta se notifique dentro de Global Exchange y le llegue a cada usuario de la app, qué tasa cambió y a cuánto la compra y venta."*
     >
     > **Decisión**: Se determinó que la fuente de verdad para las cotizaciones debía continuar siendo `operaciones.TasaDeCambio`, descartando utilizar el modelo paralelo `cotizaciones.Cotizacion`. Se aprovechó el diseño histórico de `TasaDeCambio`, donde cada actualización crea un nuevo registro, permitiendo comparar la cotización anterior con la nueva sin sobrescribir información previa.

  2. **Diseño de la arquitectura de notificaciones:**
     > *"Decime qué archivos necesitás y te paso para ir armando el código."*
     >
     > **Decisión**: Se creó una aplicación independiente `notificaciones` para evitar acoplar la funcionalidad a `operaciones`, `caja` o `usuarios`. Se definieron dos modelos:
     >
     > - `Notificacion`: almacena una única vez el evento, tipo, título, mensaje, usuario creador y fecha.
     > - `NotificacionUsuario`: relaciona cada notificación con sus destinatarios y mantiene de forma individual los campos `leida` y `fecha_lectura`.
     >
     > Este diseño evita duplicar el contenido completo de una notificación para cada usuario y deja preparada la arquitectura para futuros avisos de pagos, operaciones y eventos del sistema.

  3. **Generación automática al actualizar una tasa:**
     > *"Vamos por el paso 2."*
     >
     > **Decisión**: Se creó `notificaciones/services.py` con el servicio `crear_notificacion_cambio_tasa()`. La vista `operaciones.views.crear_tasa()` fue adaptada para recuperar la última tasa de la moneda antes de guardar la nueva, permitiendo generar mensajes con los valores anteriores y actuales de compra y venta.
     >
     > El flujo implementado quedó definido como:
     >
     > ```text
     > Analista registra nueva tasa
     >         ↓
     > Se recupera la tasa anterior
     >         ↓
     > Se guarda TasaDeCambio
     >         ↓
     > Se crea Notificacion
     >         ↓
     > Se crean NotificacionUsuario
     > para los usuarios activos
     > ```
     >
     > Se utilizó `transaction.atomic()` para mantener el registro de la nueva tasa y la generación de su notificación dentro de una misma transacción de base de datos.

  4. **Integración de la campana de notificaciones en el layout global:**
     > *"Paso 3 seguimos."*
     >
     > **Decisión**: Se reutilizó la campana existente en `layouts/base.html` en lugar de crear una interfaz independiente. Se implementó `notificaciones.context_processors.notificaciones_context` para hacer disponibles las notificaciones recientes y el contador de no leídas en todas las páginas que heredan del layout principal.
     >
     > La campana muestra:
     >
     > - Cantidad de notificaciones pendientes.
     > - Últimas cinco notificaciones.
     > - Título y detalle del cambio.
     > - Tiempo transcurrido desde la actualización.
     > - Indicador visual para elementos no leídos.
     > - Acción individual para marcar como leída.
     > - Acción para marcar todas como leídas.
     >
     > Se agregaron endpoints protegidos mediante `login_required` y `POST` para actualizar el estado de lectura mediante AJAX sin necesidad de recargar la página.

  5. **Integración visual y corrección de estructura del Topbar:**
     > *"Antes de continuar me sale así. No sé si al colocar los div pasó algo raro."*
     >
     > **Decisión**: Se detectó una alteración en la jerarquía de los elementos del `topbar` producida al incorporar el nuevo dropdown. Se reorganizó la estructura HTML para mantener como elementos hermanos dentro de `.topbar-right` al selector de cliente, menú de notificaciones, divisores y menú del usuario.
     >
     > La estructura final quedó conceptualmente:
     >
     > ```text
     > .topbar-right
     > ├── selector de cliente
     > ├── divisor
     > ├── notification-menu
     > │   ├── campana
     > │   └── notification-dropdown
     > ├── divisor
     > └── user-menu
     > ```
     >
     > También se extendieron `layout.css` y `layout.js` respetando el diseño existente de Global Exchange.

  6. **Aviso automático al ingresar al Dashboard:**
     > *"Seguimos con el paso 4."*
     >
     > **Decisión**: Se agregó un aviso tipo *toast* para mostrar al usuario la notificación pendiente más reciente al ingresar al Dashboard. El identificador de la última notificación mostrada se almacena temporalmente en la sesión mediante `ge_ultima_notificacion_mostrada`, evitando mostrar repetidamente el mismo aviso en cada recarga.
     >
     > Mostrar el toast no marca automáticamente la notificación como leída. El estado pendiente continúa visible en la campana hasta que el usuario lo gestione explícitamente.
     >
     > El comportamiento definido fue:
     >
     > ```text
     > Usuario ingresa al Dashboard
     >         ↓
     > Se busca última notificación no leída
     >         ↓
     > ¿Ya fue mostrada en esta sesión?
     >         ↓ No
     > Se muestra Toast
     >         ↓
     > La notificación continúa pendiente en 🔔
     > ```
     >
     > El aviso puede cerrarse manualmente y también desaparece automáticamente después de unos segundos.

* **Archivos Creados / Modificados**:

  - `notificaciones/models.py`: modelos `Notificacion` y `NotificacionUsuario`.
  - `notificaciones/services.py`: servicio de generación y distribución de notificaciones por cambio de tasa.
  - `notificaciones/context_processors.py`: disponibilidad global de notificaciones recientes y contador de pendientes.
  - `notificaciones/views.py`: endpoints para marcar una o todas las notificaciones como leídas.
  - `notificaciones/urls.py`: rutas de acciones de lectura.
  - `core/settings.py`: registro de la app y del nuevo context processor.
  - `core/urls.py`: inclusión de rutas de `notificaciones`.
  - `operaciones/views.py`: integración de la generación de notificaciones en `crear_tasa()`.
  - `templates/layouts/base.html`: campana, contador y dropdown.
  - `main/views.py`: selección de la notificación a mostrar al ingresar al Dashboard.
  - `dashboard.html`: componente visual del toast.
  - `static/css/layout.css`: estilos del dropdown, contador y toast.
  - `static/js/layout.js`: apertura/cierre del dropdown, marcado AJAX y comportamiento del toast.

* **Resultado / Decisión**: Se implementó un sistema reutilizable de notificaciones internas integrado al diseño existente de Global Exchange. Los cambios de cotización generan una notificación persistente para los usuarios activos, mostrando los valores anteriores y nuevos de compra y venta. Cada usuario mantiene independientemente su estado de lectura, puede consultar los avisos desde la campana global y recibe un aviso visual al ingresar al Dashboard. La arquitectura queda preparada para reutilizar el mismo mecanismo con futuros eventos de pagos, operaciones y mensajes del sistema, sin crear implementaciones paralelas.