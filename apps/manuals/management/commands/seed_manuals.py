"""Carga inicial de manuales de usuario detallados."""

from django.core.management.base import BaseCommand

from apps.manuals.models import ManualPage

# ---------------------------------------------------------------------------
# Estructura del manual
# ---------------------------------------------------------------------------
# Cada entrada es (slug, title, icon, parent_slug | None, sort, body_md)
# body_md siempre es Markdown.
# ---------------------------------------------------------------------------

PAGES: list[tuple[str, str, str, str | None, int, str]] = []


def _p(slug, title, icon, parent, sort, body):
    PAGES.append((slug, title, icon, parent, sort, body))


# ── 1. BIENVENIDA ──────────────────────────────────────────────────────────

_p("bienvenida", "Bienvenida a Comisiones", "👋", None, 0, """\
**¡Bienvenido a Comisiones!** Tu plataforma para gestionar comisiones de forma precisa, transparente y automatizada.

## ¿Qué puedes hacer aquí?

1. **Registrar eventos de comisión** — Cada venta, hora trabajada o acción que genere una comisión se registra como un *evento*.
2. **Definir planes y reglas** — Configura cómo se calcula cada comisión: porcentajes, montos fijos, tramos y más.
3. **Revisar y aprobar comisiones** — Supervisa las líneas de comisión generadas y apruébalas o recházalas antes de pagar.
4. **Consultar reportes** — Filtra por periodo, proyecto, equipo o empleado y exporta a Excel.

## Navegación principal

Cuando inicies sesión verás una **barra lateral izquierda** (sidebar) con las secciones del sistema. En **pantallas pequeñas** (celular o tablet), presiona el **ícono de tres líneas horizontales (☰)** en la esquina superior izquierda para abrir el menú.

> **Consejo:** Los enlaces que aparecen en la barra lateral dependen de tu rol. Si no ves alguna sección, pide a tu administrador que verifique tus permisos.

## ¿Necesitas ayuda?

Navega por las secciones de este manual usando el **índice de la izquierda**. También puedes usar el campo **Buscar** para encontrar rápidamente un tema.
""")

# ── 2. GUÍA DE INICIO RÁPIDO ──────────────────────────────────────────────

_p("inicio-rapido", "Guía de Inicio Rápido", "🚀", None, 1, """\
Sigue estos pasos para configurar tu empresa y empezar a registrar comisiones en minutos.

## Paso 1 — Registrar tu empresa

1. Desde la **página principal** (landing), haz clic en el botón naranja **"Registrar empresa"** en la esquina superior derecha.
2. Completa el formulario:
   - **Nombre de la empresa** — El nombre comercial de tu organización.
   - **Slug** — Un identificador corto sin espacios (se genera automáticamente a partir del nombre). Ejemplo: `mi-empresa`.
   - **Moneda base** — La moneda principal en la que manejas comisiones (por defecto MXN).
3. En la sección **Administrador**, ingresa tu correo electrónico y una contraseña segura.
4. Presiona el botón naranja **"Crear compañía y entrar"**.

> Se creará tu cuenta de administrador automáticamente y serás redirigido al Dashboard.

## Paso 2 — Crear proyectos y equipos

Antes de registrar eventos necesitas al menos un **proyecto** y un **equipo**:

1. En la barra lateral, busca la sección **Organización** y haz clic en **Proyectos**.
2. Presiona el botón azul **"Nuevo proyecto"** y completa nombre, slug y descripción.
3. Repite el proceso para **Equipos** (en la misma sección de Organización).
4. Entra al proyecto que creaste y en la sección derecha **"Equipos en el proyecto"**, usa el desplegable para seleccionar un equipo y presiona **"Añadir"**.

## Paso 3 — Dar de alta empleados

1. Ve a **Organización → Empleados** en la barra lateral.
2. Presiona **"Nuevo empleado"** y completa nombre, código y asigna los equipos y proyectos marcando las casillas correspondientes.

## Paso 4 — Configurar tipos de comisión

1. En la barra lateral, busca **Catálogo → Tipos de comisión**.
2. Presiona **"Nuevo tipo"** y define el nombre (por ejemplo: *Venta directa*, *Renovación*, *Referido*).
3. Entra al tipo recién creado y en la tabla **"Activar en proyectos"** presiona el botón **"Activar"** junto a cada proyecto donde aplique.

## Paso 5 — Crear un periodo

1. Ve a **Periodo y moneda → Periodos**.
2. Presiona **"Nuevo periodo"**, define un nombre (ej. *Abril 2026*), las fechas de inicio y fin, y deja el estado en **Borrador**.
3. Presiona **"Guardar"**.

## Paso 6 — Crear un plan y reglas

1. En **Planes y reglas** crea un nuevo plan y asígnale un equipo o empleados específicos.
2. Dentro del plan, presiona **"Nueva regla"** para definir cómo se calcula la comisión (porcentaje, monto fijo, etc.).

## Paso 7 — Registrar tu primer evento

1. Ve a **Operaciones → Registrar evento**.
2. Selecciona el periodo, proyecto, equipo, tipo de comisión y empleado.
3. Ingresa el monto y cualquier dato adicional.
4. Presiona el botón azul **"Guardar evento"**. El sistema calculará la comisión automáticamente.

## Paso 8 — Revisar y aprobar

1. Ve a **Operaciones → Resumen empleados** para ver las líneas de comisión generadas.
2. Usa los botones de estado para **Aprobar**, **Rechazar** o dejar como **Pendiente**.
""")

