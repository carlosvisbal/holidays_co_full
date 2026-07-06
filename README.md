# holidays_co_full

**Días festivos no laborables en Colombia**, calculados para cualquier año entre 1970 y 9999 según la [Ley 51 de 1983](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4954) (Ley Emiliani), con utilidades de días hábiles para nóminas, vencimientos y planeación.

Esta versión es una **extensión** de la librería original publicada en [PyPI](https://pypi.org/project/holidays-co/) (v1.0.0, que solo incluía `get_colombia_holidays_by_year` e `is_holiday_date`). Mantiene compatibilidad total con esa API y añade: precisión histórica del calendario, consulta del nombre del festivo, búsqueda del próximo festivo, festivos por rango de fechas, y todo el conjunto de utilidades de días hábiles.

- Sin dependencias externas: solo usa la librería estándar de Python 3.
- Resultados cacheados en memoria: consultar el mismo año repetidamente tiene costo despreciable.
- Fechas ya resueltas: los festivos trasladables se devuelven en su día efectivo de celebración.
- Precisión histórica: el traslado al lunes solo se aplica desde 1984 y cada festivo solo aparece a partir de su año de vigencia (ver [Precisión histórica](#precisión-histórica)).

## Instalación

```shell
pip install holidays_co_full
```

## Uso rápido

```python
import holidays_co_full
from datetime import date

# Todos los festivos de un año, ordenados cronológicamente
for holiday in holidays_co_full.get_colombia_holidays_by_year(2026):
    print(holiday.date, "-", holiday.celebration)

# ¿Es festivo una fecha concreta? ¿Cuál?
holidays_co_full.is_holiday_date(date(2026, 7, 13))   # True (lunes de traslado del 9 de julio)
holidays_co_full.get_holiday(date(2026, 7, 20))       # Holiday(date=..., celebration='Día de la Independencia')

# Días hábiles
holidays_co_full.is_business_day(date(2026, 7, 13))                 # False (lunes festivo)
holidays_co_full.add_business_days(date(2026, 7, 10), 5)            # date(2026, 7, 21)
holidays_co_full.business_days_between(date(2026, 7, 1), date(2026, 7, 31))  # 21
```

## API

Todas las funciones que reciben fechas aceptan `datetime.date` o `datetime.datetime` (de este último se ignora la hora), lanzan `TypeError` ante tipos inválidos y `ValueError` ante fechas fuera del rango soportado `[1970, 9999]`.

Los festivos se devuelven como `namedtuple` `Holiday`:

| Campo | Tipo | Descripción |
|---|---|---|
| `date` | `datetime.date` | Fecha efectiva de celebración (con el traslado al lunes ya aplicado) |
| `celebration` | `str` | Nombre oficial del festivo |

### Consulta de festivos

#### `get_colombia_holidays_by_year(year)`

Devuelve la lista de los 19 festivos del año, ordenada por fecha. Acepta `int` o cadena numérica (`"2026"`); rechaza `float` para evitar truncamientos silenciosos.

```python
>>> holidays_co_full.get_colombia_holidays_by_year(2026)[0]
Holiday(date=datetime.date(2026, 1, 1), celebration='Año Nuevo')
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
>>> holidays_co_full.next_holiday(date(2026, 12, 26))
Holiday(date=datetime.date(2027, 1, 1), celebration='Año Nuevo')
```

**Casos de uso:** contadores "faltan N días para el próximo festivo"; planear despliegues y mantenimientos fuera de puentes; widgets de calendario en dashboards.

#### `get_holidays_between(start, end)`

Festivos dentro de un rango de fechas (ambos extremos incluidos); el rango puede cruzar varios años.

```python
>>> [h.date.isoformat() for h in holidays_co_full.get_holidays_between(date(2026, 12, 1), date(2027, 1, 31))]
['2026-12-08', '2026-12-25', '2027-01-01', '2027-01-11']
```

**Casos de uso:** contar los festivos de un periodo de facturación o de un semestre académico; construir cronogramas de proyecto que excluyan festivos; reportes de un trimestre fiscal.

### Días hábiles

Las tres funciones aceptan el parámetro opcional `include_saturday` (por defecto `False`): con `True`, los sábados no festivos cuentan como hábiles, útil para negocios con jornada de sábado (bancos, comercio).

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
>>> holidays_co_full.get_colombia_holidays_by_year(1970)[1]   # martes 6 de enero de 1970: sin traslado
Holiday(date=datetime.date(1970, 1, 6), celebration='Día de los Reyes Magos')
>>> holidays_co_full.get_colombia_holidays_by_year(1984)[1]    # viernes 6 de enero de 1984: se traslada al lunes 9
Holiday(date=datetime.date(1984, 1, 9), celebration='Día de los Reyes Magos')
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

La suite vive en [`tests/test_holidays_co.py`](https://github.com/carlosvisbal/holidays_co_full/blob/main/tests/test_holidays_co.py) y no necesita ninguna dependencia: corre con el `unittest` de la librería estándar (también es compatible con pytest si lo tienes instalado).

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

## Requisitos

- Python 3 (solo librería estándar).

## Créditos

**Autor:** Carlos Visbal <_carlosvisbal66@gmail.com_>

- Esta versión reescribe y extiende con las funcionalidades descritas en este README, manteniendo compatibilidad con su API.
- Referencia: paquete original [holidays-co v1.0.0](https://pypi.org/project/holidays-co/) en PyPI.

## Licencia

Ver el archivo [LICENSE](https://github.com/carlosvisbal/holidays_co_full/blob/main/LICENSE) del proyecto (MIT).
