# NotiFi Team 3 CSI Collection Plan

Date: 2026-06-22  
Collector: Team 3 / 윤정아  
Recommended subject id: `yja`  
Repository: https://github.com/NotiFi2026/NotiFi-Data  
Script: `scripts/save_csi_raw.py`

---

## 1. Goal

팀원 3은 이미지 표 기준으로 `unknown` 라벨을 제외하고 `safe`, `warning`, `danger` 라벨을 모두 수집한다.

총 수집 개수:

```text
safe: 334
warning: 333
danger: 333
total: 1000
```

`save_csi_raw.py`는 라벨명만 넣으면 자동으로 risk/domain을 매핑한다.

저장 경로 예시:

```text
data/safe/absence/empty/yja/yja_empty_t001.csv
data/warning/breathing/lying_fast_breath/yja/yja_lying_fast_breath_t001.csv
data/danger/fall/fall_simulated/yja/yja_fall_simulated_t001.csv
```

---

## 2. Windows PowerShell Setup

아래 값은 본인 환경에 맞게 바꾼다.

```powershell
$Repo = "C:\Users\YOUR_NAME\NotiFI\NotiFi-Data"
$Port = "COM_PORT"
$Subject = "yja"
```

처음 한 번만 실행:

```powershell
cd C:\Users\YOUR_NAME\NotiFI
git clone https://github.com/NotiFi2026/NotiFi-Data.git
cd $Repo
py -m pip install pyserial
```

이미 clone 되어 있으면:

```powershell
cd $Repo
git pull
```

COM 포트 확인:

```powershell
[System.IO.Ports.SerialPort]::getportnames()
```

자세히 보고 싶으면:

```powershell
Get-CimInstance Win32_SerialPort | Select-Object DeviceID, Name, Description
```

receiver 보드 포트를 `$Port`에 넣는다.

예시:

```powershell
$Port = "COM4"
```

---

## 3. Basic Command Format

기본 실행 형식:

```powershell
python "$Repo\scripts\save_csi_raw.py" `
  --port $Port `
  --subject $Subject `
  --label LABEL_NAME `
  --trial t001 `
  --duration DURATION_SECONDS `
  --repeat REPEAT_COUNT `
  --delay 5 `
  --break_sec 3
```

의미:

```text
--port: receiver 보드 COM 포트
--subject: 본인 짧은 ID, 권장 yja
--label: 수집 라벨
--trial: 시작 trial 번호
--duration: 한 CSV당 수집 시간
--repeat: 반복 저장 개수
--delay: 첫 수집 전 준비 시간
--break_sec: 반복 사이 쉬는 시간
```

---

## 4. Ambient Condition Plan

실생활 환경을 반영하기 위해 같은 라벨도 아래 4개 환경으로 나누어 수집한다.

```text
quiet: 조용한 기본 환경
aircon: 에어컨 소리 있음
tv: TV 소리 있음
music: 음악 소리 있음
```

권장 비율:

```text
quiet 30%
aircon 25%
tv 25%
music 20%
```

주의:

- 현재 `save_csi_raw.py`는 ambient condition을 CSV 내부 컬럼으로 저장하지 않는다.
- 따라서 수집할 때 반드시 별도 메모에 ambient condition을 기록한다.
- 파일명은 `subject_label_trial.csv`로 저장되므로, trial 구간과 ambient condition을 매칭해서 기록해야 한다.

메모 예시:

```text
subject,label,trial_start,trial_end,duration,repeat,ambient,note
yja,empty,t001,t020,20,20,quiet,normal room
yja,empty,t021,t037,20,17,aircon,aircon on
yja,empty,t038,t053,20,16,tv,tv volume low-medium
yja,empty,t054,t066,20,13,music,music volume low-medium
```

---

## 5. Team 3 Collection Counts

### 5.1 Safe Labels

