"""Tests de holidays_co.

Se ejecutan con la librería estándar (``python -m unittest``) o con pytest
(``pytest``). Las fechas esperadas están fijadas a mano contra el
calendario oficial colombiano para blindar la lógica de cálculo.
"""

import unittest
from datetime import date, datetime

import holidays_co_full


# Calendario oficial de Colombia para 2026, fijado a mano.
EXPECTED_2026 = [
    (date(2026, 1, 1), "Año Nuevo"),
    (date(2026, 1, 12), "Día de los Reyes Magos"),
    (date(2026, 3, 23), "Día de San José"),
    (date(2026, 4, 2), "Jueves Santo"),
    (date(2026, 4, 3), "Viernes Santo"),
    (date(2026, 5, 1), "Día del Trabajo"),
    (date(2026, 5, 18), "Ascensión del Señor"),
    (date(2026, 6, 8), "Corpus Christi"),
    (date(2026, 6, 15), "Sagrado Corazón de Jesús"),
    (date(2026, 6, 29), "San Pedro y San Pablo"),
    (date(2026, 7, 13), "Día Nacional de Nuestra Señora del Rosario de Chiquinquirá"),
    (date(2026, 7, 20), "Día de la Independencia"),
    (date(2026, 8, 7), "Batalla de Boyacá"),
    (date(2026, 8, 17), "La Asunción de la Virgen"),
    (date(2026, 10, 12), "Día de la Diversidad Étnica y Cultural de la Nación Colombiana"),
    (date(2026, 11, 2), "Todos los Santos"),
    (date(2026, 11, 16), "Independencia de Cartagena"),
    (date(2026, 12, 8), "Día de la Inmaculada Concepción"),
    (date(2026, 12, 25), "Día de Navidad"),
]


class TestGetColombiaHolidaysByYear(unittest.TestCase):
    def test_full_2026_calendar(self):
        holidays = holidays_co_full.get_colombia_holidays_by_year(2026)
        self.assertEqual([(h.date, h.celebration) for h in holidays], EXPECTED_2026)

    def test_returns_19_holidays_from_2026_onward(self):
        for year in (2026, 2100, 9999):
            self.assertEqual(len(holidays_co_full.get_colombia_holidays_by_year(year)), 19)

    def test_returns_18_holidays_before_july9_holiday(self):
        # Antes de 2026 no existe el festivo del 9 de julio.
        for year in (1970, 1984, 1999, 2025):
            self.assertEqual(len(holidays_co_full.get_colombia_holidays_by_year(year)), 18)

    def test_sorted_by_date(self):
        for year in (2025, 2026, 2030):
            dates = [h.date for h in holidays_co_full.get_colombia_holidays_by_year(year)]
            self.assertEqual(dates, sorted(dates))

    def test_movable_holiday_stays_when_already_monday(self):
        # San Pedro y San Pablo: el 29 de junio de 2026 es lunes y no se mueve.
        holidays = {h.celebration: h.date for h in holidays_co_full.get_colombia_holidays_by_year(2026)}
        self.assertEqual(holidays["San Pedro y San Pablo"], date(2026, 6, 29))

    def test_movable_holiday_shifts_to_next_monday(self):
        # Reyes Magos: el 6 de enero de 2026 es martes, se celebra el lunes 12.
        holidays = {h.celebration: h.date for h in holidays_co_full.get_colombia_holidays_by_year(2026)}
        self.assertEqual(holidays["Día de los Reyes Magos"], date(2026, 1, 12))

    def test_accepts_numeric_string(self):
        self.assertEqual(holidays_co_full.get_colombia_holidays_by_year("2026")[0].date, date(2026, 1, 1))

    def test_rejects_floats(self):
        for bad in (2026.0, 2026.9):
            with self.assertRaises(TypeError):
                holidays_co_full.get_colombia_holidays_by_year(bad)

    def test_rejects_non_numeric(self):
        for bad in (None, "abc", [2026]):
            with self.assertRaises(TypeError):
                holidays_co_full.get_colombia_holidays_by_year(bad)

    def test_rejects_out_of_range_years(self):
        for bad in (1969, 10000):
            with self.assertRaises(ValueError):
                holidays_co_full.get_colombia_holidays_by_year(bad)

    def test_result_is_isolated_from_cache(self):
        first = holidays_co_full.get_colombia_holidays_by_year(2026)
        first.append("basura")
        self.assertEqual(len(holidays_co_full.get_colombia_holidays_by_year(2026)), 19)

    def test_internal_year_cache_is_bounded(self):
        # El caché por año no debe crecer sin límite: tiene un maxsize
        # LRU real, no None. Consultamos más años de los que caben para
        # forzar evictions y confirmar que el tamaño se mantiene acotado.
        for year in range(1970, 1970 + holidays_co_full._YEAR_CACHE_SIZE + 50):
            holidays_co_full.get_colombia_holidays_by_year(year)
        self.assertLessEqual(
            holidays_co_full._get_holidays.cache_info().currsize, holidays_co_full._YEAR_CACHE_SIZE
        )
        self.assertLessEqual(
            holidays_co_full._holiday_dates.cache_info().currsize, holidays_co_full._YEAR_CACHE_SIZE
        )


