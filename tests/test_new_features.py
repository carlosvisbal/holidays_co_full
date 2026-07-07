"""Tests de las funciones agregadas en la versión 1.1.0.

Cubre los metadatos de ``Holiday`` (``original_date``, ``is_shifted``,
``kind``), ``previous_holiday``, ``long_weekends``, la clase
``HolidayCalendar``, los exports JSON/iCal, la integración con pandas
(se omite si pandas no está instalado) y la CLI ``holidays-co``.
"""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime

import holidays_co_full
from holidays_co_full import cli


class TestHolidayMetadata(unittest.TestCase):
    def test_fixed_holiday_metadata(self):
        holiday = holidays_co_full.get_holiday(date(2026, 1, 1))
        self.assertEqual(holiday.original_date, date(2026, 1, 1))
        self.assertFalse(holiday.is_shifted)
        self.assertEqual(holiday.kind, "fixed")

    def test_shifted_movable_holiday_metadata(self):
        # Reyes Magos 2026: el 6 de enero es martes, se celebra el lunes 12.
        holiday = holidays_co_full.get_holiday(date(2026, 1, 12))
        self.assertEqual(holiday.original_date, date(2026, 1, 6))
        self.assertTrue(holiday.is_shifted)
        self.assertEqual(holiday.kind, "movable")

    def test_unshifted_movable_holiday_metadata(self):
        # San Pedro y San Pablo 2026: el 29 de junio ya es lunes.
        holiday = holidays_co_full.get_holiday(date(2026, 6, 29))
        self.assertEqual(holiday.original_date, date(2026, 6, 29))
        self.assertFalse(holiday.is_shifted)
        self.assertEqual(holiday.kind, "movable")

    def test_easter_holiday_metadata(self):
        holiday = holidays_co_full.get_holiday(date(2026, 4, 3))  # Viernes Santo
        self.assertEqual(holiday.kind, "easter")
        self.assertFalse(holiday.is_shifted)

    def test_shifted_easter_holiday_metadata(self):
        # Ascensión 2026: Pascua + 39 = jueves 14 de mayo, trasladada al lunes 18.
        holiday = holidays_co_full.get_holiday(date(2026, 5, 18))
        self.assertEqual(holiday.kind, "easter")
        self.assertTrue(holiday.is_shifted)
        self.assertEqual(holiday.original_date, date(2026, 5, 14))

    def test_not_shifted_before_ley_emiliani(self):
        # 1970: no rige el traslado, ningún festivo aparece como trasladado.
        for holiday in holidays_co_full.get_colombia_holidays_by_year(1970):
            self.assertFalse(holiday.is_shifted)
            self.assertEqual(holiday.date, holiday.original_date)

    def test_two_field_construction_still_works(self):
        holiday = holidays_co_full.Holiday(date(2026, 1, 1), "Año Nuevo")
        self.assertIsNone(holiday.original_date)
        self.assertFalse(holiday.is_shifted)
        self.assertIsNone(holiday.kind)


class TestPreviousHoliday(unittest.TestCase):
    def test_within_year(self):
        holiday = holidays_co_full.previous_holiday(date(2026, 7, 19))
        self.assertEqual(holiday.date, date(2026, 7, 13))

    def test_excludes_reference_date(self):
        holiday = holidays_co_full.previous_holiday(date(2026, 7, 20))
        self.assertEqual(holiday.date, date(2026, 7, 13))

    def test_crosses_year(self):
        holiday = holidays_co_full.previous_holiday(date(2026, 1, 1))
        self.assertEqual(holiday.date, date(2025, 12, 25))
        self.assertEqual(holiday.celebration, "Día de Navidad")

    def test_accepts_datetime(self):
        holiday = holidays_co_full.previous_holiday(datetime(2026, 1, 5, 8, 0))
        self.assertEqual(holiday.date, date(2026, 1, 1))

    def test_no_holiday_before_supported_range(self):
        with self.assertRaises(ValueError):
            holidays_co_full.previous_holiday(date(1970, 1, 1))

    def test_rejects_non_date(self):
        with self.assertRaises(TypeError):
            holidays_co_full.previous_holiday("2026-07-20")


