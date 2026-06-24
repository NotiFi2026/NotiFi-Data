import argparse
import ast
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path


LABEL_CONFIG = {
    "lying_slow_breath": {
        "domain": "breathing",
        "target_start": 1,
        "target_count": 20,
        "aircon_start": 21,
        "aircon_count": 17,
        "tv_start": 38,
        "tv_count": 17,
    },
    "lying_irregular_breath": {
        "domain": "breathing",
        "target_start": 1,
        "target_count": 20,
        "aircon_start": 21,
        "aircon_count": 17,
        "tv_start": 38,
        "tv_count": 17,
    },
    "bed_exit_failed": {
        "domain": "bed_exit",
        "target_start": 1,
        "target_count": 20,
        "aircon_start": 21,
        "aircon_count": 17,
        "tv_start": 38,
        "tv_count": 17,
    },
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def trial_name(number: int) -> str:
    return f"t{number:03d}"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as file_obj:
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
    return max(1, deltas[len(deltas) // 2])


def parse_csi_array(text: str) -> list[int]:
    try:
        parsed = ast.literal_eval(text.strip())
        if isinstance(parsed, list):
            return [int(float(item)) for item in parsed]
    except (SyntaxError, ValueError, TypeError):
        pass

    values = []
    for item in text.strip().strip("[]").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(float(item)))
        except ValueError:
            continue
    return values


def parse_raw_line(raw_line: str) -> tuple[list[str], list[int]]:
    try:
        parts = next(csv.reader([raw_line]))
    except csv.Error:
        return [], []
    if not parts or parts[0] != "CSI_DATA":
        return parts, []
    return parts, parse_csi_array(parts[-1])


def format_raw_line(parts: list[str], rssi: int, csi: list[int]) -> str:
    new_parts = list(parts)
    if len(new_parts) > 3:
        new_parts[3] = str(rssi)
    new_parts[-1] = "[" + ",".join(str(value) for value in csi) + "]"

    from io import StringIO

    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="")
    writer.writerow(new_parts)
    return buffer.getvalue()


def jitter_csi(values: list[int], rng: random.Random, max_jitter: int) -> list[int]:
    if max_jitter <= 0:
        return list(values)

    output = []
    for value in values:
        if value == 0:
            output.append(0)
        else:
            output.append(max(-128, min(127, value + rng.randint(-max_jitter, max_jitter))))
    return output


def synthesize_rows(
    rows: list[dict[str, str]],
    target_trial: str,
    rng: random.Random,
    max_jitter: int,
) -> list[dict[str, str]]:
    interval_ms = median_interval_ms(rows)
    start_ms = int(datetime.now().timestamp() * 1000) + rng.randint(0, 999)
    start_dt = datetime.now() + timedelta(milliseconds=rng.randint(0, 999))

    output = []
    for row_index, row in enumerate(rows):
        parts, csi = parse_raw_line(row.get("raw_line", ""))
        if not parts or not csi:
            continue
        rssi = int(parts[3]) if len(parts) > 3 and parts[3].lstrip("-").isdigit() else -70
        new_row = dict(row)
        new_row["trial_id"] = target_trial
        new_row["pc_time_ms"] = str(start_ms + row_index * interval_ms)
        new_row["datetime"] = (start_dt + timedelta(milliseconds=row_index * interval_ms)).isoformat(timespec="milliseconds")
        new_row["raw_line"] = format_raw_line(parts, rssi, jitter_csi(csi, rng, max_jitter))
        output.append(new_row)
    return output


def build_balanced_sources(config: dict[str, int]) -> list[tuple[str, int]]:
    aircon = [("aircon", config["aircon_start"] + i) for i in range(config["aircon_count"])]
    tv = [("tv", config["tv_start"] + i) for i in range(config["tv_count"])]
    sources = []
    for index in range(max(len(aircon), len(tv))):
        if index < len(aircon):
            sources.append(aircon[index])
        if index < len(tv):
            sources.append(tv[index])
    return sources


def label_data_dir(root: Path, label: str, subject: str) -> Path:
    return root / "data" / "warning" / LABEL_CONFIG[label]["domain"] / label / subject


def save_image(csv_path: Path, subject: str, label: str, trial: str) -> str:
    sys.path.insert(0, str(repo_root() / "scripts"))
    try:
        from team3_collect import save_trial_image
    except Exception as exc:
        return f"image_skipped:{exc}"
    image = save_trial_image(csv_path, subject, label, trial, "quiet")
    return str(image) if image else "image_skipped:no_csi"


def append_log(row: dict[str, str]) -> None:
    log_dir = repo_root() / "collection_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "warning_quiet_from_collected_synthesis_log.csv"
    fields = [
        "created_at",
        "subject",
        "label",
        "source_ambient",
        "target_ambient",
        "source_trial",
        "target_trial",
        "source_file",
        "target_file",
        "rows",
        "max_jitter",
        "method",
    ]
    exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def generate_label(args: argparse.Namespace, label: str) -> tuple[int, int]:
    root = repo_root()
    config = LABEL_CONFIG[label]
    data_dir = label_data_dir(root, label, args.subject)
    sources = build_balanced_sources(config)

    created = 0
    skipped = 0
    rng = random.Random(args.seed + sum(ord(ch) for ch in label))
    for offset in range(config["target_count"]):
        source_ambient, source_number = sources[offset % len(sources)]
        source_trial = trial_name(source_number)
        target_trial = trial_name(config["target_start"] + offset)
        source_path = data_dir / f"{args.subject}_{label}_{source_trial}.csv"
        target_path = data_dir / f"{args.subject}_{label}_{target_trial}.csv"

        if target_path.exists() and not args.overwrite:
            print(f"[SKIP] exists: {target_path}")
            skipped += 1
            continue
        if not source_path.exists():
            print(f"[SKIP] missing source: {source_path}")
            skipped += 1
            continue

        fieldnames, source_rows = read_rows(source_path)
        synthetic_rows = synthesize_rows(source_rows, target_trial, rng, args.max_jitter)
        with target_path.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(synthetic_rows)

        image_status = save_image(target_path, args.subject, label, target_trial)
        append_log(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "subject": args.subject,
                "label": label,
                "source_ambient": source_ambient,
                "target_ambient": "quiet",
                "source_trial": source_trial,
                "target_trial": target_trial,
                "source_file": str(source_path.relative_to(root)),
                "target_file": str(target_path.relative_to(root)),
                "rows": str(len(synthetic_rows)),
                "max_jitter": str(args.max_jitter),
                "method": "collected_aircon_tv_rows_with_small_csi_jitter_to_quiet",
            }
        )
        print(f"[OK] {label}: {source_ambient} {source_trial} -> quiet {target_trial} rows={len(synthetic_rows)} image={image_status}")
        created += 1
    return created, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill missing warning quiet trials from collected aircon/tv trials.")
    parser.add_argument("--subject", default="yja")
    parser.add_argument(
        "--label",
        action="append",
        choices=sorted(LABEL_CONFIG),
        help="Label to synthesize. Repeat for multiple labels. Default: all missing quiet labels.",
    )
    parser.add_argument("--max-jitter", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260625)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    labels = args.label or ["lying_slow_breath", "lying_irregular_breath", "bed_exit_failed"]

    total_created = 0
    total_skipped = 0
    for label in labels:
        created, skipped = generate_label(args, label)
        total_created += created
        total_skipped += skipped
    print(f"[DONE] created={total_created} skipped={total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
