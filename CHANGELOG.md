# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Añadido

- Type hints y marcador `py.typed` ([PEP 561](https://peps.python.org/pep-0561/)) para soporte de mypy/pyright e IDEs.
- Alias público `Holiday` para poder importarlo como tipo (`from holidays_co_full import Holiday`).
- CI con GitHub Actions: tests y doctests en cada push/PR sobre Python 3.7–3.13.
- Publicación automática a PyPI vía GitHub Actions (Trusted Publishing) al crear un release en GitHub.
- README en inglés (`README.en.md`) y sección comparativa frente a librerías genéricas multi-país.
- Notebook de ejemplo (`examples/demo.ipynb`) con badge de Colab.

## [1.0.0] - 2026-07-06

### Añadido

- `get_colombia_holidays_by_year(year)`: festivos de un año, ordenados por fecha.
- `is_holiday_date(d)`: compatibilidad con la API original de [`holidays-co`](https://pypi.org/project/holidays-co/).
- `get_holiday(d)`: nombre del festivo celebrado en una fecha.
- `next_holiday(d)`: próximo festivo posterior a una fecha, con cruce de año.
- `get_holidays_between(start, end)`: festivos dentro de un rango de fechas.
- `is_business_day`, `add_business_days`, `business_days_between`, `business_days_until`: utilidades de días hábiles con soporte de `include_saturday`.
- Precisión histórica: traslado al lunes solo desde 1984 (Ley 51 de 1983, Ley Emiliani), vigencia por festivo (`valid_from`) y cambios de nombre oficial (`renamed_to`/`renamed_from`).
- Cache en memoria por año (`functools.lru_cache`) para consultas repetidas.
- Suite de tests con `unittest`, compatible con `pytest`, fijada contra el calendario oficial colombiano.
