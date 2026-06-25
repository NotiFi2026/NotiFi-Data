"""
Dataset split script: 7:1.5:1.5 (train:val:test)

Per-person shuffle (seed=42) → split → merge into train/val/test folders.
lmh/mhw/yja subfolder structure is removed in the output.
"""

import random
import shutil
from pathlib import Path

SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
PERSONS = ["lmh", "mhw", "yja"]

DATA_ROOT = Path(__file__).parent.parent / "data"
OUTPUT_ROOT = Path(__file__).parent.parent / "split_data"

# Classes without person subfolders — create empty dirs only
EMPTY_CLASSES = [
    "danger/fall/walking_trip_fall",
    "danger/fall/walking_turn_fall",
    "danger/post_fall/post_walking_fall_inactive",
]


def split_files(files: list[Path], seed: int) -> tuple[list, list, list]:
    rng = random.Random(seed)
    files = list(files)
    rng.shuffle(files)
    n = len(files)
    n_train = round(n * TRAIN_RATIO)
    n_val = round(n * VAL_RATIO)
    return files[:n_train], files[n_train:n_train + n_val], files[n_train + n_val:]


def copy_files(files: list[Path], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, dest / f.name)


def main():
    # Create empty dirs for special cases
    for rel_class in EMPTY_CLASSES:
        for split in ("train", "val", "test"):
            (OUTPUT_ROOT / split / Path(rel_class)).mkdir(parents=True, exist_ok=True)
        print(f"[EMPTY] {rel_class}")

    # Find all class dirs that have person subfolders
    class_dirs = []
    for d in sorted(DATA_ROOT.rglob("*")):
        if not d.is_dir():
            continue
        children = [c.name for c in d.iterdir() if c.is_dir()]
        if any(p in children for p in PERSONS):
            class_dirs.append(d)

    for class_dir in class_dirs:
        rel = class_dir.relative_to(DATA_ROOT)

        train_all, val_all, test_all = [], [], []
        for person in PERSONS:
            person_dir = class_dir / person
            if not person_dir.exists():
                continue
            files = sorted(f for f in person_dir.iterdir() if f.is_file())
            tr, va, te = split_files(files, SEED)
            train_all.extend(tr)
            val_all.extend(va)
            test_all.extend(te)

        copy_files(train_all, OUTPUT_ROOT / "train" / rel)
        copy_files(val_all,   OUTPUT_ROOT / "val"   / rel)
        copy_files(test_all,  OUTPUT_ROOT / "test"  / rel)

        print(
            f"[OK] {str(rel):<60} "
            f"train={len(train_all):>3}  val={len(val_all):>3}  test={len(test_all):>3}  "
            f"total={len(train_all)+len(val_all)+len(test_all):>3}"
        )

    print(f"\nDone. Output → {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
