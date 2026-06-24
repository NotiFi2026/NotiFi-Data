# 2026-06-25 yja Collection Log

Subject: `yja`  
Repository: `NotiFi-Data`  
Board setup: ESP32-C6 sender/receiver CSI collection  
Dataset bundle: `yja.zip`

## Summary

Team 3 data collection for subject `yja` was organized into a single upload bundle.
The bundle includes raw CSI CSV files, visualization PNG files, and collection or
augmentation logs.

Final local bundle:

```text
/Users/yoonjeongah/Desktop/NotiFi/NotiFi-Data/yja
/Users/yoonjeongah/Desktop/NotiFi/NotiFi-Data/yja.zip
```

Google Drive destination:

```text
https://drive.google.com/drive/folders/1idY-wNY24yFioixPITnredHj11CaWbwA
```

## Final Counts

| category | count |
| --- | ---: |
| raw CSI CSV | 921 |
| visualization PNG | 921 |
| collection/synthesis logs | 6 |

## Completed Labels

Safe labels completed:

```text
empty, sitting_still, standing_still, lying_still, hand_move, walking,
sit_to_stand, stand_to_sit, stand_to_lie_normal, lie_to_stand,
lying_normal_breath
```

Warning labels completed:

```text
lying_fast_breath, lying_slow_breath, lying_irregular_breath,
unstable_walking, bed_exit_failed
```

Danger labels completed:

```text
bed_sitting_to_stand_fall, bed_lying_to_stand_fall, bed_stand_to_lie_fall,
chair_sitting_to_stand_fall, chair_stand_to_sit_fall,
post_bed_fall_inactive, post_chair_fall_inactive,
lying_apnea_like, post_fall_apnea_like, lying_convulsive_like_movement
```

Danger labels postponed:

```text
walking_trip_fall, walking_turn_fall, post_walking_fall_inactive
```

## Scripts Used

| script | role |
| --- | --- |
| `scripts/save_csi_raw.py` | Serial CSI CSV saver. |
| `scripts/team3_collect.py` | Label-aware collection runner with delay, sounds, repeat control, and PNG visualization. |
| `scripts/augment_post_fall_from_fall.py` | Creates post-fall inactive trials from fall trials. |
| `scripts/augment_warning_music_from_tv.py` | Creates music trials from collected TV trials. |
| `scripts/augment_warning_quiet_from_collected.py` | Fills missing quiet trials from collected aircon/TV trials. |
| `scripts/augment_warning_aircon_from_quiet.py` | Earlier aircon synthesis helper. |
| `scripts/augment_warning_ambient_from_quiet.py` | Earlier generic ambient synthesis helper. |

## Synthetic Data Notes

Synthetic trials are documented in `collection_logs/`.

Important synthetic operations:

| operation | log file |
| --- | --- |
| post-fall inactive from fall trials | `collection_logs/post_fall_augmentation_log.csv` |
| warning aircon synthesis | `collection_logs/warning_aircon_synthesis_log.csv` |
| warning TV/music/ambient synthesis | `collection_logs/warning_ambient_synthesis_log.csv` |
| warning music from TV | `collection_logs/warning_music_from_tv_synthesis_log.csv` |
| warning quiet from collected aircon/TV | `collection_logs/warning_quiet_from_collected_synthesis_log.csv` |

The warning quiet/music fills are useful for balancing counts, but they should be
treated as synthetic data during model training and evaluation.

## Quality Check

The dataset was checked after bundling.

| check | result |
| --- | --- |
| expected CSV files | 921/921 |
| empty CSV files | 0 |
| missing trials | 0 |
| unexpected label folders | 0 |
| metadata mismatch | 0 |
| CSI length mismatch | 0 |

One issue was found and repaired:

```text
data/warning/gait/unstable_walking/yja/yja_unstable_walking_t002.csv
```

Problem:

```text
Original t002 was only about 3.6 seconds long.
```

Repair:

```text
t002 was rebuilt from the front half of t001 and the back half of t003.
The repaired file has 1765 rows and about 19.986 seconds of timestamp span.
```

The original short file was kept locally as:

```text
yja_unstable_walking_t002.short_original.csv
```

It is excluded from the Git upload and dataset bundle.
