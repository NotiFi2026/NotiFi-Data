"""
batch_gvhmr_fast.py — GVHMR 일괄 처리 (in-process, 모델 1회 로딩)

batch_gvhmr.py 는 영상마다 demo 프로세스를 새로 띄워 매번 모델을 재로딩한다(~20s/영상 낭비).
이 버전은 한 프로세스 안에서:
  - GVHMR 본 모델을 1회만 로딩해 상주 (예측 순간만 GPU, 평소 CPU → 8GB VRAM 안전)
  - 무거운 전처리기(YOLO/ViTPose/Extractor)는 영상마다 생성/해제 (demo.py 방식 그대로)
  - python/torch/hydra 재시작 + GVHMR 모델 재로딩 오버헤드 제거
결과 .npz(joints_world/transl/frame_index)와 저장 위치는 batch_gvhmr.py 와 100% 동일.

이어하기(resumable): 이미 있는 .npz 는 SKIP.
실행(WSL, gvhmr env):
    conda activate gvhmr
    python /mnt/c/mhw/NotiFI/NotiFi-Data/scripts/smpl/batch_gvhmr_fast.py
테스트: --limit 2  (앞의 2개만)
"""
import os, sys, glob, time, shutil, gc, argparse
import numpy as np
import torch

# ============================ CONFIG ============================
GVHMR_ROOT = os.path.expanduser("~/GVHMR")
# VIDEO_ROOT: 스크립트 위치 기준으로 자동 계산 (팀원 repo 경로 달라도 수정 불필요).
#   필요시 환경변수 NOTIFI_VIDEO_ROOT 로 덮어쓰기 가능.
_HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_ROOT = os.environ.get(
    "NOTIFI_VIDEO_ROOT",
    os.path.normpath(os.path.join(_HERE, "..", "..", "collection_data", "v2")),
)
DELETE_TMP = True
BODY_MODELS = os.path.join(GVHMR_ROOT, "inputs", "checkpoints", "body_models")
# ===============================================================

sys.path.insert(0, os.path.join(GVHMR_ROOT, "tools", "demo"))
os.chdir(GVHMR_ROOT)  # hydra config / 상대경로 기준
import hydra
from pathlib import Path
from demo_gt import run_preprocess, load_data_dict, parse_args_to_cfg
from hmr4d.utils.net_utils import detach_to_cpu
import smplx


def make_cfg(video_path: str):
    """demo_gt.parse_args_to_cfg 재사용 (영상 복사·출력경로 생성 포함)."""
    sys.argv = ["demo_gt.py", "--video", video_path, "-s"]
    return parse_args_to_cfg()


def video_to_uid(video_path: str) -> str:
    return os.path.basename(video_path).replace("_video.mp4", "")


def extract_joints(pt_path: str):
    """hmr4d_results.pt -> 월드 3D 관절 (T,22,3) + 골반 위치 transl(T,3). (batch_gvhmr.py 와 동일)"""
    res = torch.load(pt_path, map_location="cpu", weights_only=False)
    g = res["smpl_params_global"]
    T = g["transl"].shape[0]
    betas = g["betas"]
    betas = betas[None].repeat(T, 1) if betas.dim() == 1 else betas
    model = smplx.create(BODY_MODELS, model_type="smplx", gender="neutral",
                         use_pca=False, batch_size=T)
    with torch.no_grad():
        out = model(body_pose=g["body_pose"][:, :63], global_orient=g["global_orient"],
                    betas=betas[:, :10], transl=g["transl"])
    return out.joints.numpy()[:, :22, :], g["transl"].numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="테스트용: 앞의 N개만 처리 (0=전체)")
    args = ap.parse_args()

    videos = sorted(glob.glob(os.path.join(VIDEO_ROOT, "**", "*_video.mp4"), recursive=True))
    if args.limit:
        videos = videos[:args.limit]
    print(f"총 영상: {len(videos)}개 | GT: 각 영상 폴더에 <uid>_pose_gvhmr.npz", flush=True)

    # ---- GVHMR 모델 1회 로딩 (상주, 평소 CPU) ----
    cfg0 = make_cfg(videos[0])
    model = hydra.utils.instantiate(cfg0.model, _recursive_=False)
    model.load_pretrained_model(cfg0.ckpt_path)
    model = model.eval()
    print("[모델 로딩 완료] GVHMR 상주 (예측시만 GPU)", flush=True)

    done = skipped = failed = 0
    t_start = time.time()
    for i, vid in enumerate(videos, 1):
        uid = video_to_uid(vid)
        out_npz = os.path.join(os.path.dirname(vid), f"{uid}_pose_gvhmr.npz")
        if os.path.exists(out_npz):
            skipped += 1
            continue

        t0 = time.time()
        try:
            cfg = make_cfg(vid)
            if not Path(cfg.paths.hmr4d_results).exists():
                run_preprocess(cfg)                     # yolo/vitpose/extractor 생성·해제
                data = load_data_dict(cfg)
                model.cuda()                            # 예측 직전 GPU
                pred = model.predict(data, static_cam=cfg.static_cam)
                pred = detach_to_cpu(pred)
                model.cpu(); torch.cuda.empty_cache()   # 예측 후 GPU 비움
                torch.save(pred, cfg.paths.hmr4d_results)

            joints, transl = extract_joints(cfg.paths.hmr4d_results)
            np.savez_compressed(out_npz, joints_world=joints, transl=transl,
                                frame_index=np.arange(len(joints)))
            done += 1
            dt = time.time() - t0
            eta = (time.time() - t_start) / max(done, 1) * (len(videos) - i) / 3600
            print(f"[{i}/{len(videos)}] OK {uid} {joints.shape} {dt:.0f}s | ETA~{eta:.1f}h", flush=True)
        except Exception as exc:
            failed += 1
            print(f"[{i}/{len(videos)}] FAIL {uid} ({type(exc).__name__}: {exc})", flush=True)
            try:
                model.cpu(); torch.cuda.empty_cache()
            except Exception:
                pass
        finally:
            if DELETE_TMP:
                shutil.rmtree(os.path.join(GVHMR_ROOT, "outputs", "demo",
                              os.path.basename(vid)[:-4]), ignore_errors=True)
            gc.collect()

    print(f"\n=== 완료 === 신규 {done} / SKIP {skipped} / 실패 {failed} "
          f"/ 총 {(time.time()-t_start)/3600:.1f}h", flush=True)


if __name__ == "__main__":
    main()
