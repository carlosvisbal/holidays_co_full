"""holidays_co_full — Días festivos no laborables en Colombia.

Calcula los días festivos oficiales de Colombia para cualquier año entre
1970 y 9999, con precisión histórica: el traslado al lunes siguiente solo
se aplica desde 1984 (Ley 51 de 1983, "Ley Emiliani"; ver
``LEY_EMILIANI_YEAR``), cada festivo solo aparece a partir del año en
que empezó a regir (ver el campo ``valid_from``; p. ej. el 9 de julio
solo existe desde 2026 por la Ley 2578 de 2026), y el nombre de un
festivo puede cambiar según el año si tuvo un cambio de nombre oficial
(ver ``renamed_to``/``renamed_from``; p. ej. el 12 de octubre se llama
oficialmente "Día de la Diversidad Étnica y Cultural de la Nación
Colombiana" desde 2021, por la Resolución 0138 de 2021).

El calendario incluye tres tipos de festivos:

1. **Fijos**: se celebran siempre en su fecha (p. ej. Año Nuevo, Día de
   la Independencia, Navidad).
2. **Trasladables**: desde 1984, si no caen lunes se celebran el lunes
   siguiente; antes de 1984 se celebran siempre en su fecha (p. ej.
   Reyes Magos, San Pedro y San Pablo).
3. **Relativos a Pascua**: se calculan a partir del Domingo de Pascua
   (Jueves y Viernes Santo, y —trasladables desde 1984— Ascensión,
   Corpus Christi y Sagrado Corazón).

Funciones disponibles:

- :func:`get_colombia_holidays_by_year`: todos los festivos de un año.
- :func:`is_holiday_date`: indica si una fecha es festivo.
- :func:`get_holiday`: nombre de la celebración de una fecha, o ``None``.
- :func:`next_holiday`: el próximo festivo después de una fecha.
- :func:`previous_holiday`: el festivo anterior a una fecha.
- :func:`get_holidays_between`: festivos dentro de un rango de fechas.
- :func:`long_weekends`: los puentes (fines de semana largos) de un año.
- :func:`is_business_day`: indica si una fecha es día hábil.
- :func:`add_business_days`: suma o resta días hábiles a una fecha.
- :func:`business_days_between`: cuenta los días hábiles de un rango.
- :func:`business_days_until`: días hábiles que quedan hasta una fecha objetivo.
- :func:`to_json`: exporta los festivos de uno o varios años como JSON.
- :func:`to_ical`: exporta los festivos como calendario iCalendar (``.ics``).
- :func:`custom_business_day`: offset de pandas con los festivos colombianos
  (requiere instalar ``pandas``).
- :class:`HolidayCalendar`: calendario configurable (sábados hábiles y
  días no laborables propios de una empresa).

También hay una interfaz de línea de comandos: ``holidays-co --help``
(o ``python -m holidays_co_full --help``).

Ejemplo de uso::

    >>> import holidays_co_full
    >>> from datetime import date
    >>> holidays = holidays_co_full.get_colombia_holidays_by_year(2026)
    >>> holidays[0].date, holidays[0].celebration
    (datetime.date(2026, 1, 1), 'Año Nuevo')
    >>> holidays_co_full.is_holiday_date(date(2026, 7, 20))
    True

:copyright: Portado desde https://github.com/nequibc/colombia-holidays
:license: MIT, ver el archivo LICENSE del proyecto.
"""

from __future__ import annotations

import calendar
import json
from collections import namedtuple
from datetime import date, timedelta, datetime
from functools import lru_cache
from typing import Callable, Iterable, List, Optional, Union

#: Acepta tanto ``date`` como ``datetime`` en las funciones públicas
#: (de este último se ignora la hora).
DateLike = Union[date, datetime]

#: Tamaño máximo de los cachés internos por año (``_get_holidays`` y
#: ``_holiday_dates``). El rango soportado tiene 8030 años posibles
#: (1970-9999), pero el uso real consulta un puñado de años cercanos entre
#: sí (el actual y algunos adyacentes para rangos de fechas o días
#: hábiles). 128 cubre eso con margen amplio y, al ser un límite LRU real
#: en vez de ``None``, evita que un proceso de larga duración acumule
#: memoria sin cota si llega a consultar muchos años distintos.
_YEAR_CACHE_SIZE = 128

#: Año a partir del cual rige la Ley 51 de 1983 ("Ley Emiliani"), que
#: traslada al lunes siguiente los festivos que no caen lunes. Antes de
#: este año, todos los festivos —incluidos los relativos a Pascua que
#: son trasladables— se celebran en su fecha natural, sin traslado.
LEY_EMILIANI_YEAR = 1984

#: Festivo ya resuelto para un año concreto, tal como lo devuelven las
#: funciones públicas. ``date`` es un :class:`datetime.date` con la fecha
#: efectiva de celebración y ``celebration`` el nombre oficial del festivo.
#: Los campos de metadatos permiten distinguir el traslado de la Ley
#: Emiliani: ``original_date`` es la fecha natural del festivo antes del
#: traslado (igual a ``date`` si no se movió), ``is_shifted`` indica si el
#: festivo fue trasladado al lunes siguiente y ``kind`` clasifica el
#: festivo: ``"fixed"`` (fecha fija), ``"movable"`` (trasladable),
#: ``"easter"`` (relativo a Pascua) o ``"extra"`` (día no laborable propio
#: de un :class:`HolidayCalendar`). Los campos nuevos tienen valores por
#: defecto para que ``Holiday(date, celebration)`` siga funcionando.
_nt_holiday = namedtuple(
    "Holiday",
    ["date", "celebration", "original_date", "is_shifted", "kind"],
    defaults=[None, False, None],
)

#: Alias público de :data:`_nt_holiday`, para poder importarlo como
#: ``from holidays_co_full import Holiday`` (anotaciones de tipo, mypy, IDEs).
Holiday = _nt_holiday

#: Puente (fin de semana largo) detectado por :func:`long_weekends`:
#: ``start`` y ``end`` son las fechas extremas (inclusivas) del bloque de
#: días no hábiles consecutivos, ``days`` su longitud en días calendario y
#: ``holidays`` la tupla de festivos que caen dentro del bloque.
_nt_long_weekend = namedtuple("LongWeekend", ["start", "end", "days", "holidays"])

