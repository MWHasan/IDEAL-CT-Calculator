# -*- coding: utf-8 -*-
"""IDEAL-CT / CT-Index calculator.

This program reads IDEAL-CT load-displacement CSV files in two supported forms:

1. Equipment/export CSV files with recognizable time, load, and LVDT/LLD columns.
2. A generic CSV format with metadata rows followed by a time-load-displacement table.

The calculation engine retains full numerical precision. ASTM D8225-26 reporting
precision is applied only to the exported summary presentation.

This software implements selected calculations and data-quality checks described in
ASTM D8225-26. It does not determine laboratory compliance with the standard.
"""

from __future__ import annotations

import csv
import glob
import math
import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.stats import linregress

SOFTWARE_VERSION = "0.1.1"
METHOD_BASIS = "ASTM D8225-26"
DEFAULT_DIAMETER_MM = 150.0
DEFAULT_THICKNESS_MM = 62.0
TERMINAL_LOAD_KN = 0.1
SAMPLING_RATE_MIN_HZ = 40.0
DISPLACEMENT_RATE_MIN_MM_MIN = 48.0
DISPLACEMENT_RATE_MAX_MM_MIN = 52.0

COLUMN_ALIASES = {
    "time": [
        "time", "time (s)", "time (sec)", "time(s)", "time(sec)",
    ],
    "load": [
        "load", "load cell", "load (kn)", "load(kn)", "load cell (kn)",
        "force", "force (kn)", "load (n)", "force (n)",
    ],
    "displacement": [
        "displacement", "displacement (mm)", "frame lvdt", "frame lvdt (mm)",
        "lvdt", "lld", "load line displacement", "load line displacement (mm)",
    ],
}


def _normalize_text(value: object) -> str:
    text = str(value).strip().lower()
    text = text.replace("_", " ")
    return " ".join(text.split())


def _find_alias_column(columns: Iterable[object], aliases: Iterable[str]) -> Optional[str]:
    normalized = {_normalize_text(c): c for c in columns}
    for alias in aliases:
        alias_norm = _normalize_text(alias)
        if alias_norm in normalized:
            return normalized[alias_norm]
    for col in columns:
        col_norm = _normalize_text(col)
        for alias in aliases:
            if _normalize_text(alias) in col_norm:
                return col
    return None