class TestLongWeekends(unittest.TestCase):
    def test_2026_has_16_long_weekends(self):
        self.assertEqual(len(holidays_co_full.long_weekends(2026)), 16)

    def test_monday_holiday_makes_three_day_weekend(self):
        # Reyes Magos 2026 (lunes 12): puente sábado 10 - lunes 12.
        puente = holidays_co_full.long_weekends(2026)[0]
        self.assertEqual(puente.start, date(2026, 1, 10))
        self.assertEqual(puente.end, date(2026, 1, 12))
        self.assertEqual(puente.days, 3)
        self.assertEqual([h.celebration for h in puente.holidays], ["Día de los Reyes Magos"])

    def test_semana_santa_block_spans_four_days(self):
        # Jueves 2 y Viernes Santo 3 de abril + fin de semana = 4 días.
        puentes = {p.start: p for p in holidays_co_full.long_weekends(2026)}
        semana_santa = puentes[date(2026, 4, 2)]
        self.assertEqual(semana_santa.end, date(2026, 4, 5))
        self.assertEqual(semana_santa.days, 4)
        self.assertEqual(
            [h.celebration for h in semana_santa.holidays],
            ["Jueves Santo", "Viernes Santo"],
        )

    def test_isolated_weekday_holiday_is_not_long_weekend(self):
        # El 8 de diciembre de 2026 (martes) no forma puente.
        starts = {p.start for p in holidays_co_full.long_weekends(2026)}
        self.assertNotIn(date(2026, 12, 8), starts)

    def test_include_saturday_removes_monday_bridges(self):
        # Con sábado hábil, un lunes festivo solo deja domingo-lunes (2 días).
        puentes = holidays_co_full.long_weekends(2026, include_saturday=True)
        self.assertTrue(all(p.days >= 3 for p in puentes))
        starts = {p.start for p in puentes}
        self.assertNotIn(date(2026, 1, 10), starts)
        self.assertNotIn(date(2026, 1, 11), starts)

    def test_sorted_by_start(self):
        starts = [p.start for p in holidays_co_full.long_weekends(2026)]
        self.assertEqual(starts, sorted(starts))

    def test_year_validation(self):
        with self.assertRaises(ValueError):
            holidays_co_full.long_weekends(1969)
        with self.assertRaises(TypeError):
            holidays_co_full.long_weekends(2026.0)

    def test_supported_range_boundaries_do_not_crash(self):
        holidays_co_full.long_weekends(1970)
        holidays_co_full.long_weekends(9999)


