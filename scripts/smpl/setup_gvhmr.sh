#!/usr/bin/env bash
# =============================================================================
# setup_gvhmr.sh — GVHMR GT 파이프라인 원클릭 설치 (WSL2 Ubuntu, NVIDIA GPU 필요)
#
# 대상: Windows + NVIDIA GPU + WSL2(Ubuntu) 사용자.
#       (Mac/GPU 없는 사람은 로컬 불가 → docs/gvhmr_gt.md 의 Colab 방식 사용)
#
# 하는 일 (모두 idempotent, 다시 실행하면 이미 된 건 건너뜀):
#   1) apt 시스템 패키지 (build-essential, ffmpeg 등)
#   2) miniconda + gvhmr(python 3.10) env
#   3) GVHMR clone + 의존성 설치 (torch cu121 + prebuilt pytorch3d + chumpy 우회)
#   4) 체크포인트 4종 다운로드 (HuggingFace 미러, 구글드라이브 할당량 우회)
#   5) body model 배치 (SMPL/SMPLX — 아래 BODY_MODELS_SRC 참고)
#   6) demo_gt.py 생성 (렌더 호출 제거 = GT 전용, 시간/디스크 절약)
#
# 사용법:
#   BODY_MODELS_SRC=/mnt/c/받은경로 bash setup_gvhmr.sh
#   (BODY_MODELS_SRC = SMPLX_NEUTRAL.npz / SMPL_NEUTRAL.pkl 이 들어있는(하위포함) 폴더)
# =============================================================================
set -e
LOG="$HOME/setup_gvhmr.log"        # /root 하드코딩 금지 (비 root 사용자도 쓸 수 있게 $HOME)
exec > >(tee "$LOG") 2>&1
echo "===== setup_gvhmr START $(date) ====="

GVHMR_ROOT="$HOME/GVHMR"
CKPT="$GVHMR_ROOT/inputs/checkpoints"
# body model 원본 폴더 (SMPLX_NEUTRAL.npz / SMPL_NEUTRAL.pkl 포함). 팀 공유드라이브 or smpl-x 등록 다운로드.
BODY_MODELS_SRC="${BODY_MODELS_SRC:-}"
# root면 sudo 불필요/부재 가능 → 조건부. 일반 사용자면 sudo 사용.
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

echo "----- [1] apt 패키지 -----"
export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -y
$SUDO apt-get install -y build-essential ffmpeg unzip wget git

echo "----- [2] miniconda + gvhmr env(py3.10) -----"
if [ ! -d "$HOME/miniconda3" ]; then
  wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/mc.sh
  bash /tmp/mc.sh -b -p "$HOME/miniconda3"; rm -f /tmp/mc.sh
fi
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true
conda env list | grep -q "^gvhmr " || conda create -n gvhmr python=3.10 -c conda-forge --override-channels -y
conda activate gvhmr
python --version

echo "----- [3] GVHMR clone + 의존성 -----"
[ -d "$GVHMR_ROOT/.git" ] || git clone https://github.com/zju3dv/GVHMR "$GVHMR_ROOT"
cd "$GVHMR_ROOT"
pip install --upgrade pip
# chumpy 는 격리빌드에서 'import pip' 실패 → 제외 후 별도 설치
grep -v -i '^chumpy' requirements.txt > /tmp/req_nochumpy.txt
pip install -r /tmp/req_nochumpy.txt        # torch2.3+cu121 + prebuilt pytorch3d(py3.10) 포함
pip install "setuptools<70" wheel cython
pip install chumpy --no-build-isolation || \
  pip install "git+https://github.com/mattloper/chumpy.git" --no-build-isolation || \
  echo "chumpy 설치 실패 — GVHMR가 직접 import 안 하므로 대개 무방"
pip install -e .

