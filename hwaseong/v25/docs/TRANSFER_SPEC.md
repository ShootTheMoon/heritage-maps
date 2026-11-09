# 화성 v25 → OVERDARE 이관 명세서 (산곡 리버전 규약 준용)

2026-09-09. 기준 문서: `JSN_Sangok2\SGK_이관_명세서.md`, `06_OVERDARE\IMPORT_GUIDE.md`, `_scripts\sgk_export.py`. 화성 옛 명세서(`OVERDARE_화성_이식_명세서.md`)의 "Orientation 전부 0" 규약은 **폐기**하고 산곡 확정판을 따른다.

## 규약 (산곡 그대로)

| 항목 | 값 |
|---|---|
| FBX | 1 파일 = 1 메시, ≤27,000 tri(collapse), `axis_up Y / forward -Z / FBX_SCALE_NONE`, 텍스처 디스크 PNG `path_mode COPY`, pack 금지 |
| 재질 | 재질 1 = 텍스처 1장(Base Color만), ≤1024² (1024×2048 은 알파 폐기), 알파는 엔진이 안 씀 → 잎은 실루엣 컷 + 인필 |
| 좌표 | `X = x·100 + X0`, `Y = z·100`, `Z = −y·100`, `yaw = rot_z + 180(MESH_YAW_FIX)`. Size = bbox 실치수 cm, Y/Z 스왑 |
| 배치 | 정적물(성곽·지형·문)은 월드좌표 FBX → 컨테이너 원점 + X0. 마스터(담장 모듈·소품·나무)는 바닥중심 피벗 → placements.json 인스턴스 |
| 콜리전 | 지형 메시는 못 걷는다 → Part 슬랩(쿼드트리 16→2 m, 두께 1 m, `Transparency 1 / CanCollide / Material Unlit`) |
| 임포트 | 세션당 ≤12 파일, 재임포트 금지(중복 발행), 프로브 3종(yaw 180·Size·슬랩 부호) 먼저 |
| 컨테이너 | `Workspace.HWS_Hwaseong`, **X0 = −58000**(창덕궁 겹침 회피, hwaseong-handover-spec). 산곡 X0 −30000 컨테이너와 비겹침 확인 필요(산곡 X 범위 ±?) |

## 산출 계획 (폴더 `ovdr_export\hwaseong_v25\`)

| 단계 | 내용 | 산출 | 상태 |
|---|---|---|---|
| 1 JAM | Sketchfab KCISA 원본 75 메시(문짝 제외 67) → 재질별 1 FBX, ≤27k collapse(원본은 collapse 정상 — v24 파생본과 다름), 텍스처 1024 PNG | `01_JAM\HWS_JAM_##_<mat>.fbx` 67개, 1.02M tri | **완료** |
| 2 DOORS | 문짝 8 메시 + 힌지 4(`manifest.doors`: pivot_world_m, open_deg ±88). Studio 에서 TweenService 로 힌지 기준 회전 | `02_DOORS\HWS_DOOR_*.fbx` 8개 | **완료** |
| 3 MASTERS | 담장 모듈 3(NH_WALL 2재질·PARAPET·SECRETGATE 3재질 → 1텍스처 베이크, 익스포트 사본에서만), BlenderKit 소품 3(항아리·술통·짚단) | `10_MASTERS\*.fbx` 6개 + 인스턴스 78+15 | 예정 |
| 4 TERRAIN | 지면 2메시(정점색 6-way) → 40 m 타일 1024² 베이크(안쪽 5×4=20) + 외곽 100 m 타일 12장, 각 ≤27k tri. 콜리전 Part 슬랩 = `relief()/berm()` 로 sgk_collision 방식 | `03_TERRAIN\HWS_TER_xy.fbx`, `_collision\*.json` | 예정 |
| 5 VEG | 나무 690·고사리 70·억새 55·쑥 16·바위 8·그루터기 6·고목 3 = **FBX 없음**. 산곡이 이미 발행한 MST_* 에셋 ID(`JSN_Sangok2\06_OVERDARE\asset_ids.json`, 48건) 재사용 → placements.json | `placements_veg.json` | 예정(같은 Studio 프로젝트일 때만) |
| 6 PLACE | 정적 21+67+8 → items_static, 마스터 인스턴스 → `_place\place_###.json`(200개 청크), Lua MapService 등록 | json | 예정 |

## 예산

- 인스턴스: 정적 96 + 담장 78 + 소품 15 + 식생 848 + 콜리전 슬랩(추정 400) ≈ 1,450 (산곡 2,330, 로비 44 fps). 외곽 나무 564 는 절반으로 줄이거나 12 m 간격으로 재산포 권장.
- 삼각형: JAM 1.02M 은 과함 → 2차 감축(캡 12k) 검토. 산곡 총량 참고치 없음 → 프로브 후 fps 실측으로 결정.

## 열린 질문

1. 화성을 산곡과 **같은 onlyoneshot 프로젝트**에 넣는가? (예 → 나무·소품 848개는 재발행 없이 ID 재사용)
2. JAM 1.02M tri 를 그대로 갈지, 캡을 12k 로 내려 ~45만으로 갈지.
3. 지면 타일 크기 40 m(산곡) 유지 여부.

## 진행 기록 (2026-09-09 밤)
- 1 JAM 67 FBX(1.02M tri) · 2 DOORS 8 · 3 MASTERS 6(담장 모듈은 재질 2~3개 그대로 → 유닛 2~3, 소품 3) · 4 TERRAIN 30 타일(안쪽 40 m 20 + 외곽 100 m 10, 1024 베이크 확인) · 콜리전 541 슬랩(안쪽 399, 외곽은 16 m 이상 굵게) — 모두 텍스처 검사 통과.
- `scene_dump.json`(마스터 6·인스턴스 941·정적 105) → `hws_place.py` → `items_static.json` 105, `_place\place_000~004.json` 941(식생 848 은 산곡 asset_ids 로 meshId 채움), `placements.csv`.
- meshId 미해석: 정적 105 + 마스터 6 은 Studio 발행 후 `python hws_place.py <UGCLocalAssetTable.json>` 로 재실행하면 채워진다(bundleName = 파일 stem).
- 다음: Studio 프로브 3종(yaw 180·Size·슬랩 부호) → 12파일/세션 발행(JAM 67 은 6세션) → 배치 → Lua(MapService 등록, 문 TweenService).
