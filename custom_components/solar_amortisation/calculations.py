"""Pure calculation helpers for Solar Amortisation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from math import ceil

from .models import DailyRecord, EnergyDeltas, Forecasts, MeterSnapshot, PricePeriod


def value_for_date(periods: Sequence[PricePeriod], target_date: date) -> float:
    """Return the period value that applies on target_date."""

    applicable = [
        period for period in sorted(periods, key=lambda item: item.valid_from)
        if period.valid_from <= target_date
    ]
    if not applicable:
        msg = f"No value configured for {target_date.isoformat()}"
        raise ValueError(msg)
    return applicable[-1].value


def calculate_daily_record(
    *,
    site_id: str,
    record_date: date,
    investment_amount: float,
    deltas: EnergyDeltas,
    electricity_price_eur_kwh: float,
    feed_in_tariff_eur_kwh: float,
    previous_records: Sequence[DailyRecord],
) -> DailyRecord:
    """Calculate and freeze one daily accounting record."""

    self_consumed_pv_kwh = max(deltas.pv_generation_kwh - deltas.grid_export_kwh, 0)
    daily_savings_eur = self_consumed_pv_kwh * electricity_price_eur_kwh
    daily_revenue_eur = deltas.grid_export_kwh * feed_in_tariff_eur_kwh
    daily_return_eur = daily_savings_eur + daily_revenue_eur

    previous_total = sum(record.daily_return_eur for record in previous_records)
    cumulative_return_eur = previous_total + daily_return_eur
    remaining_amount_eur = investment_amount - cumulative_return_eur

    return DailyRecord(
        site_id=site_id,
        record_date=record_date,
        pv_generation_kwh=round(deltas.pv_generation_kwh, 6),
        grid_import_kwh=round(deltas.grid_import_kwh, 6),
        grid_export_kwh=round(deltas.grid_export_kwh, 6),
        self_consumed_pv_kwh=round(self_consumed_pv_kwh, 6),
        electricity_price_eur_kwh=round(electricity_price_eur_kwh, 6),
        feed_in_tariff_eur_kwh=round(feed_in_tariff_eur_kwh, 6),
        daily_savings_eur=round(daily_savings_eur, 6),
        daily_revenue_eur=round(daily_revenue_eur, 6),
        daily_return_eur=round(daily_return_eur, 6),
        cumulative_return_eur=round(cumulative_return_eur, 6),
        remaining_amount_eur=round(remaining_amount_eur, 6),
    )


def calculate_days_since_start(start_date: date, today: date) -> int:
    """Calculate elapsed days since the configured start date."""

    return max((today - start_date).days, 0)


def calculate_energy_deltas(
    *,
    previous: MeterSnapshot,
    current: MeterSnapshot,
) -> EnergyDeltas:
    """Calculate positive energy deltas between two absolute meter snapshots."""

    return EnergyDeltas(
        pv_generation_kwh=max(
            current.pv_generation_kwh - previous.pv_generation_kwh,
            0,
        ),
        grid_import_kwh=max(current.grid_import_kwh - previous.grid_import_kwh, 0),
        grid_export_kwh=max(current.grid_export_kwh - previous.grid_export_kwh, 0),
    )


def calculate_backfill_records(
    *,
    site_id: str,
    start_date: date,
    end_date: date,
    investment_amount: float,
    daily_deltas: dict[date, EnergyDeltas],
    electricity_price_eur_kwh: float,
    feed_in_tariff_eur_kwh: float,
    previous_records: Sequence[DailyRecord],
) -> list[DailyRecord]:
    """Calculate a continuous set of historical daily records."""

    existing_dates = {record.record_date for record in previous_records}
    records = sorted(previous_records, key=lambda item: item.record_date)
    backfilled: list[DailyRecord] = []
    current_date = start_date

    while current_date <= end_date:
        if current_date not in existing_dates and current_date in daily_deltas:
            record = calculate_daily_record(
                site_id=site_id,
                record_date=current_date,
                investment_amount=investment_amount,
                deltas=daily_deltas[current_date],
                electricity_price_eur_kwh=electricity_price_eur_kwh,
                feed_in_tariff_eur_kwh=feed_in_tariff_eur_kwh,
                previous_records=records,
            )
            records.append(record)
            backfilled.append(record)
        current_date += timedelta(days=1)

    return backfilled


def calculate_forecasts(
    *,
    records: Sequence[DailyRecord],
    remaining_amount_eur: float,
) -> Forecasts:
    """Calculate remaining amortisation days from rolling averages."""

    if remaining_amount_eur <= 0:
        return Forecasts(
            days_30=0,
            days_365=0,
            days_since_start=0,
            recommended="paid_off",
        )

    sorted_records = sorted(records, key=lambda item: item.record_date)
    days_30 = _forecast_for_records(sorted_records[-30:], remaining_amount_eur)
    days_365 = _forecast_for_records(sorted_records[-365:], remaining_amount_eur)
    days_since_start = _forecast_for_records(sorted_records, remaining_amount_eur)

    if len(sorted_records) >= 365 and days_365 is not None:
        recommended = "365_days"
    elif len(sorted_records) >= 30 and days_30 is not None:
        recommended = "30_days"
    else:
        recommended = "since_start" if days_since_start is not None else None

    return Forecasts(
        days_30=days_30,
        days_365=days_365,
        days_since_start=days_since_start,
        recommended=recommended,
    )


def _forecast_for_records(
    records: Sequence[DailyRecord],
    remaining_amount_eur: float,
) -> int | None:
    if not records:
        return None

    average = _average(record.daily_return_eur for record in records)
    if average <= 0:
        return None
    return ceil(remaining_amount_eur / average)


def _average(values: Iterable[float]) -> float:
    values_list = list(values)
    if not values_list:
        return 0
    return sum(values_list) / len(values_list)
