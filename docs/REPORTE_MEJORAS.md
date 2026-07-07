# Reporte de posibles mejoras y "plus" — holidays_co_full

**Fecha:** julio de 2026 · **Estado:** análisis inicial (nada implementado)

## 1. Punto de partida

La librería hoy resuelve muy bien un problema acotado:

- Festivos oficiales nacionales de Colombia, 1970–9999, con precisión
  histórica (Ley Emiliani desde 1984, `valid_from` por festivo,
  renombres oficiales).
- Utilidades de días hábiles: `is_business_day`, `add_business_days`,
  `business_days_between`, `business_days_until`, con la opción
  `include_saturday`.

## 2. Hallazgo clave sobre "cobertura por departamentos"

En Colombia **los festivos no laborables oficiales son nacionales**
(Ley 51 de 1983). A diferencia de España, Brasil o Argentina, no hay
festivos departamentales ni municipales con fuerza legal general. Es
decir: la librería ya "cubre" los 32 departamentos en lo oficial.

Lo que **sí varía por territorio** y afecta la operación real de
empresas e instituciones:

| Tipo | Ejemplos | Efecto práctico |
|---|---|---|
| Días cívicos locales (decreto de alcaldía/gobernación) | Cumpleaños de la ciudad, día del departamento | No laborable para sector público local; comercio abre |
| Eventos culturales masivos | Carnaval de Barranquilla (lun-mar antes de Ceniza), Feria de Cali (25-30 dic), Feria de las Flores, San Pacho (Quibdó), Semana Santa en Popayán | Muchas empresas locales cierran o reducen jornada; logística y bancos operan distinto |
| Calendarios sectoriales locales | Receso escolar de octubre (Decreto 1373 de 2007), vacancia judicial | Afecta plazos de sectores específicos |

**Propuesta:** una capa opcional de *eventos regionales* que no se
mezcle con los festivos oficiales:

- Nuevo tipo `RegionalEvent(date, name, department, municipality,
  dane_code, kind, affects_work)` con `kind` ∈ {`civic`, `cultural`,
  `sectorial`}.
- API: `get_regional_events(year, department="ATL")` y un parámetro
  opcional `region=` en las funciones de días hábiles para que quien lo
  necesite pueda tratar esos días como no hábiles.
- Datos en un archivo declarativo (JSON/YAML) versionado, con fuente
  legal o decreto citado por entrada — mismo estándar de rigor que ya
  usa la librería (leyes citadas en el código).

Riesgo a gestionar: los días cívicos locales se decretan año a año y
no siempre son predecibles. Conviene marcar cada entrada como
`recurring` o `decreed` y documentar que la capa regional es
"mejor esfuerzo", a diferencia del núcleo oficial que es exacto.

## 3. Módulos por dominio ("departamentos" funcionales)

Donde los días festivos y hábiles impactan de verdad es en dominios de
negocio. Ordenados por valor estimado:

### 3.1 Nómina / Talento Humano (mayor impacto)

- **Clasificación de horas y recargos**: dado un rango de fecha-hora,
  clasificar horas en ordinaria/nocturna/dominical/festiva y devolver
  el factor de recargo vigente. La reforma laboral (Ley 2466 de 2025)
  cambia el recargo dominical/festivo de forma gradual (80 % → 90 % en
  julio 2026 → 100 % en julio 2027) y adelanta el inicio de la jornada
  nocturna a las 7 p. m. Es exactamente el mismo patrón de "vigencia
  histórica" que ya maneja la librería con la Ley Emiliani, aplicado a
  factores en vez de fechas. *(Verificar fechas y porcentajes exactos
  contra el texto de la ley antes de implementar.)*
- **Jornada máxima legal**: `max_weekly_hours(date)` con la reducción
  gradual de la Ley 2101 de 2021 (46 h → 44 h → 42 h en julio 2026).
- **Vacaciones**: dado un inicio y N días hábiles de vacaciones,
  calcular fecha de reintegro (con la opción de sábado ya existente).
- **Suspensiones y licencias**: fecha de fin de una suspensión contada
  en días hábiles o calendario — caso de uso directo del portal de
  talento humano (suspensiones) ya en desarrollo.

