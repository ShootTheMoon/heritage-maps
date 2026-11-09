# JSN_Sangok2 ("sgk") — 산곡 리메이크: 5v5 대칭 3레인 전투 지형

## Context
2026-08-14에 만든 `JSN_Sangok`(조선 산곡, OVERDARE 타깃)은 **게임플레이 지형이 전혀 없는 풍경**이었다.
자체 보행성 감사(`05_Documentation/walkability.md`)가 증명했다: 60° 넘는 셀 0개, "능선" 마루가 6.7°,
2.1 m 협곡은 걸어서 넘어감 → 어디든 자유 보행. 스폰·경계·거점·콜리전 Part도 없었다.
이번 리메이크는 (1) 지형이 실제로 이동을 제약하는 **대칭 3레인 팀전 맵**으로 다시 설계하고,
(2) PolyHaven/KHS 에셋과 재료를 올려 품질을 높이고, (3) `onlyoneshot` 게임 규칙(점령전·스폰·경계)에
바로 꽂히는 완제품을 OVERDARE Studio까지 넣는 것이다.

## 확정 결정 (사용자, 2026-09-04)
- 구조 **대칭 3레인** (180° 점대칭: 양 팀 동일 루트, 미러처럼 안 보임)
- 에셋 **KHS 스캔 + PolyHaven CC0 (+ Sketchfab CC-BY는 폴백)**
- 구조물 **소규모**: 돌담·석축·정자 1채·돌탑·대나무다리·자연석계단
- 스케일 **160×120 m**, 스폰 간 도보 25~30 s
- (계획상 기본값, GATE에서 조정) 새 맵 id `sgk`를 투표에 **추가**하고 `jsn`은 기본맵으로 유지

## 제약 (실측)
- 디스크 C 여유 **11.9 GB** → 텍스처 pack 금지, 렌더 ≤1400 px, KHS/SSW 텍스처는 **절대경로 참조**(복사 금지)
- OVERDARE: 메시 ≤30k tris, **파일당 1메시 ≤27k**(벌크 임포트가 파일을 합침: 36k→0 등록, 81k→크래시), 프롭 텍스처 512, 지형 타일 1024 허용
- **UCX 콜리전 불가** → 엔진 Part(Transparency 1, CanCollide, Anchored, Static). 회전 프롭은 오리엔티드 박스
- 게임 성능 = **Workspace 인스턴스 수**가 유일한 레버(−1,331 파트 → 28→44 fps). 이전 맵 3,396개(콜리전 슬랩 1,669) → 목표 **≤1,050**
- 게임 규칙: MaxSlopeAngle **45°**, 점프 1.9 m, 캡슐 2.05×0.6 m, 크라우치/등반 없음, 걷기 7 / 달리기 11.9 m/s, FOV 100 1인칭 고정,
  국궁 화살이 맵 전체 커버 → **55 m 넘는 직선 시야 금지**, 주몽 버프 5.6 m 홉 + 11 m 슬라이드, 점령 구역은 코드가 랜덤 배치(반경·스폰거리·여백만 맵별 설정), 스폰은 반경 11 m 평지 필요
- Blender 5.2.1(Steam), blender-mcp 포크(MCP 호출 90 s 제한) → 무거운 빌드는 `blender.exe -b` 헤드리스
- **자체 승인 금지** — 각 GATE에서 사용자 렌더 리뷰