#: Alias público de :data:`_nt_long_weekend`.
LongWeekend = _nt_long_weekend

#: Definición de un festivo de fecha fija en el calendario. ``month`` y
#: ``day`` son enteros; ``days_to_sum`` es ``calendar.MONDAY`` si el
#: festivo es trasladable (el traslado solo se aplica desde
#: ``LEY_EMILIANI_YEAR``) o ``None`` si es fijo. ``valid_from`` es el
#: primer año en que el festivo existe, o ``None`` si no tiene límite
#: inferior dentro del rango soportado (1970). ``renamed_to`` y
#: ``renamed_from`` permiten modelar un cambio de nombre oficial del
#: festivo: desde el año ``renamed_from`` se usa ``renamed_to`` en vez de
#: ``celebration``; ambos ``None`` si el festivo nunca cambió de nombre.
_nt_holiday_stock = namedtuple(
    "HolidayStock",
    ["month", "day", "days_to_sum", "celebration", "valid_from", "renamed_to", "renamed_from"],
    defaults=[None, None, None],
)

#: Definición de un festivo relativo a Pascua. ``days_after_easter`` es el
#: desplazamiento en días respecto al Domingo de Pascua (puede ser
#: negativo). ``days_to_sum`` es ``calendar.MONDAY`` si el festivo es
#: trasladable (desde ``LEY_EMILIANI_YEAR``) o ``None`` si no se traslada
#: (Jueves y Viernes Santo).
_nt_easter_holiday_stock = namedtuple(
    "EasterHolidayStock", ["days_after_easter", "days_to_sum", "celebration"]
)

#: Festivos que dependen de la fecha de Pascua, con su desplazamiento
#: natural (sin trasladar): Jueves Santo (-3) y Viernes Santo (-2) nunca
#: se trasladan; Ascensión (+39), Corpus Christi (+60) y Sagrado Corazón
#: (+68) se trasladan al lunes siguiente desde ``LEY_EMILIANI_YEAR``.
EASTER_WEEK_HOLIDAYS = [
    _nt_easter_holiday_stock(days_after_easter=-3, days_to_sum=None, celebration="Jueves Santo"),
    _nt_easter_holiday_stock(days_after_easter=-2, days_to_sum=None, celebration="Viernes Santo"),
    _nt_easter_holiday_stock(days_after_easter=39, days_to_sum=calendar.MONDAY, celebration="Ascensión del Señor"),
    _nt_easter_holiday_stock(days_after_easter=60, days_to_sum=calendar.MONDAY, celebration="Corpus Christi"),
    _nt_easter_holiday_stock(days_after_easter=68, days_to_sum=calendar.MONDAY, celebration="Sagrado Corazón de Jesús")
]

#: Festivos de fecha fija en el calendario. Los que tienen
#: ``days_to_sum=calendar.MONDAY`` se celebran el lunes siguiente cuando no
#: caen lunes (desde ``LEY_EMILIANI_YEAR``); los que tienen
#: ``days_to_sum=None`` se celebran siempre en su fecha. El 9 de julio
#: solo es festivo desde 2026, por la Ley 2578 de 2026 (``valid_from``).
#: El 12 de octubre cambió su nombre oficial en 2021, por la Resolución
#: 0138 de 2021 del Ministerio de Cultura (``renamed_to``/``renamed_from``).
HOLIDAYS = [
    _nt_holiday_stock(month=1, day=1, days_to_sum=None, celebration="Año Nuevo"),
    _nt_holiday_stock(month=5, day=1, days_to_sum=None, celebration="Día del Trabajo"),
    _nt_holiday_stock(month=7, day=20, days_to_sum=None, celebration="Día de la Independencia"),
    _nt_holiday_stock(month=8, day=7, days_to_sum=None, celebration="Batalla de Boyacá"),
    _nt_holiday_stock(month=12, day=8, days_to_sum=None, celebration="Día de la Inmaculada Concepción"),
    _nt_holiday_stock(month=12, day=25, days_to_sum=None, celebration="Día de Navidad"),
    _nt_holiday_stock(month=1, day=6, days_to_sum=calendar.MONDAY, celebration="Día de los Reyes Magos"),
    _nt_holiday_stock(month=3, day=19, days_to_sum=calendar.MONDAY, celebration="Día de San José"),
    _nt_holiday_stock(month=6, day=29, days_to_sum=calendar.MONDAY, celebration="San Pedro y San Pablo"),
    _nt_holiday_stock(
        month=7, day=9, days_to_sum=calendar.MONDAY,
        celebration="Día Nacional de Nuestra Señora del Rosario de Chiquinquirá",
        valid_from=2026,  # Ley 2578 de 2026
    ),
    _nt_holiday_stock(month=8, day=15, days_to_sum=calendar.MONDAY, celebration="La Asunción de la Virgen"),
    _nt_holiday_stock(
        month=10, day=12, days_to_sum=calendar.MONDAY, celebration="Día de la Raza",
        renamed_to="Día de la Diversidad Étnica y Cultural de la Nación Colombiana",
        renamed_from=2021,  # Resolución 0138 de 2021, Ministerio de Cultura
    ),
    _nt_holiday_stock(month=11, day=1, days_to_sum=calendar.MONDAY, celebration="Todos los Santos"),
    _nt_holiday_stock(month=11, day=11, days_to_sum=calendar.MONDAY, celebration="Independencia de Cartagena")
]

def next_weekday(d: date, weekday: int) -> date:
    """Devuelve la fecha del próximo ``weekday`` estrictamente posterior a ``d``.

    Si ``d`` ya cae en el día de la semana buscado, devuelve el de la
    semana siguiente (una semana después), no la misma fecha.

    Basado en https://stackoverflow.com/a/6558571

    :param d: fecha de partida.
    :type d: datetime.date
    :param weekday: día de la semana buscado, según las constantes de
        :mod:`calendar` (``calendar.MONDAY`` = 0 … ``calendar.SUNDAY`` = 6).
    :type weekday: int
    :returns: la fecha del próximo ``weekday`` después de ``d``.
    :rtype: datetime.date
    """
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + timedelta(days_ahead)

