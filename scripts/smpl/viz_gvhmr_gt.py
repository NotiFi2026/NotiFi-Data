"""
viz_gvhmr_gt.py — GVHMR GT(.npz)를 3D 스켈레톤 애니메이션(mp4)으로 시각화

배치(batch_gvhmr.py)는 용량 절약 위해 렌더를 껐으므로, 필요한 것만 골라 이 스크립트로 본다.
GT 의 joints_world (T,22,3, SMPL 22관절) 를 바닥정렬 월드좌표 그대로 그린다. (Y=높이)

사용법 (WSL, gvhmr env):
  python viz_gvhmr_gt.py --uid mhw_E01_20260724_AM0420_bed_exit_failed_t001
  python viz_gvhmr_gt.py --npz /mnt/c/.../gvhmr_gt/xxx_pose_gvhmr.npz --out /mnt/c/.../out.mp4
  python viz_gvhmr_gt.py --uid ... --elev 15 --azim -60 --fps 30
"""
import argparse, os, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# GT(.npz) 는 각 영상 폴더 안에 있음 (batch_gvhmr.py 가 영상 옆에 저장).
# 여기서부터 재귀 검색하고, 시각화 mp4 도 GT 와 같은 폴더에 저장한다.
# 경로는 스크립트 위치 기준 자동 계산 (팀원 repo 경로 달라도 수정 불필요).
_HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_ROOT = os.environ.get(
    "NOTIFI_VIDEO_ROOT",
    os.path.normpath(os.path.join(_HERE, "..", "..", "collection_data", "v2")),
)

# SMPL 22관절 골격 (부모-자식 연결)
BONES = [(0,1),(0,2),(0,3),(1,4),(2,5),(3,6),(4,7),(5,8),(6,9),(7,10),(8,11),
         (9,12),(9,13),(9,14),(12,15),(13,16),(14,17),(16,18),(17,19),(18,20),(19,21)]


def resolve_npz(args):
    if args.npz:
        assert os.path.exists(args.npz), f"npz 없음: {args.npz}"
        return args.npz
    if args.uid:
        cand = glob.glob(os.path.join(VIDEO_ROOT, "**", f"{args.uid}*_pose_gvhmr.npz"), recursive=True)
        assert cand, f"VIDEO_ROOT 하위에서 uid 못찾음: {args.uid}"
        return sorted(cand)[0]
    # 아무것도 없으면 사용 가능한 GT 목록 안내
    files = sorted(glob.glob(os.path.join(VIDEO_ROOT, "**", "*_pose_gvhmr.npz"), recursive=True))
    raise SystemExit("--uid 또는 --npz 를 지정하세요.\n사용 가능한 GT 예시:\n  " +
                     "\n  ".join(os.path.basename(f).replace("_pose_gvhmr.npz","") for f in files[:20]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", help="GT .npz 경로")
    ap.add_argument("--uid", help="GT_ROOT 에서 uid 로 검색")
    ap.add_argument("--out", help="출력 mp4 (기본: GT(.npz) 와 같은 폴더의 <uid>_skeleton3d.mp4)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--elev", type=float, default=10, help="카메라 고도각")
    ap.add_argument("--azim", type=float, default=-70, help="카메라 방위각")
    ap.add_argument("--dpi", type=int, default=80)
    args = ap.parse_args()

    npz = resolve_npz(args)
    d = np.load(npz)
    J = d["joints_world"]                       # (T,22,3)
    T = len(J)
    uid = os.path.basename(npz).replace("_pose_gvhmr.npz", "")

    out = args.out
    if out is None:
        # GT(.npz) 와 같은 폴더에 저장 (영상 옆)
        out = os.path.join(os.path.dirname(npz), f"{uid}_skeleton3d.mp4")

    # 전체 프레임 기준 축 고정 (스켈레톤 튐 방지). 화면축: X, Z(depth), Y(height)
    P = J.reshape(-1, 3)
    xr = (P[:, 0].min(), P[:, 0].max())
    zr = (P[:, 2].min(), P[:, 2].max())
    yr = (min(0.0, P[:, 1].min()), P[:, 1].max())   # 바닥(0) 포함

    fig = plt.figure(figsize=(6, 7))
    ax = fig.add_subplot(111, projection="3d")

    def draw(i):
        ax.clear()
        p = J[i]
        ax.scatter(p[:, 0], p[:, 2], p[:, 1], c="r", s=20)
        for a, b in BONES:
            ax.plot([p[a, 0], p[b, 0]], [p[a, 2], p[b, 2]], [p[a, 1], p[b, 1]], "b-", lw=2)
        ax.set_xlim(*xr); ax.set_ylim(*zr); ax.set_zlim(*yr)
        ax.set_box_aspect((xr[1]-xr[0]+1e-6, zr[1]-zr[0]+1e-6, yr[1]-yr[0]+1e-6))
        ax.set_xlabel("x"); ax.set_ylabel("z(depth)"); ax.set_zlabel("height(m)")
        ax.set_title(f"{uid}\nframe {i}/{T-1}")
        ax.view_init(elev=args.elev, azim=args.azim)

    anim = FuncAnimation(fig, draw, frames=T, interval=1000 / args.fps)
    anim.save(out, fps=args.fps, dpi=args.dpi)
    plt.close()
    print("저장:", out, "| frames:", T, "| 높이범위 %.2f~%.2f m" % (yr[0], yr[1]))


if __name__ == "__main__":
    main()
