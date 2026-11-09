# SGK Studio 벌크 임포트 순서 — 이 PC(HSP) 용 (최종, 2026-09-06)

이 PC 에는 임포트 RPC 가 없다. **Studio GUI 에서 사람이** 아래 순서대로 벌크 임포트한다. 세션당 ≤12 파일(유닛 36/40 캡), 세션 사이 **Studio 재시작**.
재임포트 = 중복 발행(되돌릴 수 없음). 파일명이 곧 에셋 이름이다(`_overdare` 접미가 붙을 수 있음). 지형·정적은 `SGK_` 접두라 산옥(JSN) 에셋과 겹치지 않는다.

## 절차
1. Studio 에서 `onlyoneshot` 열기, 플레이테스트 정지.
2. `_scripts\sgk_place.ps1 -Check` → 이미 테이블에 있는 이름이 0개인지 확인 (있으면 그 파일은 건너뛴다).
3. `_scripts\sgk_place.ps1 -Snapshot` → before_ids.txt (임포트 직전에 다시!).
4. 세션 1 임포트 → Studio 재시작 → `-Resolve` 로 세션 1 파일이 전부 잡히는지 확인 → 세션 2 … (세션마다 확인하면 실패를 바로 잡는다).
5. 전부 끝나면 `-Resolve`(43/43 + 재사용 5) → `-Probe -Apply` → 플레이테스트 확인 → `-Apply` → `-Lua -Apply`.

총 43 파일 = 지형 18 + 정적 4 + 마스터 21 (+ 재사용 5: MST_EULALIA/ARTEMISIA/ROCK_A/D/E — 임포트 금지)

## 세션 1 (12 파일)

- [ ] `01_TERRAIN\SGK_STA_TER_00.fbx`  tris 12800  tex `SGK_TER_00`
- [ ] `01_TERRAIN\SGK_STA_TER_10.fbx`  tris 12800  tex `SGK_TER_10`
- [ ] `01_TERRAIN\SGK_STA_TER_20.fbx`  tris 12800  tex `SGK_TER_20`
- [ ] `01_TERRAIN\SGK_STA_TER_30.fbx`  tris 12800  tex `SGK_TER_30`
- [ ] `01_TERRAIN\SGK_STA_TER_01.fbx`  tris 12800  tex `SGK_TER_01`
- [ ] `01_TERRAIN\SGK_STA_TER_11.fbx`  tris 12800  tex `SGK_TER_11`
- [ ] `01_TERRAIN\SGK_STA_TER_21.fbx`  tris 12800  tex `SGK_TER_21`
- [ ] `01_TERRAIN\SGK_STA_TER_31.fbx`  tris 12800  tex `SGK_TER_31`
- [ ] `01_TERRAIN\SGK_STA_TER_02.fbx`  tris 12800  tex `SGK_TER_02`
- [ ] `01_TERRAIN\SGK_STA_TER_12.fbx`  tris 12800  tex `SGK_TER_12`
- [ ] `01_TERRAIN\SGK_STA_TER_22.fbx`  tris 12800  tex `SGK_TER_22`
- [ ] `01_TERRAIN\SGK_STA_TER_32.fbx`  tris 12800  tex `SGK_TER_32`

→ Studio 재시작 후 `-Resolve` 로 중간 확인

## 세션 2 (12 파일)

- [ ] `01_TERRAIN\SGK_STA_WALL_E.fbx`  tris 8224  tex `SGK_WALL_E`
- [ ] `01_TERRAIN\SGK_STA_WALL_W.fbx`  tris 8224  tex `SGK_WALL_W`
- [ ] `01_TERRAIN\SGK_STA_WALL_N1.fbx`  tris 8816  tex `SGK_WALL_N1`
- [ ] `01_TERRAIN\SGK_STA_WALL_N2.fbx`  tris 8816  tex `SGK_WALL_N2`
- [ ] `01_TERRAIN\SGK_STA_WALL_S1.fbx`  tris 8816  tex `SGK_WALL_S1`
- [ ] `01_TERRAIN\SGK_STA_WALL_S2.fbx`  tris 8816  tex `SGK_WALL_S2`
- [ ] `02_STATIC\SGK_STA_Terrace_N.fbx`  tris 12  tex `STONEWALL`
- [ ] `02_STATIC\SGK_STA_Cairn.fbx`  tris 180  tex `BASALT`
- [ ] `02_STATIC\SGK_STA_STEPS.fbx`  tris 744  tex `BASALT`
- [ ] `02_STATIC\SGK_STA_StreamWater.fbx`  tris 1440  tex `SGK_WATER`
- [ ] `10_MASTERS\MST_PAVILION.fbx`  tris 12392  tex `MST_PAVILION_ATL`
- [ ] `10_MASTERS\MST_BRIDGE.fbx`  tris 9128  tex `MST_BRIDGE_ATL`

→ Studio 재시작 후 `-Resolve` 로 중간 확인

## 세션 3 (12 파일)

- [ ] `10_MASTERS\MST_WALL_9M.fbx`  tris 26189  tex `MST_WALL_9M_ATL`
- [ ] `10_MASTERS\MST_WALL_L.fbx`  tris 26190  tex `MST_WALL_L_ATL`
- [ ] `10_MASTERS\MST_BOULDER_A.fbx`  tris 26613  tex `BOULDER_A`
- [ ] `10_MASTERS\MST_BOULDER_B.fbx`  tris 26189  tex `BOULDER_B`
- [ ] `10_MASTERS\MST_FERN.fbx`  tris 6232  tex `FERN`
- [ ] `10_MASTERS\MST_STUMP.fbx`  tris 26189  tex `STUMP`
- [ ] `10_MASTERS\MST_DEADTRUNK.fbx`  tris 26190  tex `DEADTRUNK`
- [ ] `10_MASTERS\MST_PINE_L1.fbx`  tris 4502  tex `MST_PINE_L1_ATL`
- [ ] `10_MASTERS\MST_PINE_L2.fbx`  tris 4793  tex `MST_PINE_L2_ATL`
- [ ] `10_MASTERS\MST_PINE_L3.fbx`  tris 5485  tex `MST_PINE_L3_ATL`
- [ ] `10_MASTERS\MST_PINE_M1.fbx`  tris 4425  tex `MST_PINE_M1_ATL`
- [ ] `10_MASTERS\MST_PINE_M2.fbx`  tris 3967  tex `MST_PINE_M2_ATL`

→ Studio 재시작 후 `-Resolve` 로 중간 확인

## 세션 4 (7 파일)

- [ ] `10_MASTERS\MST_PINE_M3.fbx`  tris 2923  tex `MST_PINE_M3_ATL`
- [ ] `10_MASTERS\MST_PINE_S1.fbx`  tris 2136  tex `MST_PINE_S1_ATL`
- [ ] `10_MASTERS\MST_PINE_S2.fbx`  tris 2333  tex `MST_PINE_S2_ATL`
- [ ] `10_MASTERS\MST_PINE_XL1.fbx`  tris 11844  tex `MST_PINE_XL1_ATL`
- [ ] `10_MASTERS\MST_PINE_XL2.fbx`  tris 10142  tex `MST_PINE_XL2_ATL`
- [ ] `10_MASTERS\MST_SAPLING1.fbx`  tris 587  tex `MST_SAPLING1_ATL`
- [ ] `10_MASTERS\MST_SAPLING2.fbx`  tris 646  tex `MST_SAPLING2_ATL`

→ 끝. `-Resolve` 43/43 확인