class TestHistoricalAccuracy(unittest.TestCase):
    """La Ley Emiliani (traslado al lunes) solo rige desde 1984."""

    def test_movable_holiday_not_shifted_before_1984(self):
        # 1970-01-06 es martes; antes de la Ley Emiliani no se traslada.
        holidays = {h.celebration: h.date for h in holidays_co_full.get_colombia_holidays_by_year(1970)}
        self.assertEqual(holidays["Día de los Reyes Magos"], date(1970, 1, 6))

    def test_movable_holiday_shifted_from_1984(self):
        # 1984-01-06 es viernes; desde la Ley Emiliani se traslada al lunes 9.
        holidays = {h.celebration: h.date for h in holidays_co_full.get_colombia_holidays_by_year(1984)}
        self.assertEqual(holidays["Día de los Reyes Magos"], date(1984, 1, 9))

    def test_easter_movable_holiday_not_shifted_before_1984(self):
        holidays = {h.celebration: h.date for h in holidays_co_full.get_colombia_holidays_by_year(1970)}
        self.assertEqual(holidays["Ascensión del Señor"].weekday(), 3)  # jueves, sin trasladar

    def test_easter_fixed_holidays_never_shift(self):
        # Jueves y Viernes Santo nunca se trasladan, en ningún año.
        for year in (1970, 1984, 2026):
            holidays = {h.celebration: h.date for h in holidays_co_full.get_colombia_holidays_by_year(year)}
            self.assertEqual(holidays["Jueves Santo"].weekday(), 3)
            self.assertEqual(holidays["Viernes Santo"].weekday(), 4)

    def test_july9_holiday_absent_before_2026(self):
        holidays = {h.celebration for h in holidays_co_full.get_colombia_holidays_by_year(2025)}
        self.assertNotIn("Día Nacional de Nuestra Señora del Rosario de Chiquinquirá", holidays)

    def test_july9_holiday_present_from_2026(self):
        holidays = {h.celebration for h in holidays_co_full.get_colombia_holidays_by_year(2026)}
        self.assertIn("Día Nacional de Nuestra Señora del Rosario de Chiquinquirá", holidays)

    def test_is_holiday_date_respects_historical_shift(self):
        # 1970-01-06 (martes) no se traslada: el día festivo es el 6, no el 12.
        self.assertTrue(holidays_co_full.is_holiday_date(date(1970, 1, 6)))
        self.assertFalse(holidays_co_full.is_holiday_date(date(1970, 1, 12)))

    def test_october12_uses_old_name_before_2021(self):
        holiday = holidays_co_full.get_holiday(date(2020, 10, 12))
        self.assertEqual(holiday.celebration, "Día de la Raza")

    def test_october12_uses_new_name_from_2021(self):
        # El 12 de octubre de 2021 es martes; se traslada al lunes 18.
        holiday = holidays_co_full.get_holiday(date(2021, 10, 18))
        self.assertEqual(
            holiday.celebration, "Día de la Diversidad Étnica y Cultural de la Nación Colombiana"
        )