# ── 3. OPERACIONES (padre) ─────────────────────────────────────────────────

_p("operaciones", "Operaciones", "⚙️", None, 2, """\
La sección **Operaciones** es el corazón del día a día. Desde aquí registras eventos, consultas el resumen de comisiones por empleado y gestionas ajustes.

Las subsecciones son:

- **Inicio (Dashboard)** — Vista general con estadísticas y periodos recientes.
- **Registrar evento** — Formulario para capturar cada acción que genera comisión.
- **Resumen empleados** — Consulta detallada de las líneas de comisión por persona.
- **Ajustes** — Correcciones manuales sobre líneas o eventos.
""")

# ── 3.1 Dashboard ──────────────────────────────────────────────────────────

_p("dashboard", "Inicio (Dashboard)", "📊", "operaciones", 0, """\
El **Dashboard** es la primera pantalla que ves al iniciar sesión. Muestra un resumen rápido de tu actividad de comisiones.

## ¿Qué información encuentro aquí?

### Líneas pendientes

En la parte superior verás una tarjeta con el número de **líneas de comisión pendientes** que requieren revisión. Este número se actualiza cada vez que entras al Dashboard.

### Periodos recientes

Debajo se muestra una lista con los **periodos de comisión más recientes**, incluyendo:

- **Nombre del periodo** (por ejemplo, *Marzo 2026*).
- **Rango de fechas** (inicio y fin).
- **Estado** — Una etiqueta que indica si el periodo está en *Borrador*, *En revisión* o *Cerrado*.

### Recalcular un periodo

Si tienes permisos de administrador, junto a cada periodo verás un botón gris **"Recalcular"**.

> **¿Cuándo usarlo?** Cuando hayas modificado reglas, ajustado montos o añadido nuevos eventos y quieras que el sistema vuelva a procesar todas las comisiones de ese periodo.

1. Localiza el periodo que deseas recalcular en la lista.
2. Presiona el botón **"Recalcular"** a la derecha del periodo.
3. Verás un mensaje de confirmación en la parte superior de la pantalla indicando que el recálculo se ha puesto en cola.
4. El proceso se ejecuta en segundo plano. Refresca la página tras unos segundos para ver los resultados actualizados.

## Estado vacío

Si aún no has creado ningún periodo, verás un mensaje con un ícono de calendario y un enlace directo para **crear tu primer periodo**. Haz clic en él para ir a la sección de Periodos.
""")

# ── 3.2 Registrar evento ──────────────────────────────────────────────────

_p("registrar-evento", "Registrar Evento", "➕", "operaciones", 1, """\
Esta pantalla te permite capturar los eventos que generan comisiones: una venta, horas trabajadas, una renovación, etc.

## Estructura de la pantalla

La página se divide en **dos columnas**:

- **Izquierda — Formulario "Nuevo evento"**: aquí ingresas los datos del evento.
- **Derecha — "Últimos eventos"**: tabla con los eventos registrados recientemente donde puedes hacer ediciones rápidas.

## Campos del formulario

| Campo | Descripción | Notas |
|-------|-------------|-------|
| **Periodo** | Selecciona el periodo de comisión al que pertenece este evento. | Solo aparecen periodos no bloqueados. |
| **Proyecto** | El proyecto al que se asocia la actividad. | Al cambiar de proyecto, los campos de **Equipo** y **Tipo de comisión** se actualizan automáticamente para mostrar solo las opciones válidas para ese proyecto. |
| **Equipo** | El equipo responsable. | Se filtra según el proyecto seleccionado. |
| **Tipo de comisión** | Categoría de la comisión (ej. *Venta directa*). | Solo muestra los tipos activados para el proyecto elegido. |
| **Empleado** | La persona que realizó la actividad. | |
| **Clase de evento** | Texto libre que describe la naturaleza (ej. *venta*, *renovación*). | |
| **Fecha** | Fecha en que ocurrió el evento. | |
| **Monto** | Valor monetario asociado al evento. | |
| **Tipo de cambio** | Si la operación es en moneda extranjera, selecciona la tasa. | Opcional. |
| **Horas / Horario laboral** | Para comisiones basadas en tiempo. | Opcionales. |
| **Canal de venta** | Origen de la operación (ej. *online*, *presencial*). | Opcional. |
| **Notas** | Cualquier comentario adicional. | Opcional. |

## Guardar el evento

1. Completa todos los campos obligatorios (marcados con asterisco).
2. Presiona el botón azul **"Guardar evento"** en la parte inferior del formulario.
3. El sistema ejecuta automáticamente el motor de reglas y genera la línea de comisión correspondiente.
4. El evento aparecerá en la tabla **"Últimos eventos"** de la derecha.

## Edición rápida en la tabla

En la tabla de últimos eventos puedes modificar directamente:

- **Fecha** — Haz clic en la celda de fecha, selecciona la nueva fecha y el cambio se guarda automáticamente.
- **Monto** — Haz clic en la celda del monto, escribe el nuevo valor y presiona **Enter** o haz clic fuera. Se recalculará la comisión.

> **Nota:** Si tu rol es de *Auditor*, las celdas de fecha y monto aparecerán en modo solo lectura (no podrás editarlas).

## Sin acceso

Si no tienes equipos asignados y no tienes acceso general a la empresa, verás un mensaje indicando que no puedes registrar eventos. Contacta a tu administrador para que te asigne a un equipo.
""")

