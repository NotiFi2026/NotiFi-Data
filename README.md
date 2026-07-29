# NotiFi Dataset Collection v2.0

NotiFi의 3TX+1RX CSI와 RGB 영상을 동기화해 수집하고, 영상에서 GVHMR로 3D pose teacher GT를 만드는 현장용 도구다. 기준은 `NotiFi 데이터셋 수집 계획서 v2.0 찐막 (2026-07-24)`이며, 이전 데이터셋의 배경음·가전 상태별 분기와 과거 라벨은 사용하지 않는다.

## 수집 목표

| Risk | 라벨 수 | 1인·1환경 | 1인·3환경 | 4인 전체 |
| --- | ---: | ---: | ---: | ---: |
| SAFE | 9 | 150 | 450 | 1,800 |
| WARNING | 3 | 75 | 225 | 900 |
| DANGER | 5 | 50 | 150 | 600 |
| 합계 | 17 | 275 | 825 | 3,300 |

수집자는 `ajh`, `lmh`, `mhw`, `yja` 네 명이며, 네 명 모두 동일한 세 물리적 환경 `E01`, `E02`, `E03`에서 전체 라벨을 수집한다. 모든 원본 trial은 10초다.

## 1. 설치

Windows PowerShell:

```powershell
git clone https://github.com/NotiFi2026/NotiFi-Data.git
cd NotiFi-Data
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/generate_sounds.py
```

Python 3.11을 권장한다. Windows의 카메라와 COM 포트를 사용하므로 VS Code도 같은 `.venv` 인터프리터를 선택해야 한다.

COM 포트 확인:

```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

## 2. 3TX+1RX 준비

- TX1 MAC: `1a:00:00:00:00:00`
- TX2 MAC: `1a:00:00:00:00:01`
- TX3 MAC: `1a:00:00:00:00:02`
- TX별 송신률: `30 pkt/s`
- 네 보드 채널: 동일한 `11`
- RX 시리얼: 기본 `921600 baud`

펌웨어 수정과 플래시는 [3TX+1RX 펌웨어 가이드](firmware/README.md)를 먼저 완료한다. 본 수집 전 세 TX를 모두 켜고 RX만 PC에 연결한 뒤 아래 검사를 통과해야 한다.

```powershell
python scripts/check_tx_links.py COM_PORT --rate 30
```

10초 기준 TX1/TX2/TX3가 각각 1 frame 이상이면 수집을 시작할 수 있다. 240/270 frames 같은 낮은 수신량 기준은 경고나 중단 조건으로 쓰지 않는다. `idf.py monitor`가 RX 포트를 사용 중이면 `Ctrl+]`로 종료한다.

## 3. 장비 배치

| 장비 | 기준 |
| --- | --- |
| RX | 활동 중심 정면, 높이 0.80 m, USB로 노트북 연결 |
| TX1 | RX 맞은편, RX와 1.50 m, 높이 0.80 m |
| TX2 | 활동 중심 측면, 높이 1.45 m |
| TX3 | 활동 중심 대각 바닥 측, 높이 0.35 m |
| 안테나 | 네 보드 모두 세로 편파, 케이블 위치 고정 |
| 카메라 | 활동 중심을 향하며 전신·매트·의자·침대가 모두 보이도록 고정 |

세 환경에서 같은 로컬 좌표와 가구 배치를 사용한다. TX2와 TX3의 정확한 수평 좌표는 파일럿에서 확정한 실측값을 세 환경에 동일하게 복제하고 setup 사진에 남긴다. session 중 위치가 2 cm 또는 각도가 3도 이상 바뀌면 수집을 멈추고 새 `device_config_id`를 사용한다.

카메라 확인:

```powershell
python scripts/check_camera_source.py
python scripts/preview_camera.py --camera 0
```

macOS에서 iPhone/iPad/Continuity Camera가 감지되면 `check_camera_source.py`, `preview_camera.py`, `collect_dataset.py`가 수집을 시작하지 않는다. 노트북 내장 카메라만 남도록 Continuity Camera를 끄거나 휴대폰 연결을 해제한 뒤 다시 실행한다.

## 4. 세션 설정

환경이나 날짜가 바뀔 때마다 새 session을 만든다. placeholder를 실제 값으로 바꾼다.

```powershell
python scripts/create_session.py `
  --subject SUBJECT_ID `
  --environment E01 `
  --session YYYYMMDD_AM01 `
  --port COM_PORT `
  --camera 0 `
  --firmware-commit FIRMWARE_COMMIT `
  --device-config K0_P0 `
  --channel 11 `
  --packet-rate 30
```