class TestIsHolidayDate(unittest.TestCase):
    def test_holiday_true(self):
        self.assertTrue(holidays_co_full.is_holiday_date(date(2026, 7, 20)))

    def test_shifted_holiday(self):
        # El 9 de julio de 2026 (jueves) se traslada al lunes 13.
        self.assertFalse(holidays_co_full.is_holiday_date(date(2026, 7, 9)))
        self.assertTrue(holidays_co_full.is_holiday_date(date(2026, 7, 13)))

    def test_regular_day_false(self):
        self.assertFalse(holidays_co_full.is_holiday_date(date(2026, 7, 14)))

    def test_accepts_datetime(self):
        self.assertTrue(holidays_co_full.is_holiday_date(datetime(2026, 7, 20, 15, 30)))

    def test_rejects_non_date(self):
        with self.assertRaises(TypeError):
            holidays_co_full.is_holiday_date("2026-07-20")

    def test_rejects_year_before_1970(self):
        with self.assertRaises(ValueError):
            holidays_co_full.is_holiday_date(date(1969, 12, 25))


class TestGetHoliday(unittest.TestCase):
    def test_returns_celebration(self):
        holiday = holidays_co_full.get_holiday(date(2026, 7, 20))
        self.assertEqual(holiday.celebration, "Día de la Independencia")
        self.assertEqual(holiday.date, date(2026, 7, 20))

    def test_returns_none_for_regular_day(self):
        self.assertIsNone(holidays_co_full.get_holiday(date(2026, 7, 14)))

    def test_accepts_datetime(self):
        holiday = holidays_co_full.get_holiday(datetime(2026, 12, 25, 8, 0))
        self.assertEqual(holiday.celebration, "Día de Navidad")


class TestNextHoliday(unittest.TestCase):
    def test_within_year(self):
        holiday = holidays_co_full.next_holiday(date(2026, 7, 14))
        self.assertEqual(holiday.date, date(2026, 7, 20))

    def test_excludes_reference_date(self):
        holiday = holidays_co_full.next_holiday(date(2026, 7, 20))
        self.assertEqual(holiday.date, date(2026, 8, 7))

    def test_crosses_year(self):
        holiday = holidays_co_full.next_holiday(date(2026, 12, 26))
        self.assertEqual(holiday.date, date(2027, 1, 1))
        self.assertEqual(holiday.celebration, "Año Nuevo")

    def test_no_holiday_after_supported_range(self):
        with self.assertRaises(ValueError):
            holidays_co_full.next_holiday(date(9999, 12, 26))


class TestGetHolidaysBetween(unittest.TestCase):
    def test_inclusive_range(self):
        holidays = holidays_co_full.get_holidays_between(date(2026, 7, 13), date(2026, 7, 20))
        self.assertEqual([h.date for h in holidays], [date(2026, 7, 13), date(2026, 7, 20)])

    def test_crosses_years(self):
        holidays = holidays_co_full.get_holidays_between(date(2026, 12, 1), date(2027, 1, 31))
        self.assertEqual(
            [h.date for h in holidays],
            [date(2026, 12, 8), date(2026, 12, 25), date(2027, 1, 1), date(2027, 1, 11)],
        )

    def test_empty_range(self):
        self.assertEqual(holidays_co_full.get_holidays_between(date(2026, 7, 14), date(2026, 7, 17)), [])

    def test_start_after_end_raises(self):
        with self.assertRaises(ValueError):
            holidays_co_full.get_holidays_between(date(2026, 7, 20), date(2026, 7, 13))


class TestIsBusinessDay(unittest.TestCase):
    def test_weekday_is_business_day(self):
        self.assertTrue(holidays_co_full.is_business_day(date(2026, 7, 14)))  # martes

    def test_holiday_is_not_business_day(self):
        self.assertFalse(holidays_co_full.is_business_day(date(2026, 7, 13)))  # lunes festivo

    def test_sunday_is_not_business_day(self):
        self.assertFalse(holidays_co_full.is_business_day(date(2026, 7, 12)))

    def test_saturday_depends_on_flag(self):
        saturday = date(2026, 7, 11)
        self.assertFalse(holidays_co_full.is_business_day(saturday))
        self.assertTrue(holidays_co_full.is_business_day(saturday, include_saturday=True))