# ── 3.3 Resumen empleados ─────────────────────────────────────────────────

_p("resumen-empleados", "Resumen de Empleados", "👥", "operaciones", 2, """\
La pantalla de **Resumen de empleados** te permite consultar, filtrar y gestionar las líneas de comisión generadas por el sistema para cada persona.

## Filtros disponibles

En la parte superior encontrarás una barra de filtros con los siguientes campos:

- **Proyecto** — Filtra por un proyecto específico.
- **Equipo** — Filtra por equipo.
- **Periodo** — Selecciona el periodo de comisión.
- **Estado** — Filtra por estado de la línea (Pendiente, Aprobada, Rechazada, etc.).

Después de seleccionar los filtros deseados, presiona el botón azul **"Filtrar"** para aplicarlos.

## Exportar a Excel

En la esquina superior derecha verás un botón gris con ícono de descarga **"Exportar Excel"**. Al presionarlo se descargará un archivo `.xlsx` con los datos filtrados.

> Los filtros que hayas aplicado se mantienen al exportar: el archivo reflejará exactamente lo que ves en pantalla.

## Tarjetas por empleado

Debajo de los filtros, el sistema muestra una **tarjeta por cada empleado** que tiene líneas de comisión. Cada tarjeta incluye:

### Encabezado de la tarjeta
- **Nombre del empleado** a la izquierda.
- **Monto total** a la derecha, con el símbolo de la moneda.

### Líneas de comisión

Cada fila dentro de la tarjeta representa una **línea de comisión** y muestra:

- **Explicación** — Texto breve que describe cómo se calculó la comisión. Si es muy largo, se muestra truncado.
- **Monto** de la línea.
- **Indicador de tipo de cambio** — Si aplica, verás una etiqueta pequeña con la moneda y la tasa utilizada.
- **Estado** — Una etiqueta de color:
  - 🟡 **Pendiente** — Amarilla/neutra. La línea aún no ha sido revisada.
  - 🔵 **Pendiente de aprobación** — Azulada. Requiere que un supervisor la apruebe.
  - 🟢 **Aprobada** — Verde. Lista para pago.
  - 🔴 **Rechazada** — Roja. La línea fue rechazada.
  - ⚫ **Ajustada** — Gris oscura. Se aplicó un ajuste manual.
  - 🟣 **Pagada** — Púrpura/morada. El pago ya se realizó.

### Botones de acción

Dependiendo de tu rol, junto a cada línea aparecerán botones:

- **"Más detalles"** — Botón gris con borde. Te lleva a la **vista de detalle de la línea** donde puedes ver toda la información del evento original y la explicación completa del cálculo.
- **"Aprobar"** — Botón verde con borde. Cambia el estado de la línea a *Aprobada*.
- **"Rechazar"** — Botón rojo con borde. Cambia el estado a *Rechazada*.
- **"Marcar pendiente"** — Botón gris con borde. Devuelve la línea al estado *Pendiente*.

> **Importante:** Solo los administradores de la empresa y los líderes de equipo pueden aprobar o rechazar líneas de comisión. Si no ves estos botones, es porque tu rol no tiene ese permiso.

## Detalle de una línea

Al presionar **"Más detalles"** en cualquier línea, se abre una página con dos tarjetas:

1. **Evento original** — Muestra todos los datos del evento que generó la comisión (proyecto, fecha, monto, empleado, etc.).
2. **Línea de comisión** — Detalla el monto calculado, la regla aplicada, la explicación del cálculo y el estado actual.

En esta vista también puedes cambiar el estado de la línea usando los botones de la parte inferior. Presiona **"Volver"** para regresar al resumen.
""")

# ── 3.4 Ajustes ───────────────────────────────────────────────────────────

