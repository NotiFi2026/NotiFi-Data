import argparse
import ast
import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# duration thresholds for phase annotation lines (fraction of total time)
PHASE_SPLITS = (0.25, 0.65)


def parse_csi_array(raw_line: str) -> np.ndarray | None:
    m = re.search(r'"?\[(.+?)\]"?', raw_line)
    if not m:
        return None
    vals = np.array(ast.literal_eval(f"[{m.group(1)}]"), dtype=np.float32)
    return vals


def amplitude(vals: np.ndarray) -> float:
    I = vals[0::2]
    Q = vals[1::2]
    amp = np.sqrt(I**2 + Q**2)
    # ignore zero subcarriers (null/pilot)
    amp = amp[amp > 0]
    return float(amp.mean()) if len(amp) else 0.0


def load_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    times, amps = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("raw_line", "")
            if not raw.startswith("CSI_DATA"):
                continue
            vals = parse_csi_array(raw)
            if vals is None or len(vals) < 2:
                continue
            times.append(int(row["pc_time_ms"]))
            amps.append(amplitude(vals))

    t = np.array(times, dtype=np.float64)
    a = np.array(amps, dtype=np.float64)
    t = (t - t[0]) / 1000.0  # ms → sec, start at 0
    return t, a


def phase_labels(label: str) -> tuple[str, str, str]:
    """Return (before, transition, after) phase names from label."""
    mapping = {
        "sit_to_stand":        ("sitting",  "sit → stand",  "standing"),
        "stand_to_sit":        ("standing", "stand → sit",  "sitting"),
        "stand_to_lie_normal": ("standing", "stand → lie",  "lying"),
        "lie_to_stand":        ("lying",    "lie → stand",  "standing"),
    }
    return mapping.get(label, ("phase 1", label.replace("_", " "), "phase 2"))


def plot(path: Path, smooth: int = 5) -> None:
    t, a = load_csv(path)

    # optional smoothing
    if smooth > 1:
        kernel = np.ones(smooth) / smooth
        a_plot = np.convolve(a, kernel, mode="same")
    else:
        a_plot = a

    label = path.stem.split("_", 1)[1].rsplit("_", 1)[0]  # subject_label_trial → label
    # extract label from filename: <subject>_<label>_<trial>
    parts = path.stem.split("_")
    # find label from LABEL_MAP keys by trying progressively longer substrings
    known_labels = [
        "sit_to_stand", "stand_to_sit", "stand_to_lie_normal", "lie_to_stand",
        "empty", "sitting_still", "standing_still", "lying_still",
        "hand_move", "walking", "lying_normal_breath",
        "lying_fast_breath", "lying_long_breath", "lying_shallow_breath",
        "lying_breath_hold_short", "sitting_inactive_long",
        "standing_inactive_long", "lying_inactive_long",
        "fall_like_recovered", "fall_simulated", "post_fall_inactive",
        "lying_apnea_like", "lying_breath_signal_lost",
    ]
    detected_label = path.parent.parent.name  # structure: .../label/subject/file.csv
    before, transition, after = phase_labels(detected_label)

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(t, a_plot, linewidth=1.0, color="#1f77b4")

    # phase split lines
    t_max = t[-1]
    t1 = t_max * PHASE_SPLITS[0]
    t2 = t_max * PHASE_SPLITS[1]
    for tx in (t1, t2):
        ax.axvline(tx, color="#1f77b4", linestyle="--", linewidth=1, alpha=0.7)

    # phase annotations
    y_top = ax.get_ylim()[1]
    for tx, text in ((t_max * 0.10, before),
                     (t_max * 0.43, transition),
                     (t_max * 0.80, after)):
        ax.text(tx, y_top, text, ha="left", va="top",
                fontsize=10, color="#333333")

    ax.set_xlabel("Time (sec)")
    ax.set_ylabel("Mean CSI amplitude")
    ax.set_title(f"{path.stem} - Mean CSI amplitude")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5)
    fig.tight_layout()

    out = path.with_suffix(".png")
    fig.savefig(out, dpi=150)
    print(f"Saved: {out}")


def main():
    parser = argparse.ArgumentParser(description="Visualize CSI amplitude from a recorded CSV")
    parser.add_argument("csv", nargs="?", help="Path to CSV file")
    parser.add_argument("--smooth", type=int, default=5, help="Moving average window (default 5)")
    args = parser.parse_args()

    if args.csv:
        plot(Path(args.csv), smooth=args.smooth)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
