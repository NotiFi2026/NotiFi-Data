import argparse
import ast
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path


SUBJECT_DEFAULT = "yja"
LABEL_DEFAULT = "lying_fast_breath"
SOURCE_AMBIENT = "quiet"


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


def parse_csi_array(text: str) -> list[float]:
    text = text.strip()
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [float(item) for item in parsed]
    except (SyntaxError, ValueError, TypeError):
        pass
    values = []
    for item in text.strip("[]").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except ValueError:
            continue
    return values


def parse_raw_line(raw_line: str) -> tuple[list[str], list[float]]:
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


def mean_abs(csi_rows: list[list[float]]) -> float:
    values = [abs(value) for row in csi_rows for value in row]
    return sum(values) / len(values) if values else 1.0


def csi_rows_from(rows: list[dict[str, str]]) -> list[list[float]]:
    csi_rows = []
    for row in rows:
        _, csi = parse_raw_line(row.get("raw_line", ""))
        if csi:
            csi_rows.append(csi)
    return csi_rows


def rssi_values_from(rows: list[dict[str, str]]) -> list[int]:
    values = []
    for row in rows:
        parts, _ = parse_raw_line(row.get("raw_line", ""))
        if len(parts) > 3:
            try:
                values.append(int(parts[3]))
            except ValueError:
                pass
    return values


def per_index_mean(csi_rows: list[list[float]]) -> list[float]:
    if not csi_rows:
        return []
    size = min(len(row) for row in csi_rows)
    return [sum(row[index] for row in csi_rows) / len(csi_rows) for index in range(size)]