class TestHolidayCalendar(unittest.TestCase):
    def setUp(self):
        self.calendar = holidays_co_full.HolidayCalendar(
            extra_non_working=[(date(2026, 12, 24), "Cierre de fin de año")]
        )

    def test_extra_day_is_not_business_day(self):
        self.assertFalse(self.calendar.is_business_day(date(2026, 12, 24)))

    def test_official_holidays_still_apply(self):
        self.assertFalse(self.calendar.is_business_day(date(2026, 7, 20)))
        self.assertTrue(self.calendar.is_holiday_date(date(2026, 7, 20)))

    def test_get_holiday_returns_extra_with_kind(self):
        holiday = self.calendar.get_holiday(date(2026, 12, 24))
        self.assertEqual(holiday.celebration, "Cierre de fin de año")
        self.assertEqual(holiday.kind, "extra")

    def test_get_holiday_prefers_official(self):
        calendar = holidays_co_full.HolidayCalendar(
            extra_non_working=[(date(2026, 12, 25), "Cierre")]
        )
        holiday = calendar.get_holiday(date(2026, 12, 25))
        self.assertEqual(holiday.celebration, "Día de Navidad")
        # Y no aparece duplicado en el listado anual.
        dates = [h.date for h in calendar.get_holidays_by_year(2026)]
        self.assertEqual(len(dates), len(set(dates)))

    def test_add_business_days_skips_extra(self):
        # Miércoles 23 dic + 1 hábil: salta 24 (extra), 25 (festivo) y el finde.
        self.assertEqual(
            self.calendar.add_business_days(date(2026, 12, 23), 1), date(2026, 12, 28)
        )

    def test_business_days_between_discounts_extra(self):
        with_extra = self.calendar.business_days_between(date(2026, 12, 21), date(2026, 12, 24))
        without_extra = holidays_co_full.business_days_between(date(2026, 12, 21), date(2026, 12, 24))
        self.assertEqual(with_extra, without_extra - 1)

    def test_business_days_until_matches_module_semantics(self):
        plain = holidays_co_full.HolidayCalendar()
        self.assertEqual(
            plain.business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6)),
            holidays_co_full.business_days_until(date(2026, 7, 17), from_date=date(2026, 7, 6)),
        )

    def test_include_saturday_flag(self):
        calendar = holidays_co_full.HolidayCalendar(include_saturday=True)
        self.assertTrue(calendar.is_business_day(date(2026, 7, 11)))  # sábado

    def test_get_holidays_by_year_includes_extras_sorted(self):
        holidays = self.calendar.get_holidays_by_year(2026)
        self.assertEqual(len(holidays), 20)  # 19 oficiales + 1 extra
        dates = [h.date for h in holidays]
        self.assertEqual(dates, sorted(dates))
        self.assertIn(date(2026, 12, 24), dates)

    def test_next_and_previous_holiday_see_extras(self):
        self.assertEqual(
            self.calendar.next_holiday(date(2026, 12, 9)).date, date(2026, 12, 24)
        )
        self.assertEqual(
            self.calendar.previous_holiday(date(2026, 12, 25)).date, date(2026, 12, 24)
        )

    def test_long_weekends_extended_by_extra(self):
        # El 24 dic 2026 es jueves y el 25 viernes festivo: con el extra,
        # el bloque va del jueves 24 al domingo 27 (4 días).
        puentes = {p.start: p for p in self.calendar.long_weekends(2026)}
        self.assertIn(date(2026, 12, 24), puentes)
        self.assertEqual(puentes[date(2026, 12, 24)].days, 4)

    def test_accepts_plain_dates_and_dict(self):
        from_list = holidays_co_full.HolidayCalendar(extra_non_working=[date(2026, 3, 2)])
        self.assertEqual(
            from_list.get_holiday(date(2026, 3, 2)).celebration, "Día no laborable"
        )
        from_dict = holidays_co_full.HolidayCalendar(
            extra_non_working={date(2026, 3, 2): "Aniversario"}
        )
        self.assertEqual(from_dict.get_holiday(date(2026, 3, 2)).celebration, "Aniversario")

    def test_rejects_invalid_extras(self):
        with self.assertRaises(TypeError):
            holidays_co_full.HolidayCalendar(extra_non_working=["2026-03-02"])
        with self.assertRaises(TypeError):
            holidays_co_full.HolidayCalendar(extra_non_working=[(date(2026, 3, 2), 42)])
        with self.assertRaises(ValueError):
            holidays_co_full.HolidayCalendar(extra_non_working=[date(1969, 1, 1)])


class TestToJson(unittest.TestCase):
    def test_single_year(self):
        data = json.loads(holidays_co_full.to_json(2026))
        self.assertEqual(len(data), 19)
        self.assertEqual(data[0]["date"], "2026-01-01")
        self.assertEqual(data[0]["celebration"], "Año Nuevo")
        self.assertEqual(data[0]["kind"], "fixed")
        self.assertFalse(data[0]["is_shifted"])

    def test_shifted_holiday_fields(self):
        data = json.loads(holidays_co_full.to_json(2026))
        reyes = next(h for h in data if h["celebration"] == "Día de los Reyes Magos")
        self.assertEqual(reyes["date"], "2026-01-12")
        self.assertEqual(reyes["original_date"], "2026-01-06")
        self.assertTrue(reyes["is_shifted"])

    def test_multiple_years_sorted_and_deduplicated(self):
        data = json.loads(holidays_co_full.to_json([2027, 2026, 2026]))
        self.assertEqual(len(data), 38)  # 19 + 19, sin duplicados
        dates = [h["date"] for h in data]
        self.assertEqual(dates, sorted(dates))

    def test_preserves_accents(self):
        self.assertIn("Año Nuevo", holidays_co_full.to_json(2026))

    def test_invalid_years(self):
        with self.assertRaises(ValueError):
            holidays_co_full.to_json(1969)
        with self.assertRaises(TypeError):
            holidays_co_full.to_json(None)