| label | duration | total | quiet | aircon | tv | music |
|---|---:|---:|---:|---:|---:|---:|
| empty | 20s | 66 | 20 | 17 | 16 | 13 |
| sitting_still | 20s | 22 | 7 | 6 | 5 | 4 |
| standing_still | 20s | 22 | 7 | 6 | 5 | 4 |
| lying_still | 20s | 22 | 7 | 6 | 5 | 4 |
| hand_move | 20s | 33 | 10 | 8 | 8 | 7 |
| walking | 20s | 34 | 10 | 9 | 8 | 7 |
| sit_to_stand | 10s | 17 | 5 | 4 | 4 | 4 |
| stand_to_sit | 10s | 17 | 5 | 4 | 4 | 4 |
| stand_to_lie_normal | 10s | 17 | 5 | 4 | 4 | 4 |
| lie_to_stand | 10s | 17 | 5 | 4 | 4 | 4 |
| lying_normal_breath | 20s | 67 | 20 | 17 | 17 | 13 |

Safe total: 334

### 5.2 Warning Labels

| label | duration | total | quiet | aircon | tv | music |
|---|---:|---:|---:|---:|---:|---:|
| lying_fast_breath | 20s | 28 | 8 | 7 | 7 | 6 |
| lying_long_breath | 20s | 28 | 8 | 7 | 7 | 6 |
| lying_shallow_breath | 20s | 27 | 8 | 7 | 7 | 5 |
| lying_breath_hold_short | 10s | 28 | 8 | 7 | 7 | 6 |
| sitting_inactive_long | 20s | 37 | 11 | 9 | 9 | 8 |
| standing_inactive_long | 20s | 37 | 11 | 9 | 9 | 8 |
| lying_inactive_long | 20s | 37 | 11 | 9 | 9 | 8 |
| fall_like_recovered | 10s | 111 | 33 | 28 | 28 | 22 |

Warning total: 333

### 5.3 Danger Labels

| label | duration | total | quiet | aircon | tv | music |
|---|---:|---:|---:|---:|---:|---:|
| fall_simulated | 10s | 83 | 25 | 21 | 21 | 16 |
| post_fall_inactive | 20s | 83 | 25 | 21 | 21 | 16 |
| lying_apnea_like | 20s | 83 | 25 | 21 | 21 | 16 |
| lying_breath_signal_lost | 20s | 84 | 25 | 21 | 21 | 17 |

Danger total: 333

Note:

- 기존 매뉴얼 텍스트에는 `lying_breath_signal_lost` 삭제 메모가 있으나, 사용자가 준 이미지와 카톡 라벨 목록에는 포함되어 있다.
- 이 계획서는 사용자의 최신 지시인 "unknown 제외 모든 safe/warning/danger 라벨 수집"을 기준으로 `lying_breath_signal_lost`를 포함한다.
- 팀에서 삭제가 최종 확정되면 이 라벨은 수집하지 않는다.

---

## 6. How to Run a Label by Ambient Condition

예시: `empty` 총 66개 수집

```powershell
# quiet: t001-t020
python "$Repo\scripts\save_csi_raw.py" `
  --port $Port `
  --subject $Subject `
  --label empty `
  --trial t001 `
  --duration 20 `
  --repeat 20 `
  --delay 5 `
  --break_sec 3

# aircon: t021-t037
python "$Repo\scripts\save_csi_raw.py" `
  --port $Port `
  --subject $Subject `
  --label empty `
  --trial t021 `
  --duration 20 `
  --repeat 17 `
  --delay 5 `
  --break_sec 3

# tv: t038-t053
python "$Repo\scripts\save_csi_raw.py" `
  --port $Port `
  --subject $Subject `
  --label empty `
  --trial t038 `
  --duration 20 `
  --repeat 16 `
  --delay 5 `
  --break_sec 3

# music: t054-t066
python "$Repo\scripts\save_csi_raw.py" `
  --port $Port `
  --subject $Subject `
  --label empty `
  --trial t054 `
  --duration 20 `
  --repeat 13 `
  --delay 5 `
  --break_sec 3
```

