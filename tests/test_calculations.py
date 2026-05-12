"""Tests for pure Solar Amortisation calculations."""

from __future__ import annotations

import unittest
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from custom_components.solar_amortisation.calculations import (
    calculate_backfill_records,
    calculate_daily_record,
    calculate_days_since_start,
    calculate_energy_deltas,
    calculate_forecasts,
    value_for_date,
)
from custom_components.solar_amortisation.energy_dashboard import (
    energy_dashboard_config_from_prefs,
)
from custom_components.solar_amortisation.models import (
    DailyRecord,
    EnergyDeltas,
    MeterSnapshot,
    PricePeriod,
)
from custom_components.solar_amortisation.statistics import (
    build_daily_deltas_from_statistics,
)
from custom_components.solar_amortisation.statistics_importer import (
    build_measurement_statistics,
)


class CalculationTest(unittest.TestCase):
    def test_value_for_date_uses_latest_applicable_period(self) -> None:
        periods = (
            PricePeriod(date(2026, 1, 1), 0.30),
            PricePeriod(date(2026, 4, 1), 0.34),
            PricePeriod(date(2027, 1, 1), 0.29),
        )

        self.assertEqual(value_for_date(periods, date(2026, 5, 4)), 0.34)

    def test_value_for_date_raises_when_no_period_applies(self) -> None:
        with self.assertRaisesRegex(ValueError, "No value configured"):
            value_for_date((PricePeriod(date(2026, 5, 1), 0.30),), date(2026, 4, 30))

    def test_calculate_daily_record_stores_daily_price_and_tariff(self) -> None:
        record = calculate_daily_record(
            site_id="site-a",
            record_date=date(2026, 5, 4),
            investment_amount=10_000,
            deltas=EnergyDeltas(
                pv_generation_kwh=20,
                grid_import_kwh=5,
                grid_export_kwh=8,
            ),
            electricity_price_eur_kwh=0.32,
            feed_in_tariff_eur_kwh=0.08,
            previous_records=[],
        )

        self.assertEqual(record.self_consumed_pv_kwh, 12)
        self.assertEqual(record.battery_discharge_kwh, 0)
        self.assertEqual(record.battery_charge_kwh, 0)
        self.assertEqual(record.daily_savings_eur, 3.84)
        self.assertEqual(record.daily_revenue_eur, 0.64)
        self.assertEqual(record.daily_return_eur, 4.48)
        self.assertEqual(record.remaining_amount_eur, 9_995.52)
        self.assertEqual(record.electricity_price_eur_kwh, 0.32)
        self.assertEqual(record.feed_in_tariff_eur_kwh, 0.08)

    def test_calculate_daily_record_includes_previous_returns(self) -> None:
        previous = _record(date(2026, 5, 3), 10)

        record = calculate_daily_record(
            site_id="site-a",
            record_date=date(2026, 5, 4),
            investment_amount=100,
            deltas=EnergyDeltas(
                pv_generation_kwh=10,
                grid_import_kwh=0,
                grid_export_kwh=0,
            ),
            electricity_price_eur_kwh=0.50,
            feed_in_tariff_eur_kwh=0,
            previous_records=[previous],
        )

        self.assertEqual(record.daily_return_eur, 5)
        self.assertEqual(record.cumulative_return_eur, 15)
        self.assertEqual(record.remaining_amount_eur, 85)

    def test_calculate_daily_record_uses_battery_aware_local_consumption(self) -> None:
        record = calculate_daily_record(
            site_id="site-a",
            record_date=date(2026, 5, 8),
            investment_amount=1_000,
            deltas=EnergyDeltas(
                pv_generation_kwh=20.1,
                grid_import_kwh=4.33,
                grid_export_kwh=10.5,
                battery_discharge_kwh=2.0,
                battery_charge_kwh=1.6,
            ),
            electricity_price_eur_kwh=0.3485,
            feed_in_tariff_eur_kwh=0,
            previous_records=[],
        )

        self.assertAlmostEqual(record.self_consumed_pv_kwh, 10.0)
        self.assertAlmostEqual(record.daily_return_eur, 3.485)

    def test_calculate_energy_deltas_never_goes_negative(self) -> None:
        previous = MeterSnapshot("site-a", date(2026, 5, 3), 100, 80, 30, 5, 4)
        current = MeterSnapshot("site-a", date(2026, 5, 4), 90, 85, 42, 8, 3)

        deltas = calculate_energy_deltas(previous=previous, current=current)

        self.assertEqual(deltas.pv_generation_kwh, 0)
        self.assertEqual(deltas.grid_import_kwh, 5)
        self.assertEqual(deltas.grid_export_kwh, 12)
        self.assertEqual(deltas.battery_discharge_kwh, 3)
        self.assertEqual(deltas.battery_charge_kwh, 0)

    def test_calculate_days_since_start_clamps_to_zero(self) -> None:
        self.assertEqual(
            calculate_days_since_start(date(2026, 5, 5), date(2026, 5, 4)),
            0,
        )

    def test_calculate_forecasts_uses_30_days_before_365_days_available(self) -> None:
        records = [
            _record(date(2026, 1, 1) + timedelta(days=day), 10)
            for day in range(30)
        ]

        forecasts = calculate_forecasts(records=records, remaining_amount_eur=100)

        self.assertEqual(forecasts.days_30, 10)
        self.assertEqual(forecasts.days_365, 10)
        self.assertEqual(forecasts.days_since_start, 10)
        self.assertEqual(forecasts.recommended, "30_days")

    def test_calculate_forecasts_prefers_365_days_after_full_year(self) -> None:
        records = [
            _record(date(2025, 1, 1) + timedelta(days=day), 5)
            for day in range(365)
        ]

        forecasts = calculate_forecasts(records=records, remaining_amount_eur=100)

        self.assertEqual(forecasts.days_365, 20)
        self.assertEqual(forecasts.recommended, "365_days")

    def test_calculate_forecasts_returns_none_for_non_positive_average(self) -> None:
        records = [_record(date(2026, 5, 4), 0)]

        forecasts = calculate_forecasts(records=records, remaining_amount_eur=100)

        self.assertIsNone(forecasts.days_30)
        self.assertIsNone(forecasts.days_365)
        self.assertIsNone(forecasts.days_since_start)
        self.assertIsNone(forecasts.recommended)

    def test_calculate_backfill_records_uses_fixed_prices(self) -> None:
        records = calculate_backfill_records(
            site_id="site-a",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            investment_amount=100,
            daily_deltas={
                date(2026, 5, 1): EnergyDeltas(10, 3, 2),
                date(2026, 5, 2): EnergyDeltas(12, 2, 4),
            },
            electricity_price_eur_kwh=0.30,
            feed_in_tariff_eur_kwh=0.10,
            previous_records=[],
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].daily_return_eur, 2.6)
        self.assertEqual(records[1].daily_return_eur, 2.8)
        self.assertEqual(records[1].cumulative_return_eur, 5.4)
        self.assertEqual(records[1].remaining_amount_eur, 94.6)

    def test_build_daily_deltas_derive_from_daily_sums(self) -> None:
        rows = {
            "sensor.pv_one": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 95},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 100},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 107},
            ],
            "sensor.pv_two": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 47},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 50},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 54},
            ],
            "sensor.import": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 28},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 30},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 31},
            ],
            "sensor.export": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 16},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 20},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 25},
            ],
        }

        deltas = build_daily_deltas_from_statistics(
            rows=rows,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            pv_generation_entities=("sensor.pv_one", "sensor.pv_two"),
            grid_import_entity="sensor.import",
            grid_export_entity="sensor.export",
        )

        self.assertEqual(deltas[date(2026, 5, 1)].pv_generation_kwh, 8)
        self.assertEqual(deltas[date(2026, 5, 2)].pv_generation_kwh, 11)
        self.assertEqual(deltas[date(2026, 5, 2)].grid_import_kwh, 1)
        self.assertEqual(deltas[date(2026, 5, 2)].grid_export_kwh, 5)

    def test_build_daily_deltas_can_derive_from_sum_baseline(self) -> None:
        rows = {
            "sensor.pv": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 100},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 108},
            ],
            "sensor.import": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 20},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 23},
            ],
            "sensor.export": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 7},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 9},
            ],
        }

        deltas = build_daily_deltas_from_statistics(
            rows=rows,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 1),
            pv_generation_entities=("sensor.pv",),
            grid_import_entity="sensor.import",
            grid_export_entity="sensor.export",
        )

        self.assertEqual(deltas[date(2026, 5, 1)].pv_generation_kwh, 8)
        self.assertEqual(deltas[date(2026, 5, 1)].grid_import_kwh, 3)
        self.assertEqual(deltas[date(2026, 5, 1)].grid_export_kwh, 2)

    def test_build_daily_deltas_includes_battery_flows(self) -> None:
        rows = {
            "sensor.pv": [{"start": "2026-05-01T00:00:00+00:00", "change": 10}],
            "sensor.import": [{"start": "2026-05-01T00:00:00+00:00", "change": 3}],
            "sensor.export": [{"start": "2026-05-01T00:00:00+00:00", "change": 2}],
            "sensor.battery_out": [{"start": "2026-05-01T00:00:00+00:00", "change": 1.5}],
            "sensor.battery_in": [{"start": "2026-05-01T00:00:00+00:00", "change": 0.7}],
        }

        deltas = build_daily_deltas_from_statistics(
            rows=rows,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 1),
            pv_generation_entities=("sensor.pv",),
            grid_import_entity="sensor.import",
            grid_export_entity="sensor.export",
            battery_discharge_entities=("sensor.battery_out",),
            battery_charge_entities=("sensor.battery_in",),
        )

        self.assertEqual(deltas[date(2026, 5, 1)].battery_discharge_kwh, 1.5)
        self.assertEqual(deltas[date(2026, 5, 1)].battery_charge_kwh, 0.7)

    def test_build_daily_deltas_allows_pv_sources_to_start_later(self) -> None:
        rows = {
            "sensor.pv_early": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 100},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 108},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 118},
            ],
            "sensor.pv_late": [
                {"start": "2026-05-02T00:00:00+00:00", "sum": 5},
            ],
            "sensor.import": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 20},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 23},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 25},
            ],
            "sensor.export": [
                {"start": "2026-04-30T00:00:00+00:00", "sum": 7},
                {"start": "2026-05-01T00:00:00+00:00", "sum": 9},
                {"start": "2026-05-02T00:00:00+00:00", "sum": 12},
            ],
        }

        deltas = build_daily_deltas_from_statistics(
            rows=rows,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 2),
            pv_generation_entities=("sensor.pv_early", "sensor.pv_late"),
            grid_import_entity="sensor.import",
            grid_export_entity="sensor.export",
        )

        self.assertEqual(deltas[date(2026, 5, 1)].pv_generation_kwh, 8)
        self.assertEqual(deltas[date(2026, 5, 2)].pv_generation_kwh, 15)
        self.assertEqual(len(deltas), 2)

    def test_build_daily_deltas_prefers_change_and_converts_wh(self) -> None:
        rows = {
            "sensor.pv_kwh": [
                {"start": "2026-05-01T00:00:00+00:00", "sum": 110, "change": 10},
            ],
            "sensor.pv_wh": [
                {"start": "2026-05-01T00:00:00+00:00", "sum": 5000, "change": 5000},
            ],
            "sensor.import": [
                {"start": "2026-05-01T00:00:00+00:00", "sum": 3000, "change": 3000},
            ],
            "sensor.export": [
                {"start": "2026-05-01T00:00:00+00:00", "sum": 2000, "change": 2000},
            ],
        }

        deltas = build_daily_deltas_from_statistics(
            rows=rows,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 1),
            pv_generation_entities=("sensor.pv_kwh", "sensor.pv_wh"),
            grid_import_entity="sensor.import",
            grid_export_entity="sensor.export",
            entity_units={
                "sensor.pv_kwh": "kWh",
                "sensor.pv_wh": "Wh",
                "sensor.import": "Wh",
                "sensor.export": "Wh",
            },
        )

        self.assertEqual(deltas[date(2026, 5, 1)].pv_generation_kwh, 15)
        self.assertEqual(deltas[date(2026, 5, 1)].grid_import_kwh, 3)
        self.assertEqual(deltas[date(2026, 5, 1)].grid_export_kwh, 2)

    def test_build_daily_deltas_handles_epoch_millis_as_local_day(self) -> None:
        rows = {
            "sensor.pv": [
                {"start": 1777586400000, "change": 10},
            ],
            "sensor.import": [
                {"start": 1777586400000, "change": 3},
            ],
            "sensor.export": [
                {"start": 1777586400000, "change": 2},
            ],
        }

        deltas = build_daily_deltas_from_statistics(
            rows=rows,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 1),
            pv_generation_entities=("sensor.pv",),
            grid_import_entity="sensor.import",
            grid_export_entity="sensor.export",
            local_timezone=ZoneInfo("Europe/Berlin"),
        )

        self.assertEqual(deltas[date(2026, 5, 1)].pv_generation_kwh, 10)
        self.assertEqual(deltas[date(2026, 5, 1)].grid_import_kwh, 3)
        self.assertEqual(deltas[date(2026, 5, 1)].grid_export_kwh, 2)

    def test_build_measurement_statistics_fills_record_date(self) -> None:
        rows = build_measurement_statistics(
            records=[_record(date(2026, 5, 1), 4.2)],
            local_timezone=ZoneInfo("Europe/Berlin"),
            value_fn=lambda record: record.daily_return_eur,
        )

        self.assertEqual(len(rows), 24)
        self.assertEqual(rows[0]["start"].isoformat(), "2026-05-01T00:00:00+02:00")
        self.assertEqual(rows[-1]["start"].isoformat(), "2026-05-01T23:00:00+02:00")
        self.assertTrue(all(row["mean"] == 4.2 for row in rows))
        self.assertTrue(all(row["min"] == 4.2 for row in rows))
        self.assertTrue(all(row["max"] == 4.2 for row in rows))

    def test_energy_dashboard_config_extracts_sources(self) -> None:
        config = energy_dashboard_config_from_prefs(
            {
                "energy_sources": [
                    {
                        "type": "solar",
                        "stat_energy_from": "sensor.pv_a",
                    },
                    {
                        "type": "solar",
                        "stat_energy_from": "sensor.pv_b",
                    },
                    {
                        "type": "grid",
                        "stat_energy_from": "sensor.grid_in",
                        "stat_energy_to": "sensor.grid_out",
                        "number_energy_price": 0.34,
                        "number_energy_price_export": 0.08,
                    },
                    {
                        "type": "battery",
                        "stat_energy_from": "sensor.battery_out",
                        "stat_energy_to": "sensor.battery_in",
                    },
                ]
            }
        )

        self.assertEqual(config.grid_import_entity, "sensor.grid_in")
        self.assertEqual(config.grid_export_entity, "sensor.grid_out")
        self.assertEqual(config.pv_generation_entities, ("sensor.pv_a", "sensor.pv_b"))
        self.assertEqual(config.battery_discharge_entities, ("sensor.battery_out",))
        self.assertEqual(config.battery_charge_entities, ("sensor.battery_in",))
        self.assertEqual(config.electricity_price, 0.34)
        self.assertEqual(config.feed_in_tariff, 0.08)


def _record(record_date: date, daily_return: float) -> DailyRecord:
    return DailyRecord(
        site_id="site-a",
        record_date=record_date,
        pv_generation_kwh=0,
        grid_import_kwh=0,
        grid_export_kwh=0,
        self_consumed_pv_kwh=0,
        battery_discharge_kwh=0,
        battery_charge_kwh=0,
        electricity_price_eur_kwh=0,
        feed_in_tariff_eur_kwh=0,
        daily_savings_eur=daily_return,
        daily_revenue_eur=0,
        daily_return_eur=daily_return,
        cumulative_return_eur=daily_return,
        remaining_amount_eur=100 - daily_return,
    )