## 프로젝트 설정 (Phase 0)
새 폴더 `C:\Users\29\Desktop\blender\JSN_Sangok2\` (JSN_Sangok은 라이브 맵이라 건드리지 않음).
`00_Source_Blender\SGK_Master.blend`, `04_Previews`, `05_Documentation`, `06_OVERDARE\{01_TERRAIN,02_STATIC,10_MASTERS,_texwork,_place,_collision}`, `_TexLib\polyhaven`, `_scripts`.

| 항목 | 값 |
|---|---|
| map id / label | `sgk` / SANGOK II, sub "VALLEY 3-LANE / 160 x 120m" |
| 컨테이너 | `SGK_Sangok` (Workspace Model) |
| 스폰 / 경계 | `SGK_Spawn_Red`(서) `SGK_Spawn_Blue`(동), `SGK_Bound_North/South/East/West` — 전부 컨테이너 안 |
| 엔진 X 밴드 | 중심 X = **−30,000 cm**, Z = 0 → rect X −38,000..−22,000, Z −6,000..+6,000 (jsn −47k, 로비 0/8000, cdg +22.8k와 겹치지 않음) |
| 좌표 변환 | `X = x·100 − 30000, Y = z·100, Z = y·100, yaw = −deg(rot_z)` — **Phase 3에서 프로브 1개로 부호 확인** |

스크립트 (포크 원본):
- `sgk_layout.py` — **bpy 없는 순수 수학**: 프리미티브, `height_at`, `lane_mask`, `blend_at`, 상수. PIL 베이크가 직접 import (jsn_pure 스텁 불필요)
- `sgk_live.py` ← `jsn_live.py`: 씬 빌드·재질·물·구조물·스캐터·카메라·렌더
- `sgk_verify.py`: 단면 프로파일, 보행성+연결성분+이동시간, 시야선, 스폰 평탄도, 구역 몬테카를로, 콜리전 커버리지
- `sgk_collision.py` ← `MeshTest/ucx_lib.py:98` + `make_collision_parts.py:61`
- `sgk_placements.py` — **없던 placements.csv 라이터** (모델: `MeshTest/shibuya_export_v2.py:394 run_instances`)
- `sgk_studio.py`: 컨테이너/스폰/경계 items JSON + `MapService_1.lua` sgk 항목 텍스트
- `ovd_*.py` 포크: `EXTENT_X=160, EXTENT_Y=120, TILES 4×3`, `TABLE = onlyoneshot\UGCLocalAssetTable.json`
- `run_headless.py`: `blender.exe -b <blend> --python run_headless.py -- <stage>` (패턴: `MeshTest/run_bake_headless.py`)

## 레이아웃 스펙 (Blender m, Z-up, +Y 북, 원점 = 맵 중심)
- 플레이 rect **x∈[−80,80], y∈[−60,60]**, 메시 220×180. 외곽 산벽 `r=max(|x|/80,|y|/60)>1`에서 30 m 상승(≈54°), 스커트 −40 m
- 바닥 `z_floor = −0.017·x` (동쪽으로 2 m 기울어 계류가 흐름). **모든 서쪽 프리미티브 P(x,y)를 P(−x,−y)에도 적용**

| 요소 | 좌표 (서쪽 절반) | z (바닥 기준) | 비고 |
|---|---|---|---|
| 서 스폰 디스크 | (−63,−4) r12 | +2.5 평지 ≤5° | 나무·바위 keep-out r14, 상공 개방. 동 스폰 (+63,+4), 간격 126 m |
| 북 지릉 마루 (서팀 능선) | (−48,34)→(−40,28)→(−26,17)→끝 (−14,9) | 11→10→8.5→7.5 | 마루 폭 6 m, (−34,23)에 2 m 굴곡으로 직선 끊기 |
| 계류 쪽 사면 | 7~10 m | **58° 절벽** | R2·T 외 통과 불가 |
| 뒷면 사면 | 8~10 m | **50° 절벽** | R3 외 통과 불가 ("언덕화" 방지) |
| R1 자기편 진입 | (−60,30) z3 → (−48,34) z11 | 34°, 폭 8 | 스폰 마당→능선 |
| R2 계류변 선반 | (−22,12) z1 → (−34,22) z10 | 24°, 선반 3 m (자연석계단) | 계류↔능선 교차 |
| R3 뒷면 램프 | (−32,32) z1.5 → (−28,19) z9 | 35°, 폭 5 | 적이 북측 띠에서 능선 진입 |
| T 끝단 계단 | (−14,9) z7.5 → (−6,3) z0.3 | 30°, 폭 4 | 능선→중앙 양방향 |
| 끝단 낙차 | 그 외 끝단 가장자리 | 7~7.5 m | 전원 일방통행 (주몽 5.6 m 홉도 못 올라옴) |
| 노즈 턱 | R1 남측 (−52,22) | 3.5 m | 주몽만 복귀 가능 — **GATE 1 결정: 유지 or 6 m로** |
| 계류 | `y_s(x) = −7·sin(πx/60)` (|x|≤60, 72에서 소멸, 가장자리까지 안 감) | 바닥 −1.8, 수면 −1.4 | 상폭 6, 바닥 2, 벽 58°. 점프로 탈출 가능(1.9>1.8) 허용 |
| 도섭 | x = −42(폭 8), 0(다리+징검돌), +42 | 둔치 25°, 깊이 0.6 | 3곳 |
| 중앙 분지 | (0,0) r15 | −0.5 | 1차 거점 |
| 초정(정자) | (0,+9) 5×5 석축 1.2 m 위 | | 미러 (0,−9): 5×5 석축 + 돌탑 1.6 m (정자 1채 존중, 엄폐 면적 동일) |
| 투죽위교 | x=0 남북 | 데크 +0.5 | 계류 레인 정체성 |
| 숲길 (서팀) | (−55,−16)→(−40,−30)→(−20,−36)→(0,−38)→(20,−44)→(40,−46)→(56,−40)→동 마당 (60,−24) | ±1 m 기복 | 5 m 통로, S커브로 56 m 직선 절단 |
| 남 개활지 교차 | (0,−36)→(0,−14) | +2→−0.5 | 폭 12, 돌담 L자 (0,−26) |
| 돌담 (9 m, 높이 2.0) | (−40,−30) yaw30°, (−6,−27) L, (34,−46) yaw−20° | | 대칭 포함 6개 |
| 북측 띠 (자기 지릉 뒤) | x∈[−60,−10], y∈[마루+10, 56] ≈ 14 m | +1.5 | 밀림·바위. 적은 NE 사분면에서 진입 |

- 팀별 루트(회전 대칭으로 동일): **좌 = 능선**(R1→마루→T, 자기 계류와 적 숲길 감시) / **중 = 계류**(저지대, 둔치 1.8 m, 도섭 3) / **우 = 숲**(자기 사분면→적 지릉 절벽 밑→적 북측 띠→적 마당 or R3)
- 초크 폭: R1 8 / R2 3 / R3 5 / T 4 / 도섭 8 / 개활지 12 / 북안 턱 3~4 / 숲길 5(회랑 20)
- 엄폐 배치 존만 허용: 분지 림 6 (r10~14, 1.5~2.5 m), 계류변 3 (x≈±35, ±12), 숲길 가장자리(담+바위 15 m마다 지그재그), 마루 노두(주상절리 8/지릉, 절벽쪽 난간처럼), 북측 띠 너덜
- 경사 규칙: 루트 ≤38°, 차단면 ≥50° (**42~48° 금지**: 보이지 않는 벽 느낌), 평지 ≤5°, 낙차 7~7.5(전원 일방) 또는 3.5(주몽 복귀), 능선 7.5~11, 산벽 30
- 구역 파라미터(cm): `zoneRadius 900`, `minSpawnDist 3500`, `edgeMargin 2500` → 후보 박스 110×70 m 중 64.5% 통과, 20회 연속 실패 확률 ≈1e-9 (jsn의 6500이면 90% 배제 → 구역 안 움직임). |Δy|≤10 m 판정은 마루 가장자리 5 m 띠만 걸림 → MC로 보고
- 이동시간: 스폰↔스폰 직선 126 m, 계류 레인 ≈135, 능선→중앙 ≈85, 숲→적 마당 ≈150. **`moveScale 0.85` 제안**(걷기 23 s, 달리기 14 s) — GATE 3에서 조정
- 스폰 스냅: `snapRise 3000, rayTop 9000, rayLen 22000, groundY 250`

## 지형 저작 (`sgk_layout.py`)
- 합성 순서 **가산 → 절삭 → 산벽**: `h = z_floor + Σ(ridge, plateau, noise·(1−flat))`; 이후 `(mask,target)` 절삭을 `lerp`로 (계류, R2/T 선반, 스폰 디스크, 개활지); 마지막 `wall()`
- 프리미티브: `plateau(cx,cy,r,h,soft)`, `ridge(polyline, top_w, z_profile, slope_L, slope_R)` (폴리라인 부호거리, 외적으로 좌우, 마루 평탄 후 `tan(slope)` 하강), `ramp(p0,p1,w,z0,z1)` 절삭, `trench(center_fn, top_w, bed_w, depth, wall_deg, fords)`, `noise` = `jsn_live.py:212` 3옥타브(바닥 0.35 / 숲 0.9), `sym(prim)`
- `lane_mask(x,y)` → {spawn, stream, ford, crest, cliff, ramp, path, glade, strip, bowl, wall} 0..1 — **재질·스캐터·콜리전·보행성·레이아웃 맵이 전부 이 하나를 읽는다**
- `blend_at`: R 흙/길, G 암반(`smoothstep((s−0.42)/0.55)` + cliff 0.9, 산벽 근처 완화), B 젖은 자갈, **A 솔잎 낙엽** → 6-way 재질(`_terrain_material :360` 확장, Object+BOX, 노이즈 MapRange 0.08~0.42)
- 격자 **0.5 m**: 320×240 = 153,600 tris; 타일 40 m 4×3 → **12,800 tris/타일**(0.4 m로 내려도 20k). 최소 지형 특징 폭 1.5 m(3셀). 산벽은 1 m 격자 별도 메시 4장(N/S 13.2k, E/W 7.2k)
- 물: `make_water :707`을 호 길이 파라미터화, 법선 단면, 양측 수변 이분법 24회, `Flow` 정점색(R 유속, G 둔치) — 1메시 ≈3.8k
- **`verify_layout()`이 PASS 찍기 전엔 렌더 금지**: 마루 폴리라인·R1/R2/R3/T·양 사면 각 6 단면·계류 8 단면·도섭·스폰·개활지 수치 단면 출력

## 품질 (Phase 2)
- **재질**: PolyHaven **1k** (`download_polyhaven_asset` → %TEMP%에서 `_TexLib\polyhaven\<asset>\`로 복사·리패스): `aerial_grass_rock`(풀), `brown_mud_leaves_01`(솔잎 A채널), `brown_mud_dry`(길), `brown_mud_rocks_01`(젖은), `aerial_rocks_02`(암반2). 절벽은 KHS `T_MDS_UnitA_BC/N/R` 유지. 타일 거리 4/3.5/3/3/6 m. 익스포트 베이크 1024/40 m = 25.6 px/m (구버전 15.8)
- **식생** ≈532: PolyHaven `pine_tree_01` → **크기별 마스터 3종**(M 14 / L 18 / XL 22 m, 산벽용) — 런타임 스케일 불필요; `prep_veg` 아일랜드 시닝 ≤27k; 수피는 `tune_pine :1180` 방식으로 적송 그라디언트(부위는 텍스처 파일명으로 판별). `pine_sapling_medium/small` 50, `tree_stump_01`·`dead_tree_trunk` 12, `fern_02` 60, **억새·물쑥 기존 ID 재사용** 40/30. 전나무는 제외(고산 느낌). 클럼프 시드 12 m 격자, 4~7주, 밀도는 `lane_mask`(길·스폰·마루·램프·계류 0, 띠 0.3, 숲 0.9, 산벽 1.0). 하층은 레인 8 m 이내와 분지만. 잔돌은 삭제(텍스처로)
- **바위**: `boulder_01`(1.5 / 3 m 두 마스터), `coast_rocks_01/03`, `namaqualand_boulder_02` → 신규 5 마스터(`prep_rock :97` 방식 ≤27k); 마루 난간은 기존 `MST_ROCK_A/D/E` 16개. ≈52개, 콜리전은 1.2 m 이상만. `mountainside`·ROCK_MASS 제외
- **구조물** (SSW `_extracted`, `ssw_live.py:649/718/753`로 임포트·배선, **Phase 0에서 tris 실측**): 초정 `Chojeong_Pavilion.fbx`(4.8×4.7×3.9 m, 처마 밑 헤드룸 ≥2.7 m 확인, 재질 4→1 아틀라스), 투죽위교(길이 vs 상폭 6 m 확인), 담장 `Stonewall.fbx`(3.0×0.79×3.3 → 0.6 배 베이크, 5장 조인 = MST_WALL_9M, 3+2 = MST_WALL_L), 화계(석축, 무거우면 평면 데시메이트), 자연석계단은 **참조만**(계단은 `make_steps :831` 방식 절차 슬랩 → `STA_STEPS` 1메시), 돌탑은 절차(`_pebble_mesh :1590` 스택)
- 물 재질 `_water_material :580` 유지, 라이팅 `make_lighting :910` + 그라디언트 스카이, EEVEE `use_raytracing` on. HDRI는 프리뷰 전용(1k)
- **인스턴스 예산** (하드 ≤1,200, 목표 ≤1,050): 지형 12 + 산벽 4 + 물 1 + 계단 1 = 18 / 구조물 11 / 바위 52 / 식생 ≤532 / 콜리전 ≤420 / 스폰·경계·컨테이너 7 → **≈1,040**. 렌더 MeshPart는 `canCollide=false, canQuery=false`(스폰·구역 레이캐스트가 COL Part를 맞도록)

## 콜리전 (`sgk_collision.py`)
- `lane_mask` 구역별: **계류/도섭** → 8 m 호 구간마다 바닥 박스 + 둔치 박스 2(58°/25° 피치, yaw = 접선) ≈57 / **절벽 띠** → 6 m마다 피치 슬랩 ≈28 / **나머지** → 쿼드트리 + 셀별 **최소자승 평면 피팅**(`adaptive_boxes :98`의 평탑 대신), 잔차 ≤0.25 m 허용, 셀 2~16 m, 오리엔티드 Part(두께 1.0, skin 0.15) ≈355
- 바위·담·구조물: 로컬 bbox × 인스턴스 yaw 오리엔티드 박스 (`make_collision_parts.py:121–157`). 계단은 없음(지형 슬랩이 램프를 따름)
- rect 밖은 콜리전 없음(경계가 죽임). 출력 `06_OVERDARE\_collision\items_col_NNN.json`(200/청크), 이름 `COL_TER_%04d`, `COL_ROCK_*`, `COL_WALL_*`

## 검증 (`sgk_verify.py`, 매 Phase, 결과 → `05_Documentation\`)
1. `verify_layout()` 수치 단면 → `profiles.txt`
2. `walkability()`(`:1763` 포크, 1 m 셀, rect, WALK 40 / SCRAMBLE 45 / 차단 >45, 바위 원판) → **연결성분 1개 ≥95%**; 키포인트: 스폰 2, 마루 끝 2, R1/R2/R3 상단, 도섭 3, 개활지, 띠, 분지. 히트맵 `walkmap.py` 포크
3. 이동시간: 보행 격자 A*, 비용 = 길이/(v·max(0.5, 1−deg/90)) → 레인별 스폰→중앙·스폰→스폰 걷기/달리기 → `travel.json` (목표: 계류 걷기 18~24 s, 능선→중앙 12~15 s)
4. 시야선: 눈높이 +1.7에서 서 스폰 중심·디스크 N/S 가장자리·NW 끝·마루 중간 (−32,21)·R2 상단·숲길 노드·띠 노드·분지 중심 → 전 레인 중심선 5 m 샘플 + 적측 대응점. 하드 차폐 = 지형 BVH + 바위/구조물 박스, 소프트 = 소나무 줄기 r0.35 + 수관 구. **레인 간 하드 직선 >55 m면 FAIL** → `sightlines.md`
5. 스폰 디스크: r12 1 m 샘플 경사 ≤5°, z 범위 ≤0.6, 14 m 내 인스턴스 0, 상공 수관 없음
6. 구역 MC: `CaptureServer.lua:272–308 pickSpot` 그대로 200회 → 통과 %, >40° %, 계류 안 %, 마루 %, r9 안 마루 낙차>5 % → `zone_mc.json` (기대 통과 ≥60%, >40° ≤8%)
7. 렌더 ≤1400 px: Top ortho, Survey, SpawnW/E_POV(16 mm ≈ FOV 100), Bowl, CrestNW, ForestMid, StripN + 레인별 walkthrough 9장
8. 익스포트: `MeshTest/verify_export.py`(≤30k/메시, 파일당 렌더메시 1, 이미지 존재, ≤15 MB) + bbox ±5%
9. 콜리전 커버리지: rect 안 1 m 격자에서 `Part 상단 − height_at` ∈ [−0.05, +0.35]가 보행 셀의 ≥99%, 음수 0 → `collision_cov.json`
10. Studio 플레이테스트 체크리스트 (Phase 3)

## Phase & GATE
### Phase 0 — 셋업·포크 (게이트 없음, 파일 트리 보고)
폴더·스크립트 골격·`run_headless.py`. **실측**: 소쇄원 FBX 6개 + `pine_tree_01`을 스크래치 blend에 임포트해 tris/치수/재질 → `asset_survey.md`. `get_polyhaven_status`/`get_sketchfab_status`. `onlyoneshot\UGCLocalAssetTable.json`에서 기존 `MST_ROCK_A..F, MST_PINE, MST_EULALIA, MST_ARTEMISIA` ID 회수(`ovd_place_build.refresh_ids :24`).

### Phase 1 — 레이아웃 블록아웃 → **GATE 1**
`sgk_layout.py` 완성, `sgk_live.py`(`make_terrain`, `make_water`, `make_lighting`, `make_cameras`, `make_blockouts`: 정자 5×5×4·다리 2×7×1·담·석축 박스, 스폰 12 m 색 원반, 경계 16 m 얇은 판), `sgk_verify.py` 1~7. 지형 재질은 lane_mask 디버그 색 + 풀 1종. **측정 통과 후** Top/Survey/POV×2/Bowl/CrestNW 렌더 + 표(이동시간·시야선·MC) → **사용자 리뷰**. 수정은 `sgk_layout.py` 숫자만.
GATE 1 결정 항목: 노즈 턱 3.5 m 유지/6 m, 바닥 2 m 기울기, 정자 vs 석축+돌탑 비대칭.

### Phase 2 — 드레싱 → **GATE 2**
6-way 지형 재질, `import_polyhaven`(복사·리패스), `import_khs`(SSW 배선), `make_steps`→`STA_STEPS`, `make_cairn`, `scatter_*`(lane_mask 기반, `_instance :1277` 공유 메시, `_h01 :1262`, `_off_limits` 재작성, CAM_KEEPOUT에 수관 반경 포함), `place_structures`(height_at 싱크), `scene_report :1707`, `export_manifest :1905`.
측정: 인스턴스 표 vs 예산, 고유 메시 ≤30, 마스터 tris ≤27k(ovd_masters 드라이런), 메시당 텍스처 1, `packed_images == 0`, 렌더 8캠 + 레인 워크스루 3, 검증 2/4/5/6 재실행(프롭 포함) → **사용자 리뷰**.

### Phase 3 — 익스포트·Studio → **GATE 3**
1. `ovd_textures`(512 BC+OP, 지형 소스 1024) → `ovd_atlas`(정자/다리/담/소나무) → `ovd_masters`(TRI_CAP 27000, 크기별 소나무, `export_fbx :169` 파일당 1메시) → `ovd_terrain.bake_tiles`(4×3 + 산벽 4) → `ovd_static.split_terrain`(rect 타일, 월드좌표, 타일별 UV), `prep_water`, `STA_STEPS`
2. `sgk_placements.py` → `placements.csv`; `sgk_collision.py` → `items_col_*.json`; `sgk_studio.py` → `items_studio.json` + `MapService_sgk.lua`
3. `verify_export.py` PASS + 콜리전 커버리지 PASS (자체 체크포인트)
4. Studio: 플레이테스트 정지 → `SGK_Sangok` Model → `JSN_Spawn_*`/`JSN_Bound_*`를 `overdare_duplicate_instance`로 복제·개명·재부모(North [16200,1600,50] Z+6000, South Z−6000, East [50,1600,12200] X−22000, West X−38000; 스폰 (−36300,300,−400)/(−23700,300,+400)). FBX 37개 **`overdare_mesh_bulk_import` 파일당 1회, `bundleName = stem`**, 세션당 ≤12파일(3유닛×12=36/40), 세션 사이 Studio 재시작, 재개 전 `ovd_import_state.py` 장부 확인(**재임포트 = 중복 발행, 되돌릴 수 없음**). 순서: 정적 17 → 구조물 6 → 바위 5 → 식생 8
5. **프로브 (대량 배치 전)**: 스케일 — `MST_PINE_M` 3개 size [100]/[200]/[50], `canQuery=true`, Lua 10줄로 레이캐스트 높이 출력 → 14/28/7 = percent, 14/14/14 = 무시(unit 가설 재시도, 그래도 14면 스케일 포기 → 크기별 마스터만). 좌표/yaw — NW 끝 바위 1 + (−40,−30) yaw30° 담 1 스크린샷, 사분면 틀리면 `sgk_placements`에서 Z 부호 반전
6. 정적 배치(`items_static.json`, `size`를 bbox로 명시 — `make_placement_items.py:110`) → `place_NNN.json` `overdare_create_instances(parent="Workspace.SGK_Sangok")`, 청크마다 `overdare_save` → 콜리전 청크
7. Lua: `MapService_1.lua` `M.MAPS`에 `sgk` 추가 + `M.ORDER`에 `"sgk"` (`DEFAULT="jsn"` 유지), 테스트 세션만 `DEBUG_FORCE="sgk"`. 스크립트 반영은 `overdare_script_edit`. `LobbyUI.lua:652` 카드 5개 렌더 확인
8. 플레이테스트 체크: Play.log `[Team] SGK_Spawn_* 바닥에 붙임` Y≈250~300, `[Map] jsn -> sgk`, 경계 rect ±8000/±6000 @ −30000, 1차 거점 = 다리, 90 s마다 이동·지면 안착 ≥3회(MC와 비교), 레인별 도보(R1/R2/R3/T/도섭 통과, 절벽 등반 불가), 정자 밑 서기, 다리 건너기, 계류 점프 탈출, 양 끝단 시야 확인, 로비·중앙 fps vs 기준 44 → `DEBUG_FORCE=nil`. **사용자 플레이 승인 → GATE 3.** 사후 튠: `zoneRadius`, `minSpawnDist`, `moveScale`

## 리스크·미지수
- 스케일 의미론 미확인 → §Phase 3-5 프로브; 파이프라인은 스케일 1.0만 의존(크기별 마스터)
- 소쇄원 킷 무게 미실측(FBX 0.3~1.7 MB → 5~30k 추정) → Phase 0 실측, 박스형은 평면 데시메이트만(콜랩스 금지)
- PolyHaven 용량: 1k만(총 ≈150 MB), %TEMP% 정리; `pine_tree_01` 잎 카드가 27k로 못 내려오면 Sketchfab 팩(CC-BY 크레딧 파일 + 게임 설명 문구) 또는 기존 곰솔 재틴트로 폴백
- `download_polyhaven_asset`이 이미지를 pack하거나 temp 경로를 남길 수 있음 → 저장 전 `bpy.data.images` filepath/packed_file 감사
- SeamFiller는 `seam = { enabled = false }` (타일 CanCollide off + 연속 Part 콜리전이라 불필요)
- 빌드 중 Workspace에 맵 2개 → Studio fps 저하만; MapService 항목 생기면 `cleanupStrayMaps`가 비기본 맵을 파킹
- 정자 헤드룸·다리 스팬 미측정 → 폴백: 통 콜리전 박스 / 계류 절삭 확폭

## 핵심 파일
- 포크 원본 `C:\Users\29\Desktop\blender\JSN_Sangok\_scripts\jsn_live.py` — `height_at :164`, `blend_at :243`, `_pbr :316`, `_terrain_material :360`, `_water_material :580`, `make_water :707`, `make_steps :831`, `make_lighting :910`, `make_cameras :957`, `_import_fbx_file :1013`, `_wire_mat :1041`, `tune_pine :1180`, `_h01 :1262`, `_instance :1277`, `_off_limits :1305`, `scatter_pines :1364`, `_pebble_mesh :1590`, `walkability :1763`, `walkthrough :1991`
- 익스포트 체인 `JSN_Sangok\_scripts\ovd_textures.py / ovd_atlas.py / ovd_masters.py(:97 prep_rock, :169 export_fbx, :260 prep_veg) / ovd_terrain.py(:42 bake_tiles) / ovd_static.py(:64 split_terrain) / ovd_place_build.py(:24, :46) / ovd_import_state.py`
- 콜리전·검증 `C:\Users\29\Desktop\MeshTest\ucx_lib.py:98 adaptive_boxes`, `make_collision_parts.py:61 part / :121–157`, `shibuya_export_v2.py:394 run_instances`, `verify_export.py:53`, `run_bake_headless.py`
- 소쇄원 킷 `C:\Users\29\Desktop\blender\SSW_Soswaewon\_extracted\{Chojeong_Pavilion,Tujugwigyo,Stonewall,Hwagye,Stair}` + `_scripts\ssw_live.py:649 _do_import / :718 _find_maps / :753 wire_materials`
- 게임 계약 `C:\Users\29\Desktop\onlyoneshot\Lua\MapService_1.lua`(jsn 항목 :61–125 → sgk 항목 추가, `M.ORDER :33`), `CaptureServer.lua:272 pickSpot`, `TeamServer.lua:144 snapToGround / :200 SPAWN_SPREAD`, `BoundaryServer_1.lua:130 readRect`, `MovementSpeedServer_6.lua:16–22`, `SeamFiller.lua:16 MaxSlopeAngle`