class TestToIcal(unittest.TestCase):
    def test_structure(self):
        ics = holidays_co_full.to_ical(2026)
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        self.assertEqual(ics.count("BEGIN:VEVENT"), 19)
        self.assertEqual(ics.count("END:VEVENT"), 19)

    def test_all_day_event_fields(self):
        ics = holidays_co_full.to_ical(2026)
        self.assertIn("DTSTART;VALUE=DATE:20260101", ics)
        self.assertIn("DTEND;VALUE=DATE:20260102", ics)
        self.assertIn("SUMMARY:Año Nuevo", ics)

    def test_uids_are_unique_and_deterministic(self):
        ics = holidays_co_full.to_ical(2026)
        uids = [line for line in ics.split("\r\n") if line.startswith("UID:")]
        self.assertEqual(len(uids), 19)
        self.assertEqual(len(set(uids)), 19)
        self.assertEqual(ics, holidays_co_full.to_ical(2026))


class TestCustomBusinessDay(unittest.TestCase):
    def setUp(self):
        try:
            import pandas  # noqa: F401
        except ImportError:
            self.skipTest("pandas no está instalado")

    def test_skips_colombian_holidays(self):
        import pandas as pd

        cbd = holidays_co_full.custom_business_day(start_year=2026, end_year=2026)
        # Viernes 10 de julio + 1 hábil salta el lunes festivo 13.
        result = pd.Timestamp("2026-07-10") + cbd
        self.assertEqual(result, pd.Timestamp("2026-07-14"))

    def test_include_saturday_weekmask(self):
        import pandas as pd

        cbd = holidays_co_full.custom_business_day(
            start_year=2026, end_year=2026, include_saturday=True
        )
        result = pd.Timestamp("2026-07-10") + cbd
        self.assertEqual(result, pd.Timestamp("2026-07-11"))

    def test_validates_year_order(self):
        with self.assertRaises(ValueError):
            holidays_co_full.custom_business_day(start_year=2027, end_year=2026)


class TestCli(unittest.TestCase):
    def _run(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_year_lists_holidays(self):
        code, out, _ = self._run(["year", "2026"])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 19)
        self.assertEqual(lines[0], "2026-01-01  Año Nuevo")

    def test_year_json(self):
        code, out, _ = self._run(["year", "2026", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)), 19)

    def test_year_ics(self):
        code, out, _ = self._run(["year", "2026", "--ics"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("BEGIN:VCALENDAR"))

    def test_check_holiday_exit_codes(self):
        code, out, _ = self._run(["check", "2026-07-20"])
        self.assertEqual(code, 0)
        self.assertIn("Día de la Independencia", out)
        code, out, _ = self._run(["check", "2026-07-21"])
        self.assertEqual(code, 1)
        self.assertIn("no es festivo", out)

    def test_next_and_prev(self):
        code, out, _ = self._run(["next", "--from", "2026-07-14"])
        self.assertEqual(code, 0)
        self.assertIn("2026-07-20", out)
        code, out, _ = self._run(["prev", "--from", "2026-07-14"])
        self.assertEqual(code, 0)
        self.assertIn("2026-07-13", out)

    def test_puentes(self):
        code, out, _ = self._run(["puentes", "2026"])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), 16)
        self.assertIn("Jueves Santo, Viernes Santo", out)

    def test_business_days(self):
        code, out, _ = self._run(["business-days", "2026-07-13", "2026-07-17"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "4")

    def test_add(self):
        code, out, _ = self._run(["add", "2026-07-10", "1"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "2026-07-14")

    def test_validation_error_exit_code(self):
        code, _, err = self._run(["year", "1969"])
        self.assertEqual(code, 2)
        self.assertIn("error:", err)


if __name__ == "__main__":
    unittest.main()
