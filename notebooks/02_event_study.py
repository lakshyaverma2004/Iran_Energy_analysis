import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR = PROJECT_ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Event definitions ────────────────────────────────────────────────────────

EVENTS = {
    "E1_Strikes":  "2026-02-28",
    "E2_MoU":      "2026-06-17",
    "E3_Talks":    "2026-06-18",
    "HORMUZ":      "2026-03-15",
}

PRIMARY_ASSETS = ["Brent_Crude", "WTI_Crude", "Natural_Gas"]
ALL_ASSETS = PRIMARY_ASSETS + [
    "USD_Index", "ExxonMobil", "Halliburton",
    "United_Airlines", "Lockheed_Martin",
]

BASELINE_START = "2026-01-02"
BASELINE_END = "2026-02-27"

# ── PART A — Load data and compute log returns ──────────────────────────────

print("=" * 70)
print("PART A — Log returns")
print("=" * 70)

prices = pd.read_csv(PROC_DIR / "prices.csv", index_col="Date", parse_dates=True)

returns = np.log(prices[ALL_ASSETS] / prices[ALL_ASSETS].shift(1))
returns = returns.dropna(how="all")
returns.index.name = "Date"

returns.to_csv(PROC_DIR / "returns.csv")
print(f"Saved returns.csv -> {returns.shape[0]} rows x {returns.shape[1]} cols")
print(f"\nFirst 5 rows:\n{returns.head()}")
print(f"\nDescriptive stats:\n{returns.describe().round(6)}")

# ── PART B — Expected returns from baseline window ──────────────────────────

print("\n" + "=" * 70)
print("PART B — Baseline expected returns")
print("=" * 70)

baseline = returns.loc[BASELINE_START:BASELINE_END]
print(f"Baseline window: {baseline.index.min().date()} to {baseline.index.max().date()} ({len(baseline)} trading days)")

expected_returns = baseline[PRIMARY_ASSETS].mean().to_dict()

print("\nExpected daily log returns (baseline mean):")
for asset, er in expected_returns.items():
    print(f"  {asset:<16s}  {er:+.6f}  ({er*100:+.4f}%)")

# ── PART C — Event window function ──────────────────────────────────────────


def get_event_window(returns_df, event_date_str, window=10):
    event_date = pd.Timestamp(event_date_str)
    available = returns_df.index
    if event_date not in available:
        future = available[available >= event_date]
        if len(future) == 0:
            raise ValueError(f"No trading days on or after {event_date_str}")
        event_date = future[0]

    loc = available.get_loc(event_date)
    start = max(loc - window, 0)
    end = min(loc + window + 1, len(available))
    return returns_df.iloc[start:end], event_date


# ── PART D — Abnormal Returns and CAR for all events ────────────────────────
#
# Raw CAR = cumulative sum of AR from the start of the window (day -W).
# Normalised post-event CAR = CAR[t] - CAR[-1], so it is zero-based at the
# event boundary.  Summary statistics use the normalised version so they
# capture only the incremental impact of each event.

print("\n" + "=" * 70)
print("PART D — Abnormal Returns & CAR")
print("=" * 70)

results = {}

for event_name, event_date_str in EVENTS.items():
    results[event_name] = {}
    print(f"\n--- {event_name} (target: {event_date_str}) ---")

    for asset in PRIMARY_ASSETS:
        window_df, actual_date = get_event_window(returns, event_date_str, window=10)
        loc = window_df.index.get_loc(actual_date)

        actual_ret = window_df[asset].values
        ar = actual_ret - expected_returns[asset]
        car_raw = np.cumsum(ar)

        rel_days = np.arange(-loc, len(ar) - loc)

        ar_series = pd.Series(ar, index=rel_days, name="AR")
        car_raw_series = pd.Series(car_raw, index=rel_days, name="CAR_raw")

        # Normalised: subtract CAR at day -1 so post-event starts from 0
        car_at_minus1 = car_raw_series.get(-1, 0.0)
        car_norm_series = car_raw_series - car_at_minus1
        car_norm_series.name = "CAR"

        results[event_name][asset] = {
            "event_date": event_date_str,
            "actual_date_used": str(actual_date.date()),
            "AR": ar_series,
            "CAR_raw": car_raw_series,
            "CAR": car_norm_series,
            "CAR_pre_event_raw": car_at_minus1,
        }

        car5 = car_norm_series.get(5, float("nan"))
        car10 = car_norm_series.get(10, float("nan"))
        print(f"  {asset:<16s}  actual_date={actual_date.date()}  "
              f"CAR[+5]={car5*100:+.2f}%  "
              f"CAR[+10]={car10*100:+.2f}%")