def synthesize_rows(
    source_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
    target_trial: str,
    residual_weight: float,
    rng: random.Random,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    source_csi_rows = csi_rows_from(source_rows)
    reference_csi_rows = csi_rows_from(reference_rows)
    if not source_csi_rows or not reference_csi_rows:
        raise ValueError("source or reference rows have no CSI data")

    source_mean_abs = mean_abs(source_csi_rows)
    reference_mean_abs = mean_abs(reference_csi_rows)
    scale = reference_mean_abs / source_mean_abs if source_mean_abs else 1.0
    scale = max(0.75, min(1.75, scale))

    reference_mean_vector = per_index_mean(reference_csi_rows)
    reference_rssi_values = rssi_values_from(reference_rows) or [-68]
    interval_ms = median_interval_ms(source_rows)
    start_ms = int(datetime.now().timestamp() * 1000) + rng.randint(0, 999)
    start_dt = datetime.now() + timedelta(milliseconds=rng.randint(0, 999))

    output = []
    used_rows = 0
    for row_index, row in enumerate(source_rows):
        parts, source_csi = parse_raw_line(row.get("raw_line", ""))
        if not parts or not source_csi:
            continue

        reference_csi = reference_csi_rows[row_index % len(reference_csi_rows)]
        size = min(len(source_csi), len(reference_csi), len(reference_mean_vector))
        new_csi = []
        for index in range(size):
            residual = reference_csi[index] - reference_mean_vector[index]
            value = source_csi[index] * scale + residual * residual_weight
            new_csi.append(int(round(max(-128, min(127, value)))))

        rssi = reference_rssi_values[row_index % len(reference_rssi_values)]
        new_row = dict(row)
        new_row["trial_id"] = target_trial
        new_row["pc_time_ms"] = str(start_ms + row_index * interval_ms)
        new_row["datetime"] = (start_dt + timedelta(milliseconds=row_index * interval_ms)).isoformat(timespec="milliseconds")
        new_row["raw_line"] = format_raw_line(parts, rssi, new_csi)
        output.append(new_row)
        used_rows += 1

    meta = {
        "source_mean_abs": f"{source_mean_abs:.3f}",
        "reference_mean_abs": f"{reference_mean_abs:.3f}",
        "scale": f"{scale:.3f}",
        "residual_weight": f"{residual_weight:.3f}",
        "rows": str(used_rows),
    }
    return output, meta


def append_log(row: dict[str, str]) -> None:
    log_dir = repo_root() / "collection_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "warning_ambient_synthesis_log.csv"
    fields = [
        "created_at",
        "subject",
        "label",
        "source_ambient",
        "target_ambient",
        "source_trial",
        "reference_trial",
        "target_trial",
        "source_file",
        "reference_file",
        "target_file",
        "rows",
        "source_mean_abs",
        "reference_mean_abs",
        "scale",
        "residual_weight",
        "method",
    ]
    exists = log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def save_image(csv_path: Path, subject: str, label: str, trial: str, target_ambient: str) -> str:
    sys.path.insert(0, str(repo_root() / "scripts"))
    try:
        from team3_collect import save_trial_image
    except Exception as exc:
        return f"image_skipped:{exc}"
    image = save_trial_image(csv_path, subject, label, trial, target_ambient)
    return str(image) if image else "image_skipped:no_csi"


def generate(args: argparse.Namespace) -> int:
    root = repo_root()
    data_dir = root / "data" / "warning" / "breathing" / args.label / args.subject
    data_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    created = 0
    for offset in range(args.count):
        source_trial = trial_name(args.source_start + offset)
        reference_trial = trial_name(args.reference_start + (offset % args.reference_count))
        target_trial = trial_name(args.target_start + offset)
        source_path = data_dir / f"{args.subject}_{args.label}_{source_trial}.csv"
        reference_path = data_dir / f"{args.subject}_{args.label}_{reference_trial}.csv"
        target_path = data_dir / f"{args.subject}_{args.label}_{target_trial}.csv"

        if target_path.exists() and not args.overwrite:
            print(f"[SKIP] exists: {target_path}")
            continue
        if not source_path.exists():
            print(f"[SKIP] missing source: {source_path}")
            continue
        if not reference_path.exists():
            print(f"[SKIP] missing reference: {reference_path}")
            continue

        fieldnames, source_rows = read_rows(source_path)
        _, reference_rows = read_rows(reference_path)
        synthetic_rows, meta = synthesize_rows(
            source_rows,
            reference_rows,
            target_trial,
            residual_weight=args.residual_weight,
            rng=rng,
        )

        with target_path.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(synthetic_rows)

        image_status = save_image(target_path, args.subject, args.label, target_trial, args.target_ambient)
        append_log(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "subject": args.subject,
                "label": args.label,
                "source_ambient": SOURCE_AMBIENT,
                "target_ambient": args.target_ambient,
                "source_trial": source_trial,
                "reference_trial": reference_trial,
                "target_trial": target_trial,
                "source_file": str(source_path.relative_to(root)),
                "reference_file": str(reference_path.relative_to(root)),
                "target_file": str(target_path.relative_to(root)),
                "rows": meta["rows"],
                "source_mean_abs": meta["source_mean_abs"],
                "reference_mean_abs": meta["reference_mean_abs"],
                "scale": meta["scale"],
                "residual_weight": meta["residual_weight"],
                "method": f"quiet_scaled_plus_{args.target_ambient}_residual",
            }
        )
        print(
            f"[OK] {source_trial}+{reference_trial} -> {target_trial} "
            f"rows={meta['rows']} scale={meta['scale']} image={image_status}"
        )
        created += 1

    print(f"[DONE] created={created}/{args.count}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthesize warning ambient trials from quiet trials and real ambient references.")
    parser.add_argument("--subject", default=SUBJECT_DEFAULT)
    parser.add_argument("--label", default=LABEL_DEFAULT)
    parser.add_argument("--target-ambient", required=True, choices=["aircon", "tv", "music"])
    parser.add_argument("--source-start", type=int, default=1)
    parser.add_argument("--target-start", type=int, required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--reference-start", type=int, required=True)
    parser.add_argument("--reference-count", type=int, required=True)
    parser.add_argument("--residual-weight", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260624)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(generate(parse_args()))