class TestAddBusinessDays(unittest.TestCase):
    def test_skips_weekend_and_holiday(self):
        # Viernes 10 + 1 hábil: salta sábado, domingo y el lunes festivo 13.
        self.assertEqual(holidays_co_full.add_business_days(date(2026, 7, 10), 1), date(2026, 7, 14))

    def test_multiple_days(self):
        self.assertEqual(holidays_co_full.add_business_days(date(2026, 7, 10), 5), date(2026, 7, 21))

    def test_negative_days(self):
        self.assertEqual(holidays_co_full.add_business_days(date(2026, 7, 14), -1), date(2026, 7, 10))

    def test_zero_returns_same_date(self):
        self.assertEqual(holidays_co_full.add_business_days(date(2026, 7, 13), 0), date(2026, 7, 13))

    def test_include_saturday(self):
        self.assertEqual(
            holidays_co_full.add_business_days(date(2026, 7, 10), 1, include_saturday=True),
            date(2026, 7, 11),
        )

    def test_rejects_non_integer_n(self):
        for bad in (1.5, "2", None, True):
            with self.assertRaises(TypeError):
                holidays_co_full.add_business_days(date(2026, 7, 10), bad)


class TestBusinessDaysBetween(unittest.TestCase):
    def test_week_with_holiday(self):
        # Semana del 13 al 17 de julio de 2026: 5 días menos el lunes festivo.
        self.assertEqual(holidays_co_full.business_days_between(date(2026, 7, 13), date(2026, 7, 17)), 4)

    def test_full_week_with_weekend(self):
        self.assertEqual(holidays_co_full.business_days_between(date(2026, 7, 13), date(2026, 7, 19)), 4)

    def test_include_saturday(self):
        self.assertEqual(
            holidays_co_full.business_days_between(date(2026, 7, 13), date(2026, 7, 19), include_saturday=True),
            5,
        )

    def test_single_day_range(self):
        self.assertEqual(holidays_co_full.business_days_between(date(2026, 7, 14), date(2026, 7, 14)), 1)
        self.assertEqual(holidays_co_full.business_days_between(date(2026, 7, 13), date(2026, 7, 13)), 0)

    def test_start_after_end_raises(self):
        with self.assertRaises(ValueError):
            holidays_co_full.business_days_between(date(2026, 7, 17), date(2026, 7, 13))


class TestBusinessDaysUntil(unittest.TestCase):
    def test_excludes_reference_day_and_holiday(self):
        # Del lunes 6 al viernes 17 de julio de 2026: se cuenta desde el
        # martes 7 y el lunes 13 es festivo → 8 días hábiles restantes.
        self.assertEqual(
            holidays_co_full.business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6)), 8
        )

    def test_same_date_returns_zero(self):
        self.assertEqual(
            holidays_co_full.business_days_until(date(2026, 7, 14), from_date=date(2026, 7, 14)), 0
        )

    def test_next_day_holiday_counts_zero(self):
        # Del viernes 10 al lunes festivo 13: fin de semana + festivo → 0.
        self.assertEqual(
            holidays_co_full.business_days_until(date(2026, 7, 13), from_date=date(2026, 7, 10)), 0
        )

    def test_include_saturday(self):
        self.assertEqual(
            holidays_co_full.business_days_until(
                date(2026, 7, 13), from_date=date(2026, 7, 10), include_saturday=True
            ),
            1,
        )

    def test_defaults_to_today(self):
        from datetime import timedelta
        today = date.today()
        target = today + timedelta(days=30)
        expected = holidays_co_full.business_days_until(target, from_date=today)
        self.assertEqual(holidays_co_full.business_days_until(target), expected)

    def test_target_before_reference_raises(self):
        with self.assertRaises(ValueError):
            holidays_co_full.business_days_until(date(2026, 7, 10), from_date=date(2026, 7, 17))

    def test_include_today_counts_reference_day(self):
        # El lunes 6 es hábil: con include_today el conteo pasa de 8 a 9.
        self.assertEqual(
            holidays_co_full.business_days_until(
                date(2026, 7, 17), from_date=date(2026, 7, 6), include_today=True
            ),
            9,
        )

    def test_include_today_same_date_business_day(self):
        # Objetivo = referencia y es día hábil: cuenta 1 con include_today.
        self.assertEqual(
            holidays_co_full.business_days_until(
                date(2026, 7, 14), from_date=date(2026, 7, 14), include_today=True
            ),
            1,
        )

    def test_include_today_ignores_non_business_reference(self):
        # La referencia es el lunes festivo 13: aunque include_today=True, no cuenta.
        self.assertEqual(
            holidays_co_full.business_days_until(
                date(2026, 7, 14), from_date=date(2026, 7, 13), include_today=True
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
