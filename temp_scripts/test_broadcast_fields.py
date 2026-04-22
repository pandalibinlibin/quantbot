"""
Test script: verify broadcast fields (shibor_1y, afre_monthly_flow) were
correctly injected into instrument CSVs and converted to Qlib .bin files.

Run inside Docker:
    docker compose exec backend python /app/temp_scripts/test_broadcast_fields.py
"""

import sys
from pathlib import Path

# ── 1. Check instrument CSVs for broadcast columns ─────────────────────
csv_dir = Path("/app/csv_data/cn_data")
csv_files = sorted(csv_dir.glob("*.csv"))

print(f"=== CSV CHECK ===")
print(f"CSV dir: {csv_dir}")
print(f"Total CSV files: {len(csv_files)}")

if not csv_files:
    print("ERROR: No CSV files found!")
    sys.exit(1)

import pandas as pd

# Sample 3 CSVs: first, middle, last
sample_indices = [0, len(csv_files) // 2, len(csv_files) - 1]
fields_to_check = ["shibor_1y", "afre_monthly_flow"]

has_shibor = 0
has_afre = 0
total_checked = 0

for idx in sample_indices:
    f = csv_files[idx]
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    total_checked += 1
    print(f"\n--- {f.name} ---")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")

    for field in fields_to_check:
        if field in df.columns:
            series = df[field]
            non_null = series.notna().sum()
            pct = non_null / len(series) * 100
            print(f"  {field}: {non_null}/{len(series)} non-null ({pct:.1f}%)")
            print(f"    min={series.min():.4f}, max={series.max():.4f}, last_5={series.tail(5).tolist()}")
            if field == "shibor_1y":
                has_shibor += 1
            else:
                has_afre += 1
        else:
            print(f"  {field}: *** MISSING ***")

print(f"\n--- Summary (sampled {total_checked} CSVs) ---")
print(f"  shibor_1y present: {has_shibor}/{total_checked}")
print(f"  afre_monthly_flow present: {has_afre}/{total_checked}")

# Quick full scan: check ALL CSVs for column presence
print(f"\n=== FULL SCAN (column presence only) ===")
shibor_count = 0
afre_count = 0
for f in csv_files:
    try:
        cols = pd.read_csv(f, nrows=0).columns.tolist()
        if "shibor_1y" in cols:
            shibor_count += 1
        if "afre_monthly_flow" in cols:
            afre_count += 1
    except Exception as e:
        print(f"  Error reading {f.name}: {e}")

print(f"  shibor_1y present in: {shibor_count}/{len(csv_files)} CSVs")
print(f"  afre_monthly_flow present in: {afre_count}/{len(csv_files)} CSVs")

# ── 2. Check normalized CSVs ───────────────────────────────────────────
norm_dir = csv_dir.parent / "normalized"
norm_files = sorted(norm_dir.glob("*.csv")) if norm_dir.exists() else []

print(f"\n=== NORMALIZED CSV CHECK ===")
print(f"Normalized dir: {norm_dir}")
print(f"Total normalized files: {len(norm_files)}")

if norm_files:
    sample_norm = norm_files[0]
    ndf = pd.read_csv(sample_norm, index_col=0, parse_dates=True)
    print(f"  Sample: {sample_norm.name}")
    print(f"  Shape: {ndf.shape}")
    print(f"  Columns: {ndf.columns.tolist()}")
    for field in fields_to_check:
        if field in ndf.columns:
            s = ndf[field]
            print(f"  {field}: {s.notna().sum()}/{len(s)} non-null, last={s.iloc[-1]}")
        else:
            print(f"  {field}: *** MISSING in normalized ***")

# ── 3. Check Qlib .bin files ───────────────────────────────────────────
qlib_dir = Path("/app/qlib_data")
print(f"\n=== QLIB BIN CHECK ===")
print(f"Qlib dir: {qlib_dir}")

# Check if .bin files exist for broadcast fields
for field in fields_to_check:
    bin_file = qlib_dir / "features" / csv_files[0].stem / f"{field}.day.bin"
    # Also try without .day suffix
    bin_file2 = qlib_dir / "features" / csv_files[0].stem / f"{field}.bin"

    # List all bin files in one instrument dir
    inst_dir = qlib_dir / "features" / csv_files[0].stem
    if inst_dir.exists():
        bin_files_in_dir = sorted(inst_dir.glob("*.bin"))
        if not any(field in str(b) for b in bin_files_in_dir):
            print(f"  {field}: *** NO .bin file found ***")
        else:
            matching = [b.name for b in bin_files_in_dir if field in b.name]
            print(f"  {field}: found {matching}")
    else:
        print(f"  {field}: instrument dir {inst_dir} does not exist")

# List all .bin files in one sample instrument dir
sample_inst_dir = qlib_dir / "features" / csv_files[0].stem
if sample_inst_dir.exists():
    all_bins = sorted(sample_inst_dir.glob("*.bin"))
    print(f"\n  All .bin files in {sample_inst_dir.name}/:")
    for b in all_bins:
        size = b.stat().st_size
        print(f"    {b.name} ({size} bytes)")
else:
    # Try listing features dir
    feat_dir = qlib_dir / "features"
    if feat_dir.exists():
        subdirs = sorted([d.name for d in feat_dir.iterdir() if d.is_dir()])
        print(f"\n  Features subdirs (first 5): {subdirs[:5]}")
        if subdirs:
            first_dir = feat_dir / subdirs[0]
            all_bins = sorted(first_dir.glob("*.bin"))
            print(f"  All .bin files in {subdirs[0]}/:")
            for b in all_bins:
                size = b.stat().st_size
                print(f"    {b.name} ({size} bytes)")
    else:
        # Try listing qlib_dir contents
        print(f"  Contents of {qlib_dir}:")
        for item in sorted(qlib_dir.iterdir()):
            print(f"    {item.name} ({'dir' if item.is_dir() else 'file'})")

# ── 4. Verify shibor_1y data quality (daily, should have no big gaps) ──
print(f"\n=== DATA QUALITY CHECK ===")
sample_csv = csv_files[0]
df = pd.read_csv(sample_csv, index_col=0, parse_dates=True)

if "shibor_1y" in df.columns:
    s = df["shibor_1y"].dropna()
    if len(s) > 1:
        gaps = s.index.to_series().diff().dropna()
        max_gap = gaps.max().days
        print(f"  shibor_1y ({sample_csv.name}):")
        print(f"    Non-null values: {len(s)}")
        print(f"    Max gap between values: {max_gap} days")
        print(f"    Value range: {s.min():.4f} to {s.max():.4f}")
    else:
        print(f"  shibor_1y: only {len(s)} non-null values")

if "afre_monthly_flow" in df.columns:
    s = df["afre_monthly_flow"].dropna()
    if len(s) > 1:
        # After ffill, should be daily
        gaps = s.index.to_series().diff().dropna()
        max_gap = gaps.max().days
        unique_vals = s.nunique()
        print(f"  afre_monthly_flow ({sample_csv.name}):")
        print(f"    Non-null values: {len(s)}")
        print(f"    Unique values (monthly -> ~39): {unique_vals}")
        print(f"    Max gap between values: {max_gap} days")
        print(f"    Value range: {s.min():.1f} to {s.max():.1f}")
        print(f"    Last 5 values: {s.tail(5).tolist()}")
    else:
        print(f"  afre_monthly_flow: only {len(s)} non-null values")

print("\n=== DONE ===")
