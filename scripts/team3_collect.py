import argparse
import ast
import csv
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


SUBJECT_DEFAULT = "yja"

PLAN = {
    # safe
    "empty": {"duration": 20, "quiet": 20, "aircon": 17, "tv": 16, "music": 13},
    "sitting_still": {"duration": 20, "quiet": 7, "aircon": 6, "tv": 5, "music": 4},
    "standing_still": {"duration": 20, "quiet": 7, "aircon": 6, "tv": 5, "music": 4},
    "lying_still": {"duration": 20, "quiet": 7, "aircon": 6, "tv": 5, "music": 4},
    "hand_move": {"duration": 20, "quiet": 10, "aircon": 8, "tv": 8, "music": 7},
    "walking": {"duration": 20, "quiet": 10, "aircon": 9, "tv": 8, "music": 7},
    "sit_to_stand": {"duration": 10, "quiet": 5, "aircon": 4, "tv": 4, "music": 4},
    "stand_to_sit": {"duration": 10, "quiet": 5, "aircon": 4, "tv": 4, "music": 4},
    "stand_to_lie_normal": {"duration": 10, "quiet": 5, "aircon": 4, "tv": 4, "music": 4},
    "lie_to_stand": {"duration": 10, "quiet": 5, "aircon": 4, "tv": 4, "music": 4},
    "lying_normal_breath": {"duration": 20, "quiet": 20, "aircon": 17, "tv": 17, "music": 13},
    # warning
    "lying_fast_breath": {"duration": 20, "quiet": 20, "aircon": 17, "tv": 16, "music": 13},
    "lying_slow_breath": {"duration": 20, "quiet": 20, "aircon": 17, "tv": 17, "music": 13},
    "lying_irregular_breath": {"duration": 20, "quiet": 20, "aircon": 17, "tv": 17, "music": 13},
    "unstable_walking": {"duration": 20, "quiet": 20, "aircon": 17, "tv": 16, "music": 13},
    "bed_exit_failed": {"duration": 10, "quiet": 20, "aircon": 17, "tv": 17, "music": 13},
    # danger v2
    "bed_sitting_to_stand_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 6, "music": 5},
    "bed_lying_to_stand_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "bed_stand_to_lie_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "chair_sitting_to_stand_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 6, "music": 5},
    "chair_stand_to_sit_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "walking_trip_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "walking_turn_fall": {"duration": 10, "quiet": 8, "aircon": 7, "tv": 6, "music": 5},
    "post_bed_fall_inactive": {"duration": 20, "quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "post_chair_fall_inactive": {"duration": 20, "quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "post_walking_fall_inactive": {"duration": 20, "quiet": 8, "aircon": 7, "tv": 6, "music": 5},
    "lying_apnea_like": {"duration": 20, "quiet": 7, "aircon": 6, "tv": 5, "music": 5},
    "post_fall_apnea_like": {"duration": 20, "quiet": 7, "aircon": 6, "tv": 5, "music": 5},
    "lying_convulsive_like_movement": {"duration": 10, "quiet": 6, "aircon": 5, "tv": 5, "music": 5},
}

AMBIENTS = ["quiet", "aircon", "tv", "music"]

ACTION_GUIDE = {
    "empty": "사람 없음. sender/receiver 사이를 비우고, 실험자는 최소 2m 이상 떨어진다.",
    "sitting_still": "중앙 의자에 앉기. receiver 방향, 손은 무릎 위, 발은 바닥, 몸 움직임 최소화.",
    "standing_still": "중앙에 서기. receiver 방향, 발 어깨너비, 팔은 자연스럽게 내리고 정지.",
    "lying_still": "중앙 매트에 천장 보고 눕기. 머리는 sender 쪽 권장, 팔/다리 움직임 최소화.",
    "hand_move": "중앙에 서서 오른손만 가슴 높이에서 좌우 약 30cm, 약 1초 1회 왕복.",
    "walking": "sender-receiver 직선 경로를 천천히 왕복. 뛰지 않고 보드 30cm 이내 접근 금지.",
    "sit_to_stand": "의자에 앉은 상태에서 자연스럽게 일어나고 마지막 2-3초는 선 자세 정지.",
    "stand_to_sit": "선 상태에서 자연스럽게 앉고 마지막 2-3초는 앉은 자세 정지.",
    "stand_to_lie_normal": "선 상태에서 정상적으로 천천히 눕고 마지막 2-3초는 누운 자세 정지.",
    "lie_to_stand": "누운 상태에서 천천히 일어나 선 자세로 끝내고 마지막 2-3초 정지.",
    "lying_normal_breath": "누운 상태에서 평소처럼 호흡. 호흡 과장 금지, 몸 움직임 최소화.",
    "lying_fast_breath": "침대/매트에 정자세로 누워 평소보다 빠르게 호흡. 몸 움직임은 최소화하고, 어지러우면 즉시 중단.",
    "lying_slow_breath": "침대/매트에 정자세로 누워 평소보다 천천히 호흡. 들숨/날숨 간격을 길게 하되 숨을 무리하게 참지 않음.",
    "lying_irregular_breath": "침대/매트에 정자세로 누워 빠른 호흡과 느린 호흡을 불규칙하게 섞음. 일부 구간은 얕게, 일부 구간은 크게 호흡.",
    "unstable_walking": "sender-receiver 사이 경로를 천천히 걷되, 중심을 살짝 잃은 것처럼 좌우로 흔들리거나 보폭을 불규칙하게 함. 실제 낙상 금지.",
    "bed_exit_failed": "침대/매트에 누운 상태에서 일어나려다가 상체만 조금 들거나 팔로 지탱하다가 다시 눕기. 완전히 일어나지 않음.",
    "bed_sitting_to_stand_fall": "침대 가장자리에 앉은 상태에서 일어나려다가 균형을 잃고 매트 쪽으로 천천히 무너짐. 실제 충격 금지.",
    "bed_lying_to_stand_fall": "침대에 누운 상태에서 일어나려다가 균형을 잃고 매트 쪽으로 천천히 무너짐. 실제 충격 금지.",
    "bed_stand_to_lie_fall": "서 있는 상태에서 침대에 눕거나 앉으려다 위치를 놓쳐 매트 쪽으로 천천히 무너짐. 실제 충격 금지.",
    "chair_sitting_to_stand_fall": "의자에 앉은 상태에서 일어나려다가 균형을 잃고 매트 쪽으로 천천히 무너짐. 실제 충격 금지.",
    "chair_stand_to_sit_fall": "서 있는 상태에서 의자에 앉으려다가 착석 실패 또는 균형 상실로 매트 쪽으로 천천히 무너짐.",
    "walking_trip_fall": "걷다가 발이 걸린 것처럼 한두 걸음 후 매트 쪽으로 천천히 무너짐. 보드/케이블과 30cm 이상 거리 유지.",
    "walking_turn_fall": "걷다가 방향 전환 중 균형을 잃은 것처럼 매트 쪽으로 천천히 무너짐. 보드/케이블과 30cm 이상 거리 유지.",
    "post_bed_fall_inactive": "침대 옆 바닥/매트에 누운 상태로 20초 동안 거의 움직이지 않기. 정상 호흡 유지.",
    "post_chair_fall_inactive": "의자 옆 바닥/매트에 누운 상태로 20초 동안 거의 움직이지 않기. 정상 호흡 유지.",
    "post_walking_fall_inactive": "보행 경로/통로 바닥에 누운 상태로 20초 동안 거의 움직이지 않기. 정상 호흡 유지.",
    "lying_apnea_like": "침대/매트에 누운 상태에서 몸과 가슴 움직임을 최소화. 숨을 오래 참지 말고 아주 얕고 작게 호흡.",
    "post_fall_apnea_like": "낙상 후 바닥/매트에 누운 상태처럼 몸 움직임과 호흡 움직임을 매우 작게 유지. 무리한 숨참기 금지.",
    "lying_convulsive_like_movement": "침대/매트에 누운 상태에서 팔/다리/상체를 짧고 불규칙하게 움찔거리거나 떨기. 실제 몸에 무리가 갈 정도로 세게 하지 않기.",
}

START_SOUND = "/System/Library/Sounds/Ping.aiff"
TRIAL_DONE_SOUND = "/System/Library/Sounds/Pop.aiff"
SET_DONE_SOUND = "/System/Library/Sounds/Glass.aiff"


def trial_number(trial: str) -> int:
    if not trial.startswith("t"):
        raise ValueError("trial must look like t001")
    return int(trial[1:])


def trial_name(number: int) -> str:
    return f"t{number:03d}"


def ambient_start_trial(label: str, ambient: str) -> str:
    start = 1
    for item in AMBIENTS:
        if item == ambient:
            return trial_name(start)
        start += PLAN[label][item]
    raise ValueError(f"unknown ambient: {ambient}")


def ambient_end_trial(label: str, ambient: str) -> str:
    start = trial_number(ambient_start_trial(label, ambient))
    count = PLAN[label][ambient]
    return trial_name(start + count - 1)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def append_log(args: argparse.Namespace, start_trial: str, end_trial: str, count: int, status: str) -> None:
    log_dir = repo_root() / "collection_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "team3_ambient_log.csv"
    exists = log_path.exists()

    with open(log_path, "a", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        if not exists:
            writer.writerow([
                "logged_at",
                "subject",
                "label",
                "ambient",
                "trial_start",
                "trial_end",
                "duration_s",
                "repeat",
                "port",
                "status",
                "note",
            ])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            args.subject,
            args.label,
            args.ambient,
            start_trial,
            end_trial,
            PLAN[args.label]["duration"],
            count,
            args.port,
            status,
            args.note,
        ])


