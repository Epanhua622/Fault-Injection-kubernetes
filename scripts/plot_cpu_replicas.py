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
        description="Plot clean vs faulty CPU-based HPA desired replicas from a collector CSV.",
    )
    parser.add_argument("input_csv", help="Path to a collector CSV file")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output image path. Defaults to <input>-cpu-replicas.png",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional plot title",
    )
    return parser.parse_args()


def load_rows(csv_path):
    timestamps = []
    clean = []
    faulty = []

    with open(csv_path, newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "timestamp",
            "desired_replicas_cpu_clean",
            "desired_replicas_cpu_faulty",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(f"CSV is missing required columns: {missing_str}")

        for row in reader:
            timestamps.append(datetime.fromisoformat(row["timestamp"]))
            clean.append(float(row["desired_replicas_cpu_clean"]))
            faulty.append(float(row["desired_replicas_cpu_faulty"]))

    if not timestamps:
        raise ValueError("CSV contains no data rows.")

    return timestamps, clean, faulty


def plot(csv_path, output_path, title):
    timestamps, clean, faulty = load_rows(csv_path)

    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, clean, label="CPU Clean", linewidth=2)
    plt.plot(timestamps, faulty, label="CPU Faulty", linewidth=2)
    plt.xlabel("Time")
    plt.ylabel("Desired Replicas")
    plt.title(title or "Desired CPU Replicas: Clean vs Faulty")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.ylim(bottom=0)  # origin at 0

    plt.yticks([1, 25, 50, 75, 100, 125, 150, 175, 200, 225, 250])  # custom ticks
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def main():
    args = parse_args()
    input_path = Path(args.input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV does not exist: {input_path}")

    output_path = Path(args.output) if args.output else input_path.with_name(
        f"{input_path.stem}-cpu-replicas.png"
    )

    plot(input_path, output_path, args.title)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
