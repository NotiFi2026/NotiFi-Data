import argparse
import ast
import csv
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path


SUBJECT_DEFAULT = "yja"
AMBIENTS = ["quiet", "aircon", "tv", "music"]

SOURCE_PLAN = {
    "bed_sitting_to_stand_fall": {"quiet": 8, "aircon": 7, "tv": 6, "music": 5},
    "bed_lying_to_stand_fall": {"quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "bed_stand_to_lie_fall": {"quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "chair_sitting_to_stand_fall": {"quiet": 8, "aircon": 7, "tv": 6, "music": 5},
    "chair_stand_to_sit_fall": {"quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "walking_trip_fall": {"quiet": 8, "aircon": 7, "tv": 7, "music": 5},
    "walking_turn_fall": {"quiet": 8, "aircon": 7, "tv": 6, "music": 5},
}

TARGET_PLAN = {
    "post_bed_fall_inactive": {
        "sources": ["bed_sitting_to_stand_fall", "bed_lying_to_stand_fall", "bed_stand_to_lie_fall"],
        "quiet": 8,
        "aircon": 7,
        "tv": 7,
        "music": 5,
    },
    "post_chair_fall_inactive": {
        "sources": ["chair_sitting_to_stand_fall", "chair_stand_to_sit_fall"],
        "quiet": 8,
        "aircon": 7,
        "tv": 7,
        "music": 5,
    },
    "post_walking_fall_inactive": {
        "sources": ["walking_trip_fall", "walking_turn_fall"],
        "quiet": 8,
        "aircon": 7,
        "tv": 6,
        "music": 5,
    },
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def trial_name(number: int) -> str:
    return f"t{number:03d}"


def ambient_start_trial(label: str, ambient: str, plan: dict) -> int:
    start = 1
    for item in AMBIENTS:
        if item == ambient:
            return start
        start += plan[label][item]
    raise ValueError(f"unknown ambient: {ambient}")


def ambient_for_source_trial(label: str, trial_num: int) -> str | None:
    start = 1
    for ambient in AMBIENTS:
        end = start + SOURCE_PLAN[label][ambient] - 1
        if start <= trial_num <= end:
            return ambient
        start = end + 1
    return None


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        return list(reader.fieldnames or []), list(reader)


def median_interval_ms(rows: list[dict[str, str]]) -> int:
    times = []
    for row in rows:
        try:
            times.append(int(row["pc_time_ms"]))
        except (KeyError, ValueError):
            continue
    deltas = [b - a for a, b in zip(times, times[1:]) if 0 < b - a < 1000]
    if not deltas:
        return 10
    deltas.sort()
    return max(1, int(deltas[len(deltas) // 2]))


def first_datetime(rows: list[dict[str, str]]) -> datetime:
    if rows:
        text = rows[0].get("datetime", "")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
    return datetime.now()


def parse_csi_array(value: str) -> list[float]:
    text = value.strip()
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [float(item) for item in parsed]
    except (SyntaxError, ValueError, TypeError):
        pass

    values: list[float] = []
    for item in text.strip("[]").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except ValueError:
            continue
    return values


def parse_raw_csi(raw_line: str) -> list[float]:
    try:
        parts = next(csv.reader([raw_line]))
    except csv.Error:
        return []
    if not parts or parts[0] != "CSI_DATA":
        return []
    return parse_csi_array(parts[-1])


def mean_abs(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.mean(abs(value) for value in values)


def frame_diff(left: list[float], right: list[float]) -> float | None:
    size = min(len(left), len(right))
    if size == 0:
        return None
    return statistics.mean(abs(right[index] - left[index]) for index in range(size))


def tail_quality(
    rows: list[dict[str, str]],
    tail_start: int,
    tail_len: int,
) -> tuple[float, float]:
    csi_rows = [parse_raw_csi(row.get("raw_line", "")) for row in rows]
    full_mags = [mean_abs(row) for row in csi_rows]
    full_mags = [value for value in full_mags if value is not None]
    full_diffs = [frame_diff(left, right) for left, right in zip(csi_rows, csi_rows[1:])]
    full_diffs = [value for value in full_diffs if value is not None]

    tail_rows = csi_rows[tail_start:tail_start + tail_len]
    tail_mags = [mean_abs(row) for row in tail_rows]
    tail_mags = [value for value in tail_mags if value is not None]
    tail_diffs = [frame_diff(left, right) for left, right in zip(tail_rows, tail_rows[1:])]
    tail_diffs = [value for value in tail_diffs if value is not None]

    full_diff_mean = statistics.mean(full_diffs) if full_diffs else 0
    tail_diff_mean = statistics.mean(tail_diffs) if tail_diffs else 0
    full_mag_std = statistics.pstdev(full_mags) if len(full_mags) > 1 else 0
    tail_mag_std = statistics.pstdev(tail_mags) if len(tail_mags) > 1 else 0

    diff_ratio = tail_diff_mean / full_diff_mean if full_diff_mean else 0
    std_ratio = tail_mag_std / full_mag_std if full_mag_std else 0
    return diff_ratio, std_ratio


def find_tail_window(
    rows: list[dict[str, str]],
    tail_len: int,
    search_frames: int,
    diff_threshold: float,
    std_threshold: float,
) -> tuple[int, float, float, bool]:
    frame_count = len(rows)
    latest_start = max(0, frame_count - tail_len)
    earliest_start = max(0, latest_start - search_frames)
    best = (latest_start, float("inf"), float("inf"), False)

    for tail_start in range(latest_start, earliest_start - 1, -1):
        diff_ratio, std_ratio = tail_quality(rows, tail_start, tail_len)
        if diff_ratio <= diff_threshold and std_ratio <= std_threshold:
            return tail_start, diff_ratio, std_ratio, True
        if max(diff_ratio, std_ratio) < max(best[1], best[2]):
            best = (tail_start, diff_ratio, std_ratio, False)

    return best


def extend_rows(
    rows: list[dict[str, str]],
    target_label: str,
    target_trial: str,
    tail_seconds: float,
    tail_start: int,
    tail_len: int,
    source_duration: float,
    target_duration: float,
) -> tuple[list[dict[str, str]], int]:
    if not rows:
        raise ValueError("source has no rows")

    interval_ms = median_interval_ms(rows)
    tail_rows = rows[tail_start:tail_start + tail_len]
    target_span_ms = int(target_duration * 1000)

    output_rows = []
    synthetic_time = first_datetime(rows)
    try:
        synthetic_ms = int(rows[0]["pc_time_ms"])
    except (KeyError, ValueError):
        synthetic_ms = int(synthetic_time.timestamp() * 1000)

    def rewrite(row: dict[str, str], index: int) -> dict[str, str]:
        new_row = dict(row)
        current_ms = synthetic_ms + index * interval_ms
        current_dt = synthetic_time + timedelta(milliseconds=index * interval_ms)
        new_row["pc_time_ms"] = str(current_ms)
        new_row["datetime"] = current_dt.isoformat(timespec="milliseconds")
        new_row["risk"] = "danger"
        new_row["domain"] = "post_fall"
        new_row["label"] = target_label
        new_row["trial_id"] = target_trial
        return new_row

    index = 0
    for row in rows:
        output_rows.append(rewrite(row, index))
        index += 1

    while (index - 1) * interval_ms < target_span_ms:
        for row in tail_rows:
            if (index - 1) * interval_ms >= target_span_ms:
                break
            output_rows.append(rewrite(row, index))
            index += 1

    return output_rows, tail_len


def collect_source_files_by_label(subject: str, target_label: str, ambient: str) -> dict[str, list[Path]]:
    root = repo_root()
    files_by_label: dict[str, list[Path]] = {}
    for source_label in TARGET_PLAN[target_label]["sources"]:
        source_dir = root / "data" / "danger" / "fall" / source_label / subject
        files_by_label[source_label] = []
        for path in sorted(source_dir.glob(f"{subject}_{source_label}_t*.csv")):
            try:
                trial_num = int(path.stem.rsplit("_t", 1)[1])
            except (IndexError, ValueError):
                continue
            if ambient_for_source_trial(source_label, trial_num) == ambient:
                files_by_label[source_label].append(path)
    return files_by_label


def round_robin_sources(files_by_label: dict[str, list[Path]], target_count: int) -> list[Path]:
    selected: list[Path] = []
    labels = list(files_by_label)
    index = 0
    while len(selected) < target_count:
        added = False
        for label in labels:
            files = files_by_label[label]
            if index < len(files):
                selected.append(files[index])
                added = True
                if len(selected) == target_count:
                    break
        if not added:
            break
        index += 1
    return selected


def save_image_if_possible(csv_path: Path, subject: str, label: str, trial: str, ambient: str) -> str:
    try:
        from team3_collect import save_trial_image
    except Exception as exc:
        return f"image_skipped:{exc}"

    image_path = save_trial_image(csv_path, subject, label, trial, ambient)
    return str(image_path) if image_path else "image_skipped:no_csi"


def append_log(row: dict[str, str]) -> None:
    log_dir = repo_root() / "collection_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "post_fall_augmentation_log.csv"
    exists = log_path.exists()
    fields = [
        "created_at",
        "subject",
        "target_label",
        "ambient",
        "target_trial",
        "source_file",
        "source_rows",
        "output_rows",
        "output_duration_sec",
        "tail_seconds",
        "tail_frames",
        "tail_start_frame",
        "tail_diff_ratio",
        "tail_std_ratio",
        "tail_quality",
        "method",
    ]
    with open(log_path, "a", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def generate(args: argparse.Namespace) -> int:
    if args.label not in TARGET_PLAN:
        raise ValueError(f"unknown target label: {args.label}")
    if args.ambient not in AMBIENTS:
        raise ValueError(f"unknown ambient: {args.ambient}")

    root = repo_root()
    target_count = TARGET_PLAN[args.label][args.ambient]
    start_trial = ambient_start_trial(args.label, args.ambient, TARGET_PLAN)
    source_files_by_label = collect_source_files_by_label(args.subject, args.label, args.ambient)
    source_count = sum(len(files) for files in source_files_by_label.values())

    if source_count < target_count:
        print(
            f"[SKIP] {args.label}/{args.ambient}: source files {source_count} "
            f"< target count {target_count}"
        )
        return 2

    out_dir = root / "data" / "danger" / "post_fall" / args.label / args.subject
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    created = 0
    selected_sources = round_robin_sources(source_files_by_label, target_count)
    for index, source_path in enumerate(selected_sources):
        trial = trial_name(start_trial + index)
        out_path = out_dir / f"{args.subject}_{args.label}_{trial}.csv"
        if out_path.exists() and not args.overwrite:
            print(f"[SKIP] exists: {out_path}")
            continue

        fieldnames, rows = read_rows(source_path)
        if not fieldnames or not rows:
            print(f"[SKIP] empty source: {source_path}")
            continue

        tail_seconds = rng.uniform(args.tail_min, args.tail_max)
        interval_ms = median_interval_ms(rows)
        fps = 1000 / interval_ms
        tail_len = max(1, min(len(rows), round(fps * tail_seconds)))
        search_frames = max(0, round(fps * args.tail_search_seconds))
        if args.tail_quality == "off":
            tail_start = max(0, len(rows) - tail_len)
            diff_ratio, std_ratio = tail_quality(rows, tail_start, tail_len)
            tail_ok = True
        else:
            tail_start, diff_ratio, std_ratio, tail_ok = find_tail_window(
                rows,
                tail_len,
                search_frames,
                args.tail_diff_ratio_threshold,
                args.tail_std_ratio_threshold,
            )
        if args.tail_quality == "skip" and not tail_ok:
            print(
                f"[SKIP] unstable tail: {source_path} "
                f"diff_ratio={diff_ratio:.3f} std_ratio={std_ratio:.3f}"
            )
            continue
        if args.tail_quality == "warn" and not tail_ok:
            print(
                f"[WARN] using unstable tail: {source_path} "
                f"diff_ratio={diff_ratio:.3f} std_ratio={std_ratio:.3f}"
            )

        output_rows, tail_frames = extend_rows(
            rows,
            target_label=args.label,
            target_trial=trial,
            tail_seconds=tail_seconds,
            tail_start=tail_start,
            tail_len=tail_len,
            source_duration=args.source_duration,
            target_duration=args.target_duration,
        )

        with open(out_path, "w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        image_status = save_image_if_possible(out_path, args.subject, args.label, trial, args.ambient)
        append_log(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "subject": args.subject,
                "target_label": args.label,
                "ambient": args.ambient,
                "target_trial": trial,
                "source_file": str(source_path.relative_to(root)),
                "source_rows": str(len(rows)),
                "output_rows": str(len(output_rows)),
                "output_duration_sec": f"{(len(output_rows) - 1) * median_interval_ms(output_rows) / 1000:.3f}",
                "tail_seconds": f"{tail_seconds:.3f}",
                "tail_frames": str(tail_frames),
                "tail_start_frame": str(tail_start),
                "tail_diff_ratio": f"{diff_ratio:.3f}",
                "tail_std_ratio": f"{std_ratio:.3f}",
                "tail_quality": "ok" if tail_ok else args.tail_quality,
                "method": "fall_10s_plus_repeated_tail_to_20s",
            }
        )
        print(f"[OK] {out_path} rows={len(output_rows)} image={image_status}")
        created += 1

    print(f"[DONE] created={created}/{target_count} for {args.label}/{args.ambient}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create post-fall inactive CSVs from 10s fall trials.")
    parser.add_argument("--subject", default=SUBJECT_DEFAULT)
    parser.add_argument("--label", required=True, choices=sorted(TARGET_PLAN.keys()))
    parser.add_argument("--ambient", required=True, choices=AMBIENTS)
    parser.add_argument("--tail-min", type=float, default=1.5)
    parser.add_argument("--tail-max", type=float, default=3.0)
    parser.add_argument("--tail-quality", choices=["off", "warn", "skip"], default="warn")
    parser.add_argument("--tail-search-seconds", type=float, default=4.0)
    parser.add_argument("--tail-diff-ratio-threshold", type=float, default=1.35)
    parser.add_argument("--tail-std-ratio-threshold", type=float, default=1.35)
    parser.add_argument("--source-duration", type=float, default=10.0)
    parser.add_argument("--target-duration", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=20260623)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(generate(parse_args()))
