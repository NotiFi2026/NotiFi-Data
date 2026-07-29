"""
batch_gvhmr.py — GVHMR 로컬 일괄 처리 (RTX 3060 등 GPU 컴퓨터용)

영상들을 GVHMR으로 돌려 3D 관절 GT(.npz)를 만든다.
- 이어하기(resumable): 이미 만든 GT는 SKIP → 세션/재부팅으로 끊겨도 다시 실행하면 이어짐
- Colab 전용 코드(drive.mount / /content / 버전 패치) 전부 제거
- 파이썬 3.10 + torch 2.3.0 클린 설치면 별도 패치 불필요

사용법(WSL2/Linux 예):
    conda activate gvhmr
    cd ~/GVHMR
    nohup python /path/to/batch_gvhmr.py > ~/batch.log 2>&1 &
    tail -f ~/batch.log

경로 3개만 본인 환경에 맞게 수정하세요 → CONFIG 섹션.
"""
import os
import glob
import subprocess
import numpy as np
import torch
import smplx

# ============================ CONFIG (여기만 수정) ============================
# GVHMR 설치 폴더
GVHMR_ROOT = os.path.expanduser("~/GVHMR")

# 처리할 영상들이 있는 최상위 폴더 (하위까지 재귀 탐색해서 *_video.mp4 를 모두 찾음)
#   스크립트 위치 기준 자동 계산 (팀원 repo 경로 달라도 수정 불필요).
#   필요시 환경변수 NOTIFI_VIDEO_ROOT 로 덮어쓰기.
_HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_ROOT = os.environ.get(
    "NOTIFI_VIDEO_ROOT",
    os.path.normpath(os.path.join(_HERE, "..", "..", "collection_data", "v2")),
)

# 결과 GT(.npz) 는 각 영상과 같은 폴더에 저장됨 (영상 옆 _pose_overlay.mp4 처럼).
#   예: .../bed_exit_failed_t001/mhw_..._t001_video.mp4
#       .../bed_exit_failed_t001/mhw_..._t001_pose_gvhmr.npz  ← 여기

# GVHMR 실행 중간 산출물(렌더 영상·전처리 캐시) 삭제해서 디스크 절약
DELETE_TMP = True

# GVHMR 인체모델 폴더 (보통 그대로)
BODY_MODELS = os.path.join(GVHMR_ROOT, "inputs", "checkpoints", "body_models")
# ============================================================================


def video_to_uid(video_path: str) -> str:
    """mhw_..._t001_video.mp4 -> mhw_..._t001"""
    return os.path.basename(video_path).replace("_video.mp4", "")


def extract_joints(pt_path: str):
    """hmr4d_results.pt -> 월드 3D 관절 (T, 22, 3) + 골반 위치(transl)."""
    res = torch.load(pt_path, map_location="cpu", weights_only=False)
    g = res["smpl_params_global"]
    T = g["transl"].shape[0]
    betas = g["betas"]
    betas = betas[None].repeat(T, 1) if betas.dim() == 1 else betas
    model = smplx.create(
        BODY_MODELS, model_type="smplx", gender="neutral",
        use_pca=False, batch_size=T,
    )
    with torch.no_grad():
        out = model(
            body_pose=g["body_pose"][:, :63],
            global_orient=g["global_orient"],
            betas=betas[:, :10],
            transl=g["transl"],
        )
    joints = out.joints.numpy()[:, :22, :]      # (T, 22, 3)
    transl = g["transl"].numpy()                # (T, 3)  골반 위치(높이 포함)
    return joints, transl


def main():
    videos = sorted(glob.glob(os.path.join(VIDEO_ROOT, "**", "*_video.mp4"), recursive=True))
    print(f"총 영상: {len(videos)}개")
    print(f"GT 저장: 각 영상과 같은 폴더에 <uid>_pose_gvhmr.npz\n")

    done = skipped = failed = 0
    for i, vid in enumerate(videos, 1):
        uid = video_to_uid(vid)
        # GT 는 영상과 같은 폴더에 저장 (영상 옆)
        out_npz = os.path.join(os.path.dirname(vid), f"{uid}_pose_gvhmr.npz")

        if os.path.exists(out_npz):
            skipped += 1
            print(f"[{i}/{len(videos)}] SKIP {uid}")
            continue

        print(f"[{i}/{len(videos)}] RUN  {uid}")

        # 1) GVHMR 실행 (-s = static_cam: 고정 카메라라 SLAM 생략)
        #    demo_gt.py = demo.py 에서 렌더 호출만 제거한 GT 전용 버전 (시간 절약)
        r = subprocess.run(
            ["python", "tools/demo/demo_gt.py", "--video", vid, "-s"],
            cwd=GVHMR_ROOT,
        )
        if r.returncode != 0:
            failed += 1
            print(f"    demo 실패 → 건너뜀: {uid}")
            continue

        # 2) .pt -> 3D 관절 -> npz
        outdir = os.path.join(GVHMR_ROOT, "outputs", "demo", os.path.basename(vid)[:-4])
        pt_path = os.path.join(outdir, "hmr4d_results.pt")
        try:
            joints, transl = extract_joints(pt_path)
            np.savez_compressed(
                out_npz,
                joints_world=joints,          # (T, 22, 3) 월드 3D 관절 = GT
                transl=transl,                # (T, 3) 골반 위치(낙상 높이)
                frame_index=np.arange(len(joints)),
            )
            done += 1
            print(f"    OK   {out_npz}  {joints.shape}")
        except Exception as exc:
            failed += 1
            print(f"    변환 실패: {uid}  ({exc})")
            continue
        finally:
            if DELETE_TMP:
                import shutil
                shutil.rmtree(outdir, ignore_errors=True)

    print(f"\n=== 완료 ===  신규 {done} / SKIP {skipped} / 실패 {failed}")


if __name__ == "__main__":
    main()