# ── PART E — Summary statistics table ───────────────────────────────────────

print("\n" + "=" * 70)
print("PART E — Event Study Summary Table")
print("=" * 70)

rows = []
for event_name in EVENTS:
    for asset in PRIMARY_ASSETS:
        r = results[event_name][asset]
        car = r["CAR"]  # normalised

        # Post-event window: days +1 to +10 (whatever is available)
        post_days = [d for d in car.index if 1 <= d <= 10]
        post_car = car.loc[post_days] if post_days else pd.Series(dtype=float)

        if len(post_car) > 0:
            peak_car = post_car.max()
            trough_car = post_car.min()
            days_to_peak = int(post_car.idxmax())
        else:
            peak_car = trough_car = float("nan")
            days_to_peak = float("nan")

        rows.append({
            "event_name":    event_name,
            "asset":         asset,
            "event_date":    r["actual_date_used"],
            "peak_CAR":      round(peak_car * 100, 2) if not np.isnan(peak_car) else np.nan,
            "trough_CAR":    round(trough_car * 100, 2) if not np.isnan(trough_car) else np.nan,
            "days_to_peak":  days_to_peak,
            "net_CAR_5d":    round(car.get(5, float("nan")) * 100, 2),
            "net_CAR_10d":   round(car.get(10, float("nan")) * 100, 2),
            "CAR_pre_event": round(r["CAR_pre_event_raw"] * 100, 2),
        })

event_summary = pd.DataFrame(rows)
event_summary.to_csv(PROC_DIR / "event_study_summary.csv", index=False)

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 150)
pd.set_option("display.float_format", lambda x: f"{x:.2f}")
print(f"\n{event_summary.to_string(index=False)}")
print(f"\nSaved event_study_summary.csv -> {event_summary.shape}")

# Sanity check: for E1 (baseline-adjacent), CAR_pre_event should be near 0
e1_rows = event_summary[event_summary["event_name"] == "E1_Strikes"]
e1_bad = e1_rows[e1_rows["CAR_pre_event"].abs() > 2.0]
if len(e1_bad) > 0:
    print(f"\nWARNING: E1 has |CAR_pre_event| > 2% — baseline may be miscalibrated:")
    print(e1_bad[["event_name", "asset", "CAR_pre_event"]])
else:
    print("\nSanity check passed: E1 CAR_pre_event values within +/-2%.")

# For later events, large pre-event CARs are expected (crisis already underway)
later = event_summary[event_summary["event_name"] != "E1_Strikes"]
print(f"\nNote: HORMUZ/E2/E3 pre-event CARs are large because their windows")
print(f"overlap the active crisis. This is expected, not a baseline error.")

# ── PART F — Headline stats ─────────────────────────────────────────────────

print("\n" + "=" * 70)
print("PART F — Key Interview Stats")
print("=" * 70)

brent_e1 = event_summary[(event_summary["event_name"] == "E1_Strikes") & (event_summary["asset"] == "Brent_Crude")].iloc[0]
wti_e1   = event_summary[(event_summary["event_name"] == "E1_Strikes") & (event_summary["asset"] == "WTI_Crude")].iloc[0]
ng_e1    = event_summary[(event_summary["event_name"] == "E1_Strikes") & (event_summary["asset"] == "Natural_Gas")].iloc[0]
brent_e2 = event_summary[(event_summary["event_name"] == "E2_MoU") & (event_summary["asset"] == "Brent_Crude")].iloc[0]