_p("ajustes", "Ajustes Manuales", "💲", "operaciones", 3, """\
Los **ajustes** son correcciones manuales que puedes aplicar sobre una línea de comisión o un evento. Se usan cuando necesitas realizar una modificación que el motor de reglas no contempla automáticamente.

## Lista de ajustes

Al entrar a **Operaciones → Ajustes**, verás una tabla con los ajustes ya creados. Las columnas son:

| Columna | Descripción |
|---------|-------------|
| **Tipo** | La categoría del ajuste (Corrección, Reembolso, Suspensión, Descuento extra, Otro). |
| **Monto** | El valor del ajuste (positivo o negativo). |
| **Motivo** | Texto explicativo de por qué se realizó. |
| **Línea / Evento** | Referencia a la línea de comisión o evento asociado. |

## Crear un nuevo ajuste

1. Presiona el botón azul **"Nuevo ajuste"** en la esquina superior derecha.
2. En el formulario:
   - **Selecciona si el ajuste aplica a una Línea o a un Evento** usando los botones de opción (radio buttons).
   - **Tipo de ajuste** — Elige entre:
     - *Corrección* — Para corregir un error de cálculo.
     - *Reembolso* — Devolver un monto cobrado.
     - *Suspensión* — Cancelar temporalmente una comisión.
     - *Descuento extra* — Aplicar un descuento adicional.
     - *Otro* — Cualquier caso especial.
   - **Monto** — Ingresa el valor del ajuste. Usa valores negativos para reducciones.
   - **Motivo** — Describe brevemente la razón del ajuste (obligatorio).
3. Presiona el botón azul **"Guardar"** para crear el ajuste.
""")

# ── 4. PLANES Y REGLAS (padre) ────────────────────────────────────────────

_p("planes-reglas", "Planes y Reglas", "📋", None, 3, """\
Los **Planes de comisión** y las **Reglas** son el motor que define cómo se calculan las comisiones automáticamente.

- Un **Plan** es un contenedor con nombre que agrupa una o más reglas y se asigna a equipos y/o empleados específicos.
- Una **Regla** define las condiciones y la acción a ejecutar (porcentaje, monto fijo, tramos, etc.).

> **Ejemplo:** El plan *"Ventas Q2 2026"* puede tener una regla que dice: *"Si el tipo de comisión es Venta directa, pagar el 10% del monto."*

## Flujo general

```
Plan ──┬── Regla 1 (prioridad 1)
       ├── Regla 2 (prioridad 2)
       └── Regla 3 (prioridad 3)
       │
       ├── Asignación: Equipo Ventas
       └── Asignación: Empleado Juan Pérez
```

Cuando se registra un evento, el sistema busca los planes aplicables al empleado (por equipo o asignación directa) y ejecuta las reglas en orden de prioridad.
""")

# ── 4.1 Planes ─────────────────────────────────────────────────────────────

_p("planes", "Gestión de Planes", "📄", "planes-reglas", 0, """\
## Lista de planes

Al entrar a **Planes y reglas** verás una cuadrícula de tarjetas, una por cada plan existente. Cada tarjeta muestra:

- **Nombre** del plan.
- Etiqueta **Activo** o **Inactivo**.
- Etiqueta **Global** si el plan aplica a toda la empresa.
- **Proyecto** al que está asociado (si tiene uno).
- **Rango de fechas** de vigencia (si se definió).

Haz clic en la tarjeta para abrir el **detalle del plan**, o presiona el texto **"Editar"** que aparece al lado de "Abrir" para ir directamente al formulario de edición.

Si no hay planes creados, verás un mensaje con un botón azul **"Crear primer plan"**.

## Crear un plan nuevo

1. Presiona el botón azul **"Nuevo plan"** (con ícono **+**) en la esquina superior derecha.
2. Completa el formulario:
   - **Nombre** — Un nombre descriptivo (ej. *"Comisiones Ventas Abril"*).
   - **Descripción** — Texto opcional para documentar el propósito del plan.
   - **Proyecto** — Si el plan aplica solo a un proyecto, selecciónalo aquí. Si aplica a todos, deja vacío.
   - **Válido desde / Válido hasta** — Fechas opcionales de vigencia.
   - **Activo** — Casilla marcada por defecto. Desmárcala si quieres crear el plan sin que entre en funcionamiento aún.
   - **Global** — Marca esta casilla si el plan debe aplicarse a todos los empleados de la empresa (sin importar equipo).
3. Presiona el botón azul **"Guardar"**.

## Detalle de un plan

Al abrir un plan verás:

### Información general
- Nombre, estado (Activo/Inactivo), si es Global, proyecto asociado y fechas de vigencia.
- Botón gris **"Editar"** (ícono de lápiz) para modificar los datos del plan.
- Botón rojo **"Eliminar"** (ícono de papelera) que abre una ventana de confirmación.

### Pestañas

El detalle tiene **dos pestañas**:

#### Pestaña "Reglas"
Muestra una tabla con las reglas del plan:
| Columna | Descripción |
|---------|-------------|
| **#** | Número de fila. |
| **Nombre** | Nombre de la regla (enlace a edición). |
| **Tipo comisión** | Tipo de comisión asociado. |
| **Alcance** | Proyecto y/o equipo al que aplica. |
| **Acción** | Descripción breve del cálculo (ej. *Porcentaje: 10%*). |

Presiona el botón azul **"Nueva regla"** para agregar una regla a este plan.

#### Pestaña "Asignaciones"
Dos tarjetas lado a lado:

- **Equipos asignados** — Lista de equipos con fechas de vigencia. Usa el formulario inferior para seleccionar un equipo y presionar **"Añadir equipo"**. Para remover uno existente, presiona el ícono rojo **✕** junto al nombre.
- **Empleados asignados** — Mismo funcionamiento pero para empleados individuales.

## Eliminar un plan

1. En el detalle del plan, presiona el botón rojo **"Eliminar"** (ícono de papelera).
2. Se abrirá una ventana emergente que dice: *"¿Eliminar plan [nombre]?"*
3. Presiona el botón rojo **"Eliminar definitivamente"** para confirmar, o **"Cancelar"** para volver.

> **Advertencia:** Eliminar un plan elimina también todas sus reglas y asignaciones. Las líneas de comisión ya calculadas conservan una copia de la regla utilizada.
""")