echo "----- [4] 체크포인트 (HuggingFace 미러 camenduru/GVHMR) -----"
mkdir -p "$CKPT"/{gvhmr,hmr2,vitpose,yolo}
pip install -q -U huggingface_hub
python - <<PY
import os, shutil
from huggingface_hub import list_repo_files, hf_hub_download
repo="camenduru/GVHMR"; CKPT="$CKPT"
files=list_repo_files(repo)
want={  # dpvo 는 -s(static cam)라 불필요 → 제외
 "gvhmr/gvhmr_siga24_release.ckpt":"gvhmr/gvhmr_siga24_release.ckpt",
 "hmr2/epoch=10-step=25000.ckpt":"hmr2/epoch=10-step=25000.ckpt",
 "vitpose/vitpose-h-multi-coco.pth":"vitpose/vitpose-h-multi-coco.pth",
 "yolo/yolov8x.pt":"yolo/yolov8x.pt",
}
for key,dest in want.items():
    d=os.path.join(CKPT,dest)
    if os.path.exists(d) and os.path.getsize(d)>1_000_000:
        print("이미 있음:",dest); continue
    m=[f for f in files if f.endswith(key)]
    if not m: print("MISS repo:",key); continue
    p=hf_hub_download(repo_id=repo, filename=m[0])
    os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy(p,d)
    print("OK",dest, round(os.path.getsize(d)/1e6,1),"MB")
PY

echo "----- [5] body models (SMPL/SMPLX) -----"
mkdir -p "$CKPT/body_models/smpl" "$CKPT/body_models/smplx"
if [ -f "$CKPT/body_models/smplx/SMPLX_NEUTRAL.npz" ]; then
  echo "SMPLX 이미 있음"
elif [ -n "$BODY_MODELS_SRC" ]; then
  npz=$(find "$BODY_MODELS_SRC" -iname "SMPLX_NEUTRAL.npz" 2>/dev/null | head -1)
  pkl=$(find "$BODY_MODELS_SRC" -iname "basicmodel_neutral*.pkl" -o -iname "SMPL_NEUTRAL.pkl" 2>/dev/null | head -1)
  [ -n "$npz" ] && cp "$npz" "$CKPT/body_models/smplx/SMPLX_NEUTRAL.npz" && echo "SMPLX OK" || echo "!! SMPLX_NEUTRAL.npz 못찾음"
  [ -n "$pkl" ] && cp "$pkl" "$CKPT/body_models/smpl/SMPL_NEUTRAL.pkl" && echo "SMPL OK"   || echo "(SMPL_NEUTRAL.pkl 없음 — GT추출엔 SMPLX만 있어도 됨)"
else
  echo "!! body models 없음. BODY_MODELS_SRC 를 지정해 다시 실행하세요."
  echo "   예: BODY_MODELS_SRC=/mnt/c/Users/you/Downloads/smpl_models bash setup_gvhmr.sh"
  echo "   (SMPLX_NEUTRAL.npz 는 https://smpl-x.is.tue.mpg.de 등록 후 다운로드, 또는 팀 공유드라이브)"
fi

echo "----- [6] demo_gt.py 생성 (렌더 호출 제거) -----"
python - <<'PY'
src=open("tools/demo/demo.py").read()
mk="    # ===== Render ===== #"
assert mk in src, "render marker 못찾음 — GVHMR demo.py 구조 변경됨"
open("tools/demo/demo_gt.py","w").write(
    src.split(mk)[0] +
    '    from hmr4d.utils.pylogger import Log as _Log\n'
    '    _Log.info("[GT ONLY] hmr4d_results.pt saved. Render skipped.")\n')
print("demo_gt.py 생성 완료")
PY

echo "----- 최종 확인 -----"
python - <<'PY'
import torch, pytorch3d, numpy, smplx
print("torch", torch.__version__, "cuda", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO-GPU")
print("pytorch3d", pytorch3d.__version__, "| numpy", numpy.__version__)
PY
find "$CKPT" -type f -exec du -h {} \; | sort -k2
echo "===== setup_gvhmr DONE $(date) ====="
echo "다음: conda activate gvhmr && python <repo>/scripts/smpl/batch_gvhmr_fast.py"
