#!/usr/bin/env python3

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(
        description="Plot clean, faulty, z-score mitigated, and IF-mitigated VPA recommendations from a collector CSV.",
    )
    parser.add_argument("input_csv", help="Path to a collector CSV file")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output image path. Defaults to <input>-vpa-mitigation.png",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional figure title",
    )
    return parser.parse_args()


def load_rows(csv_path):
    timestamps = []
    cpu_clean = []
    cpu_faulty = []
    cpu_mitigated = []
    cpu_if = []
    mem_clean = []
    mem_faulty = []
    mem_mitigated = []
    mem_if = []

    with open(csv_path, newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "timestamp",
            "vpa_cpu_rec_clean_m",
            "vpa_cpu_rec_faulty_m",
            "vpa_cpu_rec_mitigated_m",
            "vpa_cpu_rec_if_m",
            "vpa_memory_rec_clean_mi",
            "vpa_memory_rec_faulty_mi",
            "vpa_memory_rec_mitigated_mi",
            "vpa_memory_rec_if_mi",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(f"CSV is missing required columns: {missing_str}")

        for row in reader:
            timestamps.append(datetime.fromisoformat(row["timestamp"]))
            cpu_clean.append(float(row["vpa_cpu_rec_clean_m"]))
            cpu_faulty.append(float(row["vpa_cpu_rec_faulty_m"]))
            cpu_mitigated.append(float(row["vpa_cpu_rec_mitigated_m"]))
            cpu_if.append(float(row["vpa_cpu_rec_if_m"]))
            mem_clean.append(float(row["vpa_memory_rec_clean_mi"]))
            mem_faulty.append(float(row["vpa_memory_rec_faulty_mi"]))
            mem_mitigated.append(float(row["vpa_memory_rec_mitigated_mi"]))
            mem_if.append(float(row["vpa_memory_rec_if_mi"]))

    if not timestamps:
        raise ValueError("CSV contains no data rows.")

    return (
        timestamps,
        cpu_clean,
        cpu_faulty,
        cpu_mitigated,
        cpu_if,
        mem_clean,
        mem_faulty,
        mem_mitigated,
        mem_if,
    )


def plot(csv_path, output_path, title):
    (
        timestamps,
        cpu_clean,
        cpu_faulty,
        cpu_mitigated,
        cpu_if,
        mem_clean,
        mem_faulty,
        mem_mitigated,
        mem_if,
    ) = load_rows(csv_path)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(timestamps, cpu_clean, label="CPU Clean", linewidth=2)
    axes[0].plot(timestamps, cpu_faulty, label="CPU Faulty", linewidth=2)
    axes[0].plot(timestamps, cpu_mitigated, label="CPU Z-Score", linewidth=2)
    axes[0].plot(timestamps, cpu_if, label="CPU IF", linewidth=2)
    axes[0].set_ylabel("CPU Recommendation (m)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(timestamps, mem_clean, label="Memory Clean", linewidth=2)
    axes[1].plot(timestamps, mem_faulty, label="Memory Faulty", linewidth=2)
    axes[1].plot(timestamps, mem_mitigated, label="Memory Z-Score", linewidth=2)
    axes[1].plot(timestamps, mem_if, label="Memory IF", linewidth=2)
    axes[1].set_ylabel("Memory Recommendation (Mi)")
    axes[1].set_xlabel("Time")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    fig.suptitle(title or "VPA Recommendations: Clean vs Faulty vs Mitigated")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    args = parse_args()
    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV does not exist: {input_path}")

    output_path = Path(args.output) if args.output else input_path.with_name(
        f"{input_path.stem}-vpa-mitigation.png"
    )

    plot(input_path, output_path, args.title)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
