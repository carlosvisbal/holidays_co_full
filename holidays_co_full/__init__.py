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
- :func:`get_holidays_between`: festivos dentro de un rango de fechas.
- :func:`is_business_day`: indica si una fecha es día hábil.
- :func:`add_business_days`: suma o resta días hábiles a una fecha.
- :func:`business_days_between`: cuenta los días hábiles de un rango.
- :func:`business_days_until`: días hábiles que quedan hasta una fecha objetivo.

Ejemplo de uso::

    >>> import holidays_co_full
    >>> from datetime import date
    >>> holidays = holidays_co_full.get_colombia_holidays_by_year(2026)
    >>> holidays[0]
    Holiday(date=datetime.date(2026, 1, 1), celebration='Año Nuevo')
    >>> holidays_co_full.is_holiday_date(date(2026, 7, 20))
    True

:copyright: Portado desde https://github.com/nequibc/colombia-holidays
:license: MIT, ver el archivo LICENSE del proyecto.
"""

import calendar
from collections import namedtuple
from datetime import date, timedelta, datetime
from functools import lru_cache

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
_nt_holiday = namedtuple("Holiday", ["date", "celebration"])

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

def next_weekday(d, weekday):
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

def calc_easter(year):
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
def _get_holidays(year):
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
        holiday_date = date(year, holiday.month, holiday.day)
        if shift_applies and holiday.days_to_sum is not None and holiday_date.weekday() != holiday.days_to_sum:
            holiday_date = next_weekday(holiday_date, holiday.days_to_sum)
        celebration = holiday.celebration
        if holiday.renamed_from is not None and year >= holiday.renamed_from:
            celebration = holiday.renamed_to
        holidays.append(_nt_holiday(date=holiday_date, celebration=celebration))

    sunday_date = calc_easter(year)
    for holiday in EASTER_WEEK_HOLIDAYS:
        holiday_date = sunday_date + timedelta(days=holiday.days_after_easter)
        if shift_applies and holiday.days_to_sum is not None and holiday_date.weekday() != holiday.days_to_sum:
            holiday_date = next_weekday(holiday_date, holiday.days_to_sum)
        holidays.append(_nt_holiday(date=holiday_date, celebration=holiday.celebration))

    holidays.sort(key=lambda holiday: holiday.date)
    return tuple(holidays)

def get_colombia_holidays_by_year(year):
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

        >>> get_colombia_holidays_by_year(2026)[0]
        Holiday(date=datetime.date(2026, 1, 1), celebration='Año Nuevo')

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
def _holiday_dates(year):
    """Conjunto cacheado de las fechas festivas de un año ya validado.

    Permite consultas de pertenencia en O(1) para las funciones de días
    hábiles, que evalúan muchas fechas seguidas.

    :param year: año validado.
    :type year: int
    :rtype: frozenset of datetime.date
    """
    return frozenset(holiday.date for holiday in _get_holidays(year))

def _ensure_date(d):
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

def is_holiday_date(d):
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

def get_holiday(d):
    """Devuelve el festivo que se celebra en una fecha, o ``None``.

    A diferencia de :func:`is_holiday_date`, indica *cuál* festivo es,
    útil cuando el nombre debe aparecer en reportes, nóminas o
    notificaciones ("el lunes no hay servicio por Día de los Reyes Magos").

    Ejemplo::

        >>> from datetime import date
        >>> get_holiday(date(2026, 7, 20))
        Holiday(date=datetime.date(2026, 7, 20), celebration='Día de la Independencia')
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

def next_holiday(d):
    """Devuelve el próximo festivo estrictamente posterior a una fecha.

    Si no quedan festivos en el año, continúa con el siguiente (el
    resultado puede pertenecer a otro año). Útil para contadores del tipo
    "faltan N días para el próximo festivo" o para planear despliegues y
    mantenimientos fuera de puentes.

    Ejemplo::

        >>> from datetime import date
        >>> next_holiday(date(2026, 12, 26))
        Holiday(date=datetime.date(2027, 1, 1), celebration='Año Nuevo')

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

def get_holidays_between(start, end):
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

def is_business_day(d, include_saturday=False):
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

def add_business_days(d, n, include_saturday=False):
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

    step = timedelta(days=1 if n >= 0 else -1)
    remaining = abs(n)
    while remaining > 0:
        d += step
        if is_business_day(d, include_saturday=include_saturday):
            remaining -= 1
    return d

def business_days_between(start, end, include_saturday=False):
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

    count = 0
    d = start
    one_day = timedelta(days=1)
    while d <= end:
        if is_business_day(d, include_saturday=include_saturday):
            count += 1
        d += one_day
    return count

def business_days_until(d, from_date=None, include_saturday=False, include_today=False):
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