로컬 설정은 `.notifi_session.json`에 저장되며 Git에는 올라가지 않는다.

환경별 권장 session 배치는 다음과 같다. 한 session의 DANGER는 마지막에 수행하고 10회 종료 후 10분 이상 쉰다.

| Session | 비낙상 라벨 | DANGER | 합계 |
| --- | --- | --- | ---: |
| A | `stand_to_lie_normal` 30 + `unstable_walking` 20 | `fall_from_standing` 10 | 60 |
| B | `stumble_recover` 30 + `lying_still` 18 | `fall_while_walking` 10 | 58 |
| C | `bed_exit_failed` 25 + `walking` 24 | `bed_exit_fall` 10 | 59 |
| D | `lie_to_stand` 18 + `standing_still` 12 + `sitting_still` 12 | `bed_fall` 10 | 52 |
| E | `absence` 12 + `sit_to_stand` 12 + `stand_to_sit` 12 | `chair_exit_fall` 10 | 46 |

이 다섯 session을 `E01`, `E02`, `E03`에서 반복하면 개인별 825회가 된다.

## 5. 수집

예시:

```powershell
python scripts/collect_dataset.py --label walking --repeat 24
```

DANGER 예시:

```powershell
python scripts/collect_dataset.py `
  --label fall_from_standing `
  --repeat 10 `
  --safety-confirmed
```

기본 동작은 다음과 같다.

1. 첫 trial 전 5초 카운트다운
2. sound1과 동시에 CSI·영상 기록 시작
3. 동적 라벨은 2.5/3.0/3.5초를 순환하며 action cue 재생
4. 10초 후 sound2와 함께 trial 종료
5. TX1/TX2/TX3별 CSI amplitude 시각화 PNG 자동 저장
6. 다음 trial까지 2초 휴식
7. 전체 반복 완료 후 sound3 재생

정적 라벨은 action cue가 없다. DANGER는 5회 후 자동으로 3분 휴식하며, 10회 완료 후 다음 DANGER 세트까지 10분 이상 쉬어야 한다.
수집 중 포트 오류, TX별 CSI 0 frame, 카메라 오류, 자동 QC 실패 등으로 중단되면 `error.wav`가 울린 뒤 `삐삐삐` 3회 알림이 재생되고 프로그램이 즉시 종료된다. 낮은 수신량은 CSI 시각화로만 확인하고 중단 조건으로 쓰지 않는다. `--no-sound`를 사용하면 모든 알림음이 꺼진다.
CSI와 영상은 같은 PC monotonic clock과 같은 `trial_start_monotonic_ns` 기준으로 기록된다. CSI CSV와 `*_video_timestamps.csv`를 함께 사용하면 후처리에서 같은 trial 안의 CSI 프레임과 영상 프레임을 시간 기준으로 정렬할 수 있다.

수집 파일:

```text
collection_data/v2/
  SUBJECT/E01/SESSION/risk/label/source_trial_uid/
    *_csi.csv
    *_csi_visualization.png
    *_video.mp4
    *_video_timestamps.csv
    *_meta.json
    checksums.sha256
  manifests/trials.csv
```

CSI CSV에는 PC monotonic timestamp, sender MAC/ID, sequence number, firmware timestamp, RSSI, CSI 배열을 보존한다. `*_csi_visualization.png`에는 TX1/TX2/TX3의 평균 CSI amplitude가 같은 trial 기준으로 저장된다. metadata에는 cue, variant, 장비 배치, 자동 QC, CSI 시각화 생성 여부, 실제 이벤트 주석 필드를 저장한다.

잘못 수집된 trial을 다시 찍고 싶으면 해당 trial 폴더를 삭제한 뒤 같은 명령어를 다시 실행한다. 진행률과 다음 trial 번호는 manifest만 보지 않고 실제 `csi/video/meta` 파일과 trial 폴더 존재 여부를 함께 확인하므로, 폴더를 삭제한 번호부터 다시 채워진다.

## 6. 이벤트 주석

수집 영상에서 실제 행동 시작, 충돌, 행동 종료 시각을 확인한 뒤 기록한다. 충돌이 없는 SAFE/WARNING은 `--impact`를 생략한다.

```powershell
python scripts/annotate_trial.py PATH_TO_META_JSON `
  --actual-onset 2.9 `
  --impact 4.1 `
  --action-end 4.6 `
  --manual-qc ACCEPT
