import argparse
import csv
import time
import winsound
from datetime import datetime
from pathlib import Path

import serial


def beep_start():
    """삐- 삐- 삐- 삐빅(길게) → 녹화 시작 신호"""
    for _ in range(3):
        winsound.Beep(880, 150)
        time.sleep(0.15)
    winsound.Beep(1320, 500)


def beep_end():
    """낮은 삐빅 → 녹화 종료 신호"""
    winsound.Beep(440, 400)

LABEL_MAP = {
    # safe
    "empty":                ("safe",    "absence"),
    "sitting_still":        ("safe",    "posture"),
    "standing_still":       ("safe",    "posture"),
    "lying_still":          ("safe",    "posture"),
    "hand_move":            ("safe",    "motion"),
    "walking":              ("safe",    "motion"),
    "sit_to_stand":         ("safe",    "transition"),
    "stand_to_sit":         ("safe",    "transition"),
    "stand_to_lie_normal":  ("safe",    "transition"),
    "lie_to_stand":         ("safe",    "transition"),
    "lying_normal_breath":  ("safe",    "breathing"),
    # warning - breathing
    "lying_fast_breath":        ("warning", "breathing"),
    "lying_slow_breath":        ("warning", "breathing"),
    "lying_irregular_breath":   ("warning", "breathing"),
    # warning - gait
    "unstable_walking":         ("warning", "gait"),
    # warning - bed_exit
    "bed_exit_failed":          ("warning", "bed_exit"),
    # danger - fall
    "bed_sitting_to_stand_fall":   ("danger", "fall"),
    "bed_lying_to_stand_fall":     ("danger", "fall"),
    "bed_stand_to_lie_fall":       ("danger", "fall"),
    "chair_sitting_to_stand_fall": ("danger", "fall"),
    "chair_stand_to_sit_fall":     ("danger", "fall"),
    "walking_trip_fall":           ("danger", "fall"),
    "walking_turn_fall":           ("danger", "fall"),
    # danger - post_fall
    "post_bed_fall_inactive":      ("danger", "post_fall"),
    "post_chair_fall_inactive":    ("danger", "post_fall"),
    "post_walking_fall_inactive":  ("danger", "post_fall"),
    # danger - breathing
    "lying_apnea_like":                  ("danger", "breathing"),
    "post_fall_apnea_like":              ("danger", "breathing"),
    # danger - abnormal_motion
    "lying_convulsive_like_movement":    ("danger", "abnormal_motion"),
}

DATA_ROOT = Path(__file__).parent.parent / "data"


def next_trial(trial_str):
    prefix = trial_str[0]           # 't'
    num = int(trial_str[1:]) + 1    # 001 → 2
    return f"{prefix}{num:03d}"


def record_once(ser, out_path, risk, domain, subject, label, trial, duration):
    saved_count = 0
    start = time.time()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "pc_time_ms", "datetime", "risk", "domain",
            "subject_id", "label", "trial_id", "raw_line",
        ])

        while time.time() - start < duration:
            line = ser.readline().decode(errors="ignore").strip()
            if line.startswith("CSI_DATA"):
                writer.writerow([
                    int(time.time() * 1000),
                    datetime.now().isoformat(timespec="milliseconds"),
                    risk, domain, subject, label, trial, line,
                ])
                saved_count += 1

    return saved_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",     required=True)
    parser.add_argument("--baud",     type=int,   default=921600)
    parser.add_argument("--subject",  default="S01")
    parser.add_argument("--label",    required=True, choices=list(LABEL_MAP.keys()))
    parser.add_argument("--trial",    required=True, help="시작 trial 번호, e.g. t001")
    parser.add_argument("--duration", type=float, default=20,  help="녹화 시간(초)")
    parser.add_argument("--repeat",   type=int,   default=1,   help="반복 횟수 (기본 1)")
    parser.add_argument("--delay",    type=int,   default=0,   help="첫 녹화 전 대기(초)")
    parser.add_argument("--break_sec",type=int,   default=3,   help="반복 사이 대기(초), 기본 3")

    args = parser.parse_args()

    risk, domain = LABEL_MAP[args.label]
    out_dir = DATA_ROOT / risk / domain / args.label / args.subject
    out_dir.mkdir(parents=True, exist_ok=True)

    ser = serial.Serial(args.port, args.baud, timeout=1)
    time.sleep(1)

    if args.delay > 0:
        print(f"[INFO] {args.delay}s 후 시작...")
        for i in range(args.delay, 0, -1):
            print(f"  {i}s ...", end="\r")
            time.sleep(1)
        print()

    trial = args.trial
    for i in range(args.repeat):
        filename = f"{args.subject}_{args.label}_{trial}.csv"
        out_path = out_dir / filename

        if out_path.exists():
            print(f"[SKIP] 이미 존재: {out_path}")
            trial = next_trial(trial)
            continue

        print(f"\n[{i+1}/{args.repeat}] {trial}  →  {out_path}")
        print(f"  label={args.label}  duration={args.duration}s")

        beep_start()
        count = record_once(ser, out_path, risk, domain,
                            args.subject, args.label, trial, args.duration)
        beep_end()
        print(f"  저장 완료: {count} frames")

        trial = next_trial(trial)

        if i < args.repeat - 1:
            print(f"  {args.break_sec}s 후 다음 시작...")
            time.sleep(args.break_sec)

    ser.close()
    print(f"\n[DONE] 총 {args.repeat}회 완료")


if __name__ == "__main__":
    main()
