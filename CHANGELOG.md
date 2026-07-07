# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [1.1.0] - 2026-07-07

### Añadido

- Metadatos en `Holiday`: `original_date` (fecha natural antes del traslado), `is_shifted` (si se movió al lunes por la Ley Emiliani) y `kind` (`"fixed"`, `"movable"`, `"easter"` o `"extra"`). Los campos nuevos van al final y con valores por defecto, así que `Holiday(date, celebration)` y el acceso posicional a los dos primeros campos siguen funcionando.
- `previous_holiday(d)`: el festivo anterior a una fecha, simétrico de `next_holiday`, con cruce de año.
- `long_weekends(year, include_saturday=False)`: detección de puentes — bloques de 3 o más días no hábiles consecutivos con al menos un festivo (incluida la Semana Santa de 4 días). Devuelve `namedtuple` `LongWeekend` (`start`, `end`, `days`, `holidays`).
- Clase `HolidayCalendar(include_saturday=..., extra_non_working=...)`: calendario configurable con días no laborables propios de una empresa; expone los mismos métodos del módulo aplicando la configuración. Los días extra aparecen con `kind='extra'` y ante coincidencia prevalece el festivo oficial.
- Exportación: `to_json(years)` (JSON con metadatos y acentos legibles) y `to_ical(years)` (calendario iCalendar `.ics` con eventos de día completo y UID deterministas, importable en Google Calendar/Outlook/Apple Calendar).
- Integración con pandas: `custom_business_day(...)` devuelve un `CustomBusinessDay` con los festivos colombianos. Es un extra opcional (`pip install holidays_co_full[pandas]`); el núcleo sigue sin dependencias.
- CLI `holidays-co` (también `python -m holidays_co_full`): subcomandos `year` (con `--json`/`--ics`), `check` (exit 0/1 para scripts), `next`, `prev`, `puentes`, `business-days` y `add`.
- Type hints y marcador `py.typed` ([PEP 561](https://peps.python.org/pep-0561/)) para soporte de mypy/pyright e IDEs.
- Alias público `Holiday` para poder importarlo como tipo (`from holidays_co_full import Holiday`).
- CI con GitHub Actions: tests y doctests en cada push/PR sobre Python 3.7–3.13.
- Publicación automática a PyPI vía GitHub Actions (Trusted Publishing) al crear un release en GitHub.
- README en inglés (`README.en.md`) y sección comparativa frente a librerías genéricas multi-país.
- Notebook de ejemplo (`examples/demo.ipynb`) con badge de Colab.

### Cambiado

- El `repr` de `Holiday` ahora incluye los campos nuevos. El acceso por nombre y por posición a `date` y `celebration` no cambia, pero el código que compare contra el `repr` completo o construya tuplas de 2 elementos para compararlas por igualdad debe actualizarse.

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