다른 라벨도 같은 방식으로 진행한다.

trial 시작 번호 계산:

```text
quiet: t001
aircon: t(quiet count + 1)
tv: t(quiet count + aircon count + 1)
music: t(quiet count + aircon count + tv count + 1)
```

예시: `fall_simulated`는 25 / 21 / 21 / 16 이므로

```text
quiet: t001-t025
aircon: t026-t046
tv: t047-t067
music: t068-t083
```

---

## 7. Action Manual

### 7.1 empty

- 측정 구간에 사람이 없는 상태.
- 실험자는 sender/receiver 사이에서 최소 2m 이상 떨어진다.
- 중간에 사람이 지나가면 해당 trial은 실패로 기록한다.

### 7.2 sitting_still

- 중앙 위치에 의자를 둔다.
- receiver 방향을 바라보고 앉는다.
- 손은 무릎 위.
- 발은 바닥에 붙인다.
- 고개, 손, 다리, 몸통을 움직이지 않는다.

### 7.3 standing_still

- 중앙 위치에 선다.
- receiver 방향을 바라본다.
- 발은 어깨너비.
- 팔은 몸 옆에 자연스럽게 내린다.
- 몸을 좌우로 흔들지 않는다.

### 7.4 lying_still

- 중앙 위치에 매트나 침대를 둔다.
- 천장을 보고 눕는다.
- 권장 머리 방향은 sender 쪽.
- 팔은 몸 옆에 둔다.
- 다리와 고개를 움직이지 않는다.

### 7.5 hand_move

- 중앙 위치에 선다.
- 몸통과 발은 고정한다.
- 오른손만 사용한다.
- 손은 가슴 높이.
- 좌우 약 30cm 폭으로 천천히 반복한다.
- 속도는 약 1초에 1회 왕복.

### 7.6 walking

- sender와 receiver 사이 직선 경로를 천천히 왕복한다.
- sender 30cm 앞에서 시작하고 receiver 30cm 앞에서 방향 전환한다.
- 뛰지 않는다.
- 보드를 건드리지 않는다.

### 7.7 sit_to_stand

- 의자에 앉은 상태에서 시작한다.
- 10초 안에 자연스럽게 일어나 선 자세로 끝낸다.
- 급하게 튀어 오르지 않는다.
- 마지막 2-3초는 서서 정지한다.

### 7.8 stand_to_sit

- 중앙 위치에 선 상태에서 시작한다.
- 자연스럽게 의자에 앉는다.
- 마지막 2-3초는 앉아서 정지한다.

### 7.9 stand_to_lie_normal

- 선 상태에서 시작한다.
- 정상적인 동작으로 매트/침대에 천천히 눕는다.
- 낙상처럼 쓰러지지 않는다.
- 마지막 2-3초는 누운 상태로 정지한다.

### 7.10 lie_to_stand

- 누운 상태에서 시작한다.
- 천천히 일어나 선 자세로 끝낸다.
- 마지막 2-3초는 서서 정지한다.

### 7.11 lying_normal_breath

- 누운 상태에서 평소처럼 호흡한다.
- 호흡을 과장하지 않는다.
- 몸과 팔, 다리는 움직이지 않는다.

### 7.12 lying_fast_breath

- 누운 상태에서 평소보다 빠르게 호흡한다.
- 과호흡이 올 정도로 무리하지 않는다.
- 어지러우면 즉시 중단한다.

### 7.13 lying_long_breath

- 누운 상태에서 길고 천천히 호흡한다.
- 들숨과 날숨을 평소보다 길게 한다.
- 몸을 크게 들썩이지 않는다.

### 7.14 lying_shallow_breath

- 누운 상태에서 얕고 작게 호흡한다.
- 숨을 완전히 참지는 않는다.
- 가슴/복부 움직임을 작게 유지한다.

### 7.15 lying_breath_hold_short

