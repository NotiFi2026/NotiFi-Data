import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import serial

STAGE_LABELS = {
    "stage1": ["empty", "sitting_still", "standing_still", "lying_still", "hand_move", "walk"],
    "stage2": ["present_inactive", "present_active", "sitting_inactive", "standing_inactive", "lying_inactive", "walking_active"],
    "stage3": ["sit_to_stand", "stand_to_sit", "stand_to_lie", "lie_to_stand", "fall_simulated"],
    "stage4": ["lying_normal_breath", "lying_fast_breath", "lying_shallow_breath", "lying_breath_hold"],
}

DATA_ROOT = Path(__file__).parent.parent / "data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, help="COM port, e.g. COM4")
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--rx_id", default="rx1", help="rx1 or rx2 (default: rx1)")
    parser.add_argument("--stage", default="stage1", choices=list(STAGE_LABELS.keys()))
    parser.add_argument("--subject", default="S01")
    parser.add_argument("--label", required=True)
    parser.add_argument("--trial", required=True, help="e.g. t001")
    parser.add_argument("--delay", type=int, default=0, help="seconds to wait before recording starts")

    args = parser.parse_args()

    valid_labels = STAGE_LABELS[args.stage]
    if args.label not in valid_labels:
        print(f"[ERROR] '{args.label}' is not valid for {args.stage}.")
        print(f"  Valid labels: {valid_labels}")
        return

    out_dir = DATA_ROOT / args.stage / args.label
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{args.subject}_{args.rx_id}_{args.trial}.csv"
    out_path = out_dir / filename

    if out_path.exists():
        print(f"[WARNING] File already exists: {out_path}")
        answer = input("Overwrite? (y/N): ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    ser = serial.Serial(args.port, args.baud, timeout=1)

    if args.delay > 0:
        print(f"[INFO] Starting in {args.delay}s ... (준비하세요)")
        for i in range(args.delay, 0, -1):
            print(f"  {i}초 후 시작...", end="\r")
            time.sleep(1)
        print()

    print(f"[INFO] Saving to: {out_path}")
    print(f"[INFO] Recording for {args.duration}s ...")

    start = time.time()
    saved_count = 0

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "pc_time_ms",
            "datetime",
            "rx_id",
            "stage",
            "subject_id",
            "label",
            "trial_id",
            "raw_line",
        ])

        while time.time() - start < args.duration:
            line = ser.readline().decode(errors="ignore").strip()

            if line.startswith("CSI_DATA"):
                now = time.time()
                pc_time_ms = int(now * 1000)

                writer.writerow([
                    pc_time_ms,
                    datetime.now().isoformat(timespec="milliseconds"),
                    args.rx_id,
                    args.stage,
                    args.subject,
                    args.label,
                    args.trial,
                    line,
                ])

                saved_count += 1

    ser.close()
    print(f"[DONE] Saved {saved_count} CSI lines → {out_path}")


if __name__ == "__main__":
    main()
