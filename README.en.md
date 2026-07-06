# holidays_co_full

[![PyPI version](https://img.shields.io/pypi/v/holidays_co_full.svg)](https://pypi.org/project/holidays_co_full/)
[![Python versions](https://img.shields.io/pypi/pyversions/holidays_co_full.svg)](https://pypi.org/project/holidays_co_full/)
[![Tests](https://github.com/carlosvisbal/holidays_co_full/actions/workflows/tests.yml/badge.svg)](https://github.com/carlosvisbal/holidays_co_full/actions/workflows/tests.yml)
[![PyPI downloads](https://img.shields.io/pypi/dm/holidays_co_full.svg)](https://pypi.org/project/holidays_co_full/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/carlosvisbal/holidays_co_full/blob/main/LICENSE)

[🇨🇴 Español](README.md) | 🇬🇧 English

**Colombian public holidays**, computed for any year between 1970 and 9999 under [Law 51 of 1983](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4954) ("Ley Emiliani"), plus business-day utilities for payroll, deadlines and planning.

This package is an **extension** of the original library published on [PyPI](https://pypi.org/project/holidays-co/) (v1.0.0, which only included `get_colombia_holidays_by_year` and `is_holiday_date`). It keeps full API compatibility with that package and adds: historical calendar accuracy, holiday name lookup, next-holiday search, holidays within a date range, and the full set of business-day utilities.

- No external dependencies: pure Python 3 standard library.
- In-memory cached results: repeated queries for the same year are effectively free.
- Already-resolved dates: shiftable holidays are returned on their actual celebration day.
- Historical accuracy: the Monday shift only applies from 1984 onward, and each holiday only appears from the year it became law (see [Historical accuracy](#historical-accuracy)).
- Typed: ships type hints and the `py.typed` marker ([PEP 561](https://peps.python.org/pep-0561/)) for autocomplete and static checking with mypy/pyright.

## Why this library?

Generic multi-country libraries (like [`holidays`](https://pypi.org/project/holidays/)) also cover Colombia. `holidays_co_full` is built for when Colombia *is* the problem, not just one more country on a list:

| | `holidays_co_full` | Generic multi-country libraries |
|---|---|---|
| Monday shift only from 1984 (Ley Emiliani) | Yes, per queried year | Usually apply the current rule retroactively |
| Holiday with its own year of validity (July 9th since 2026) | Yes (`valid_from`) | Requires manual per-country maintenance |
| Official name valid per year (October 12th) | Yes (`renamed_to`/`renamed_from`) | Uncommon |
| Business-day utilities (`add_business_days`, `business_days_between`, `business_days_until`) | Included, with `include_saturday` | Varies by library |
| External dependencies | None | Depends on the library |

If you just need to know whether a date is a holiday in any country worldwide, a generic library may be enough. If you work with Colombian payroll, legal deadlines or planning and need historical accuracy plus business-day math, this library is built specifically for that.

## Installation

```shell
pip install holidays_co_full
```

Want to try it without installing anything? Open the [example notebook](examples/demo.ipynb) in Colab:

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/carlosvisbal/holidays_co_full/blob/main/examples/demo.ipynb)

## Quick start

```python
import holidays_co_full
from datetime import date

# All holidays of a year, in chronological order
for holiday in holidays_co_full.get_colombia_holidays_by_year(2026):
    print(holiday.date, "-", holiday.celebration)

# Is a specific date a holiday? Which one?
holidays_co_full.is_holiday_date(date(2026, 7, 13))   # True (Monday shift of July 9th)
holidays_co_full.get_holiday(date(2026, 7, 20))       # Holiday(date=..., celebration='Día de la Independencia')

# Business days
holidays_co_full.is_business_day(date(2026, 7, 13))                 # False (holiday Monday)
holidays_co_full.add_business_days(date(2026, 7, 10), 5)            # date(2026, 7, 21)
holidays_co_full.business_days_between(date(2026, 7, 1), date(2026, 7, 31))  # 21
```

## API

All functions that receive dates accept `datetime.date` or `datetime.datetime` (the time component is ignored), raise `TypeError` on invalid types and `ValueError` on dates outside the supported range `[1970, 9999]`.

Holidays are returned as the `Holiday` `namedtuple`:

| Field | Type | Description |
|---|---|---|
| `date` | `datetime.date` | Effective celebration date (with the Monday shift already applied) |
| `celebration` | `str` | Official name of the holiday |

### Querying holidays

#### `get_colombia_holidays_by_year(year)`

Returns the list of the year's 19 holidays, sorted by date. Accepts `int` or a numeric string (`"2026"`); rejects `float` to avoid silent truncation.

```python
>>> holidays_co_full.get_colombia_holidays_by_year(2026)[0]
Holiday(date=datetime.date(2026, 1, 1), celebration='Año Nuevo')
```

**Use cases:** populating a year's work calendar in a payroll or shift-scheduling system; preloading holidays into an application's database; generating an intranet's yearly calendar.

#### `is_holiday_date(d)`

`True` if the date is a holiday, `False` otherwise.

```python
>>> holidays_co_full.is_holiday_date(date(2026, 1, 12))
True
```

**Use cases:** validating in a form that a chosen date isn't a holiday (appointment scheduling, delivery planning); deciding whether to apply a holiday surcharge in a payroll settlement.

#### `get_holiday(d)`

Returns the `Holiday` celebrated on the date, or `None` if it isn't one. Unlike `is_holiday_date`, it tells you *which* holiday it is.

```python
>>> holidays_co_full.get_holiday(date(2026, 7, 20)).celebration
'Día de la Independencia'
```

**Use cases:** showing the holiday name in payroll reports and pay stubs; notifications like "no service on Monday due to Epiphany"; labeling holidays on a visual calendar.

#### `next_holiday(d)`

The next holiday strictly after the date; if none remain in the year, it continues into the next one.

```python
>>> holidays_co_full.next_holiday(date(2026, 12, 26))
Holiday(date=datetime.date(2027, 1, 1), celebration='Año Nuevo')
```

**Use cases:** "N days until the next holiday" counters; planning deployments and maintenance windows outside long weekends; calendar widgets on dashboards.

#### `get_holidays_between(start, end)`

Holidays within a date range (both ends inclusive); the range can span multiple years.

```python
>>> [h.date.isoformat() for h in holidays_co_full.get_holidays_between(date(2026, 12, 1), date(2027, 1, 31))]
['2026-12-08', '2026-12-25', '2027-01-01', '2027-01-11']
```

**Use cases:** counting the holidays in a billing period or an academic semester; building project schedules that exclude holidays; quarterly financial reports.

### Business days

All three functions accept the optional `include_saturday` parameter (`False` by default): with `True`, non-holiday Saturdays count as business days, useful for businesses with Saturday hours (banks, retail).

#### `is_business_day(d, include_saturday=False)`

`True` if the date isn't a Sunday, a holiday, or a Saturday (unless `include_saturday=True`).

```python
>>> holidays_co_full.is_business_day(date(2026, 7, 13))   # holiday Monday
False
>>> holidays_co_full.is_business_day(date(2026, 7, 11), include_saturday=True)   # Saturday
True
```

**Use cases:** deciding whether a batch process runs today; validating delivery dates in logistics; determining whether a payment is credited the same day.

#### `add_business_days(d, n, include_saturday=False)`

Adds (or subtracts, with negative `n`) `n` business days to the date, skipping weekends and holidays. The starting date doesn't count toward `n`.

```python
>>> holidays_co_full.add_business_days(date(2026, 7, 10), 1)   # Friday + 1 business day
datetime.date(2026, 7, 14)
```
Monday the 13th is a holiday, so the result skips to Tuesday the 14th.

**Use cases:** calculating deadlines ("5 business days to respond to a complaint"); legal or administrative terms; support SLA due dates; estimating when a payment will be credited.

#### `business_days_between(start, end, include_saturday=False)`

Counts the business days in the range, both ends inclusive (same criterion as the spreadsheet function `NETWORKDAYS`).

```python
>>> holidays_co_full.business_days_between(date(2026, 7, 13), date(2026, 7, 17))
4
```

**Use cases:** settling payroll by actual days worked; measuring process durations in business days; estimating a team's capacity for a sprint or a month.

#### `business_days_until(d, from_date=None, include_saturday=False, include_today=False)`

Answers "how many business days are left until this date?". Counts Monday-to-Friday days that aren't holidays, up to and including the target date. With `include_today=False` (default) the reference date (today, or `from_date`) doesn't count and counting starts the next day; with `include_today=True`, the reference date counts too if it's a business day. Raises `ValueError` if the target date has already passed.

```python
>>> # Today is Monday, July 6, 2026; Monday the 13th is a holiday
>>> holidays_co_full.business_days_until(date(2026, 7, 17))
8
>>> # Also counting today (a business-day Monday)
>>> holidays_co_full.business_days_until(date(2026, 7, 17), include_today=True)
9
>>> # With an explicit reference date (reports, simulations)
>>> holidays_co_full.business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6))
8
```

**Use cases:** business days left until a complaint or contract deadline; countdown to a monthly close or a delivery; working days remaining before a vacation; "less than 3 business days left" alerts.

## End-to-end example: a complaint's response deadline

```python
from datetime import date
import holidays_co_full

filed_on = date(2026, 7, 8)  # Wednesday
due_date = holidays_co_full.add_business_days(filed_on, 15)
print(f"Filed on {filed_on}, due on {due_date}")
if holiday := holidays_co_full.get_holiday(filed_on):
    print(f"Heads up: filed on a holiday ({holiday.celebration})")
print(f"Next holiday: {holidays_co_full.next_holiday(date.today())}")
```

## Historical accuracy

The package doesn't apply today's calendar retroactively: it reproduces the rules in force in each year.

- **Monday shift**: [Law 51 of 1983](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4954) ("Ley Emiliani") has only been in force since **1984** (constant `LEY_EMILIANI_YEAR`). For earlier years, shiftable holidays are returned on their natural date, without moving to Monday.
- **Per-holiday validity**: each entry in `HOLIDAYS` has an optional `valid_from` field; the **July 9th** holiday (Our Lady of the Rosary of Chiquinquirá) has only existed since **2026**, under **Law 2578 of 2026**.
- **Official name changes**: October 12th was called "Día de la Raza" until 2020 and has officially been called "Día de la Diversidad Étnica y Cultural de la Nación Colombiana" since **2021**, under **Resolution 0138 of 2021** from the Ministry of Culture. That holiday's `celebration` field reflects the name in force for each year.

That's why `get_colombia_holidays_by_year(year)` may return **18 holidays** for years before 2026 and **19** from 2026 onward, and the name of the same holiday may vary depending on the queried year.

```python
>>> holidays_co_full.get_colombia_holidays_by_year(1970)[1]   # Tuesday, January 6, 1970: no shift
Holiday(date=datetime.date(1970, 1, 6), celebration='Día de los Reyes Magos')
>>> holidays_co_full.get_colombia_holidays_by_year(1984)[1]    # Friday, January 6, 1984: shifted to Monday the 9th
Holiday(date=datetime.date(1984, 1, 9), celebration='Día de los Reyes Magos')
>>> len(holidays_co_full.get_colombia_holidays_by_year(2025))  # without the July 9th holiday
18
>>> len(holidays_co_full.get_colombia_holidays_by_year(2026))  # with the July 9th holiday
19
>>> holidays_co_full.get_holiday(date(2020, 10, 12)).celebration   # old name
'Día de la Raza'
>>> holidays_co_full.get_holiday(date(2026, 10, 12)).celebration   # current official name
'Día de la Diversidad Étnica y Cultural de la Nación Colombiana'
```

**Use case:** payroll calculations or retroactive settlements (e.g. recalculating past years' holiday surcharges) that need the legal calendar in force at that time, not the current one; reports that must show a holiday's correct official name based on the document's date.

## Holidays included

Colombia has 19 holidays per year since 2026 (18 in earlier years, without the July 9th holiday), of three types:

### Fixed (always celebrated on their date)

| Date | Celebration |
|---|---|
| January 1st | New Year's Day |
| May 1st | Labor Day |
| July 20th | Independence Day |
| August 7th | Battle of Boyacá |
| December 8th | Immaculate Conception |
| December 25th | Christmas Day |

### Shiftable (since 1984, moved to the following Monday if they don't fall on one — Ley Emiliani)

| Base date | Celebration |
|---|---|
| January 6th | Epiphany |
| March 19th | Saint Joseph's Day |
| June 29th | Saints Peter and Paul |
| July 9th | Our Lady of the Rosary of Chiquinquirá (since 2026, Law 2578 of 2026) |
| August 15th | Assumption of Mary |
| October 12th | Ethnic and Cultural Diversity Day of the Colombian Nation (since 2021; "Día de la Raza" in earlier years) |
| November 1st | All Saints' Day |
| November 11th | Independence of Cartagena |

### Easter-relative (depend on each year's Easter Sunday)

| Offset | Celebration | Resulting day |
|---|---|---|
| Easter − 3 | Maundy Thursday | Thursday |
| Easter − 2 | Good Friday | Friday |
| Easter + 43 | Ascension of Jesus | Monday (shifted) |
| Easter + 64 | Corpus Christi | Monday (shifted) |
| Easter + 71 | Sacred Heart of Jesus | Monday (shifted) |

## How the calculation works

A year's calculation happens in four steps (see [`holidays_co_full/__init__.py`](https://github.com/carlosvisbal/holidays_co_full/blob/main/holidays_co_full/__init__.py)):

1. **Calendar holidays**: for each entry in the `HOLIDAYS` table, the date `date(year, month, day)` is built. If the holiday is shiftable (`days_to_sum = calendar.MONDAY`) and the date doesn't fall on a Monday, it's moved to the following Monday with `next_weekday()`. If it already falls on a Monday, it's celebrated that same day.
2. **Easter Sunday**: `calc_easter(year)` computes the Western Easter date with the anonymous/Meeus computus algorithm, valid for any Gregorian calendar year.
3. **Holy Week and later holidays**: the offsets in the `EASTER_WEEK_HOLIDAYS` table are added to the Easter date. Since Easter always falls on a Sunday, the +43, +64 and +71 offsets already correspond to the shifted Mondays of Ascension (+39), Corpus Christi (+60) and Sacred Heart (+68), with no extra calculation needed.
4. **Sorting and caching**: the two lists are combined, sorted by date and stored in an in-memory cache (`functools.lru_cache`), so repeated queries for the same year — e.g. many calls to `is_holiday_date()` or the business-day functions' loops — don't recompute anything. Public functions always return new objects, so mutating a result doesn't affect the cache.

## Tests

The suite lives in [`tests/test_holidays_co.py`](https://github.com/carlosvisbal/holidays_co_full/blob/main/tests/test_holidays_co.py) and needs no dependencies: it runs with the standard library's `unittest` (also compatible with pytest if installed).

```shell
# From the repository root
python -m unittest discover tests -v

# Or with pytest
pytest tests/ -v

# Docstring examples are checkable too
python -m doctest holidays_co_full/__init__.py && echo OK
```

Every feature has its own test class, with use cases and edge cases pinned against the official Colombian calendar:

| Test class | Coverage |
|---|---|
| `TestGetColombiaHolidaysByYear` | Full 2026 calendar, Monday shifts, type/range validation, cache isolation |
| `TestHistoricalAccuracy` | Monday shift only from 1984, July 9th holiday only from 2026, Holy Week holidays never shift, October 12th name change from 2021 |
| `TestIsHolidayDate` | Holidays, regular days, shifted dates, `datetime` support |
| `TestGetHoliday` | Celebration name and `None` on regular days |
| `TestNextHoliday` | Search within the year, crossing into the next year, excluding the reference date |
| `TestGetHolidaysBetween` | Inclusive ranges, ranges crossing years, empty and invalid ranges |
| `TestIsBusinessDay` | Weekdays, holidays, Sundays and the `include_saturday` parameter |
| `TestAddBusinessDays` | Skipping weekends and holidays, negative and zero `n`, `n` validation |
| `TestBusinessDaysBetween` | Weeks with a holiday, inclusive counting, `include_saturday`, invalid ranges |
| `TestBusinessDaysUntil` | Days remaining until a date, `include_today` parameter, target date today or past, default value (today) |

## Requirements

- Python 3 (standard library only).

## Credits

**Author:** Carlos Visbal <_carlosvisbal66@gmail.com_>

- This version rewrites and extends the original with the features described in this README, while keeping API compatibility.
- Reference: original [holidays-co v1.0.0](https://pypi.org/project/holidays-co/) package on PyPI.

## License

See the project's [LICENSE](https://github.com/carlosvisbal/holidays_co_full/blob/main/LICENSE) file (MIT).