# ── 4.2 Reglas ─────────────────────────────────────────────────────────────

_p("reglas", "Configuración de Reglas", "🔧", "planes-reglas", 1, """\
Las **reglas** definen la lógica de cálculo. Cada regla pertenece a un plan y tiene condiciones, una acción y una prioridad.

## Crear o editar una regla

Al presionar **"Nueva regla"** desde un plan (o al editar una existente) se abre un formulario extenso dividido en secciones:

### Sección 1 — Identidad y alcance

- **Nombre** — Nombre descriptivo de la regla.
- **Plan** — Ya estará preseleccionado si viniste desde un plan.
- **Tipo de comisión** — El tipo al que aplica esta regla (obligatorio).
- **Proyecto** — Opcional; limita la regla a un proyecto.
- **Equipo** — Opcional; limita la regla a un equipo.
- **Prioridad** — Número entero. Las reglas se evalúan de **menor a mayor** prioridad. Si dos reglas tienen la misma prioridad, se evalúan por orden de creación.
- **Detener procesamiento** — Si marcas esta casilla, cuando esta regla se aplique, el sistema no evaluará las reglas de prioridad inferior.
- **Válido desde / hasta** — Fechas opcionales de vigencia de la regla.
- **Activa** — Casilla para activar o desactivar la regla sin eliminarla.

### Sección 2 — Condiciones

Puedes definir condiciones de dos formas:

1. **Constructor visual** — Usa los desplegables para seleccionar campo, operador y valor. Por ejemplo:
   - *Campo:* `event_kind` *Operador:* `equals` *Valor:* `venta`
   - Esto hará que la regla solo se aplique cuando el evento sea de tipo "venta".

2. **JSON avanzado** — Para usuarios técnicos, puedes escribir las condiciones directamente en formato JSON.

> Si no defines condiciones, la regla se aplicará a **todos** los eventos que coincidan con el tipo de comisión y alcance.

### Sección 3 — Acción

Selecciona qué hacer cuando las condiciones se cumplan:

- **Porcentaje** — Calcula un % del monto del evento. Al seleccionarlo aparecerá un campo para ingresar el valor (ej. `10` para el 10%).
- **Monto fijo** — Asigna un monto fijo por evento.
- **Tramos** — Define rangos escalonados (ej. de 0 a 10,000 pagar 5%; de 10,001 a 50,000 pagar 8%).

También verás **presets rápidos** (botones de acceso directo) para configuraciones comunes:
- *10%*, *20%*, *Fijo*, *Tramos* — Presiona uno de estos botones grises para precargar la configuración.

### Guardar

Presiona el botón azul **"Guardar"** en la parte inferior. La regla quedará vinculada al plan y empezará a aplicarse en los próximos cálculos (si está activa y el plan está activo).
""")

# ── 5. CATÁLOGO (padre) ───────────────────────────────────────────────────

_p("catalogo", "Catálogo", "🏷️", None, 4, """\
El **Catálogo** contiene la configuración de los tipos de comisión que maneja tu empresa. Desde aquí defines las categorías que se utilizan al registrar eventos y configurar reglas.
""")

# ── 5.1 Tipos de comisión ─────────────────────────────────────────────────

_p("tipos-comision", "Tipos de Comisión", "🏷️", "catalogo", 0, """\
Los **tipos de comisión** clasifican los eventos. Ejemplos comunes: *Venta directa*, *Renovación*, *Referido*, *Hora extra*.

## Lista de tipos

En la tabla verás:
| Columna | Descripción |
|---------|-------------|
| **Nombre** | Nombre del tipo de comisión. |
| **Slug** | Identificador corto en minúsculas. |
| **Editar / proyectos** | Enlace para ver el detalle y gestionar en qué proyectos está activo. |

Presiona el botón azul **"Nuevo tipo"** para crear uno.

## Crear un tipo de comisión

1. Presiona **"Nuevo tipo"**.
2. Completa:
   - **Nombre** — El nombre visible (ej. *Venta directa*).
   - **Slug** — Identificador único (ej. `venta-directa`). Se genera solo al escribir el nombre.
   - **Descripción** — Texto opcional para documentar cuándo se usa este tipo.
3. Presiona **"Guardar"**.

## Detalle y activación en proyectos

Al entrar al detalle de un tipo, verás:

- **Izquierda** — Formulario para editar nombre, slug y descripción. Presiona **"Guardar"** para aplicar cambios.
- **Derecha — "Activar en proyectos"** — Tabla con todos los proyectos de la empresa:

| Columna | Descripción |
|---------|-------------|
| **Proyecto** | Nombre del proyecto. |
| **Estado** | *Activo* (verde) o *Inactivo* (gris). |
| **Acción** | Botón **"Activar"** o **"Desactivar"**. |

Para que un tipo de comisión esté disponible al registrar eventos en un proyecto, debe estar **activado** para ese proyecto. Presiona el botón correspondiente para cambiar su estado.
""")