def calc_easter(year: int) -> date:
    """Calcula la fecha del Domingo de Pascua (occidental) para un año.

    Implementa el algoritmo de computus anónimo/Meeus.
    Upstream: http://code.activestate.com/recipes/576517-calculate-easter-western-given-a-year/

    :param year: año a calcular; se acepta cualquier valor convertible a ``int``.
    :type year: int
    :returns: la fecha del Domingo de Pascua de ese año.
    :rtype: datetime.date
    :raises ValueError: si ``year`` no es convertible a entero.
    """
    year = int(year)
    a = year % 19
    b = year // 100
    c = year % 100
    d = (19 * a + b - b // 4 - ((b - (b + 8) // 25 + 1) // 3) + 15) % 30
    e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
    f = d + e - 7 * ((a + 11 * d + 22 * e) // 451) + 114
    month = f // 31
    day = f % 31 + 1
    return date(year, month, day)

@lru_cache(maxsize=_YEAR_CACHE_SIZE)
def _get_holidays(year: int) -> tuple:
    """Calcula y cachea los festivos de un año ya validado.

    Función interna: asume que ``year`` es un ``int`` dentro del rango
    válido. Devuelve una tupla inmutable para que el valor cacheado no
    pueda ser modificado por los llamadores; el API público la convierte
    en lista nueva en cada llamada.

    :param year: año validado.
    :type year: int
    :returns: festivos del año ordenados por fecha. Puede tener menos de
        19 elementos en años anteriores a la vigencia de algún festivo
        (p. ej. 18 antes de 2026, por el festivo del 9 de julio), y el
        nombre de un festivo puede variar según el año si tuvo un cambio
        de nombre oficial (p. ej. el 12 de octubre desde 2021).
    :rtype: tuple of Holiday
    """
    shift_applies = year >= LEY_EMILIANI_YEAR

    holidays = []
    for holiday in HOLIDAYS:
        if holiday.valid_from is not None and year < holiday.valid_from:
            continue
        original_date = date(year, holiday.month, holiday.day)
        holiday_date = original_date
        if shift_applies and holiday.days_to_sum is not None and holiday_date.weekday() != holiday.days_to_sum:
            holiday_date = next_weekday(holiday_date, holiday.days_to_sum)
        celebration = holiday.celebration
        if holiday.renamed_from is not None and year >= holiday.renamed_from:
            celebration = holiday.renamed_to
        holidays.append(_nt_holiday(
            date=holiday_date,
            celebration=celebration,
            original_date=original_date,
            is_shifted=holiday_date != original_date,
            kind="fixed" if holiday.days_to_sum is None else "movable",
        ))

    sunday_date = calc_easter(year)
    for holiday in EASTER_WEEK_HOLIDAYS:
        original_date = sunday_date + timedelta(days=holiday.days_after_easter)
        holiday_date = original_date
        if shift_applies and holiday.days_to_sum is not None and holiday_date.weekday() != holiday.days_to_sum:
            holiday_date = next_weekday(holiday_date, holiday.days_to_sum)
        holidays.append(_nt_holiday(
            date=holiday_date,
            celebration=holiday.celebration,
            original_date=original_date,
            is_shifted=holiday_date != original_date,
            kind="easter",
        ))

    holidays.sort(key=lambda holiday: holiday.date)
    return tuple(holidays)

def get_colombia_holidays_by_year(year: Union[int, str]) -> List[Holiday]:
    """Devuelve los festivos no laborables de Colombia para un año.

    Las fechas devueltas son las de celebración efectiva y con precisión
    histórica: los festivos trasladables solo aparecen movidos al lunes
    siguiente para años desde 1984 (``LEY_EMILIANI_YEAR``, Ley 51 de
    1983); antes de esa fecha se devuelven en su día natural. Además,
    cada festivo solo aparece a partir de su año de vigencia (por
    ejemplo, el 9 de julio solo existe desde 2026, Ley 2578 de 2026), y
    el nombre puede variar si el festivo tuvo un cambio de nombre oficial
    (el 12 de octubre se llama "Día de la Diversidad Étnica y Cultural de
    la Nación Colombiana" desde 2021, Resolución 0138 de 2021, y "Día de
    la Raza" en años anteriores). La lista viene ordenada
    cronológicamente y puede tener menos de 19 elementos en años donde
    algún festivo aún no regía.

    Ejemplo::

        >>> holidays = get_colombia_holidays_by_year(2026)
        >>> holidays[0].date, holidays[0].celebration
        (datetime.date(2026, 1, 1), 'Año Nuevo')
        >>> # Reyes Magos 2026: el 6 de enero es martes y se traslada al lunes 12.
        >>> holidays[1].original_date, holidays[1].date, holidays[1].is_shifted, holidays[1].kind
        (datetime.date(2026, 1, 6), datetime.date(2026, 1, 12), True, 'movable')

    :param year: año a consultar, entre 1970 y 9999. Se aceptan enteros
        y cadenas numéricas (``"2026"``); los ``float`` se rechazan para
        evitar truncamientos silenciosos.
    :type year: int or str
    :returns: lista nueva (mutable sin efectos laterales) de festivos
        ordenados por fecha.
    :rtype: list of Holiday
    :raises TypeError: si ``year`` no es un entero ni una cadena numérica.
    :raises ValueError: si ``year`` está fuera del rango [1970, 9999].
    """
    if isinstance(year, float):
        raise TypeError("El año debe ser un entero")
    try:
        year = int(year)
    except (ValueError, TypeError):
        raise TypeError("El año debe ser un entero")

    if year < 1970 or year > 9999:
        raise ValueError("El año debe ser mayor a 1969 y menor a 10000")

    return list(_get_holidays(year))

@lru_cache(maxsize=_YEAR_CACHE_SIZE)
def _holiday_dates(year: int) -> frozenset:
    """Conjunto cacheado de las fechas festivas de un año ya validado.

    Permite consultas de pertenencia en O(1) para las funciones de días
    hábiles, que evalúan muchas fechas seguidas.

    :param year: año validado.
    :type year: int
    :rtype: frozenset of datetime.date
    """
    return frozenset(holiday.date for holiday in _get_holidays(year))

def _ensure_date(d: DateLike) -> date:
    """Valida y normaliza una fecha de entrada del API público.

    :param d: valor a validar.
    :returns: un :class:`datetime.date` (si ``d`` era ``datetime``, sin la hora).
    :rtype: datetime.date
    :raises TypeError: si ``d`` no es un objeto ``date`` ni ``datetime``.
    :raises ValueError: si el año de ``d`` es anterior a 1970.
    """
    if not isinstance(d, date):
        raise TypeError("Debe proporcionar un objeto tipo date")
    if isinstance(d, datetime):
        d = d.date()
    if d.year < 1970:
        raise ValueError("El año debe ser mayor a 1969 y menor a 10000")
    return d

def is_holiday_date(d: DateLike) -> bool:
    """Indica si una fecha es un día festivo no laborable en Colombia.

    Ejemplo::

        >>> from datetime import date
        >>> is_holiday_date(date(2026, 7, 20))
        True

    :param d: fecha a consultar; se acepta también un
        :class:`datetime.datetime`, del cual se toma solo la fecha.
    :type d: datetime.date or datetime.datetime
    :returns: ``True`` si la fecha es festivo, ``False`` en caso contrario.
    :rtype: bool
    :raises TypeError: si ``d`` no es un objeto ``date`` ni ``datetime``.
    :raises ValueError: si el año de ``d`` es anterior a 1970.
    """
    d = _ensure_date(d)
    return d in _holiday_dates(d.year)

def get_holiday(d: DateLike) -> Optional[Holiday]:
    """Devuelve el festivo que se celebra en una fecha, o ``None``.

    A diferencia de :func:`is_holiday_date`, indica *cuál* festivo es,
    útil cuando el nombre debe aparecer en reportes, nóminas o
    notificaciones ("el lunes no hay servicio por Día de los Reyes Magos").

    Ejemplo::

        >>> from datetime import date
        >>> get_holiday(date(2026, 7, 20)).celebration
        'Día de la Independencia'
        >>> get_holiday(date(2026, 7, 21)) is None
        True

    :param d: fecha a consultar; se acepta también ``datetime``.
    :type d: datetime.date or datetime.datetime
    :returns: el ``Holiday`` celebrado ese día, o ``None`` si no es festivo.
    :rtype: Holiday or None
    :raises TypeError: si ``d`` no es un objeto ``date`` ni ``datetime``.
    :raises ValueError: si el año de ``d`` es anterior a 1970.
    """
    d = _ensure_date(d)
    for holiday in _get_holidays(d.year):
        if holiday.date == d:
            return holiday
    return None

def next_holiday(d: DateLike) -> Holiday:
    """Devuelve el próximo festivo estrictamente posterior a una fecha.

    Si no quedan festivos en el año, continúa con el siguiente (el
    resultado puede pertenecer a otro año). Útil para contadores del tipo
    "faltan N días para el próximo festivo" o para planear despliegues y
    mantenimientos fuera de puentes.

    Ejemplo::

        >>> from datetime import date
        >>> holiday = next_holiday(date(2026, 12, 26))
        >>> holiday.date, holiday.celebration
        (datetime.date(2027, 1, 1), 'Año Nuevo')

    :param d: fecha de referencia (excluida del resultado); se acepta
        también ``datetime``.
    :type d: datetime.date or datetime.datetime
    :returns: el primer ``Holiday`` con fecha posterior a ``d``.
    :rtype: Holiday
    :raises TypeError: si ``d`` no es un objeto ``date`` ni ``datetime``.
    :raises ValueError: si el año de ``d`` es anterior a 1970, o si no hay
        festivos posteriores dentro del rango soportado (año 9999).
    """
    d = _ensure_date(d)
    year = d.year
    while year <= 9999:
        for holiday in _get_holidays(year):
            if holiday.date > d:
                return holiday
        year += 1
    raise ValueError("No hay festivos posteriores a la fecha dentro del rango soportado")

def previous_holiday(d: DateLike) -> Holiday:
    """Devuelve el festivo más reciente estrictamente anterior a una fecha.

    Es el simétrico de :func:`next_holiday`: si no hay festivos previos en
    el año, continúa con el anterior (el resultado puede pertenecer a otro
    año). Útil para reportes del tipo "días transcurridos desde el último
    festivo" o para ubicar el puente anterior a una fecha de corte.

    Ejemplo::

        >>> from datetime import date
        >>> holiday = previous_holiday(date(2026, 1, 5))
        >>> holiday.date, holiday.celebration
        (datetime.date(2026, 1, 1), 'Año Nuevo')
        >>> previous_holiday(date(2026, 1, 1)).date
        datetime.date(2025, 12, 25)

    :param d: fecha de referencia (excluida del resultado); se acepta
        también ``datetime``.
    :type d: datetime.date or datetime.datetime
    :returns: el último ``Holiday`` con fecha anterior a ``d``.
    :rtype: Holiday
    :raises TypeError: si ``d`` no es un objeto ``date`` ni ``datetime``.
    :raises ValueError: si el año de ``d`` es anterior a 1970, o si no hay
        festivos anteriores dentro del rango soportado (desde 1970).
    """
    d = _ensure_date(d)
    year = d.year
    while year >= 1970:
        for holiday in reversed(_get_holidays(year)):
            if holiday.date < d:
                return holiday
        year -= 1
    raise ValueError("No hay festivos anteriores a la fecha dentro del rango soportado")

def get_holidays_between(start: DateLike, end: DateLike) -> List[Holiday]:
    """Devuelve los festivos dentro de un rango de fechas, inclusivo.

    El rango puede cruzar varios años. Es la consulta natural para
    periodos de facturación, cronogramas de proyecto o semestres
    académicos: "¿qué festivos caen dentro de este periodo?".

    Ejemplo::

        >>> from datetime import date
        >>> [h.date.isoformat() for h in get_holidays_between(date(2026, 12, 1), date(2027, 1, 31))]
        ['2026-12-08', '2026-12-25', '2027-01-01', '2027-01-11']

    :param start: fecha inicial del rango (incluida).
    :type start: datetime.date or datetime.datetime
    :param end: fecha final del rango (incluida).
    :type end: datetime.date or datetime.datetime
    :returns: festivos dentro del rango, ordenados por fecha.
    :rtype: list of Holiday
    :raises TypeError: si ``start`` o ``end`` no son ``date`` ni ``datetime``.
    :raises ValueError: si algún año es anterior a 1970, o si
        ``start`` es posterior a ``end``.
    """
    start = _ensure_date(start)
    end = _ensure_date(end)
    if start > end:
        raise ValueError("La fecha inicial debe ser menor o igual a la final")

    holidays = []
    for year in range(start.year, end.year + 1):
        for holiday in _get_holidays(year):
            if start <= holiday.date <= end:
                holidays.append(holiday)
    return holidays

def _add_business_days_impl(d: date, n: int, is_business: Callable[[date], bool]) -> date:
    """Desplaza ``n`` días hábiles según el predicado ``is_business``.

    Lógica compartida entre :func:`add_business_days` y
    :class:`HolidayCalendar`, que difieren solo en cómo deciden si un día
    es hábil.
    """
    step = timedelta(days=1 if n >= 0 else -1)
    remaining = abs(n)
    while remaining > 0:
        d += step
        if is_business(d):
            remaining -= 1
    return d

def _business_days_between_impl(start: date, end: date, is_business: Callable[[date], bool]) -> int:
    """Cuenta días hábiles en [start, end] según el predicado ``is_business``.

    Lógica compartida entre :func:`business_days_between` y
    :class:`HolidayCalendar`.
    """
    count = 0
    d = start
    one_day = timedelta(days=1)
    while d <= end:
        if is_business(d):
            count += 1
        d += one_day
    return count

def is_business_day(d: DateLike, include_saturday: bool = False) -> bool:
    """Indica si una fecha es día hábil en Colombia.

    Un día es hábil si no es domingo, no es festivo y —salvo que
    ``include_saturday`` sea ``True``— tampoco es sábado. El parámetro
    existe porque en Colombia muchos negocios y plazos cuentan el sábado
    como día hábil (p. ej. jornadas bancarias y comerciales).

    Ejemplo::

        >>> from datetime import date
        >>> is_business_day(date(2026, 7, 13))  # lunes festivo
        False
        >>> is_business_day(date(2026, 7, 11))  # sábado
        False
        >>> is_business_day(date(2026, 7, 11), include_saturday=True)
        True

    :param d: fecha a consultar; se acepta también ``datetime``.
    :type d: datetime.date or datetime.datetime
    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles. Por defecto ``False``.
    :type include_saturday: bool
    :returns: ``True`` si la fecha es día hábil, ``False`` en caso contrario.
    :rtype: bool
    :raises TypeError: si ``d`` no es un objeto ``date`` ni ``datetime``.
    :raises ValueError: si el año de ``d`` es anterior a 1970.
    """
    d = _ensure_date(d)
    if d.weekday() == calendar.SUNDAY:
        return False
    if d.weekday() == calendar.SATURDAY and not include_saturday:
        return False
    return d not in _holiday_dates(d.year)

def add_business_days(d: DateLike, n: int, include_saturday: bool = False) -> date:
    """Suma (o resta) ``n`` días hábiles a una fecha, saltando festivos.

    Es la operación base para calcular vencimientos y plazos: "5 días
    hábiles para responder una petición", "el pago se acredita en 2 días
    hábiles", términos judiciales o administrativos, ANS de soporte. La
    fecha de partida no necesita ser hábil y no cuenta dentro de ``n``.

    Ejemplo::

        >>> from datetime import date
        >>> add_business_days(date(2026, 7, 10), 1)  # viernes + 1 hábil
        datetime.date(2026, 7, 14)

    (El lunes 13 de julio de 2026 es festivo, así que el siguiente día
    hábil es el martes 14.)

    :param d: fecha de partida; se acepta también ``datetime``.
    :type d: datetime.date or datetime.datetime
    :param n: cantidad de días hábiles a desplazar; puede ser negativo
        para retroceder y cero devuelve la misma fecha.
    :type n: int
    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles. Por defecto ``False``.
    :type include_saturday: bool
    :returns: la fecha resultante del desplazamiento.
    :rtype: datetime.date
    :raises TypeError: si ``d`` no es ``date``/``datetime`` o ``n`` no es
        un entero.
    :raises ValueError: si el desplazamiento sale del rango [1970, 9999].
    """
    d = _ensure_date(d)
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("El número de días debe ser un entero")

    return _add_business_days_impl(
        d, n, lambda day: is_business_day(day, include_saturday=include_saturday)
    )

def business_days_between(start: DateLike, end: DateLike, include_saturday: bool = False) -> int:
    """Cuenta los días hábiles de un rango de fechas, inclusivo.

    Ambos extremos cuentan si son hábiles (mismo criterio que la función
    ``NETWORKDAYS`` de las hojas de cálculo). Útil para liquidar nóminas
    por días trabajados, medir duraciones de proceso en días hábiles o
    estimar capacidad de un equipo en un sprint.

    Ejemplo::

        >>> from datetime import date
        >>> business_days_between(date(2026, 7, 13), date(2026, 7, 17))
        4

    (Semana de 5 días menos el lunes festivo 13 de julio.)

    :param start: fecha inicial del rango (incluida).
    :type start: datetime.date or datetime.datetime
    :param end: fecha final del rango (incluida).
    :type end: datetime.date or datetime.datetime
    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles. Por defecto ``False``.
    :type include_saturday: bool
    :returns: cantidad de días hábiles dentro del rango.
    :rtype: int
    :raises TypeError: si ``start`` o ``end`` no son ``date`` ni ``datetime``.
    :raises ValueError: si algún año es anterior a 1970, o si
        ``start`` es posterior a ``end``.
    """
    start = _ensure_date(start)
    end = _ensure_date(end)
    if start > end:
        raise ValueError("La fecha inicial debe ser menor o igual a la final")

    return _business_days_between_impl(
        start, end, lambda day: is_business_day(day, include_saturday=include_saturday)
    )

def business_days_until(
    d: DateLike,
    from_date: Optional[DateLike] = None,
    include_saturday: bool = False,
    include_today: bool = False,
) -> int:
    """Cuenta los días hábiles que quedan hasta una fecha objetivo.

    Cuenta los días de lunes a viernes que no son festivos, hasta la
    fecha objetivo incluida (si es hábil). El día de referencia se
    controla con ``include_today``: por defecto no cuenta (el día en
    curso ya no se considera restante) y el conteo empieza el día
    siguiente. Responde la pregunta "¿cuántos días hábiles me quedan
    para esta fecha?": vencimiento de una PQR o un contrato, cierre
    contable, entrega de un proyecto, días laborables antes de las
    vacaciones.

    Ejemplo::

        >>> from datetime import date
        >>> # Del lunes 6 de julio de 2026 al viernes 17: el lunes 13 es festivo
        >>> business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6))
        8
        >>> # Contando también el lunes 6 (el día de referencia es hábil)
        >>> business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6), include_today=True)
        9

    :param d: fecha objetivo; se acepta también ``datetime``.
    :type d: datetime.date or datetime.datetime
    :param from_date: fecha de referencia desde la que se cuenta. Si es
        ``None`` (por defecto), se usa la fecha actual del sistema.
    :type from_date: datetime.date or datetime.datetime or None
    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles. Por defecto ``False`` (solo lunes a viernes).
    :type include_saturday: bool
    :param include_today: si es ``True``, el día de referencia cuenta
        dentro de los días restantes cuando es hábil. Por defecto
        ``False`` (se empieza a contar desde el día siguiente).
    :type include_today: bool
    :returns: cantidad de días hábiles restantes; ``0`` si la fecha
        objetivo es la misma fecha de referencia y esta no cuenta o no
        es hábil.
    :rtype: int
    :raises TypeError: si ``d`` o ``from_date`` no son ``date`` ni ``datetime``.
    :raises ValueError: si algún año es anterior a 1970, o si ``d`` es
        anterior a ``from_date``.
    """
    d = _ensure_date(d)
    if from_date is None:
        from_date = date.today()
    from_date = _ensure_date(from_date)
    if d < from_date:
        raise ValueError("La fecha objetivo debe ser igual o posterior a la fecha de referencia")

    start = from_date if include_today else from_date + timedelta(days=1)
    if start > d:
        return 0
    return business_days_between(start, d, include_saturday=include_saturday)

def _long_weekends_impl(
    year_holidays: Iterable[Holiday],
    is_business: Callable[[date], bool],
    holidays_between: Callable[[date, date], List[Holiday]],
) -> List[LongWeekend]:
    """Detecta puentes a partir de una lista de festivos y un predicado.

    Para cada festivo expande hacia atrás y hacia adelante el bloque de
    días no hábiles consecutivos que lo contiene y conserva los bloques
    de 3 o más días. Lógica compartida entre :func:`long_weekends` y
    :class:`HolidayCalendar`. La expansión se detiene en los bordes del
    rango soportado (1970-9999) para no evaluar fechas fuera de él.
    """
    one_day = timedelta(days=1)
    blocks = []
    seen_starts = set()
    for holiday in year_holidays:
        start = holiday.date
        while True:
            prev = start - one_day
            if prev.year < 1970 or is_business(prev):
                break
            start = prev
        if start in seen_starts:
            continue
        seen_starts.add(start)
        end = holiday.date
        while True:
            nxt = end + one_day
            if nxt.year > 9999 or is_business(nxt):
                break
            end = nxt
        days = (end - start).days + 1
        if days < 3:
            continue
        blocks.append(_nt_long_weekend(
            start=start, end=end, days=days, holidays=tuple(holidays_between(start, end))
        ))
    blocks.sort(key=lambda block: block.start)
    return blocks

def long_weekends(year: Union[int, str], include_saturday: bool = False) -> List[LongWeekend]:
    """Devuelve los puentes (fines de semana largos) de un año.

    Un puente es un bloque de 3 o más días no hábiles consecutivos que
    contiene al menos un festivo: el clásico sábado-domingo-lunes festivo
    de la Ley Emiliani, un viernes festivo seguido de fin de semana, o la
    Semana Santa (jueves a domingo, 4 días). Útil para planear turnos,
    mantenimientos, campañas de turismo o la logística de RR. HH.

    Los bloques pueden extenderse a días de años vecinos (p. ej. un
    puente de Año Nuevo que empieza el 30 de diciembre anterior), pero
    siempre contienen al menos un festivo del año consultado.

    Ejemplo::

        >>> puentes = long_weekends(2026)
        >>> len(puentes)
        16
        >>> puentes[0].start, puentes[0].end, puentes[0].days
        (datetime.date(2026, 1, 10), datetime.date(2026, 1, 12), 3)
        >>> [h.celebration for h in puentes[2].holidays]
        ['Jueves Santo', 'Viernes Santo']

    :param year: año a consultar, entre 1970 y 9999 (mismas reglas de
        validación que :func:`get_colombia_holidays_by_year`).
    :type year: int or str
    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles y cortan los bloques (un lunes festivo deja
        de formar puente de 3 días). Por defecto ``False``.
    :type include_saturday: bool
    :returns: lista de :data:`LongWeekend` ordenados por fecha de inicio.
    :rtype: list of LongWeekend
    :raises TypeError: si ``year`` no es un entero ni una cadena numérica.
    :raises ValueError: si ``year`` está fuera del rango [1970, 9999].
    """
    year_holidays = get_colombia_holidays_by_year(year)
    return _long_weekends_impl(
        year_holidays,
        lambda day: is_business_day(day, include_saturday=include_saturday),
        get_holidays_between,
    )

def _holidays_for_years(years: Union[int, str, Iterable[Union[int, str]]]) -> List[Holiday]:
    """Normaliza el argumento ``years`` de los exports a una lista de festivos.

    Acepta un año suelto (``int`` o ``str``) o un iterable de años; valida
    cada año con las mismas reglas del API público, ordena por fecha y
    elimina duplicados (por si se repite un año).
    """
    if isinstance(years, (int, str)):
        years = [years]
    try:
        iterator = iter(years)
    except TypeError:
        raise TypeError("years debe ser un año o un iterable de años")

    holidays = []
    for year in iterator:
        holidays.extend(get_colombia_holidays_by_year(year))
    holidays.sort(key=lambda holiday: holiday.date)
    return list(dict.fromkeys(holidays))

def to_json(years: Union[int, str, Iterable[Union[int, str]]], indent: Optional[int] = 2) -> str:
    """Exporta los festivos de uno o varios años como una cadena JSON.

    Cada festivo se serializa con sus metadatos completos: fecha efectiva
    (``date``), nombre (``celebration``), fecha natural antes del traslado
    (``original_date``), si fue trasladado (``is_shifted``) y su tipo
    (``kind``). Las fechas van en formato ISO 8601 (``YYYY-MM-DD``) y los
    acentos se conservan (no se escapan como ``\\uXXXX``), listo para
    consumir desde un front-end o una API.

    Ejemplo::

        >>> import json
        >>> data = json.loads(to_json(2026))
        >>> len(data)
        19
        >>> data[0]['date'], data[0]['celebration']
        ('2026-01-01', 'Año Nuevo')

    :param years: un año (``int`` o ``str``) o un iterable de años.
    :type years: int or str or iterable
    :param indent: sangría del JSON generado; ``None`` produce una sola
        línea compacta. Por defecto 2.
    :type indent: int or None
    :returns: cadena JSON con la lista de festivos ordenada por fecha.
    :rtype: str
    :raises TypeError: si algún año no es un entero ni una cadena numérica.
    :raises ValueError: si algún año está fuera del rango [1970, 9999].
    """
    holidays = _holidays_for_years(years)
    payload = [
        {
            "date": holiday.date.isoformat(),
            "celebration": holiday.celebration,
            "original_date": holiday.original_date.isoformat(),
            "is_shifted": holiday.is_shifted,
            "kind": holiday.kind,
        }
        for holiday in holidays
    ]
    return json.dumps(payload, ensure_ascii=False, indent=indent)

def _ical_escape(text: str) -> str:
    """Escapa un valor de texto según RFC 5545 (comas, puntos y comas, saltos)."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )

def to_ical(years: Union[int, str, Iterable[Union[int, str]]]) -> str:
    """Exporta los festivos como un calendario iCalendar (``.ics``).

    Genera un ``VCALENDAR`` con un evento de día completo (``VEVENT`` con
    ``DTSTART;VALUE=DATE``) por festivo, importable en Google Calendar,
    Outlook o Apple Calendar. Los eventos se marcan ``TRANSP:TRANSPARENT``
    para que no bloqueen disponibilidad, y los UID son deterministas: el
    mismo año produce siempre el mismo archivo (reimportar actualiza en
    vez de duplicar). Las líneas van separadas por CRLF según RFC 5545.

    Ejemplo::

        >>> ics = to_ical(2026)
        >>> ics.splitlines()[0]
        'BEGIN:VCALENDAR'
        >>> ics.count('BEGIN:VEVENT')
        19

    :param years: un año (``int`` o ``str``) o un iterable de años.
    :type years: int or str or iterable
    :returns: contenido del archivo ``.ics`` como cadena.
    :rtype: str
    :raises TypeError: si algún año no es un entero ni una cadena numérica.
    :raises ValueError: si algún año está fuera del rango [1970, 9999].
    """
    holidays = _holidays_for_years(years)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//holidays_co_full//Festivos de Colombia//ES",
        "CALSCALE:GREGORIAN",
    ]
    for index, holiday in enumerate(holidays):
        lines.extend([
            "BEGIN:VEVENT",
            "UID:{:%Y%m%d}-{}@holidays-co-full".format(holiday.date, index),
            "DTSTAMP:{:%Y%m%d}T000000Z".format(holiday.date),
            "DTSTART;VALUE=DATE:{:%Y%m%d}".format(holiday.date),
            "DTEND;VALUE=DATE:{:%Y%m%d}".format(holiday.date + timedelta(days=1)),
            "SUMMARY:" + _ical_escape(holiday.celebration),
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

def custom_business_day(
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    include_saturday: bool = False,
):
    """Devuelve un ``CustomBusinessDay`` de pandas con los festivos colombianos.

    Permite usar el calendario colombiano directamente en pandas::

        import pandas as pd
        import holidays_co_full

        cbd = holidays_co_full.custom_business_day()
        pd.date_range("2026-07-01", periods=10, freq=cbd)  # días hábiles CO
        pd.Timestamp("2026-07-10") + 1 * cbd               # siguiente hábil

    Requiere tener pandas instalado (``pip install holidays_co_full[pandas]``);
    el núcleo de la librería sigue sin dependencias.

    :param start_year: primer año cuyos festivos se cargan en el offset.
        Por defecto, el año actual menos 1.
    :type start_year: int or None
    :param end_year: último año cargado (inclusive). Por defecto, el año
        actual más 5. Fechas fuera de [start_year, end_year] no conocen
        los festivos, así que el rango debe cubrir el periodo a analizar.
    :type end_year: int or None
    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles. Por defecto ``False``.
    :type include_saturday: bool
    :returns: un ``pandas.tseries.offsets.CustomBusinessDay`` configurado.
    :raises ImportError: si pandas no está instalado.
    :raises TypeError: si los años no son enteros.
    :raises ValueError: si los años están fuera de rango o en desorden.
    """
    try:
        from pandas.tseries.offsets import CustomBusinessDay
    except ImportError:
        raise ImportError(
            "custom_business_day requiere pandas; instálelo con "
            "'pip install pandas' o 'pip install holidays_co_full[pandas]'"
        )

    current_year = date.today().year
    if start_year is None:
        start_year = current_year - 1
    if end_year is None:
        end_year = current_year + 5
    for value in (start_year, end_year):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Los años deben ser enteros")
    if start_year < 1970 or end_year > 9999:
        raise ValueError("El año debe ser mayor a 1969 y menor a 10000")
    if start_year > end_year:
        raise ValueError("El año inicial debe ser menor o igual al final")

    holiday_dates = [
        holiday.date
        for year in range(start_year, end_year + 1)
        for holiday in _get_holidays(year)
    ]
    weekmask = "Mon Tue Wed Thu Fri Sat" if include_saturday else "Mon Tue Wed Thu Fri"
    return CustomBusinessDay(holidays=holiday_dates, weekmask=weekmask)

class HolidayCalendar:
    """Calendario de días hábiles configurable sobre los festivos de Colombia.

    Evita repetir ``include_saturday=...`` en cada llamada y permite
    declarar días no laborables propios de una organización (cierres de
    fin de año, días de la familia, aniversarios de la empresa) que las
    funciones de días hábiles tratan igual que un festivo. Los festivos
    oficiales nacionales siempre están incluidos.

    Los días extra aparecen en las consultas del calendario como
    ``Holiday`` con ``kind='extra'``; si un día extra coincide con un
    festivo oficial, prevalece el festivo.

    Ejemplo::

        >>> from datetime import date
        >>> cal = HolidayCalendar(extra_non_working=[(date(2026, 12, 24), 'Cierre de fin de año')])
        >>> cal.is_business_day(date(2026, 12, 24))
        False
        >>> cal.get_holiday(date(2026, 12, 24)).celebration
        'Cierre de fin de año'
        >>> cal.add_business_days(date(2026, 12, 23), 1)
        datetime.date(2026, 12, 28)

    :param include_saturday: si es ``True``, los sábados no festivos
        cuentan como hábiles en todos los métodos. Por defecto ``False``.
    :type include_saturday: bool
    :param extra_non_working: días no laborables adicionales. Acepta un
        iterable de fechas (``date``/``datetime``), de tuplas
        ``(fecha, nombre)``, o un dict ``{fecha: nombre}``. Las fechas sin
        nombre reciben ``"Día no laborable"``.
    :raises TypeError: si algún elemento no es una fecha válida o el
        nombre no es una cadena.
    :raises ValueError: si alguna fecha extra es anterior a 1970.
    """

    _DEFAULT_EXTRA_NAME = "Día no laborable"

    def __init__(self, include_saturday: bool = False, extra_non_working=None) -> None:
        self.include_saturday = bool(include_saturday)
        extras = {}
        if extra_non_working is not None:
            if isinstance(extra_non_working, dict):
                items = extra_non_working.items()
            else:
                items = extra_non_working
            for item in items:
                if isinstance(item, tuple):
                    if len(item) != 2:
                        raise TypeError(
                            "Cada día extra debe ser una fecha o una tupla (fecha, nombre)"
                        )
                    raw_date, name = item
                    if not isinstance(name, str):
                        raise TypeError("El nombre del día extra debe ser una cadena")
                else:
                    raw_date, name = item, self._DEFAULT_EXTRA_NAME
                extras[_ensure_date(raw_date)] = name
        #: Días no laborables propios del calendario: ``{date: nombre}``.
        self.extra_non_working = extras

    def _extra_holiday(self, d: date) -> Holiday:
        """Construye el ``Holiday`` sintético de un día extra del calendario."""
        return _nt_holiday(
            date=d, celebration=self.extra_non_working[d],
            original_date=d, is_shifted=False, kind="extra",
        )

    def _year_holidays(self, year: int) -> List[Holiday]:
        """Festivos oficiales + días extra de un año validado, ordenados."""
        official_dates = _holiday_dates(year)
        merged = list(_get_holidays(year))
        merged.extend(
            self._extra_holiday(d)
            for d in self.extra_non_working
            if d.year == year and d not in official_dates
        )
        merged.sort(key=lambda holiday: holiday.date)
        return merged

    def get_holidays_by_year(self, year: Union[int, str]) -> List[Holiday]:
        """Festivos oficiales y días extra del calendario para un año.

        Mismas reglas de validación que
        :func:`get_colombia_holidays_by_year`.
        """
        get_colombia_holidays_by_year(year)  # valida tipo y rango
        return self._year_holidays(int(year))

    def is_holiday_date(self, d: DateLike) -> bool:
        """Indica si la fecha es festivo oficial o día extra del calendario."""
        d = _ensure_date(d)
        return d in _holiday_dates(d.year) or d in self.extra_non_working

    def get_holiday(self, d: DateLike) -> Optional[Holiday]:
        """Festivo oficial o día extra celebrado en la fecha, o ``None``."""
        d = _ensure_date(d)
        official = get_holiday(d)
        if official is not None:
            return official
        if d in self.extra_non_working:
            return self._extra_holiday(d)
        return None

    def next_holiday(self, d: DateLike) -> Holiday:
        """Próximo festivo o día extra estrictamente posterior a la fecha."""
        d = _ensure_date(d)
        year = d.year
        while year <= 9999:
            for holiday in self._year_holidays(year):
                if holiday.date > d:
                    return holiday
            year += 1
        raise ValueError("No hay festivos posteriores a la fecha dentro del rango soportado")

    def previous_holiday(self, d: DateLike) -> Holiday:
        """Festivo o día extra más reciente estrictamente anterior a la fecha."""
        d = _ensure_date(d)
        year = d.year
        while year >= 1970:
            for holiday in reversed(self._year_holidays(year)):
                if holiday.date < d:
                    return holiday
            year -= 1
        raise ValueError("No hay festivos anteriores a la fecha dentro del rango soportado")

    def get_holidays_between(self, start: DateLike, end: DateLike) -> List[Holiday]:
        """Festivos oficiales y días extra dentro de un rango, inclusivo."""
        start = _ensure_date(start)
        end = _ensure_date(end)
        if start > end:
            raise ValueError("La fecha inicial debe ser menor o igual a la final")

        holidays = []
        for year in range(start.year, end.year + 1):
            for holiday in self._year_holidays(year):
                if start <= holiday.date <= end:
                    holidays.append(holiday)
        return holidays

    def is_business_day(self, d: DateLike) -> bool:
        """Día hábil según el calendario: descuenta también los días extra."""
        d = _ensure_date(d)
        if not is_business_day(d, include_saturday=self.include_saturday):
            return False
        return d not in self.extra_non_working

    def add_business_days(self, d: DateLike, n: int) -> date:
        """Suma o resta ``n`` días hábiles según el calendario."""
        d = _ensure_date(d)
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError("El número de días debe ser un entero")
        return _add_business_days_impl(d, n, self.is_business_day)

    def business_days_between(self, start: DateLike, end: DateLike) -> int:
        """Cuenta los días hábiles del rango inclusivo según el calendario."""
        start = _ensure_date(start)
        end = _ensure_date(end)
        if start > end:
            raise ValueError("La fecha inicial debe ser menor o igual a la final")
        return _business_days_between_impl(start, end, self.is_business_day)

    def business_days_until(
        self,
        d: DateLike,
        from_date: Optional[DateLike] = None,
        include_today: bool = False,
    ) -> int:
        """Días hábiles restantes hasta la fecha objetivo según el calendario.

        Misma semántica que :func:`business_days_until` (la fecha de
        referencia no cuenta salvo ``include_today=True``).
        """
        d = _ensure_date(d)
        if from_date is None:
            from_date = date.today()
        from_date = _ensure_date(from_date)
        if d < from_date:
            raise ValueError("La fecha objetivo debe ser igual o posterior a la fecha de referencia")

        start = from_date if include_today else from_date + timedelta(days=1)
        if start > d:
            return 0
        return self.business_days_between(start, d)

    def long_weekends(self, year: Union[int, str]) -> List[LongWeekend]:
        """Puentes del año según el calendario (los días extra pueden alargarlos)."""
        return _long_weekends_impl(
            self.get_holidays_by_year(year), self.is_business_day, self.get_holidays_between
        )
