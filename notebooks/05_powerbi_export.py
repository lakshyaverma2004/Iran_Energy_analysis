import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
DASH_DIR = PROJECT_ROOT / "dashboard"
DASH_DIR.mkdir(parents=True, exist_ok=True)

# ── FILE 1: powerbi_master.csv ──────────────────────────────────────────────

print("=" * 60)
print("FILE 1 — powerbi_master.csv")
print("=" * 60)

prices = pd.read_csv(PROC_DIR / "prices.csv", index_col="Date", parse_dates=True)
returns = pd.read_csv(PROC_DIR / "returns.csv", index_col="Date", parse_dates=True)
vol = pd.read_csv(PROC_DIR / "volatility.csv", index_col="Date", parse_dates=True)

PRICE_COLS = {
    "Brent_Crude": "Brent_Close",
    "WTI_Crude": "WTI_Close",
    "Natural_Gas": "NatGas_Close",
    "USD_Index": "USD_Index_Close",
    "ExxonMobil": "ExxonMobil_Close",
    "Halliburton": "Halliburton_Close",
    "United_Airlines": "United_Airlines_Close",
    "Lockheed_Martin": "Lockheed_Martin_Close",
}

RETURN_COLS = {
    "Brent_Crude": "Brent_LogReturn",
    "WTI_Crude": "WTI_LogReturn",
    "Natural_Gas": "NatGas_LogReturn",
}

VOL_COLS = {
    "Brent_Crude": "Brent_RollingVol",
    "WTI_Crude": "WTI_RollingVol",
    "Natural_Gas": "NatGas_RollingVol",
}

master = prices[list(PRICE_COLS.keys())].rename(columns=PRICE_COLS)

ret_pct = (returns[list(RETURN_COLS.keys())] * 100).rename(columns=RETURN_COLS)
master = master.join(ret_pct)

vol_sub = vol[list(VOL_COLS.keys())].rename(columns=VOL_COLS)
master = master.join(vol_sub)

EVENT_MAP = {
    "2026-02-28": "E1: US Strikes Begin",
    "2026-06-17": "E2: US-Iran MoU Signed",
    "2026-06-18": "E3: Swiss Talks Postponed",
}

master["Event_Label"] = ""
for date_str, label in EVENT_MAP.items():
    mask = master.index == pd.Timestamp(date_str)
    master.loc[mask, "Event_Label"] = label

def assign_window(dt):
    if dt < pd.Timestamp("2026-02-28"):
        return "Pre-Conflict"
    elif dt <= pd.Timestamp("2026-06-16"):
        return "Conflict"
    else:
        return "Post-MoU"

master["Window"] = master.index.map(assign_window)

master.index = master.index.strftime("%Y-%m-%d")
master.index.name = "Date"

master.to_csv(DASH_DIR / "powerbi_master.csv")
print(f"Shape: {master.shape}")
print(f"\nFirst 3 rows:\n{master.head(3).to_string()}")

# ── FILE 2: event_annotations.csv ───────────────────────────────────────────

print("\n" + "=" * 60)
print("FILE 2 — event_annotations.csv")
print("=" * 60)

annotations = pd.DataFrame([
    {"Date": "2026-02-28", "Event_Name": "US-Israel Strikes Begin",
     "Event_Short": "E1 Strikes", "Color_Hex": "#E24B4A", "Sort_Order": 1},
    {"Date": "2026-06-17", "Event_Name": "US-Iran MoU Signed",
     "Event_Short": "E2 MoU", "Color_Hex": "#3B6D11", "Sort_Order": 2},
    {"Date": "2026-06-18", "Event_Name": "Swiss Technical Talks Postponed",
     "Event_Short": "E3 Swiss", "Color_Hex": "#BA7517", "Sort_Order": 3},
])

annotations.to_csv(DASH_DIR / "event_annotations.csv", index=False)
print(annotations.to_string(index=False))

# ── FILE 3: vol_summary_powerbi.csv ─────────────────────────────────────────

print("\n" + "=" * 60)
print("FILE 3 — vol_summary_powerbi.csv")
print("=" * 60)

vol_summary = pd.read_csv(PROC_DIR / "volatility_summary.csv")

pivoted = vol_summary.pivot(index="asset", columns="window", values="mean_vol")
pivoted = pivoted.rename(columns={
    "PRE_CONFLICT": "Pre_Conflict_Vol",
    "CONFLICT": "Conflict_Vol",
    "POST_MOU": "Post_MoU_Vol",
})
pivoted = pivoted[["Pre_Conflict_Vol", "Conflict_Vol", "Post_MoU_Vol"]]
pivoted["Vol_Spike_Ratio"] = (pivoted["Conflict_Vol"] / pivoted["Pre_Conflict_Vol"]).round(2)
pivoted.index.name = "Asset"

pivoted.to_csv(DASH_DIR / "vol_summary_powerbi.csv")
print(pivoted.to_string())

# ── FILE 4: event_summary_powerbi.csv ───────────────────────────────────────

print("\n" + "=" * 60)
print("FILE 4 — event_summary_powerbi.csv")
print("=" * 60)

event_summary = pd.read_csv(PROC_DIR / "event_study_summary.csv")

# Values are already in percentage form — add _Pct aliases for Power BI clarity
event_summary["Peak_CAR_Pct"] = event_summary["peak_CAR"]
event_summary["Net_CAR_10d_Pct"] = event_summary["net_CAR_10d"]

event_summary.to_csv(DASH_DIR / "event_summary_powerbi.csv", index=False)
print(event_summary.to_string(index=False))

# ── Summary ─────────────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("ALL FILES COMPLETE")
print("=" * 60)

for f in ["powerbi_master.csv", "event_annotations.csv",
          "vol_summary_powerbi.csv", "event_summary_powerbi.csv"]:
    p = DASH_DIR / f
    size = p.stat().st_size / 1024
    print(f"  {f:<35s}  {size:>7.1f} KB")