def _parse_number(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_metadata(lines: list[str]) -> dict[str, object]:
    metadata: dict[str, object] = {
        "specimen_id": None,
        "diameter": None,
        "thickness": None,
        "temperature": None,
        "nmas": None,
        "air_voids": None,
        "asphalt_mixture_type": None,
        "specimen_type": None,
        "aging_condition": None,
    }

    numeric_keys = {
        "diameter": {"diameter", "average diameter"},
        "thickness": {"thickness", "height", "average height", "average height h", "average height (h)"},
        "temperature": {"temperature", "test temperature", "test temperature c"},
        "nmas": {"nmas", "nominal maximum aggregate size", "nominal maximum aggregate size nmas"},
        "air_voids": {"air voids", "air void content", "air voids percent", "air voids %"},
    }
    text_keys = {
        "specimen_id": {"specimen id", "sample id", "specimen"},
        "asphalt_mixture_type": {"asphalt mixture type", "mixture type"},
        "specimen_type": {"specimen type"},
        "aging_condition": {"aging condition", "aging"},
    }

    for raw_line in lines:
        try:
            parts = next(csv.reader([raw_line]))
        except csv.Error:
            parts = [part.strip() for part in raw_line.split(",")]
        parts = [part.strip() for part in parts]
        if not parts:
            continue

        label = _normalize_text(parts[0].rstrip(":;"))
        joined = _normalize_text(" ".join(parts[:2]))

        for candidate, labels in numeric_keys.items():
            if label in labels or joined in labels:
                for part in parts[1:]:
                    number = _parse_number(part)
                    if number is not None:
                        metadata[candidate] = number
                        break
                break
        else:
            for candidate, labels in text_keys.items():
                if label in labels:
                    value = parts[1] if len(parts) > 1 else ""
                    metadata[candidate] = value.strip() or None
                    break

    return metadata


def _find_header_row(lines: list[str]) -> Optional[int]:
    for i, raw_line in enumerate(lines):
        try:
            parts = next(csv.reader([raw_line]))
        except csv.Error:
            parts = raw_line.strip().split(",")
        normalized = {_normalize_text(p) for p in parts}
        has_time = any(_normalize_text(alias) in normalized for alias in COLUMN_ALIASES["time"])
        has_load = any(_normalize_text(alias) in normalized for alias in COLUMN_ALIASES["load"])
        has_disp = any(_normalize_text(alias) in normalized for alias in COLUMN_ALIASES["displacement"])
        if has_time and has_load and has_disp:
            return i

        line_lower = _normalize_text(raw_line)
        if "time" in line_lower and "load" in line_lower and (
            "lvdt" in line_lower or "displacement" in line_lower or "lld" in line_lower
        ):
            return i
    return None


def _detect_data_columns(df: pd.DataFrame) -> dict[str, str]:
    result: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        column = _find_alias_column(df.columns, aliases)
        if column is not None:
            result[canonical] = column
    return result


def _read_input_file(file_path: str) -> tuple[pd.DataFrame, dict[str, object], str]:
    path = Path(file_path)
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()

    metadata = _parse_metadata(lines)
    header_row_index = _find_header_row(lines)
    if header_row_index is None:
        raise ValueError(
            "Could not find a data header. The file must contain time, load, and "
            "displacement/LVDT columns."
        )

    df = pd.read_csv(path, skiprows=header_row_index)
    source_header_text = " ".join(str(c).lower() for c in df.columns)
    col_map = _detect_data_columns(df)
    missing = [name for name in ("time", "load", "displacement") if name not in col_map]
    if missing:
        raise ValueError("Missing required data column(s): " + ", ".join(missing))

    df = df[[col_map["time"], col_map["load"], col_map["displacement"]]].copy()
    df.columns = ["Time", "Load Cell", "Frame LVDT"]
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna().reset_index(drop=True)

    if len(df) < 3:
        raise ValueError("Not enough valid data points remain after numeric filtering.")

    input_format = (
        "custom"
        if ("frame lvdt" not in source_header_text and "load cell" not in source_header_text)
        else "equipment/export"
    )

    if metadata["diameter"] is None:
        metadata["diameter"] = DEFAULT_DIAMETER_MM
    if metadata["thickness"] is None:
        metadata["thickness"] = DEFAULT_THICKNESS_MM

    return df, metadata, input_format


def _get_post_peak_displacement(
    target_load: float,
    full_df: pd.DataFrame,
    peak_index: int,
) -> float:
    post_df = full_df.loc[peak_index:]
    below_idx = post_df[post_df["Load Cell_Norm"] < target_load].index
    if below_idx.empty:
        return np.nan

    idx_after = int(below_idx[0])
    if idx_after == peak_index:
        return np.nan
    idx_before = idx_after - 1
    y2 = float(full_df.loc[idx_after, "Load Cell_Norm"])
    y1 = float(full_df.loc[idx_before, "Load Cell_Norm"])
    x2 = float(full_df.loc[idx_after, "Frame LVDT_Norm"])
    x1 = float(full_df.loc[idx_before, "Frame LVDT_Norm"])

    if y2 == y1:
        return x1
    return x1 + (target_load - y1) * (x2 - x1) / (y2 - y1)


def _validate_specimen_dimensions(
    diameter: float,
    thickness: float,
    specimen_type: Optional[str],
    nmas: Optional[float],
    warnings: list[str],
) -> None:
    if abs(diameter - 150.0) > 2.0:
        warnings.append(
            f"Diameter is {diameter:.3f} mm; ASTM D8225-26 specifies a nominal 150 +/- 2 mm diameter."
        )

    normalized_type = _normalize_text(specimen_type) if specimen_type else ""
    is_core = normalized_type in {"roadway core", "core", "field core", "roadway cores"}
    is_lab = normalized_type in {
        "lmlc", "pmlc", "laboratory", "laboratory specimen", "laboratory compacted",
        "laboratory-compacted", "laboratory compacted specimen",
    }

    if thickness < 38.0:
        warnings.append(
            "Specimen thickness is below 38 mm; ASTM D8225-26 does not permit a roadway core below 38 mm "
            "and specifies thicker dimensions for laboratory specimens."
        )
    elif is_core:
        return
    elif is_lab and nmas is not None:
        expected = 62.0 if float(nmas) <= 20.0 else 95.0
        if abs(thickness - expected) > 1.0:
            warnings.append(
                f"Thickness is {thickness:.3f} mm; for a laboratory specimen with NMAS {float(nmas):.2f} mm, "
                f"ASTM D8225-26 specifies {expected:.0f} +/- 1 mm."
            )
    elif is_lab and nmas is None:
        warnings.append(
            "NMAS is missing; laboratory specimen thickness cannot be checked against the 62 mm or 95 mm requirement."
        )
    elif not is_core and not is_lab:
        warnings.append(
            "Specimen type is missing or not recognized; thickness QC was not classified as laboratory or roadway-core QC."
        )


def _estimate_sampling_rate(time_seconds: pd.Series) -> float:
    dt = np.diff(time_seconds.to_numpy(dtype=float))
    positive_dt = dt[dt > 0]
    if len(positive_dt) == 0:
        return np.nan
    return float(1.0 / np.median(positive_dt))


def _estimate_full_record_displacement_rate(time_seconds: pd.Series, displacement_mm: pd.Series) -> float:
    elapsed_min = float((time_seconds.iloc[-1] - time_seconds.iloc[0]) / 60.0)
    if elapsed_min <= 0:
        return np.nan
    displacement_change = float(displacement_mm.iloc[-1] - displacement_mm.iloc[0])
    return displacement_change / elapsed_min


def analyze_ct_file(
    file_path: str,
    baseline_correction: bool = True,
    apply_terminal_load_cutoff: bool = True,
) -> tuple[dict, pd.DataFrame, str]:
    """Analyze one IDEAL-CT file.

    Returns
    -------
    parameters : dict
        Calculation results and QC diagnostics. Numerical values retain full precision.
    data : pandas.DataFrame
        Processed data used for the analysis.
    input_format : str
        ``custom`` or ``equipment/export``.
    """
    df, metadata, input_format = _read_input_file(file_path)
    warnings: list[str] = []

    diameter = float(metadata["diameter"])
    thickness = float(metadata["thickness"])
    temperature = metadata["temperature"]
    nmas = metadata["nmas"]
    air_voids = metadata["air_voids"]
    specimen_type = metadata["specimen_type"]
    mixture_type = metadata["asphalt_mixture_type"]
    aging_condition = metadata["aging_condition"]
    specimen_id = metadata["specimen_id"]

    if diameter <= 0 or thickness <= 0:
        raise ValueError("Specimen diameter and thickness must be positive.")

    _validate_specimen_dimensions(diameter, thickness, specimen_type, nmas, warnings)

    if air_voids is None:
        warnings.append("Air void content was not found in the input metadata; ASTM D8225-26 reporting requires air voids.")
    if specimen_type is None:
        warnings.append("Specimen type was not found in the input metadata.")
    if aging_condition is None:
        warnings.append("Aging condition was not found in the input metadata.")
    if temperature is None:
        warnings.append("Test temperature was not found in the input metadata.")

    initial_load = float(df["Load Cell"].iloc[0])
    initial_disp = float(df["Frame LVDT"].iloc[0])
    if baseline_correction:
        df["Load Cell_Norm"] = df["Load Cell"] - initial_load
        df["Frame LVDT_Norm"] = df["Frame LVDT"] - initial_disp
        if abs(initial_load) > TERMINAL_LOAD_KN:
            warnings.append(
                f"Initial recorded load was {initial_load:.3f} kN. Baseline correction was applied; "
                "verify that the initial seating/preload does not contribute to the reported result."
            )
    else:
        df["Load Cell_Norm"] = df["Load Cell"]
        df["Frame LVDT_Norm"] = df["Frame LVDT"]

    df["Stress"] = (2.0 * df["Load Cell_Norm"]) / ((math.pi * diameter * thickness) / 1_000_000.0)

    peak_idx = int(df["Load Cell_Norm"].idxmax())
    post_peak = df.loc[peak_idx:]
    terminal_candidates = post_peak[post_peak["Load Cell_Norm"] < TERMINAL_LOAD_KN].index
    terminated_at_01kN = not terminal_candidates.empty

    if terminated_at_01kN and apply_terminal_load_cutoff:
        end_idx = int(terminal_candidates[0])
        df = df.loc[:end_idx].copy()
    elif not terminated_at_01kN:
        warnings.append(
            f"Post-peak load did not reach below {TERMINAL_LOAD_KN:.1f} kN in the supplied file; "
            "the analysis uses the available end of the record and is not a complete D8225-26 test record."
        )

    max_load_idx = int(df["Load Cell_Norm"].idxmax())
    max_load = float(df["Load Cell_Norm"].max())
    time_at_failure = float(df.loc[max_load_idx, "Time"])
    tensile_strength = float(df.loc[max_load_idx, "Stress"])

    # ASTM D8225-26 defines Wf as the area under the load-LLD curve using the
    # quadrangle rule. For sequential points this is the trapezoidal form below.
    x = df["Frame LVDT_Norm"].to_numpy(dtype=float)
    y = df["Load Cell_Norm"].to_numpy(dtype=float)
    dx = np.diff(x)
    mean_load = (y[1:] + y[:-1]) / 2.0
    incremental_energy = np.insert(mean_load * dx, 0, 0.0)
    df["Incremental Energy"] = incremental_energy
    df["Cumulative Energy"] = np.cumsum(incremental_energy)

    Wf = float(df["Cumulative Energy"].iloc[-1])  # kN-mm = J
    Gf = float((Wf / (diameter * thickness)) * 1_000_000.0)

    pre_peak_energy = float(df.loc[max_load_idx, "Cumulative Energy"])
    pre_peak_fracture_energy = float((pre_peak_energy / (diameter * thickness)) * 1_000_000.0)
    post_peak_energy = Gf - pre_peak_fracture_energy

    P85 = 0.85 * max_load
    P75 = 0.75 * max_load
    P65 = 0.65 * max_load

    l85 = _get_post_peak_displacement(P85, df, max_load_idx)
    l75 = _get_post_peak_displacement(P75, df, max_load_idx)
    l65 = _get_post_peak_displacement(P65, df, max_load_idx)

    post_peak_df = df.loc[max_load_idx:]
    slope_df = post_peak_df[
        (post_peak_df["Load Cell_Norm"] <= P85)
        & (post_peak_df["Load Cell_Norm"] >= P65)
    ]
    if len(slope_df) > 1:
        m75 = abs(linregress(slope_df["Frame LVDT_Norm"], slope_df["Load Cell_Norm"]).slope)
    elif not np.isnan(l85) and not np.isnan(l65) and l65 != l85:
        m75 = abs((P85 - P65) / (l85 - l65))
    else:
        m75 = np.nan

    if not np.isnan(l75) and not np.isnan(m75) and m75 != 0:
        # The slope computed from kN/mm has the same numerical value as MN/m.
        ct_index = (thickness / 62.0) * (l75 / diameter) * (Gf / m75)
    else:
        ct_index = np.nan

    # Additional research parameter reported in VTRC IDT-CT work.
    # VTRC 23-R3 defines Gf in kN/mm and St in kPa and calculates:
    # FST = (Gf / St) * 10^6. Since this program stores Gf in J/m^2
    # (numerically equivalent to kN/m), the expression simplifies numerically
    # to Gf[J/m^2] / St[kPa], yielding FST in mm.
    if tensile_strength != 0 and not np.isnan(tensile_strength):
        fst_index = Gf / tensile_strength
    else:
        fst_index = np.nan

    sampling_hz = _estimate_sampling_rate(df["Time"])
    loading_rate_mm_min = _estimate_full_record_displacement_rate(df["Time"], df["Frame LVDT_Norm"])

    if not np.isnan(sampling_hz) and sampling_hz < (SAMPLING_RATE_MIN_HZ - 0.001):
        warnings.append(f"Estimated sampling frequency is {sampling_hz:.1f} Hz, below the 40 Hz minimum.")
    if not np.isnan(loading_rate_mm_min) and not (
        DISPLACEMENT_RATE_MIN_MM_MIN <= loading_rate_mm_min <= DISPLACEMENT_RATE_MAX_MM_MIN
    ):
        warnings.append(
            f"Full-record displacement-rate estimate is {loading_rate_mm_min:.2f} mm/min; "
            "this is a diagnostic estimate, not a procedural compliance determination."
        )

    parameters = {
        "Software Version": SOFTWARE_VERSION,
        "Method Basis": METHOD_BASIS,
        "Specimen ID": specimen_id if specimen_id is not None else "",
        "Input Format": input_format,
        "Baseline Correction Applied": baseline_correction,
        "Initial Load [kN]": initial_load,
        "Initial Displacement [mm]": initial_disp,
        "Asphalt Mixture Type": mixture_type if mixture_type is not None else "",
        "Specimen Type": specimen_type if specimen_type is not None else "",
        "NMAS [mm]": nmas if nmas is not None else np.nan,
        "Air Voids [%]": air_voids if air_voids is not None else np.nan,
        "Aging Condition": aging_condition if aging_condition is not None else "",
        "Diameter [mm]": diameter,
        "Thickness [mm]": thickness,
        "Test Temperature [deg C]": temperature if temperature is not None else np.nan,
        "Estimated Sampling Frequency [Hz]": sampling_hz,
        "Estimated Displacement Rate [mm/min]": loading_rate_mm_min,
        "Terminal Load Reached [below 0.1 kN]": terminated_at_01kN,
        "Analysis End Load [kN]": float(df["Load Cell_Norm"].iloc[-1]),
        "Time at Peak Load [s]": time_at_failure,
        "Maximum Load (P_Max) [kN]": max_load,
        "Tensile Strength (St) [kPa]": tensile_strength,
        "Fracture Strain Tolerance (FST) [mm]": fst_index,
        "Work of Failure (Wf) [J]": Wf,
        "Failure Energy (Gf) [J/m^2]": Gf,
        "P85 [kN]": P85,
        "l85 [mm]": l85,
        "P75 [kN]": P75,
        "l75 [mm]": l75,
        "P65 [kN]": P65,
        "l65 [mm]": l65,
        "Post-Peak Slope (|m75|) [MN/m]": m75,
        "CTIndex": ct_index,
        "QC Warnings": " | ".join(warnings) if warnings else "None",
    }

    return parameters, df, input_format


REPORT_NUMBER_FORMATS = {
    "Test Temperature [deg C]": "0.0",
    "Air Voids [%]": "0.0",
    "Thickness [mm]": "0.0",
    "Diameter [mm]": "0",
    "l75 [mm]": "0.00",
    "Post-Peak Slope (|m75|) [MN/m]": "0.000",
    "Failure Energy (Gf) [J/m^2]": "0",
    "Fracture Strain Tolerance (FST) [mm]": "0.00",
    "CTIndex": "0.0",
}


def _write_summary_workbook(
    output_path: str,
    data: pd.DataFrame,
    parameters: dict,
) -> None:
    summary_df = pd.DataFrame(list(parameters.items()), columns=["Parameter", "Value"])
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Normalized Data", index=False)
        summary_df.to_excel(writer, sheet_name="Summary Results", index=False)

        ws = writer.book["Summary Results"]
        for row in range(2, ws.max_row + 1):
            parameter_name = ws.cell(row=row, column=1).value
            number_format = REPORT_NUMBER_FORMATS.get(parameter_name)
            if number_format:
                ws.cell(row=row, column=2).number_format = number_format


def process_ct_index_files(input_folder: str = ".", output_folder: str = "Results") -> None:
    """Process all CSV files in a folder and write individual and batch Excel results."""
    os.makedirs(output_folder, exist_ok=True)
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
    print(f"Found {len(csv_files)} CSV files to process.")

    all_summaries: dict[str, dict] = {}
    all_curves: dict[str, pd.DataFrame] = {}

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        sample_name = os.path.splitext(filename)[0]
        print(f"Processing: {filename}...")
        try:
            parameters, data, _ = analyze_ct_file(file_path)
            all_summaries[sample_name] = parameters
            all_curves[sample_name] = data[["Frame LVDT_Norm", "Load Cell_Norm"]].copy()

            output_path = os.path.join(output_folder, f"Processed_{sample_name}.xlsx")
            _write_summary_workbook(output_path, data, parameters)
            print(f"Saved Individual: {output_path}")
        except ValueError as exc:
            if "Not enough valid data points" in str(exc) and "template" in filename.lower():
                print(f"Skipping blank template file: {filename}")
            else:
                print(f"Error processing {filename}: {exc}")
        except Exception as exc:
            print(f"Error processing {filename}: {exc}")

    if not all_summaries:
        print("No files were successfully processed.")
        return

    summary_table = pd.DataFrame(all_summaries).T
    numeric_summary = summary_table.apply(pd.to_numeric, errors="coerce")
    numeric_only = numeric_summary.select_dtypes(include=[np.number])
    batch_params_df = pd.DataFrame({
        "Average": numeric_only.mean(axis=0),
        "Std Dev": numeric_only.std(axis=0),
    })
    batch_params_df["COV (%)"] = (batch_params_df["Std Dev"] / batch_params_df["Average"]) * 100.0
    batch_params_df["Standard Error"] = batch_params_df["Std Dev"] / np.sqrt(len(all_summaries))
    batch_params_df.reset_index(inplace=True)
    batch_params_df.rename(columns={"index": "Parameter"}, inplace=True)

    if len(all_summaries) < 5:
        print(
            "WARNING: ASTM D8225-26 specifies a minimum of five specimens for a laboratory mixture or roadway-core test set."
        )

    max_disp = max(curve["Frame LVDT_Norm"].max() for curve in all_curves.values())
    if max_disp > 0:
        common_x = np.arange(0.0, max_disp + 0.005, 0.005)
        interpolated_loads = []
        for curve in all_curves.values():
            x_vals = curve["Frame LVDT_Norm"].to_numpy(dtype=float)
            y_vals = curve["Load Cell_Norm"].to_numpy(dtype=float)
            x_vals, unique_indices = np.unique(x_vals, return_index=True)
            y_vals = y_vals[unique_indices]
            if len(x_vals) < 2:
                continue
            f = interp1d(x_vals, y_vals, kind="linear", bounds_error=False, fill_value=np.nan)
            interpolated_loads.append(f(common_x))

        if interpolated_loads:
            avg_curve_df = pd.DataFrame({
                "Average Frame LVDT (mm)": common_x,
                "Average Normalized Load (kN)": np.nanmean(np.vstack(interpolated_loads), axis=0),
            })
        else:
            avg_curve_df = pd.DataFrame(columns=["Average Frame LVDT (mm)", "Average Normalized Load (kN)"])
    else:
        avg_curve_df = pd.DataFrame(columns=["Average Frame LVDT (mm)", "Average Normalized Load (kN)"])

    batch_output_path = os.path.join(output_folder, "Summary_Results_CT.xlsx")
    with pd.ExcelWriter(batch_output_path, engine="openpyxl") as writer:
        batch_params_df.to_excel(writer, sheet_name="Summary Statistics", index=False)
        avg_curve_df.to_excel(writer, sheet_name="Average Curve", index=False)
    print(f"Batch Summary Saved: {batch_output_path}")


if __name__ == "__main__":
    process_ct_index_files()
