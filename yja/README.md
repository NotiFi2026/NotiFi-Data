# yja CSI Dataset Bundle

Subject: `yja`  
Collector: Team 3 / 윤정아  
Date: 2026-06-25  
Project: NotiFi

This folder tracks the scripts, logs, manifest, and dated notes for the `yja`
CSI dataset bundle. The large raw CSV files and visualization PNG files are kept
in Google Drive, not GitHub.

## Drive Upload

Google Drive folder:

```text
https://drive.google.com/drive/folders/1idY-wNY24yFioixPITnredHj11CaWbwA
```

Local upload files:

```text
/Users/yoonjeongah/Desktop/NotiFi/NotiFi-Data/yja
/Users/yoonjeongah/Desktop/NotiFi/NotiFi-Data/yja.zip
```

## Bundle Contents

| item | count |
| --- | ---: |
| raw CSI CSV | 921 |
| visualization PNG | 921 |
| collection/synthesis logs | 6 |

## Tracked Contents

| path | purpose |
| --- | --- |
| `README.md` | This subject-level summary. |
| `MANIFEST.json` | Counts and local bundle metadata. |
| `scripts/` | Scripts used during collection, visualization, repair, and augmentation. |
| `collection_logs/` | CSV provenance logs for direct collection and synthetic data generation. |
| `docs/logs/2026-06-25-yja-collection.md` | Human-readable dated work log. |

## Final Label Counts

### Safe

| label | count |
| --- | ---: |
| `empty` | 66 |
| `sitting_still` | 22 |
| `standing_still` | 22 |
| `lying_still` | 22 |
| `hand_move` | 33 |
| `walking` | 34 |
| `sit_to_stand` | 17 |
| `stand_to_sit` | 17 |
| `stand_to_lie_normal` | 17 |
| `lie_to_stand` | 17 |
| `lying_normal_breath` | 67 |

Safe total: 334

### Warning

| label | count |
| --- | ---: |
| `lying_fast_breath` | 66 |
| `lying_slow_breath` | 67 |
| `lying_irregular_breath` | 67 |
| `unstable_walking` | 66 |
| `bed_exit_failed` | 67 |

Warning total: 333

### Danger

Completed:

| label | count | source |
| --- | ---: | --- |
| `bed_sitting_to_stand_fall` | 26 | direct |
| `bed_lying_to_stand_fall` | 27 | direct |
| `bed_stand_to_lie_fall` | 27 | direct |
| `chair_sitting_to_stand_fall` | 26 | direct |
| `chair_stand_to_sit_fall` | 27 | direct |
| `post_bed_fall_inactive` | 27 | synthetic from fall trials |
| `post_chair_fall_inactive` | 27 | synthetic from fall trials |
| `lying_apnea_like` | 23 | direct |
| `post_fall_apnea_like` | 23 | direct |
| `lying_convulsive_like_movement` | 21 | direct |

Postponed:

| label | planned count | note |
| --- | ---: | --- |
| `walking_trip_fall` | 27 | postponed |
| `walking_turn_fall` | 26 | postponed |
| `post_walking_fall_inactive` | 26 | postponed |

## Quality Check

Final local quality check after repair:

| check | result |
| --- | --- |
| expected CSV files | 921/921 |
| empty CSV files | 0 |
| missing trials | 0 |
| unexpected label folders | 0 |
| metadata mismatch | 0 |
| CSI length mismatch | 0 |

Repair:

```text
data/warning/gait/unstable_walking/yja/yja_unstable_walking_t002.csv
```

The original file was only about 3.6 seconds long. It was rebuilt from the front
half of `t001` and the back half of `t003`, then timestamp-normalized to about
20 seconds. The original short file is excluded from Git and the Drive bundle.

## Synthetic Data Notes

Some balancing data was generated synthetically. These files should be marked or
handled carefully during model evaluation.

| operation | log file |
| --- | --- |
| post-fall inactive from fall trials | `collection_logs/post_fall_augmentation_log.csv` |
| warning aircon synthesis | `collection_logs/warning_aircon_synthesis_log.csv` |
| warning ambient synthesis | `collection_logs/warning_ambient_synthesis_log.csv` |
| warning music from TV | `collection_logs/warning_music_from_tv_synthesis_log.csv` |
| warning quiet from collected aircon/TV | `collection_logs/warning_quiet_from_collected_synthesis_log.csv` |

## Main Scripts

| script | role |
| --- | --- |
| `scripts/save_csi_raw.py` | Save serial `CSI_DATA` rows as CSV. |
| `scripts/team3_collect.py` | Run planned Team 3 collection sets with sounds, delay, repeats, and visualization output. |
| `scripts/augment_post_fall_from_fall.py` | Generate post-fall inactive trials from fall trials. |
| `scripts/augment_warning_music_from_tv.py` | Generate warning music trials from TV trials. |
| `scripts/augment_warning_quiet_from_collected.py` | Fill missing warning quiet trials from collected aircon/TV trials. |