- 10초 trial 기준.
- 누운 상태에서 짧게 숨을 참는다.
- 무리하지 않는다.
- 불편하면 즉시 중단하고 실패 trial로 기록한다.

### 7.16 sitting_inactive_long

- 앉은 상태로 20초 동안 거의 움직이지 않는다.
- 손, 발, 고개를 움직이지 않는다.
- 장시간 무활동의 짧은 샘플로 수집한다.

### 7.17 standing_inactive_long

- 선 상태로 20초 동안 거의 움직이지 않는다.
- 균형이 흔들리면 자세를 편하게 다시 잡고 다음 trial에서 수집한다.

### 7.18 lying_inactive_long

- 누운 상태로 20초 동안 거의 움직이지 않는다.
- 정상 호흡은 하되 몸 움직임은 최소화한다.

### 7.19 fall_like_recovered

- 낙상처럼 보이는 동작을 안전하게 흉내 낸 뒤 다시 회복한다.
- 실제로 세게 넘어지지 않는다.
- 두꺼운 매트 위에서만 수행한다.
- 예: 균형을 잃은 것처럼 몸을 낮추고, 곧바로 앉거나 일어나 회복.

### 7.20 fall_simulated

- 통제된 모의 낙상.
- 반드시 두꺼운 매트에서 진행한다.
- 무릎, 팔꿈치, 머리에 충격이 가지 않게 한다.
- 실제 위험한 낙상처럼 하지 않는다.
- 통증이 있으면 즉시 중단한다.

### 7.21 post_fall_inactive

- 모의 낙상 이후 누운 상태로 움직이지 않는 상황.
- 20초 동안 누워서 정지한다.
- 머리/팔/다리를 움직이지 않는다.

### 7.22 lying_apnea_like

- 무호흡 의심 상태를 흉내 낸다.
- 20초 trial 안에서 약 10초 이상 호흡 움직임을 매우 줄이거나 잠깐 멈춘다.
- 절대 무리하지 않는다.
- 어지러움이나 불편함이 있으면 즉시 중단한다.

### 7.23 lying_breath_signal_lost

- 누운 상태에서 호흡에 의한 몸의 미세 움직임이 거의 보이지 않는 상황을 흉내 낸다.
- 숨을 오래 참는 목적이 아니라, 몸 움직임을 극도로 줄이는 것이 핵심이다.
- 정상적인 얕은 호흡은 유지한다.
- 팀에서 이 라벨 삭제가 확정되면 수집하지 않는다.

---

## 8. Before Every Run

체크리스트:

```text
1. receiver 보드가 PC에 연결되어 있는가?
2. sender 보드 전원이 켜져 있는가?
3. CSI_DATA가 들어오는 상태인가?
4. 보드 간 거리 1.50m가 유지되는가?
5. 보드 높이 80cm가 유지되는가?
6. 안테나 방향이 vertical / upward인가?
7. participant center 위치가 표시되어 있는가?
8. ambient condition을 기록했는가?
9. label과 duration이 맞는가?
10. fall/breathing 라벨은 안전하게 수행 가능한가?
```

---

## 9. Recommended Collection Order

1일차 또는 첫 세션:

```text
safe labels
```

2일차 또는 두 번째 세션:

```text
warning labels
```

3일차 또는 세 번째 세션:

```text
danger labels
```

위험/호흡 관련 라벨은 피로도가 높으므로 한 번에 몰아서 하지 않는다.

---

## 10. Important Safety Notes

- 실제 낙상을 하지 않는다.
- 모의 낙상은 반드시 매트 위에서 천천히 수행한다.
- 머리, 목, 허리, 무릎에 충격이 가면 안 된다.
- 호흡 관련 라벨은 불편하면 즉시 중단한다.
- 숨참기나 무호흡 유사는 의료 실험이 아니며, 짧고 안전한 범위에서만 흉내 낸다.
- 실패한 trial은 억지로 성공 처리하지 말고 메모하고 다시 수집한다.