# ── 6. PERIODO Y MONEDA (padre) ───────────────────────────────────────────

_p("periodo-moneda", "Periodo y Moneda", "📅", None, 5, """\
Esta sección contiene la gestión de **periodos de comisión** (los intervalos de tiempo para agrupar eventos) y los **tipos de cambio** (tasas de conversión de moneda).
""")

# ── 6.1 Periodos ──────────────────────────────────────────────────────────

_p("periodos", "Periodos de Comisión", "📅", "periodo-moneda", 0, """\
Un **periodo** es un rango de fechas que agrupa eventos de comisión (por ejemplo, un mes, una quincena o un trimestre).

## Lista de periodos

La tabla muestra:
| Columna | Descripción |
|---------|-------------|
| **Nombre** | Nombre del periodo (ej. *Abril 2026*). |
| **Inicio** | Fecha de inicio. |
| **Fin** | Fecha de fin. |
| **Estado** | *Borrador*, *En revisión* o *Cerrado*. |
| **Bloqueado** | Indica si el periodo está bloqueado para ediciones. |
| **Editar** | Enlace al formulario de edición. |

Presiona el botón azul **"Nuevo periodo"** para crear uno.

## Crear o editar un periodo

El formulario tiene las siguientes secciones:

### Identificación
- **Nombre** — Un nombre descriptivo (ej. *Marzo 2026*, *Q1 2026*).

### Fechas
- **Fecha de inicio** — Primer día del periodo.
- **Fecha de fin** — Último día del periodo.

### Estado y tipo de cambio
- **Estado** — Selecciona entre:
  - **Borrador** — El periodo está en preparación. Se pueden añadir y modificar eventos libremente.
  - **En revisión** — El periodo está siendo revisado. Los eventos ya no deberían modificarse.
  - **Cerrado** — El periodo se ha cerrado. No se permiten cambios.
- **Política de tipo de cambio** — Define cómo se determina la tasa de cambio:
  - *Fecha de la operación* — Usa la tasa vigente en la fecha del evento.
  - *Fin de periodo* — Usa la tasa vigente al último día del periodo.

### Bloqueado
- **Bloqueado** — Casilla que impide cualquier modificación sobre eventos y líneas del periodo, independientemente del estado.

Presiona el botón azul **"Guardar"** para aplicar los cambios.

> **Consejo:** En la barra lateral derecha del formulario encontrarás explicaciones detalladas sobre cada estado y la política de tipo de cambio.
""")

# ── 6.2 Tipo de cambio ────────────────────────────────────────────────────

_p("tipo-cambio", "Tipo de Cambio (FX)", "💱", "periodo-moneda", 1, """\
Si tu empresa maneja operaciones en más de una moneda, aquí gestionas las **tasas de cambio** (FX rates).

## ¿Qué es una tasa de cambio?

La tasa representa cuántas unidades de tu **moneda base** (configurada en Ajustes de empresa, por defecto MXN) equivalen a **1 unidad** de otra moneda.

> **Ejemplo:** Si tu moneda base es MXN y 1 USD = 17.50 MXN, el valor de la tasa para USD es `17.50`.

## Agregar o actualizar una tasa

En la parte superior de la página verás una tarjeta con tres campos:

1. **Moneda** — Escribe el código de 3 letras (ej. `USD`, `EUR`, `COP`).
2. **Fecha** — Selecciona la fecha para la que aplica la tasa.
3. **Valor** — Ingresa el valor numérico de la tasa.

Presiona el botón azul **"Guardar"** debajo de los campos. Si ya existe una tasa para esa moneda y fecha, se actualizará. Si no, se creará una nueva.

> La tabla de tasas se actualiza automáticamente sin recargar la página al guardar.

## Tabla de tasas

Debajo del formulario verás la tabla con todas las tasas registradas:

| Columna | Descripción |
|---------|-------------|
| **Fecha** | Fecha de la tasa. |
| **Moneda** | Código de la moneda. |
| **Valor** | Tasa actual. Este campo es **editable directamente**: haz clic sobre el número, escríbelo nuevo y el cambio se guarda automáticamente después de un breve instante. |
| **Fuente** | Indica cómo se registró la tasa (ej. *manual*). |

> **Nota:** Solo los administradores de la empresa pueden crear o editar tasas de cambio.
""")

# ── 7. ORGANIZACIÓN (padre) ───────────────────────────────────────────────

_p("organizacion", "Organización", "🏢", None, 6, """\
La sección de **Organización** te permite gestionar la estructura de tu empresa: proyectos, equipos y empleados. Estos son los bloques fundamentales sobre los que se construyen las comisiones.
""")

# ── 7.1 Proyectos ─────────────────────────────────────────────────────────