def play_sound(sound_path: str, fallback_bells: int = 1) -> None:
    if platform.system() == "Darwin" and Path(sound_path).exists():
        subprocess.run(["afplay", sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    for _ in range(fallback_bells):
        print("\a", end="", flush=True)
        time.sleep(0.15)


def parse_csi_array(value: str) -> list[int]:
    text = value.strip()
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [int(item) for item in parsed]
    except (SyntaxError, ValueError, TypeError):
        pass

    text = text.strip("[]")
    if not text:
        return []
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def parse_raw_line(raw_line: str) -> tuple[int | None, list[int]]:
    try:
        parsed = next(csv.reader([raw_line]))
    except csv.Error:
        return None, []

    if not parsed or parsed[0] != "CSI_DATA":
        return None, []

    rssi = None
    if len(parsed) > 3:
        try:
            rssi = int(parsed[3])
        except ValueError:
            rssi = None

    csi = []
    if parsed:
        try:
            csi = parse_csi_array(parsed[-1])
        except ValueError:
            csi = []

    return rssi, csi


def find_trial_csv(subject: str, label: str, trial: str) -> Path | None:
    filename = f"{subject}_{label}_{trial}.csv"
    matches = list((repo_root() / "data").glob(f"*/*/{label}/{subject}/{filename}"))
    if not matches:
        return None
    return matches[0]


def count_saved_frames(csv_path: Path) -> int:
    with open(csv_path, newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        return sum(1 for _ in reader)


def save_trial_image(csv_path: Path, subject: str, label: str, trial: str, ambient: str) -> Path | None:
    os.environ.setdefault("MPLCONFIGDIR", str(repo_root() / ".matplotlib_cache"))
    (repo_root() / ".matplotlib_cache").mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - only used during local collection
        print(f"[WARN] Could not import matplotlib, image skipped: {exc}")
        return None

    rssi_values: list[int] = []
    mean_abs_values: list[float] = []
    csi_rows: list[list[int]] = []

    with open(csv_path, newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            raw_line = row.get("raw_line", "")
            rssi, csi = parse_raw_line(raw_line)
            if rssi is not None:
                rssi_values.append(rssi)
            if csi:
                mean_abs_values.append(sum(abs(item) for item in csi) / len(csi))
                csi_rows.append(csi)

    if not csi_rows:
        print(f"[WARN] No CSI rows found for image: {csv_path}")
        return None

    max_frames = 300
    step = max(1, len(csi_rows) // max_frames)
    sampled_csi = csi_rows[::step]
    sampled_rssi = rssi_values[::step] if rssi_values else []
    sampled_mean_abs = mean_abs_values[::step]

    out_dir = repo_root() / "visualizations" / label / subject
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{subject}_{label}_{trial}_{ambient}.png"

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True)
    fig.suptitle(f"{subject} | {label} | {trial} | {ambient}", fontsize=14)

    axes[0].plot(sampled_rssi, linewidth=1)
    axes[0].set_title("RSSI over frames")
    axes[0].set_ylabel("RSSI")
    axes[0].grid(True, alpha=0.25)

    axes[1].plot(sampled_mean_abs, linewidth=1, color="#0f766e")
    axes[1].set_title("CSI mean absolute value over frames")
    axes[1].set_ylabel("Mean abs")
    axes[1].grid(True, alpha=0.25)

    heatmap = axes[2].imshow(sampled_csi, aspect="auto", interpolation="nearest", cmap="viridis")
    axes[2].set_title("CSI raw value heatmap")
    axes[2].set_xlabel("CSI index")
    axes[2].set_ylabel("Sampled frame")
    fig.colorbar(heatmap, ax=axes[2], fraction=0.025, pad=0.015)

    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def print_plan(label: str | None = None) -> None:
    labels = [label] if label else PLAN.keys()
    for item in labels:
        plan = PLAN[item]
        total = sum(plan[a] for a in AMBIENTS)
        print(f"\n{item}: duration={plan['duration']}s total={total}")
        for ambient in AMBIENTS:
            print(
                f"  {ambient}: {plan[ambient]} "
                f"({ambient_start_trial(item, ambient)}-{ambient_end_trial(item, ambient)})"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Team 3 NotiFi CSI collection helper.")
    parser.add_argument("--port", help="Receiver serial port, e.g. /dev/cu.usbmodem101 or COM4")
    parser.add_argument("--subject", default=SUBJECT_DEFAULT)
    parser.add_argument("--label", choices=sorted(PLAN.keys()))
    parser.add_argument("--ambient", choices=AMBIENTS)
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--break_sec", type=float, default=1.5)
    parser.add_argument("--repeat-override", type=int, default=None, help="Collect only this many trials from the ambient range.")
    parser.add_argument("--note", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show-plan", action="store_true")
    parser.add_argument("--no-sound", action="store_true")
    parser.add_argument("--no-image", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.show_plan:
        print_plan(args.label)
        return 0

    if not args.port or not args.label or not args.ambient:
        print("ERROR: --port, --label, and --ambient are required unless --show-plan is used.", file=sys.stderr)
        return 2

    plan = PLAN[args.label]
    repeat = plan[args.ambient]
    if args.repeat_override is not None:
        if args.repeat_override <= 0:
            print("ERROR: --repeat-override must be positive.", file=sys.stderr)
            return 2
        if args.repeat_override > repeat:
            print(f"ERROR: --repeat-override cannot exceed planned repeat {repeat}.", file=sys.stderr)
            return 2
        repeat = args.repeat_override
    duration = plan["duration"]
    start_trial = ambient_start_trial(args.label, args.ambient)
    end_trial = trial_name(trial_number(start_trial) + repeat - 1)

    save_script = repo_root() / "scripts" / "save_csi_raw.py"

    print("\n[Team 3 Collection]")
    print(f"subject: {args.subject}")
    print(f"label: {args.label}")
    print(f"ambient: {args.ambient}")
    print(f"duration: {duration}s")
    print(f"repeat: {repeat}")
    print(f"trial range: {start_trial}-{end_trial}")
    print(f"guide: {ACTION_GUIDE[args.label]}")
    print(f"start sound: {Path(START_SOUND).name}")
    print(f"trial done sound: {Path(TRIAL_DONE_SOUND).name}")
    print(f"set done sound: {Path(SET_DONE_SOUND).name}")
    print(f"save image: {'no' if args.no_image else 'yes'}")
    print("\nCommand preview:")
    print(
        f"{sys.executable} {save_script} --port {args.port} --baud {args.baud} "
        f"--subject {args.subject} --label {args.label} --trial {start_trial} "
        f"--duration {duration} --repeat {repeat} --delay {args.delay} --break_sec {args.break_sec}"
    )

    if args.dry_run:
        print("\n[DRY RUN] No collection started.")
        return 0

    current_trial_num = trial_number(start_trial)
    status = "done"
    if args.delay > 0:
        print(f"\n[TEAM3] {args.delay}s before first collection. Leave the room now.")
        for remaining in range(args.delay, 0, -1):
            print(f"[TEAM3] starting in {remaining}s...", end="\r", flush=True)
            time.sleep(1)
        print()

    for index in range(repeat):
        current_trial = trial_name(current_trial_num + index)
        if not args.no_sound:
            play_sound(START_SOUND, fallback_bells=2)

        command = [
            sys.executable,
            str(save_script),
            "--port",
            args.port,
            "--baud",
            str(args.baud),
            "--subject",
            args.subject,
            "--label",
            args.label,
            "--trial",
            current_trial,
            "--duration",
            str(duration),
            "--repeat",
            "1",
            "--delay",
            "0",
            "--break_sec",
            "0",
        ]

        print(f"\n[TEAM3] {args.label}/{args.ambient} {index + 1}/{repeat} ({current_trial})")
        result = subprocess.run(command, cwd=repo_root())
        if result.returncode != 0:
            status = f"failed:{result.returncode}:at:{current_trial}"
            print(f"\n[ERROR] Collection stopped at {current_trial}")
            break

        csv_path = find_trial_csv(args.subject, args.label, current_trial)
        if not csv_path:
            status = f"failed:no_csv:at:{current_trial}"
            print(f"\n[ERROR] CSV not found for {current_trial}")
            break

        saved_frames = count_saved_frames(csv_path)
        print(f"[CHECK] {current_trial}: {saved_frames} CSI_DATA frames")
        if saved_frames <= 0:
            status = f"failed:no_csi_data:at:{current_trial}"
            print(f"\n[ERROR] No CSI_DATA rows saved in {csv_path}")
            print("[ERROR] Stop collection and check receiver port / sender power / CSI_DATA output.")
            break

        if not args.no_sound:
            play_sound(TRIAL_DONE_SOUND, fallback_bells=1)

        if not args.no_image:
            image_path = save_trial_image(csv_path, args.subject, args.label, current_trial, args.ambient)
            if image_path:
                print(f"[IMAGE] {image_path}")

        if index < repeat - 1 and args.break_sec > 0:
            print(f"[TEAM3] {args.break_sec}s break before next trial...")
            time.sleep(args.break_sec)

    if status == "done" and not args.no_sound:
        play_sound(SET_DONE_SOUND, fallback_bells=3)

    append_log(args, start_trial, end_trial, repeat, status)
    print(f"\n[LOG] collection_logs/team3_ambient_log.csv updated: {status}")
    return 0 if status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