```

planned cue와 actual onset 차이가 0.5초를 넘거나 동작 정의를 위반하면 `REJECT`로 기록하고 재수집한다.
정적 라벨은 `--actual-onset`, `--action-end`를 생략하면 자동으로 `0.0`, `10.0`이 기록된다. DANGER는 `--impact`가 필수다.

## 7. 3D teacher GT (GVHMR)

teacher GT는 **GVHMR**로 만든다. 이전의 mediapipe 13-point(`extract_pose13.py`)는 카메라 각도 때문에 절대 높이·바닥정렬이 부정확해 교체했다. GVHMR는 **중력정렬 월드 3D 좌표(절대 높이 포함)**를 주며, 낙상·침대탈출처럼 높이가 중요한 라벨에서 차이가 크다.

- 입력: 각 trial의 `*_video.mp4`
- 출력(GT): 같은 폴더에 `*_pose_gvhmr.npz`
  - `joints_world` `(T,22,3)` — SMPL 22관절 월드 3D 좌표 = **학습 타깃**
  - `transl` `(T,3)` — 골반 위치(높이 포함), `frame_index` `(T,)`
- **학습엔 이 `.npz` 숫자만 쓴다.** 오버레이/스켈레톤 영상은 사람이 눈으로 검수하는 용도일 뿐 학습에 안 들어간다.

### 7.1 환경 (GVHMR는 NVIDIA GPU 필수)

| 내 장비 | 방법 |
| --- | --- |
| Windows + NVIDIA GPU | **WSL2 로컬** (7.2). 가장 빠르고 오프라인 가능 |


> Mac은 WSL·CUDA가 없어 로컬 GVHMR가 불가능하다. 이 경우 Colab을 쓴다. GVHMR는 리눅스 기준 프로젝트라 네이티브 Windows(비 WSL)는 pytorch3d 빌드가 번거로워 권장하지 않는다.

### 7.2 설치 (Windows + NVIDIA, 최초 1회)

```powershell
wsl --install -d Ubuntu      # WSL2 우분투 (재부팅)
```

**사전 준비 & 확인:**
- 윈도우에 **최신 NVIDIA 드라이버**가 설치돼 있어야 WSL에서 GPU가 잡힌다.
- 우분투 **첫 실행 시 Unix 사용자(이름/비밀번호) 만들기** 화면이 나오면 하나 만든다. (일반 사용자로 진행되며 `setup_gvhmr.sh`가 알아서 처리한다.)
- 우분투(bash)에서 GPU 인식 확인:

```bash
nvidia-smi -L      # 내 GPU 이름이 나오면 OK. 안 나오면 윈도우 NVIDIA 드라이버부터 최신으로.
```

> **경로 규칙**: 이하 `/mnt/c/경로/NotiFi-Data`는 **1장에서 clone한 repo의 WSL 경로**다. `/mnt/c` = 윈도우 C드라이브. 예를 들어 `C:\Users\내이름\NotiFi-Data`에 clone했으면 → `/mnt/c/Users/내이름/NotiFi-Data`. **7.3~7.5 명령은 모두 이 repo 폴더 안에서 실행**하므로, WSL에서 먼저 자기 경로로 이동해 둔다: `cd /mnt/c/경로/NotiFi-Data`

body model(`SMPLX_NEUTRAL.npz` 필수, `SMPL_NEUTRAL.pkl` 선택)은 라이선스 파일이라 자동 다운로드가 안 된다. 팀 공유드라이브에서 받거나 [SMPL-X](https://smpl-x.is.tue.mpg.de) 등록 후 받아 한 폴더에 둔다. 그 폴더를 `BODY_MODELS_SRC`로 넘겨 원클릭 설치:

```bash
BODY_MODELS_SRC=/mnt/c/Users/"이름"/Downloads/smpl_models \
  bash /mnt/c/경로/NotiFi-Data/scripts/smpl/setup_gvhmr.sh