_p("proyectos", "Proyectos", "📁", "organizacion", 0, """\
Los **proyectos** representan las unidades de negocio o clientes para los que se generan comisiones.

## Lista de proyectos

Verás una tabla con:
| Columna | Descripción |
|---------|-------------|
| **Nombre** | Nombre del proyecto. |
| **Slug** | Identificador corto. |
| **Estado** | Etiqueta *Activo* (verde) o *Inactivo* (roja). |
| **Editar** | Enlace al detalle. |

Presiona el botón azul **"Nuevo proyecto"** para crear uno.

## Crear un proyecto

1. Presiona **"Nuevo proyecto"**.
2. Completa:
   - **Nombre** — Nombre completo del proyecto.
   - **Slug** — Identificador URL-friendly (se autocompleta).
   - **Descripción** — Texto libre para documentar el proyecto.
   - **Activo** — Marca la casilla si el proyecto está operativo.
3. Presiona el botón azul **"Guardar"**.

## Detalle del proyecto

Al hacer clic en un proyecto, verás dos secciones:

### Datos del proyecto (izquierda)
Formulario editable con los mismos campos de creación. Presiona **"Guardar"** para aplicar cambios.

### Equipos en el proyecto (derecha)
Lista de equipos actualmente vinculados al proyecto. Cada uno tiene un botón rojo **"Quitar"** para desvincularlo.

Para agregar un equipo:
1. En el desplegable inferior, selecciona el equipo deseado.
2. Presiona el botón azul **"Añadir"**.

> Un equipo debe estar vinculado a un proyecto para que sus empleados puedan registrar eventos en ese proyecto.
""")

# ── 7.2 Equipos ───────────────────────────────────────────────────────────

_p("equipos", "Equipos", "👥", "organizacion", 1, """\
Los **equipos** agrupan empleados y determinan quién puede registrar eventos y recibir comisiones en cada proyecto.

## Lista de equipos

Tabla con columnas:
| Columna | Descripción |
|---------|-------------|
| **Nombre** | Nombre del equipo (ej. *Ventas Norte*). |
| **Slug** | Identificador corto. |
| **Estado** | *Activo* o *Inactivo*. |
| **Editar** | Enlace al formulario. |

Presiona el botón azul **"Nuevo equipo"** para crear uno.

## Crear o editar un equipo

1. **Nombre** — Nombre descriptivo del equipo.
2. **Slug** — Se genera automáticamente.
3. **Activo** — Marca la casilla si el equipo está en operación.
4. Presiona **"Guardar"**.

> **Uso operativo:** Al registrar un evento de comisión, el formulario filtrará los equipos según el proyecto seleccionado. Asegúrate de vincular cada equipo a los proyectos correspondientes desde la pantalla de detalle del proyecto.
""")

# ── 7.3 Empleados ─────────────────────────────────────────────────────────

_p("empleados", "Empleados", "🧑‍💼", "organizacion", 2, """\
Los **empleados** son las personas que reciben comisiones. Cada empleado puede pertenecer a uno o más equipos y proyectos.

## Lista de empleados

Tabla con:
| Columna | Descripción |
|---------|-------------|
| **Nombre** | Nombre completo del empleado. |
| **Código** | Identificador interno (ej. número de nómina). |
| **Equipos** | Equipos a los que pertenece. |
| **Activo** | Estado del empleado. |
| **Editar** | Enlace al formulario. |

Presiona el botón azul **"Nuevo empleado"** para dar de alta uno.

## Crear o editar un empleado

El formulario tiene las siguientes secciones:

### Nombre
- **Nombre** y **Apellido** — Campos obligatorios.

### Identificadores
- **Código de empleado** — Identificador opcional (ej. número de nómina, matrícula).
- **Usuario del sistema** — Si el empleado tiene cuenta en la plataforma, selecciónalo aquí para vincular su perfil.

### Equipos y proyectos
Verás dos áreas con **casillas de verificación** (checkboxes):
- **Equipos** — Marca todos los equipos a los que pertenece el empleado. Puedes desplazarte si hay muchos.
- **Proyectos** — Marca los proyectos en los que participa directamente.

### Estado
- **Activo** — Casilla marcada por defecto. Desmárcala si el empleado ya no está en operación.

Presiona **"Guardar"** para aplicar los cambios.

> **Consejo:** En la barra lateral derecha del formulario encontrarás una nota sobre el **alcance**: los empleados solo pueden recibir comisiones en los proyectos y equipos a los que estén asignados.
""")

# ── 8. GESTIÓN DE USUARIOS (padre) ────────────────────────────────────────

_p("gestion-usuarios", "Gestión de Usuarios", "👤", None, 7, """\
Esta sección está disponible para **administradores** y permite gestionar las cuentas de usuario, sus roles y permisos dentro de la empresa.
""")

# ── 8.1 Usuarios ──────────────────────────────────────────────────────────

