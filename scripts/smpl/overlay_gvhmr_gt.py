"""
overlay_gvhmr_gt.py — GVHMR 복원 결과를 원본 영상 위에 2D 오버레이 (검수용)

skeleton3d.mp4(허공 3D)와 달리, incam(카메라시점) 관절을 카메라 K로 2D 투영해
원본 프레임 위에 골격을 그린다. "복원이 실제 사람 동작과 맞나" 확인용.
※ 이 영상은 검수 전용 — 학습엔 .npz(joints_world) 숫자만 사용됨.

방식: hmr4d_results.pt 의 smpl_params_incam + K_fullimg 사용 (pytorch3d 렌더 불필요).
      .pt 가 없으면 demo_gt.py 를 자동 실행해 생성.

사용법 (WSL, gvhmr env, cd ~/GVHMR 권장):
  python scripts/smpl/overlay_gvhmr_gt.py --uid mhw_E01_20260724_AM0420_bed_exit_failed_t001
  python overlay_gvhmr_gt.py --video /mnt/c/.../xxx_video.mp4 [--out /mnt/c/.../out.mp4]
"""
import argparse, os, sys, glob, subprocess
import numpy as np
import torch
import cv2
import smplx

GVHMR_ROOT = os.path.expanduser("~/GVHMR")
_HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_ROOT = os.environ.get(
    "NOTIFI_VIDEO_ROOT",
    os.path.normpath(os.path.join(_HERE, "..", "..", "collection_data", "v2")),
)
BODY_MODELS = os.path.join(GVHMR_ROOT, "inputs", "checkpoints", "body_models")

# SMPL 22관절 골격
BONES = [(0,1),(0,2),(0,3),(1,4),(2,5),(3,6),(4,7),(5,8),(6,9),(7,10),(8,11),
         (9,12),(9,13),(9,14),(12,15),(13,16),(14,17),(16,18),(17,19),(18,20),(19,21)]


def resolve_video(args):
    if args.video:
        assert os.path.exists(args.video), f"영상 없음: {args.video}"
        return args.video
    if args.uid:
        cand = glob.glob(os.path.join(VIDEO_ROOT, "**", f"{args.uid}*_video.mp4"), recursive=True)
        assert cand, f"VIDEO_ROOT 하위에서 uid 못찾음: {args.uid}"
        return sorted(cand)[0]
    raise SystemExit("--uid 또는 --video 를 지정하세요.")


def ensure_pt(video_path):
    """outputs/demo/<stem>/hmr4d_results.pt 확보 (없으면 demo_gt.py 실행). (pt_path, input_video) 반환."""
    stem = os.path.basename(video_path)[:-4]
    outdir = os.path.join(GVHMR_ROOT, "outputs", "demo", stem)
    pt = os.path.join(outdir, "hmr4d_results.pt")
    inp = os.path.join(outdir, "0_input_video.mp4")
    if not os.path.exists(pt):
        print("[overlay] .pt 없음 → demo_gt.py 실행")
        r = subprocess.run(["python", "tools/demo/demo_gt.py", "--video", video_path, "-s"],
                           cwd=GVHMR_ROOT)
        assert r.returncode == 0, "demo_gt.py 실패"
    assert os.path.exists(pt), f"pt 생성 실패: {pt}"
    if not os.path.exists(inp):
        inp = video_path  # fallback: 원본 (프레임수/타이밍 다를 수 있음)
    return pt, inp


def incam_joints_2d(pt_path):
    """smpl_params_incam -> 카메라좌표 관절 -> K 로 2D 투영. (T,22,2) uv, (T,22) Z 반환."""
    res = torch.load(pt_path, map_location="cpu", weights_only=False)
    g = res["smpl_params_incam"]
    K = res["K_fullimg"]                       # (T,3,3) or (3,3)
    if K.dim() == 2:
        K = K[None]
    T = g["transl"].shape[0]
    betas = g["betas"]; betas = betas[None].repeat(T, 1) if betas.dim() == 1 else betas
    model = smplx.create(BODY_MODELS, model_type="smplx", gender="neutral",
                         use_pca=False, batch_size=T)
    with torch.no_grad():
        out = model(body_pose=g["body_pose"][:, :63], global_orient=g["global_orient"],
                    betas=betas[:, :10], transl=g["transl"])
    Jc = out.joints[:, :22, :].numpy()         # (T,22,3) 카메라좌표
    Kf = K.numpy()
    if Kf.shape[0] == 1:
        Kf = np.repeat(Kf, T, axis=0)
    uv = np.zeros((T, 22, 2), np.float32)
    Z = Jc[:, :, 2]
    for t in range(T):
        proj = (Kf[t] @ Jc[t].T).T             # (22,3)
        uv[t, :, 0] = proj[:, 0] / proj[:, 2]
        uv[t, :, 1] = proj[:, 1] / proj[:, 2]
    return uv, Z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid"); ap.add_argument("--video"); ap.add_argument("--out")
    ap.add_argument("--keep_tmp", action="store_true", help="outputs/demo 산출물 보존")
    args = ap.parse_args()
    os.chdir(GVHMR_ROOT)

    video_path = resolve_video(args)
    uid = os.path.basename(video_path).replace("_video.mp4", "")
    pt, inp = ensure_pt(video_path)
    uv, Z = incam_joints_2d(pt)
    T = len(uv)

    out = args.out or os.path.join(os.path.dirname(video_path), f"{uid}_overlay3d.mp4")

    cap = cv2.VideoCapture(inp)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    wr = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i < T:
            p = uv[i]
            for a, b in BONES:
                if Z[i, a] > 0 and Z[i, b] > 0:
                    cv2.line(fr, tuple(p[a].astype(int)), tuple(p[b].astype(int)), (0, 255, 0), 2)
            for j in range(22):
                if Z[i, j] > 0:
                    cv2.circle(fr, tuple(p[j].astype(int)), 4, (0, 0, 255), -1)
        wr.write(fr); i += 1
    cap.release(); wr.release()

    if not args.keep_tmp:
        import shutil
        shutil.rmtree(os.path.join(GVHMR_ROOT, "outputs", "demo", os.path.basename(video_path)[:-4]),
                      ignore_errors=True)
    print("저장:", out, "| frames:", i, "| overlay 관절수: 22")


if __name__ == "__main__":
    main()
