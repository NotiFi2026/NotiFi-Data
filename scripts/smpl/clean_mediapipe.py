"""
clean_mediapipe.py — mediapipe 산출물 3종 일괄 삭제 (GVHMR 전환 후 용량 확보용)

삭제 대상 (각 trial 폴더):
  *_pose_overlay.mp4  (mediapipe 오버레이 영상, 용량 대부분)   [기본 삭제]
  *_pose_qc.json      (mediapipe 포즈 QC)                      [기본 삭제]
  *_pose13.csv        (구 teacher GT) — 기본 유지. --include-pose13 로만 삭제
                      (GVHMR vs mediapipe 비교 baseline 으로 남겨두는 걸 권장)

기본은 DRY-RUN(목록·용량만 표시, 안 지움). 실제 삭제하려면 --apply.
GVHMR 산출물(_pose_gvhmr.npz / _skeleton3d.mp4 / _overlay3d.mp4)과
원본·CSI·meta·checksum 은 건드리지 않음.

사용법:
  python clean_mediapipe.py                       # DRY-RUN (overlay+qc)
  python clean_mediapipe.py --apply               # overlay+qc 실제 삭제
  python clean_mediapipe.py --include-pose13 --apply   # pose13 까지 삭제
  python clean_mediapipe.py --root <경로>         # 대상 루트 변경
"""
import os, glob, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "collection_data", "v2"))
BASE_PATTERNS = ["*_pose_overlay.mp4", "*_pose_qc.json"]
POSE13_PATTERN = "*_pose13.csv"


def human(n):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT, help="탐색 루트 (기본: collection_data/v2)")
    ap.add_argument("--apply", action="store_true", help="실제 삭제 (없으면 DRY-RUN)")
    ap.add_argument("--include-pose13", action="store_true", help="pose13.csv 도 삭제 (기본은 유지)")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        raise SystemExit(f"루트 없음: {args.root}")

    patterns = list(BASE_PATTERNS)
    if args.include_pose13:
        patterns.append(POSE13_PATTERN)
    else:
        print("[유지] *_pose13.csv 는 baseline 으로 남겨둠 (--include-pose13 로 포함 가능)")

    print(f"루트: {args.root}")
    print(f"모드: {'실제 삭제(--apply)' if args.apply else 'DRY-RUN (안 지움)'}\n")

    grand_n = grand_sz = 0
    for pat in patterns:
        files = glob.glob(os.path.join(args.root, "**", pat), recursive=True)
        sz = sum(os.path.getsize(f) for f in files)
        grand_n += len(files); grand_sz += sz
        print(f"  {pat:20s}: {len(files):5d}개  {human(sz)}")

    print(f"\n  합계: {grand_n}개  {human(grand_sz)}")

    if not args.apply:
        print("\n[DRY-RUN] 실제로는 아무것도 안 지웠어요. 지우려면 --apply 붙이세요.")
        sample = glob.glob(os.path.join(args.root, "**", patterns[0]), recursive=True)[:3]
        if sample:
            print("예시 대상:")
            for s in sample:
                print("  ", s)
        return

    deleted_n = deleted_sz = 0
    for pat in patterns:
        for f in glob.glob(os.path.join(args.root, "**", pat), recursive=True):
            try:
                s = os.path.getsize(f)
                os.remove(f)
                deleted_n += 1; deleted_sz += s
            except OSError as e:
                print("  삭제 실패:", f, e)
    print(f"\n[완료] {deleted_n}개 삭제, {human(deleted_sz)} 확보")


if __name__ == "__main__":
    main()
