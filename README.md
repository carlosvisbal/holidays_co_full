# holidays_co_full

[![PyPI version](https://img.shields.io/pypi/v/holidays_co_full.svg)](https://pypi.org/project/holidays_co_full/)
[![Python versions](https://img.shields.io/pypi/pyversions/holidays_co_full.svg)](https://pypi.org/project/holidays_co_full/)
[![Tests](https://github.com/carlosvisbal/holidays_co_full/actions/workflows/tests.yml/badge.svg)](https://github.com/carlosvisbal/holidays_co_full/actions/workflows/tests.yml)
[![PyPI downloads](https://img.shields.io/pypi/dm/holidays_co_full.svg)](https://pypi.org/project/holidays_co_full/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/carlosvisbal/holidays_co_full/blob/main/LICENSE)

🇨🇴 Español | [🇬🇧 English](README.en.md)

**Días festivos no laborables en Colombia**, calculados para cualquier año entre 1970 y 9999 según la [Ley 51 de 1983](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4954) (Ley Emiliani), con utilidades de días hábiles para nóminas, vencimientos y planeación.

Esta versión es una **extensión** de la librería original publicada en [PyPI](https://pypi.org/project/holidays-co/) (v1.0.0, que solo incluía `get_colombia_holidays_by_year` e `is_holiday_date`). Mantiene compatibilidad total con esa API y añade: precisión histórica del calendario, consulta del nombre del festivo, búsqueda del próximo festivo y del anterior, festivos por rango de fechas, detección de puentes, todo el conjunto de utilidades de días hábiles, calendarios configurables por empresa, exportación a JSON e iCalendar, integración con pandas y una CLI (`holidays-co`).

- Sin dependencias externas: solo usa la librería estándar de Python 3.
- Resultados cacheados en memoria: consultar el mismo año repetidamente tiene costo despreciable.
- Fechas ya resueltas: los festivos trasladables se devuelven en su día efectivo de celebración.
- Precisión histórica: el traslado al lunes solo se aplica desde 1984 y cada festivo solo aparece a partir de su año de vigencia (ver [Precisión histórica](#precisión-histórica)).
- Tipado: incluye anotaciones de tipo y el marcador `py.typed` ([PEP 561](https://peps.python.org/pep-0561/)) para autocompletado y chequeo estático con mypy/pyright.

## ¿Por qué esta librería?

Hay alternativas genéricas multi-país (como [`holidays`](https://pypi.org/project/holidays/)) que también cubren Colombia. `holidays_co_full` está pensada para cuando Colombia *es* el problema, no un país más de una lista:

| | `holidays_co_full` | Librerías genéricas multi-país |
|---|---|---|
| Traslado al lunes solo desde 1984 (Ley Emiliani) | Sí, por año consultado | Normalmente aplican la regla actual a todo el histórico |
| Festivo con año de vigencia propio (9 de julio desde 2026) | Sí (`valid_from`) | Requiere mantenimiento manual por país |
| Nombre oficial vigente por año (12 de octubre) | Sí (`renamed_to`/`renamed_from`) | Poco común |
| Utilidades de días hábiles (`add_business_days`, `business_days_between`, `business_days_until`) | Incluidas, con `include_saturday` | Variable según librería |
| Dependencias externas | Ninguna | Depende de la librería |

Si solo necesitas saber si una fecha es festivo en cualquier país del mundo, una librería genérica puede bastar. Si trabajas con nóminas, vencimientos legales o planeación en Colombia y necesitas exactitud histórica y días hábiles, esta librería está construida específicamente para eso.

## Instalación

```shell
pip install holidays_co_full
```

¿Quieres probarlo sin instalar nada? Abre el [notebook de ejemplo](examples/demo.ipynb) en Colab:

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/carlosvisbal/holidays_co_full/blob/main/examples/demo.ipynb)

## Uso rápido

```python
import holidays_co_full
from datetime import date

# Todos los festivos de un año, ordenados cronológicamente
for holiday in holidays_co_full.get_colombia_holidays_by_year(2026):
    print(holiday.date, "-", holiday.celebration)

# ¿Es festivo una fecha concreta? ¿Cuál?
holidays_co_full.is_holiday_date(date(2026, 7, 13))               # True (lunes de traslado del 9 de julio)
holidays_co_full.get_holiday(date(2026, 7, 20)).celebration       # 'Día de la Independencia'

# Días hábiles
holidays_co_full.is_business_day(date(2026, 7, 13))                 # False (lunes festivo)
holidays_co_full.add_business_days(date(2026, 7, 10), 5)            # date(2026, 7, 21)
holidays_co_full.business_days_between(date(2026, 7, 1), date(2026, 7, 31))  # 21

# Puentes del año y exportación
holidays_co_full.long_weekends(2026)[0]   # LongWeekend(start=date(2026, 1, 10), end=date(2026, 1, 12), days=3, ...)
holidays_co_full.to_ical(2026)            # calendario .ics importable en Google Calendar / Outlook
```

## API

Todas las funciones que reciben fechas aceptan `datetime.date` o `datetime.datetime` (de este último se ignora la hora), lanzan `TypeError` ante tipos inválidos y `ValueError` ante fechas fuera del rango soportado `[1970, 9999]`.

Los festivos se devuelven como `namedtuple` `Holiday`:

| Campo | Tipo | Descripción |
|---|---|---|
| `date` | `datetime.date` | Fecha efectiva de celebración (con el traslado al lunes ya aplicado) |
| `celebration` | `str` | Nombre oficial del festivo |
| `original_date` | `datetime.date` | Fecha natural del festivo antes del traslado (igual a `date` si no se movió) |
| `is_shifted` | `bool` | `True` si el festivo fue trasladado al lunes siguiente (Ley Emiliani) |
| `kind` | `str` | Tipo de festivo: `"fixed"` (fijo), `"movable"` (trasladable), `"easter"` (relativo a Pascua) o `"extra"` (día propio de un `HolidayCalendar`) |

### Consulta de festivos

#### `get_colombia_holidays_by_year(year)`

Devuelve la lista de los 19 festivos del año, ordenada por fecha. Acepta `int` o cadena numérica (`"2026"`); rechaza `float` para evitar truncamientos silenciosos.

```python
>>> primero = holidays_co_full.get_colombia_holidays_by_year(2026)[0]
>>> primero.date, primero.celebration
(datetime.date(2026, 1, 1), 'Año Nuevo')
>>> reyes = holidays_co_full.get_colombia_holidays_by_year(2026)[1]
>>> reyes.original_date, reyes.date, reyes.is_shifted   # el 6 de enero cae martes
(datetime.date(2026, 1, 6), datetime.date(2026, 1, 12), True)
```

**Casos de uso:** poblar el calendario laboral del año en un sistema de nómina o turnos; precargar festivos en la base de datos de una aplicación; generar el calendario anual de una intranet.

#### `is_holiday_date(d)`

`True` si la fecha es festivo, `False` en caso contrario.

```python
>>> holidays_co_full.is_holiday_date(date(2026, 1, 12))
True
```

**Casos de uso:** validar en un formulario que la fecha elegida no sea festivo (agendamiento de citas, programación de entregas); decidir si aplicar recargo festivo en una liquidación de horas.

#### `get_holiday(d)`

Devuelve el `Holiday` que se celebra en la fecha, o `None` si no es festivo. A diferencia de `is_holiday_date`, indica *cuál* festivo es.

```python
>>> holidays_co_full.get_holiday(date(2026, 7, 20)).celebration
'Día de la Independencia'
```

**Casos de uso:** mostrar el nombre del festivo en reportes y desprendibles de nómina; notificaciones del tipo "el lunes no hay servicio por Día de los Reyes Magos"; etiquetar festivos en un calendario visual.

#### `next_holiday(d)`

El próximo festivo estrictamente posterior a la fecha; si no quedan festivos en el año, continúa con el siguiente.

```python
>>> proximo = holidays_co_full.next_holiday(date(2026, 12, 26))
>>> proximo.date, proximo.celebration
(datetime.date(2027, 1, 1), 'Año Nuevo')
```

**Casos de uso:** contadores "faltan N días para el próximo festivo"; planear despliegues y mantenimientos fuera de puentes; widgets de calendario en dashboards.

#### `previous_holiday(d)`

El festivo más reciente estrictamente anterior a la fecha; si no hay festivos previos en el año, continúa con el anterior.

```python
>>> holidays_co_full.previous_holiday(date(2026, 1, 5)).date
datetime.date(2026, 1, 1)
>>> holidays_co_full.previous_holiday(date(2026, 1, 1)).date   # cruza de año
datetime.date(2025, 12, 25)
```

**Casos de uso:** reportes "días transcurridos desde el último festivo"; ubicar el puente anterior a una fecha de corte; validar si un rezago operativo se explica por un festivo reciente.

#### `long_weekends(year, include_saturday=False)`

Los puentes del año: bloques de 3 o más días no hábiles consecutivos que contienen al menos un festivo (el clásico sábado-domingo-lunes de la Ley Emiliani, un viernes festivo con su fin de semana, o la Semana Santa de jueves a domingo). Devuelve `namedtuple` `LongWeekend` con `start`, `end`, `days` y la tupla `holidays` del bloque.

```python
>>> puentes = holidays_co_full.long_weekends(2026)
>>> len(puentes)
16
>>> puentes[0].start, puentes[0].end, puentes[0].days
(datetime.date(2026, 1, 10), datetime.date(2026, 1, 12), 3)
>>> [h.celebration for h in puentes[2].holidays]   # Semana Santa: 4 días
['Jueves Santo', 'Viernes Santo']
```

**Casos de uso:** planear turnos y personal de respaldo en puentes; campañas de turismo y comercio; congelar despliegues en fines de semana largos; calendarios de demanda en logística.

#### `get_holidays_between(start, end)`

Festivos dentro de un rango de fechas (ambos extremos incluidos); el rango puede cruzar varios años.

```python
>>> [h.date.isoformat() for h in holidays_co_full.get_holidays_between(date(2026, 12, 1), date(2027, 1, 31))]
['2026-12-08', '2026-12-25', '2027-01-01', '2027-01-11']
```

**Casos de uso:** contar los festivos de un periodo de facturación o de un semestre académico; construir cronogramas de proyecto que excluyan festivos; reportes de un trimestre fiscal.

### Días hábiles

Las funciones de esta sección aceptan el parámetro opcional `include_saturday` (por defecto `False`): con `True`, los sábados no festivos cuentan como hábiles, útil para negocios con jornada de sábado (bancos, comercio).

#### `is_business_day(d, include_saturday=False)`

`True` si la fecha no es domingo, ni festivo, ni sábado (salvo `include_saturday=True`).

```python
>>> holidays_co_full.is_business_day(date(2026, 7, 13))   # lunes festivo
False
>>> holidays_co_full.is_business_day(date(2026, 7, 11), include_saturday=True)   # sábado
True
```

**Casos de uso:** decidir si un proceso batch corre hoy; validar fechas de entrega en logística; determinar si un pago se acredita el mismo día.

#### `add_business_days(d, n, include_saturday=False)`

Suma (o resta, con `n` negativo) `n` días hábiles a la fecha, saltando fines de semana y festivos. La fecha de partida no cuenta dentro de `n`.

```python
>>> holidays_co_full.add_business_days(date(2026, 7, 10), 1)   # viernes + 1 hábil
datetime.date(2026, 7, 14)
```
El lunes 13 es festivo, así que el resultado salta al martes 14.

**Casos de uso:** calcular vencimientos ("5 días hábiles para responder una PQR"); términos judiciales o administrativos; fechas límite de ANS de soporte; estimar la fecha de acreditación de un pago.

#### `business_days_between(start, end, include_saturday=False)`

Cuenta los días hábiles del rango, ambos extremos incluidos (mismo criterio que `NETWORKDAYS` de las hojas de cálculo).

```python
>>> holidays_co_full.business_days_between(date(2026, 7, 13), date(2026, 7, 17))
4
```

**Casos de uso:** liquidar nóminas por días efectivamente laborables; medir duración de trámites en días hábiles; estimar capacidad de un equipo en un sprint o un mes.

#### `business_days_until(d, from_date=None, include_saturday=False, include_today=False)`

Responde "¿cuántos días hábiles me quedan para esta fecha?". Cuenta los días de lunes a viernes que no son festivos, hasta la fecha objetivo incluida. Con `include_today=False` (por defecto) el día de referencia (hoy, o `from_date`) no cuenta y el conteo empieza al día siguiente; con `include_today=True`, el día de referencia también cuenta si es hábil. Lanza `ValueError` si la fecha objetivo ya pasó.

```python
>>> # Hoy es lunes 6 de julio de 2026; el lunes 13 es festivo
>>> holidays_co_full.business_days_until(date(2026, 7, 17))
8
>>> # Contando también el día de hoy (es lunes hábil)
>>> holidays_co_full.business_days_until(date(2026, 7, 17), include_today=True)
9
>>> # Con una fecha de referencia explícita (reportes, simulaciones)
>>> holidays_co_full.business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6))
8
```

**Casos de uso:** días hábiles que quedan para el vencimiento de una PQR o un contrato; cuenta regresiva para un cierre contable o una entrega; días laborables que faltan antes de las vacaciones; alertas del tipo "quedan menos de 3 días hábiles".

### Calendario configurable: `HolidayCalendar`

Evita repetir `include_saturday=...` en cada llamada y permite declarar **días no laborables propios de la empresa** (cierres de fin de año, día de la familia, aniversarios), que todos los métodos tratan igual que un festivo. Acepta un iterable de fechas, de tuplas `(fecha, nombre)` o un dict `{fecha: nombre}`; los días extra aparecen como `Holiday` con `kind='extra'` y, si coinciden con un festivo oficial, prevalece el oficial.

```python
from datetime import date
from holidays_co_full import HolidayCalendar

cal = HolidayCalendar(extra_non_working=[(date(2026, 12, 24), "Cierre de fin de año")])

cal.is_business_day(date(2026, 12, 24))        # False
cal.get_holiday(date(2026, 12, 24)).kind        # 'extra'
cal.add_business_days(date(2026, 12, 23), 1)    # date(2026, 12, 28)
cal.get_holidays_by_year(2026)                  # 19 oficiales + 1 extra
```

Tiene los mismos métodos que el módulo (`is_holiday_date`, `get_holiday`, `next_holiday`, `previous_holiday`, `get_holidays_between`, `get_holidays_by_year`, `is_business_day`, `add_business_days`, `business_days_between`, `business_days_until`, `long_weekends`), aplicando la configuración del calendario.

**Casos de uso:** calendario laboral de una empresa con cierres propios; jornadas con sábado hábil sin repetir el flag; puentes "reales" de la organización (los días extra pueden alargar un puente oficial).

### Exportación: `to_json(years)` y `to_ical(years)`

Exportan los festivos de uno o varios años (un `int`/`str` o un iterable). `to_json` produce JSON con los metadatos completos y acentos legibles; `to_ical` produce un calendario iCalendar (`.ics`) con eventos de día completo, importable en Google Calendar, Outlook o Apple Calendar, con UID deterministas (reimportar actualiza en vez de duplicar).

```python
holidays_co_full.to_json(2026)            # '[\n  {\n    "date": "2026-01-01", ...'
holidays_co_full.to_json([2026, 2027])    # varios años, ordenados por fecha

with open("festivos_2026.ics", "w") as f:
    f.write(holidays_co_full.to_ical(2026))
```

**Casos de uso:** alimentar un front-end o una API interna con el calendario del año; distribuir el calendario corporativo a los empleados como `.ics`; sincronizar festivos con herramientas de agenda.

### Integración con pandas: `custom_business_day(...)`

Devuelve un [`CustomBusinessDay`](https://pandas.pydata.org/docs/reference/api/pandas.tseries.offsets.CustomBusinessDay.html) con los festivos colombianos, para usar el calendario directamente en pandas. Requiere pandas (`pip install holidays_co_full[pandas]`); el núcleo de la librería sigue sin dependencias.

```python
import pandas as pd
import holidays_co_full

cbd = holidays_co_full.custom_business_day(start_year=2026, end_year=2027)
pd.date_range("2026-07-01", periods=10, freq=cbd)   # días hábiles de Colombia
pd.Timestamp("2026-07-10") + cbd                    # → 2026-07-14 (salta el lunes festivo 13)
```

Por defecto carga los festivos desde el año pasado hasta 5 años adelante (`start_year`/`end_year` lo controlan); las fechas fuera de ese rango no conocen los festivos.

**Casos de uso:** series de tiempo financieras y de demanda que solo existen en días hábiles; features de "días hábiles hasta X" en modelos; resampling de datos operativos excluyendo festivos.

## Línea de comandos

La librería instala el comando `holidays-co` (también disponible como `python -m holidays_co_full`):

```shell
holidays-co year 2026                # lista los festivos del año
holidays-co year 2026 --json         # en JSON (con metadatos)
holidays-co year 2026 --ics          # en iCalendar, listo para importar
holidays-co check 2026-07-20         # ¿es festivo? (exit 0 sí / 1 no, útil en scripts)
holidays-co next                     # próximo festivo desde hoy
holidays-co prev --from 2026-07-14   # festivo anterior a una fecha
holidays-co puentes 2026             # fines de semana largos del año
holidays-co business-days 2026-07-01 2026-07-31   # cuenta días hábiles
holidays-co add 2026-07-10 5         # suma días hábiles a una fecha
```

Todos los subcomandos de días hábiles aceptan `--include-saturday`. El código de salida de `check` permite usarlo en automatizaciones: `holidays-co check $(date +%F) || ./correr_proceso.sh`.

## Ejemplo integrado: fecha límite de una PQR

```python
from datetime import date
import holidays_co_full

radicacion = date(2026, 7, 8)  # miércoles
plazo = holidays_co_full.add_business_days(radicacion, 15)
print(f"Radicada el {radicacion}, vence el {plazo}")
if festivo := holidays_co_full.get_holiday(radicacion):
    print(f"Ojo: se radicó un festivo ({festivo.celebration})")
print(f"Próximo festivo: {holidays_co_full.next_holiday(date.today())}")
```

## Precisión histórica

El paquete no aplica el calendario actual retroactivamente: reproduce las reglas que regían en cada año.

- **Traslado al lunes**: la [Ley 51 de 1983](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4954) ("Ley Emiliani") solo rige desde **1984** (constante `LEY_EMILIANI_YEAR`). Para años anteriores, los festivos trasladables se devuelven en su fecha natural, sin mover al lunes.
- **Vigencia por festivo**: cada entrada de `HOLIDAYS` tiene un campo `valid_from` opcional; el festivo del **9 de julio** (Día Nacional de Nuestra Señora del Rosario de Chiquinquirá) solo existe desde **2026**, por la **Ley 2578 de 2026**.
- **Cambios de nombre oficial**: el 12 de octubre se llamó "Día de la Raza" hasta 2020 y desde **2021** se llama oficialmente "Día de la Diversidad Étnica y Cultural de la Nación Colombiana", por la **Resolución 0138 de 2021** del Ministerio de Cultura. El campo `celebration` de ese festivo refleja el nombre vigente en cada año.

Por eso `get_colombia_holidays_by_year(year)` puede devolver **18 festivos** para años anteriores a 2026 y **19** desde 2026 en adelante, y el nombre de un mismo festivo puede variar según el año consultado.

```python
>>> holidays_co_full.get_colombia_holidays_by_year(1970)[1].date   # martes 6 de enero de 1970: sin traslado
datetime.date(1970, 1, 6)
>>> holidays_co_full.get_colombia_holidays_by_year(1984)[1].date   # viernes 6 de enero de 1984: se traslada al lunes 9
datetime.date(1984, 1, 9)
>>> len(holidays_co_full.get_colombia_holidays_by_year(2025))  # sin el festivo del 9 de julio
18
>>> len(holidays_co_full.get_colombia_holidays_by_year(2026))  # con el festivo del 9 de julio
19
>>> holidays_co_full.get_holiday(date(2020, 10, 12)).celebration   # nombre antiguo
'Día de la Raza'
>>> holidays_co_full.get_holiday(date(2026, 10, 12)).celebration   # nombre oficial vigente
'Día de la Diversidad Étnica y Cultural de la Nación Colombiana'
```

**Caso de uso:** cálculos de nómina o liquidaciones retroactivas (por ejemplo, recalcular recargos festivos de años anteriores) que necesitan el calendario legal vigente en ese momento, no el actual; reportes que deben mostrar el nombre oficial correcto de un festivo según la fecha del documento.

## Festivos incluidos

Colombia tiene 19 festivos por año desde 2026 (18 en años anteriores, sin el festivo del 9 de julio), de tres tipos:

### Fijos (se celebran siempre en su fecha)

| Fecha | Celebración |
|---|---|
| 1 de enero | Año Nuevo |
| 1 de mayo | Día del Trabajo |
| 20 de julio | Día de la Independencia |
| 7 de agosto | Batalla de Boyacá |
| 8 de diciembre | Día de la Inmaculada Concepción |
| 25 de diciembre | Día de Navidad |

### Trasladables (desde 1984, si no caen lunes se celebran el lunes siguiente — Ley Emiliani)

| Fecha base | Celebración |
|---|---|
| 6 de enero | Día de los Reyes Magos |
| 19 de marzo | Día de San José |
| 29 de junio | San Pedro y San Pablo |
| 9 de julio | Día Nacional de Nuestra Señora del Rosario de Chiquinquirá (desde 2026, Ley 2578 de 2026) |
| 15 de agosto | La Asunción de la Virgen |
| 12 de octubre | Día de la Diversidad Étnica y Cultural de la Nación Colombiana (desde 2021; "Día de la Raza" en años anteriores) |
| 1 de noviembre | Todos los Santos |
| 11 de noviembre | Independencia de Cartagena |

### Relativos a Pascua (dependen del Domingo de Pascua de cada año)

| Desplazamiento | Celebración | Día resultante |
|---|---|---|
| Pascua − 3 | Jueves Santo | jueves |
| Pascua − 2 | Viernes Santo | viernes |
| Pascua + 43 | Ascensión del Señor | lunes (trasladado) |
| Pascua + 64 | Corpus Christi | lunes (trasladado) |
| Pascua + 71 | Sagrado Corazón de Jesús | lunes (trasladado) |

## Cómo funciona el cálculo

El cálculo de un año se hace en cuatro pasos (ver [`holidays_co_full/__init__.py`](https://github.com/carlosvisbal/holidays_co_full/blob/main/holidays_co_full/__init__.py)):

1. **Festivos de calendario**: para cada entrada de la tabla `HOLIDAYS` se construye la fecha `date(año, mes, día)`. Si el festivo es trasladable (`days_to_sum = calendar.MONDAY`) y la fecha no cae lunes, se mueve al lunes siguiente con `next_weekday()`. Si ya cae lunes, se celebra ese mismo día.
2. **Domingo de Pascua**: `calc_easter(año)` calcula la fecha de Pascua occidental con el algoritmo de computus anónimo (Meeus), válido para cualquier año del calendario gregoriano.
3. **Festivos de Semana Santa y posteriores**: a la fecha de Pascua se le suman los desplazamientos de la tabla `EASTER_WEEK_HOLIDAYS`. Como Pascua siempre es domingo, los desplazamientos +43, +64 y +71 ya corresponden a los lunes trasladados de Ascensión (+39), Corpus Christi (+60) y Sagrado Corazón (+68), sin necesidad de cálculo adicional.
4. **Orden y cache**: las dos listas se combinan, se ordenan por fecha y se almacenan en un cache en memoria (`functools.lru_cache`), de modo que las consultas repetidas del mismo año —por ejemplo, muchas llamadas a `is_holiday_date()` o los recorridos de las funciones de días hábiles— no recalculan nada. Las funciones públicas siempre devuelven objetos nuevos, así que modificar el resultado no afecta al cache.

## Tests

La suite vive en [`tests/test_holidays_co.py`](https://github.com/carlosvisbal/holidays_co_full/blob/main/tests/test_holidays_co.py) y [`tests/test_new_features.py`](https://github.com/carlosvisbal/holidays_co_full/blob/main/tests/test_new_features.py) y no necesita ninguna dependencia: corre con el `unittest` de la librería estándar (también es compatible con pytest si lo tienes instalado). Los tests de la integración con pandas se saltan automáticamente si pandas no está instalado.

```shell
# Desde la raíz del repositorio
python -m unittest discover tests -v

# O con pytest
pytest tests/ -v

# Los ejemplos de los docstrings también son verificables
python -m doctest holidays_co_full/__init__.py && echo OK
```

Cada funcionalidad tiene su clase de tests, con los casos de uso y los casos borde fijados contra el calendario oficial colombiano:

| Clase de test | Funcionalidad cubierta |
|---|---|
| `TestGetColombiaHolidaysByYear` | Calendario 2026 completo, traslados al lunes, validación de tipos y rangos, aislamiento del cache |
| `TestHistoricalAccuracy` | Traslado al lunes solo desde 1984, festivo del 9 de julio solo desde 2026, festivos de Semana Santa sin traslado, cambio de nombre del 12 de octubre desde 2021 |
| `TestIsHolidayDate` | Festivos, días normales, fechas trasladadas, soporte de `datetime` |
| `TestGetHoliday` | Nombre de la celebración y `None` en días normales |
| `TestNextHoliday` | Búsqueda dentro del año, cruce de año, exclusión de la fecha de referencia |
| `TestGetHolidaysBetween` | Rangos inclusivos, rangos que cruzan años, rangos vacíos e inválidos |
| `TestIsBusinessDay` | Entre semana, festivos, domingos y el parámetro `include_saturday` |
| `TestAddBusinessDays` | Saltos de fin de semana y festivo, `n` negativo y cero, validación de `n` |
| `TestBusinessDaysBetween` | Semanas con festivo, conteo inclusivo, `include_saturday`, rangos inválidos |
| `TestBusinessDaysUntil` | Días restantes hasta una fecha, parámetro `include_today`, fecha objetivo hoy o vencida, valor por defecto (hoy) |
| `TestHolidayMetadata` | Campos `original_date`, `is_shifted` y `kind`, incluida la ausencia de traslados antes de 1984 |
| `TestPreviousHoliday` | Búsqueda hacia atrás dentro del año, cruce de año, borde inferior del rango (1970) |
| `TestLongWeekends` | Puentes de lunes, Semana Santa de 4 días, festivos aislados, `include_saturday`, bordes 1970/9999 |
| `TestHolidayCalendar` | Días extra de empresa, prevalencia del festivo oficial, formatos de entrada, validaciones |
| `TestToJson` / `TestToIcal` | Estructura, metadatos, acentos, varios años, UID deterministas del `.ics` |
| `TestCustomBusinessDay` | Offset de pandas con festivos y `weekmask` (se salta sin pandas) |
| `TestCli` | Todos los subcomandos, formatos de salida y códigos de salida |

## Requisitos

- Python 3 (solo librería estándar).
- Opcional: pandas, únicamente para `custom_business_day` (`pip install holidays_co_full[pandas]`).

## Créditos

**Autor:** Carlos Visbal <_carlosvisbal66@gmail.com_>

- Esta versión reescribe y extiende con las funcionalidades descritas en este README, manteniendo compatibilidad con su API.
- Referencia: paquete original [holidays-co v1.0.0](https://pypi.org/project/holidays-co/) en PyPI.

## Licencia

Ver el archivo [LICENSE](https://github.com/carlosvisbal/holidays_co_full/blob/main/LICENSE) del proyecto (MIT).