_p("usuarios", "Usuarios y Roles", "🔑", "gestion-usuarios", 0, """\
## Lista de usuarios

Al entrar a **Gestión → Usuarios** verás una tabla con todos los miembros de la empresa:

| Columna | Descripción |
|---------|-------------|
| **Email** | Correo electrónico del usuario. |
| **Rol** | Rol asignado dentro de la empresa. |
| **Empleado vinculado** | Si el usuario está vinculado a un registro de empleado. |
| **Equipos / Alcances** | Equipos y proyectos a los que tiene acceso. |

Presiona el botón azul **"Nuevo miembro"** para invitar a alguien.

## Roles disponibles

El sistema cuenta con los siguientes roles, de mayor a menor nivel de permisos:

| Rol | Descripción |
|-----|-------------|
| **Super Admin** | Acceso total a todas las empresas y funciones. Solo para el propietario de la plataforma. |
| **Admin de Empresa** | Control total sobre la empresa: configuración, catálogos, usuarios, aprobaciones. |
| **Líder de Comisiones** | Puede gestionar planes, reglas y aprobar comisiones a nivel empresa. |
| **Supervisor** | Gestiona y aprueba comisiones de sus equipos asignados. |
| **Colaborador** | Puede registrar eventos y ver sus propias comisiones. |
| **Auditor** | Acceso de solo lectura a toda la información. No puede modificar datos. |

## Crear un usuario

1. Presiona **"Nuevo miembro"**.
2. Completa:
   - **Email** — Correo del nuevo usuario.
   - **Contraseña** — Puede definirse ahora o el usuario la configura después.
   - **Rol** — Selecciona el rol apropiado del desplegable.
   - **Crear empleado** — Marca esta casilla si deseas crear automáticamente un registro de empleado vinculado al usuario.
   - **Equipos** — Selecciona los equipos a los que tendrá acceso.
   - **Líder de equipo** — Marca los equipos donde este usuario será líder (puede aprobar comisiones del equipo).
3. Presiona **"Guardar"**.

## Editar un usuario

Al hacer clic en **"Editar"** junto a un usuario puedes:
- Cambiar su **rol**.
- Modificar sus **equipos** asignados y sus roles de líder.
- Vincular o desvincular un **empleado**.
""")

# ── 9. AJUSTES (padre) ──────────────────────────────────────────────────

_p("configuracion", "Ajustes del Sistema", "⚙️", None, 8, """\
La sección de **Ajustes** te permite personalizar tu cuenta, perfil y la configuración de tu empresa.

Accede desde el botón **"Ajustes"** en la parte inferior de la barra lateral.
""")

# ── 9.1 Cuenta ───────────────────────────────────────────────────────────

_p("ajustes-cuenta", "Ajustes de Cuenta", "👤", "configuracion", 0, """\
Desde aquí puedes actualizar tus datos personales y cambiar tu contraseña.

## Datos personales

1. En la barra lateral, presiona **"Ajustes"** (parte inferior).
2. Verás la sección **"Datos"** con los siguientes campos:
   - **Email** — Tu correo electrónico de acceso.
   - **Nombre** — Tu nombre.
   - **Apellido** — Tu apellido.
3. Modifica los campos que desees.
4. Presiona el botón azul **"Guardar datos"**.

## Cambiar contraseña

Debajo de los datos personales encontrarás la sección **"Contraseña"**:

1. **Contraseña actual** — Ingresa tu contraseña vigente.
2. **Nueva contraseña** — Escribe la nueva contraseña.
3. **Confirmar nueva contraseña** — Repítela para verificar.
4. Presiona el botón azul **"Cambiar contraseña"**.

> Si olvidaste tu contraseña, contacta a un administrador de la empresa para que la restablezca.
""")

# ── 9.2 Empresa ──────────────────────────────────────────────────────────

_p("ajustes-empresa", "Ajustes de Empresa", "🏢", "configuracion", 1, """\
Solo los **administradores** pueden modificar la configuración de la empresa.

## Campos disponibles

- **Nombre de la empresa** — El nombre comercial que aparece en la plataforma.
- **Moneda base** — La moneda principal para calcular comisiones y mostrar montos. Todas las tasas de cambio se expresan en relación a esta moneda.

Modifica los campos y presiona el botón azul **"Guardar"**.

> **Importante:** Cambiar la moneda base afecta la interpretación de las tasas de cambio existentes. Se recomienda definirla al inicio y no modificarla después si ya tienes datos registrados.
""")


class Command(BaseCommand):
    help = "Crea las páginas del manual de usuario con contenido detallado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina todas las páginas existentes antes de crear las nuevas.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = ManualPage.objects.all().delete()
            self.stdout.write(f"  Eliminadas {deleted} páginas existentes.")

        slug_to_obj: dict[str, ManualPage] = {}
        created = 0
        updated = 0

        for slug, title, icon, parent_slug, sort, body in PAGES:
            parent = slug_to_obj.get(parent_slug) if parent_slug else None
            obj, is_new = ManualPage.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "icon": icon,
                    "parent": parent,
                    "sort_order": sort,
                    "content_format": "markdown",
                    "body": body.strip(),
                    "is_published": True,
                },
            )
            slug_to_obj[slug] = obj
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Manual de usuario: {created} creadas, {updated} actualizadas."
            )
        )
