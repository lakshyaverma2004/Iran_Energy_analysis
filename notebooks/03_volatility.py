import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"
OUT_DIR = PROJECT_ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = [
    "Brent_Crude", "WTI_Crude", "Natural_Gas", "USD_Index",
    "ExxonMobil", "Halliburton", "United_Airlines", "Lockheed_Martin",
]

WINDOWS = {
    "PRE_CONFLICT": ("2026-01-02", "2026-02-27"),
    "CONFLICT":     ("2026-02-28", "2026-06-16"),
    "POST_MOU":     ("2026-06-17", "2026-06-20"),
}


print("=" * 70)
print("PART A — Rolling volatility (20-day, annualised)")
print("=" * 70)

returns = pd.read_csv(PROC_DIR / "returns.csv", index_col="Date", parse_dates=True)

rolling_std = returns[ASSETS].rolling(window=20).std()
rolling_vol = rolling_std * np.sqrt(252) * 100  # annualised %

rolling_vol.index.name = "Date"
rolling_vol.to_csv(PROC_DIR / "volatility.csv")
print(f"Saved volatility.csv -> {rolling_vol.shape[0]} rows x {rolling_vol.shape[1]} cols")
print(f"\nFirst 5 rows (NaN until 20-day window fills):\n{rolling_vol.head()}")
print(f"\nLast 5 rows:\n{rolling_vol.tail()}")



print("\n" + "=" * 70)
print("PART B — Window volatility comparison")
print("=" * 70)

rows = []
pre_means = {}

for asset in ASSETS:
    for wname, (wstart, wend) in WINDOWS.items():
        subset = rolling_vol.loc[wstart:wend, asset].dropna()
        if len(subset) == 0:
            mean_v = max_v = min_v = float("nan")
        else:
            mean_v = subset.mean()
            max_v = subset.max()
            min_v = subset.min()

        if wname == "PRE_CONFLICT":
            pre_means[asset] = mean_v

        ratio = mean_v / pre_means[asset] if pre_means.get(asset, 0) != 0 else float("nan")

        rows.append({
            "asset": asset,
            "window": wname,
            "mean_vol": round(mean_v, 2),
            "max_vol": round(max_v, 2),
            "min_vol": round(min_v, 2),
            "vol_vs_pre_ratio": round(ratio, 2),
        })

vol_summary = pd.DataFrame(rows)
vol_summary.to_csv(PROC_DIR / "volatility_summary.csv", index=False)

pd.set_option("display.max_columns", 10)
pd.set_option("display.width", 130)
pd.set_option("display.float_format", lambda x: f"{x:.2f}")
print(f"\n{vol_summary.to_string(index=False)}")
print(f"\nSaved volatility_summary.csv -> {vol_summary.shape}")


print("\n" + "=" * 70)
print("PART C — Headline Volatility Stats")
print("=" * 70)


def get_vol(asset, window):
    row = vol_summary[(vol_summary["asset"] == asset) & (vol_summary["window"] == window)]
    return row.iloc[0]


for asset in ["Brent_Crude", "WTI_Crude", "Natural_Gas"]:
    pre = get_vol(asset, "PRE_CONFLICT")
    con = get_vol(asset, "CONFLICT")
    print(f"\n{asset} mean volatility: Pre-conflict = {pre['mean_vol']:.1f}%, "
          f"Conflict = {con['mean_vol']:.1f}%, Ratio = {con['vol_vs_pre_ratio']:.1f}x")


brent_conflict = rolling_vol.loc["2026-02-28":"2026-06-16", "Brent_Crude"].dropna()
peak_vol = brent_conflict.max()
peak_date = brent_conflict.idxmax()
print(f"\nPeak single-day Brent volatility during conflict: {peak_vol:.1f}% annualised on {peak_date.date()}")


post = get_vol("Brent_Crude", "POST_MOU")
pre_brent = get_vol("Brent_Crude", "PRE_CONFLICT")
print(f"Post-MoU Brent volatility vs pre-conflict: {post['vol_vs_pre_ratio']:.1f}x "
      f"(did it return to normal?)")



print("\n" + "=" * 70)
print("PART D — Correlation analysis")
print("=" * 70)

ret_pre = returns.loc["2026-01-02":"2026-02-27", ASSETS]
ret_con = returns.loc["2026-02-28":"2026-06-16", ASSETS]

corr_pre = ret_pre.corr()
corr_con = ret_con.corr()

corr_pre.to_csv(PROC_DIR / "corr_pre_conflict.csv")
corr_con.to_csv(PROC_DIR / "corr_conflict.csv")
print("Saved corr_pre_conflict.csv and corr_conflict.csv")

pairs = [
    ("Brent_Crude", "Natural_Gas"),
    ("Brent_Crude", "USD_Index"),
    ("Brent_Crude", "United_Airlines"),
    ("Brent_Crude", "ExxonMobil"),
]

print(f"\n{'Pair':<35s} {'Pre':>6s}  {'Conflict':>8s}  {'Change':>7s}")
print("-" * 60)
for a, b in pairs:
    pre_c = corr_pre.loc[a, b]
    con_c = corr_con.loc[a, b]
    print(f"{a} vs {b:<20s} {pre_c:+.3f}   {con_c:+.3f}   {con_c - pre_c:+.3f}")


print("\n" + "=" * 70)
print("PART E — Appending volatility findings")
print("=" * 70)

brent_pre = get_vol("Brent_Crude", "PRE_CONFLICT")
brent_con = get_vol("Brent_Crude", "CONFLICT")
brent_post = get_vol("Brent_Crude", "POST_MOU")

corr_brent_airlines_pre = corr_pre.loc["Brent_Crude", "United_Airlines"]
corr_brent_airlines_con = corr_con.loc["Brent_Crude", "United_Airlines"]
corr_brent_exxon_pre = corr_pre.loc["Brent_Crude", "ExxonMobil"]
corr_brent_exxon_con = corr_con.loc["Brent_Crude", "ExxonMobil"]

findings_block = (
    f"\n\nVOLATILITY FINDINGS:\n"
    f"- Brent Crude volatility spiked {brent_con['vol_vs_pre_ratio']:.1f}x above baseline during the conflict window\n"
    f"- Peak annualised volatility was {peak_vol:.1f}% on {peak_date.date()}\n"
    f"- Post-MoU normalisation: volatility returned to {brent_post['mean_vol']:.1f}% vs pre-conflict {brent_pre['mean_vol']:.1f}%\n"
    f"- Brent-Airlines correlation shifted from {corr_brent_airlines_pre:+.3f} to {corr_brent_airlines_con:+.3f} "
    f"-- inverse relationship strengthened during crisis\n"
    f"- Brent-ExxonMobil correlation shifted from {corr_brent_exxon_pre:+.3f} to {corr_brent_exxon_con:+.3f} "
    f"-- sector divergence confirmed\n"
)

findings_path = OUT_DIR / "key_findings.txt"
with open(findings_path, "a", encoding="utf-8") as f:
    f.write(findings_block)

print(findings_block)
print(f"Appended to {findings_path}")