### 3.2 Jurídico / Administrativo

- **Términos legales con catálogo**: `legal_deadline(start, kind)` con
  términos comunes ya parametrizados: derecho de petición (15 días
  hábiles), PQRS, recursos de reposición/apelación, etc. (CPACA,
  Ley 1437 de 2011).
- **Calendario judicial**: días hábiles judiciales ≠ días hábiles
  comunes — vacancia judicial (≈19 dic – 10 ene) y Semana Santa en
  algunas jurisdicciones. Sería un "perfil" de calendario adicional.

### 3.3 Financiero / Bancario

- **Perfil bancario**: los días bancarios ya se aproximan con
  `include_saturday=False`, pero para operaciones cambiarias el día
  hábil relevante es la intersección Colombia ∩ EE. UU. (festivos de la
  Fed). Función `is_fx_business_day(d)` con un calendario US mínimo.
- **Calendario tributario DIAN** (vencimientos por NIT): valioso pero
  cambia cada año por resolución; evaluar como paquete de datos anual
  opcional, no como parte del núcleo.

### 3.4 Educación y sector público

- Semana de receso estudiantil de octubre (Decreto 1373 de 2007) como
  evento sectorial calculable (primera semana antes del festivo del
  12 de octubre).
- Día de la Familia (Ley 1857 de 2017) como dato informativo.

## 4. Mejoras al núcleo de la librería

Independientes de los módulos anteriores, en orden de esfuerzo:

**Bajo esfuerzo (quick wins):**

- `previous_holiday(d)` — simétrico de `next_holiday`.
- `long_weekends(year)` — detectar puentes (festivo en lunes, o
  viernes/martes que generan fin de semana largo) y días "sándwich".
  Muy pedido en planeación de RR. HH. y turismo.
- Enriquecer `Holiday` con `original_date` (fecha natural antes del
  traslado), `is_shifted` y `kind` (`fixed`/`movable`/`easter`).
  Mantener compatibilidad: `namedtuple` con campos nuevos al final o
  migrar a `NamedTuple` tipado.
- `holidays_remaining(d)` — cuántos festivos quedan en el año.

**Esfuerzo medio:**

- Clase `HolidayCalendar(include_saturday=..., region=..., extra_holidays=...)`
  para no repetir flags en cada llamada y permitir calendarios
  empresariales personalizados (días de cierre propios de la compañía).
- Integración pandas/numpy: exponer un
  `pandas.tseries.offsets.CustomBusinessDay` y arrays compatibles con
  `numpy.busday_count` — abre la puerta al mundo analítica/finanzas.
- Export **iCal (.ics)** y JSON — consumo directo por Google
  Calendar/Outlook y por front-ends.
- CLI: `holidays-co 2026 --json`, `holidays-co next`,
  `holidays-co business-days 2026-07-01 2026-07-31`.
- i18n de nombres (es/en) vía parámetro `lang=`.

**Esfuerzo alto:**

- API REST de referencia (FastAPI) empaquetada como extra
  `pip install holidays_co_full[api]` — convierte la librería en
  servicio consumible por cualquier lenguaje/sistema interno.
- Capa regional del punto 2 (requiere curaduría de datos continua).

## 5. Priorización sugerida (primera iteración)

1. **Quick wins del núcleo** (`long_weekends`, `previous_holiday`,
   `Holiday` enriquecido) — poco código, mucho valor visible.
2. **Módulo nómina básico** (`max_weekly_hours`, recargos con
   vigencias, fin de suspensión en días hábiles) — conecta directo con
   el portal de talento humano y con la reforma laboral vigente.
3. **Export iCal/JSON + CLI** — discoverability y adopción.
4. **Perfil jurídico** (vacancia judicial + catálogo de términos).
5. **Capa regional de eventos** — de último por el costo de curaduría
   de datos, aunque es el "plus" más diferenciador frente a otras
   librerías de festivos.

## 6. Criterio transversal

Todo lo nuevo debería conservar las tres fortalezas actuales:
precisión histórica con fuente legal citada, validación estricta de
entradas y cero dependencias en el núcleo (pandas/FastAPI solo como
extras opcionales).