```

`setup_gvhmr.sh`가 miniconda + `gvhmr`(py3.10) env, GVHMR clone, 의존성(torch cu121 + pytorch3d + chumpy 우회), 체크포인트 4종(HuggingFace 미러), body model 배치, `demo_gt.py`(렌더 제거판) 생성을 모두 처리한다. 다시 실행해도 된 건 건너뛴다.

### 7.3 (시작 전) 이전 mediapipe 산출물 정리

이전에 mediapipe(`extract_pose13.py`)로 만든 결과가 남아 있으면, GT 생성 전에 `scripts/smpl/clean_mediapipe.py`로 지워 용량을 확보한다. (처음부터 GVHMR로만 수집한 경우엔 지울 게 없어 DRY-RUN이 0개로 나오니 건너뛰면 된다.) 각 trial 폴더의 mediapipe 3종이 대상이다.

| 파일 | 정체 | 기본 동작 |
| --- | --- | --- |
| `*_pose_overlay.mp4` | mediapipe 오버레이 영상 (용량 대부분) | **삭제** |
| `*_pose_qc.json` | mediapipe 포즈 QC | **삭제** |
| `*_pose13.csv` | 구 mediapipe teacher GT | **유지** (GVHMR 비교 baseline). `--include-pose13`로만 삭제 |

GVHMR 산출물(`*_pose_gvhmr.npz` / `*_skeleton3d.mp4` / `*_overlay3d.mp4`)과 원본·CSI·meta·checksum은 **건드리지 않는다.**

**1) 먼저 DRY-RUN** — 무엇이 얼마나 지워질지만 확인(아무것도 안 지움):

```bash
python scripts/smpl/clean_mediapipe.py
```

출력 예: `*_pose_overlay.mp4 : 789개 10.0GB`, `*_pose_qc.json : 789개 0.3MB`, 합계 표시.

**2) 실제 삭제** — `--apply`를 붙인다:

```bash
python scripts/smpl/clean_mediapipe.py --apply                    # overlay + qc 삭제 (pose13 유지)
python scripts/smpl/clean_mediapipe.py --include-pose13 --apply   # pose13 까지 전부 삭제
```

옵션: `--root <경로>`로 대상 루트 변경(기본 `collection_data/v2`). 표준 라이브러리만 쓰므로 `.venv`/conda 없이 아무 Python으로 실행된다(WSL·Windows·Mac 무관).

> 참고: 이전 mediapipe 방식은 `scripts/extract_pose13.py`였다(now deprecated). 세부 QC 기준(pose valid ratio, timestamp residual 등)이 필요하면 git 이력의 이전 7장을 참고한다.

### 7.4 GT 생성 (배치)

```bash
cd /mnt/c/경로/NotiFi-Data                                  # repo 폴더 (위 '경로 규칙' 참고)
source ~/miniconda3/etc/profile.d/conda.sh && conda activate gvhmr
python scripts/smpl/batch_gvhmr_fast.py                      # 스크립트가 알아서 ~/GVHMR 로 이동해 실행
```

repo 안 `collection_data/v2/**/ *_video.mp4`를 모두 찾아 각 폴더에 `*_pose_gvhmr.npz`를 만든다. **이어하기**: 이미 있는 `.npz`는 건너뛰므로 끊겨도 다시 실행하면 이어진다. 속도는 10초 영상당 ~60초(RTX 3060 Ti), peak VRAM ~4.9GB. 밤새 돌리려면 `nohup ... > ~/batch.log 2>&1 &` 후 `tail -f ~/batch.log`.

### 7.5 검수 시각화 (선택, 표본만)

```bash
python scripts/smpl/viz_gvhmr_gt.py --uid <trial_uid>      # 3D 스켈레톤 (높이·자세)
python scripts/smpl/overlay_gvhmr_gt.py --uid <trial_uid>  # 원본영상 위 2D 오버레이 (정합 스팟체크)
```

`--uid` 없이 실행하면 사용 가능한 목록을 보여준다. 모든 영상에 만들 필요 없다.

## 8. 진행률과 최종 QC

```powershell
python scripts/show_progress.py --subject SUBJECT_ID --environment E01
python scripts/validate_collection.py `
  --write-report collection_data/v2/qc_report.json
```

세부 행동·금지 행동·재수집 기준은 [전체 수집 매뉴얼](docs/collection_manual.md)을 따른다.
첨부 문서 안에 남아 있던 이전 숫자와 미사용 라벨의 처리 원칙은 [v2.0 찐막 구현 기준 메모](docs/implementation_notes.md)에 기록했다.

팀원별 명령:

- [ajh.md](ajh.md)
- [lmh.md](lmh.md)
- [mhw.md](mhw.md)
- [yja.md](yja.md)

## 안전

DANGER는 건강한 성인의 통제 하강 시뮬레이션으로만 수행한다. 실제 고령자에게 낙상 동작을 시키지 않는다. 머리·목 보호, 이중 매트, 안전요원, 고정 의자, 낮은 침대가 준비되지 않으면 `--safety-confirmed`를 사용하지 않는다. 통증, 어지럼증, 메스꺼움, 두통, 손목 또는 무릎 불편감이 있으면 즉시 중단한다.
