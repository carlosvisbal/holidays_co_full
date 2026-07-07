"""Interfaz de línea de comandos de holidays_co_full.

Se instala como el comando ``holidays-co`` (o se invoca con
``python -m holidays_co_full``). Subcomandos disponibles:

- ``holidays-co year 2026``: lista los festivos de un año; con
  ``--json`` o ``--ics`` exporta en esos formatos.
- ``holidays-co check 2026-07-20``: indica si una fecha es festivo
  (código de salida 0 si lo es, 1 si no — útil en scripts).
- ``holidays-co next [--from 2026-07-14]``: próximo festivo.
- ``holidays-co prev [--from 2026-07-14]``: festivo anterior.
- ``holidays-co puentes 2026``: los fines de semana largos del año.
- ``holidays-co business-days 2026-07-01 2026-07-31``: cuenta los días
  hábiles de un rango inclusivo.
- ``holidays-co add 2026-07-10 5``: suma (o resta, con N negativo)
  días hábiles a una fecha.

Los errores de validación (fechas mal formadas, años fuera de rango)
se reportan por stderr con código de salida 2.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import List, Optional

from . import (
    add_business_days,
    business_days_between,
    get_colombia_holidays_by_year,
    get_holiday,
    long_weekends,
    next_holiday,
    previous_holiday,
    to_ical,
    to_json,
)


def _parse_date(value: str) -> date:
    """Convierte un argumento ``YYYY-MM-DD`` en ``date`` para argparse."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "fecha inválida: {!r} (use el formato YYYY-MM-DD)".format(value)
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="holidays-co",
        description="Festivos y días hábiles de Colombia (1970-9999), con precisión histórica.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    year_parser = subparsers.add_parser("year", help="lista los festivos de un año")
    year_parser.add_argument("year", help="año a consultar (1970-9999)")
    format_group = year_parser.add_mutually_exclusive_group()
    format_group.add_argument("--json", action="store_true", help="salida en JSON")
    format_group.add_argument("--ics", action="store_true", help="salida en iCalendar (.ics)")

    check_parser = subparsers.add_parser(
        "check", help="indica si una fecha es festivo (exit 0 si lo es, 1 si no)"
    )
    check_parser.add_argument("date", type=_parse_date, help="fecha YYYY-MM-DD")

    next_parser = subparsers.add_parser("next", help="próximo festivo después de una fecha")
    next_parser.add_argument(
        "--from", dest="from_date", type=_parse_date, default=None,
        help="fecha de referencia YYYY-MM-DD (por defecto, hoy)",
    )

    prev_parser = subparsers.add_parser("prev", help="festivo anterior a una fecha")
    prev_parser.add_argument(
        "--from", dest="from_date", type=_parse_date, default=None,
        help="fecha de referencia YYYY-MM-DD (por defecto, hoy)",
    )

    puentes_parser = subparsers.add_parser(
        "puentes", help="fines de semana largos (puentes) de un año"
    )
    puentes_parser.add_argument("year", help="año a consultar (1970-9999)")
    puentes_parser.add_argument(
        "--include-saturday", action="store_true",
        help="tratar los sábados como días hábiles",
    )

    days_parser = subparsers.add_parser(
        "business-days", help="cuenta los días hábiles de un rango inclusivo"
    )
    days_parser.add_argument("start", type=_parse_date, help="fecha inicial YYYY-MM-DD")
    days_parser.add_argument("end", type=_parse_date, help="fecha final YYYY-MM-DD")
    days_parser.add_argument(
        "--include-saturday", action="store_true",
        help="tratar los sábados como días hábiles",
    )

    add_parser = subparsers.add_parser(
        "add", help="suma (o resta, con N negativo) días hábiles a una fecha"
    )
    add_parser.add_argument("date", type=_parse_date, help="fecha de partida YYYY-MM-DD")
    add_parser.add_argument("n", type=int, help="días hábiles a desplazar (puede ser negativo)")
    add_parser.add_argument(
        "--include-saturday", action="store_true",
        help="tratar los sábados como días hábiles",
    )

    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "year":
        if args.json:
            print(to_json(args.year))
        elif args.ics:
            # sys.stdout.write evita el \n extra: el .ics ya termina en CRLF.
            sys.stdout.write(to_ical(args.year))
        else:
            for holiday in get_colombia_holidays_by_year(args.year):
                print("{}  {}".format(holiday.date.isoformat(), holiday.celebration))
        return 0

    if args.command == "check":
        holiday = get_holiday(args.date)
        if holiday is None:
            print("{} no es festivo".format(args.date.isoformat()))
            return 1
        print("{}  {}".format(holiday.date.isoformat(), holiday.celebration))
        return 0

    if args.command in ("next", "prev"):
        reference = args.from_date if args.from_date is not None else date.today()
        finder = next_holiday if args.command == "next" else previous_holiday
        holiday = finder(reference)
        print("{}  {}".format(holiday.date.isoformat(), holiday.celebration))
        return 0

    if args.command == "puentes":
        for puente in long_weekends(args.year, include_saturday=args.include_saturday):
            names = ", ".join(holiday.celebration for holiday in puente.holidays)
            print("{} a {} ({} días): {}".format(
                puente.start.isoformat(), puente.end.isoformat(), puente.days, names
            ))
        return 0

    if args.command == "business-days":
        print(business_days_between(
            args.start, args.end, include_saturday=args.include_saturday
        ))
        return 0

    if args.command == "add":
        print(add_business_days(
            args.date, args.n, include_saturday=args.include_saturday
        ).isoformat())
        return 0

    raise AssertionError("subcomando no manejado: {}".format(args.command))


def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada del comando ``holidays-co``.

    :param argv: argumentos de línea de comandos sin el nombre del
        programa; ``None`` usa ``sys.argv[1:]``.
    :returns: código de salida (0 éxito; 1 "no es festivo" en ``check``;
        2 error de validación).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (ValueError, TypeError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