print(f"\n1. Brent Crude peak CAR after E1 (strikes): {brent_e1['peak_CAR']:+.2f}% in {int(brent_e1['days_to_peak'])} trading days")
print(f"2. WTI Crude peak CAR after E1 (strikes): {wti_e1['peak_CAR']:+.2f}% in {int(wti_e1['days_to_peak'])} trading days")

# E2 has limited post-event data (data ends June 18 = 1 day post-event)
e2_car = results["E2_MoU"]["Brent_Crude"]["CAR"]
e2_post_days = [d for d in e2_car.index if d >= 0]
e2_available_max = max(e2_post_days) if e2_post_days else 0
e2_car_at_max = e2_car.get(e2_available_max, float("nan"))
print(f"3. Brent Crude net CAR at day+{e2_available_max} after E2 (MoU): {e2_car_at_max*100:+.2f}%")
print(f"   (Note: data ends {e2_available_max} trading day(s) post-event; longer-term effect not observable)")

e1_peak_day = int(brent_e1["days_to_peak"])

# For E2 de-escalation speed: measure how fast pre-event CAR accumulated
# (the MoU impact was largely priced-in BEFORE the signing)
e2_car_raw = results["E2_MoU"]["Brent_Crude"]["CAR_raw"]
e2_pre_days = [d for d in e2_car_raw.index if d < 0]
e2_pre_car = e2_car_raw.loc[e2_pre_days]
e2_pre_trough_at = int(e2_pre_car.idxmin()) if len(e2_pre_car) > 0 else float("nan")
print(f"4. Escalation speed vs De-escalation speed: E1 peak at day+{e1_peak_day} vs E2 pre-event trough at day{e2_pre_trough_at}")
print(f"   (De-escalation was anticipated: prices dropped {results['E2_MoU']['Brent_Crude']['CAR_pre_event_raw']*100:+.1f}% in the 10 days BEFORE the MoU)")

e1_window, _ = get_event_window(returns, "2026-02-28", window=10)
corr = e1_window["Brent_Crude"].corr(e1_window["Natural_Gas"])
print(f"5. Natural Gas correlation to Brent during E1 window: {corr:.4f}")

# ── Interview-ready paragraph ───────────────────────────────────────────────

e2_pre_drop = abs(results["E2_MoU"]["Brent_Crude"]["CAR_pre_event_raw"] * 100)
escalation_rate = abs(brent_e1["peak_CAR"]) / e1_peak_day  # %/day
deescalation_rate = e2_pre_drop / 10  # pre-event window is 10 trading days
ratio = escalation_rate / deescalation_rate if deescalation_rate != 0 else float("nan")
ng_vs_crude = "more" if abs(ng_e1["peak_CAR"]) > abs(brent_e1["peak_CAR"]) else "less"

finding = (
    f"[PROJECT FINDING]: Brent crude posted a cumulative abnormal return of "
    f"{brent_e1['peak_CAR']:+.2f}% in {e1_peak_day} trading days following the "
    f"February 28 strikes ({escalation_rate:.1f}%/day). By contrast, the de-escalation "
    f"around the June 17 MoU was largely priced-in beforehand: Brent shed "
    f"{e2_pre_drop:.1f}% of abnormal gains over 10 pre-event trading days "
    f"({deescalation_rate:.1f}%/day), with only {e2_car_at_max*100:+.2f}% incremental "
    f"movement on the signing day itself — escalation was {ratio:.1f}x faster than "
    f"de-escalation. Natural Gas moved {ng_vs_crude} sharply than crude oil, "
    f"with a peak CAR of {ng_e1['peak_CAR']:+.2f}%."
)

print("\n" + "=" * 70)
print("INTERVIEW-READY FINDING")
print("=" * 70)
print(f"\n{finding}\n")

with open(OUT_DIR / "key_findings.txt", "w", encoding="utf-8") as f:
    f.write(finding + "\n")
print(f"Saved to outputs/key_findings.txt")
