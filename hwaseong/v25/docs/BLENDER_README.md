# 화성 v25 — 장안문 아레나 · 인계 (1차 위치 → 2차 에셋 교체 진행 중)

2026-09-09. onlyoneshot 근접전용 소형 맵. **1차 = 위치·구성만 잡은 상태.** 감축·베이크·교체는 2·3차.
사용자 지시: "일단 1차 위치만 잡고 2차, 3차 이렇게 진행".

## 파일

| 무엇 | 위치 |
|---|---|
| 작업 blend (GUI 세션에서 저장) | `hwaseong_rebuild\v25\hwaseong_v25.blend` |
| 스크립트 | `v25\kit_namhan.py`(남한산성 키트) `jam_reduce.py`(장안문 v24 재적재·재질별 합치기) `assemble_v25.py`(배치·합치기·재질 분리·도로) `props_bake.py`(소품 1텍스처 베이크·저폴리 소나무·연자방아) `snap.py`(뷰포트 스냅) `soupcheck.py`(면/껍질 비) `make_preplacement.py`(배치 json) |
| FBX 익스포트 | ovdr_export/hwaseong_v25/ — 22 파일(55 MB), MeshPart 74 + Part 1, 408k tri, manifest.json |
| 배치 초안 | `ovdr_export\hwaseong_v25\placement_v25_pre.json` (ΔX −58000/ΔY −5000, meshId 비어 있음), `collision_parts.json`(지면 Part 1장) |
| 스냅샷 | `v25\snaps\S1_*.png` (top·overview·compound·village·outside) |
| 1024 축소 텍스처 | `v25\tex\` |

## 좌표·구성

원점 = 장안문 문루 중심, **+X 성벽 방향, −Y 성 밖(북), +Y 성 안(남)**, m. 지면 z=0 (Part 200×150×1, 상면 0).
익스포트는 `gyeongbokgung\export_overdare.py --export --groups JAM,SBK,HPR,CTB,CTR,HGD,VEG` (Blender 5.2.1 헤드리스, Steam 경로).

| 컬렉션 → 그룹 | 내용 | 오브젝트 |
|---|---|---|
| 화성_장안문 → JAM | KCISA 장안문 목조 문루 (v24 원형, 재질별 1메시로 합침) | 16 |
| 화성_성벽 → SBK | KCISA 옹성·육축·성벽(±80 m)·적대 (`B_*` 저폴리 포함) 28 + 내부 담장 (남한산성 성벽 8 m×24, 여장 48, 암문 1, 포좌 2 → 7 메시) | 35 |
| 화성_소품 → HPR | KCISA 깃발·홍이포·현판·초소 | 5 |
| 화성_도시_건물 → CTB | 초가집 4(합침) · 대문 · 본채(Sketchfab PaperMouse 동아시아 2층집, 임시) · 연자방아 4(합침) | 7(재질 분리 후) |
| 화성_도시_도로 → CTR | 흙길 데칼 3 (비충돌, 팔레트 단색) | 3 |
| 화성_지면 → HGD | 지면 박스 1 → 네이티브 Part | 1 |
| 화성_수목 → VEG | 저폴리 소나무 8(수피/잎 2메시, 알파 없음) · 바위 3 | 3 |
| KIT_NH / KIT_PROPS | 프로토타입 (익스포트 제외, MISC) | — |

내부 담장(64×32 m, 높이 4 m)은 성 안 +Y 24~56 m. 북면 중앙 암문(x −4~4), 남면 중앙 대문, 북동·북서 모서리 포좌.

## 재료 출처 · 라이선스 (README 크레딧에 넣을 것)

- 장안문 일곽: KCISA 「수원화성_장안문」 스캔, Sketchfab `kcisameta`, **CC BY 4.0** (v24 blend 경유).
- 남한산성 성벽·여장·포좌·암문·돌계단, 낙안읍성 연자방아: 국가유산청 3D, **KOGL 제1유형**(출처 표시). `Desktop\국가유산_3D\`.
- 본채(임시): "Traditional East Asian-Inspired House Model" PaperMouse, Sketchfab **CC BY 4.0**, uid 504176f9f91b4effa83d6fc0a1d7dea3.
- 초가집·대문·바위무리: `gyeongbokgung\hwaseong_props.blend` (v23 Sketchfab CC-BY 계열 — **원 출처 표기 v23 문서에서 확인 필요**).
- 소나무: 절차 생성(108 tri). BlenderKit 은 로그인 안 되어 있어 이번엔 안 씀.

## 검증 결과

| 항목 | 결과 |
|---|---|
| FBX 상한 (≤30k tri, ≤200 mesh/파일) | 22 파일 전부 통과 (최대 29,902 tri) |
| 텍스처 1장/재질, ≤1024px | 통과 — 69장 전부 1024 (본채 Atlas·Windows 4096 은 v25/tex 폴더에 1024 로 축소, 패킹 해제 후 재익스포트). 총 55 MB |
| 텍스처 없는 파일 | CTR_01(도로)·VEG_01(소나무·바위) — 팔레트 단색 의도. 배치 시 material_key 색으로 칠함 |
| 창덕궁 겹침 | X −66,381 ~ −49,992 cm — 창덕궁(27,000~33,000)과 겹치지 않음 |
| 인스턴스 | MeshPart 74 + Part 1 (v23 은 189 + 992 슬래브) |

## 1차에서 확인된 문제 (2·3차 과제)

1. **장안문 목조 문루는 soup.** 지붕 170k·공포 104k tri, 경계 엣지 35%, 스파이크가 원래부터 있다. Decimate(Collapse) 는 안 먹고(ratio 0.2 → 변화 0), 복셀 리메시+베이크는 옹성이 녹아 보여 폐기. → **2차: 문루 교체** (후보 ① `hanok.py`/`roof.py` 절차 생성 2층 문루 — 경복궁 근정문 방식, 팔레트 단색; ② Sketchfab — "korean gate" 검색엔 KCISA 원본만 있었음).
2. 본채가 한옥이 아니다(동아시아 양식 2층). Sketchfab CC-BY 후보: PaperMouse 3종(30k), "Olympic Hanok" jkscott(657k, 무거움). NC 라이선스(angelinart Hanok)는 못 쓴다.
3. 상가(v23 Sketchfab)는 현대식 매점이라 제외(`USE_STALLS=False`).
4. 성벽 위 통로 폭·여장 뒤 동선, 육축 계단(G_Stair)으로 성벽 위 진입 가능 여부 미검증(플레이 테스트 필요).
5. 지면이 완전 평면 1장. 성 안/밖 단차·흙길 실 텍스처는 3차.
6. 3차 감축은 collapse 가 아닌 방법(재모델·리토폴로지)이어야 한다.

## 다음 세션 순서

1. (2차) 문루·본채 교체 → `assemble_v25.main()` 재실행 → 스냅 확인.
2. (3차) 텍스처·감축 마감 → `export_overdare.py` 재익스포트 → `check_export_textures.py` 통과.
3. Studio: FBX 1개 프로브(Orientation 0 vs yaw+180 상충 판정) → 22 파일 GUI 발행 → `make_placement.py --manifest ...\hwaseong_v25\manifest.json --parent "Hwaseong Arena"` → 배치 → 지면 Part → fps 실측.

## 2차 진행 (2026-09-09, 같은 날 후반)

사용자 지시: "아직도 화성 이상함 그냥 에셋 디폴트값으로 전부 재정렬해. 그다음에 2차 진행해, 문루는 절차 생성으로 교체하고 본채는 PaperMouse 한옥으로."

1. **기본값 재정렬** — `reset_defaults.py`: 씬을 비우고 **무가공 에셋**으로 재조립. KCISA v24 3컬렉션 원형(용접·합치기·감축 없음), 남한산성 5모듈·낙안읍성 연자방아 원본 FBX(감축·베이크 없음, 원본 PBR 재질), 초가집·대문·바위 원형, PaperMouse 집(1024 텍스처), 절차 소나무. 배치는 `assemble_v25.py` 그대로. 프로토타입 컬렉션(KIT_NH·KIT_PROPS)은 뷰 레이어에서 제외. 1차 파일 백업 `hwaseong_v25_s1.blend`. 결과 83 오브젝트 / 1.02M tri (무가공이라 무겁다 — 3차에서 처리).
2. **문루 절차 생성 교체** — `gate_house.py`: KCISA 목조 문루 32 메시 제거, `hanok.py`/`roof.py` 로 중층 우진각(gable_ratio=1.0) 문루 생성. 치수는 KCISA bbox 실측: 하층 5칸 22.8 m × 2칸 8.1 m, 상층 20.4 × 5.6 m, 육축 상면 z 7.7, 하층 처마 11.6 / 상층벽 13.2~16.2 / 상층 처마 17.0 / 용마루 21.2. 25 메시 91k tri, 팔레트 재질 7개(단청). 육축·옹성·성벽(KCISA `화성_성벽`)은 그대로.
3. **본채** — Sketchfab PaperMouse "Traditional East Asian-Inspired House Model" (CC BY 4.0) 유지, 담장 안 중앙 (0, 42) 180° 회전.
4. **BlenderKit(로그인 후)** — 무료·royalty_free·≤25k 면 조건으로 5개 다운로드 시작: Korea Ceremonial flag on stand(15k), Mud Pots 11(1.4k), Japanese Temple - Stone Lantern(5.6k), Old Wooden Barrel(3.4k), Hay Bale(368). 해상도 2K → 3차에서 1024 축소 필요. 검색 API: `api/v1/search/?query=<kw> asset_type:model`, 다운로드 `download.start_download(search.parse_result(raw), model_location=…, resolution=…)`(비동기). "hanok" 검색은 1건(1.9M 면, 유료)뿐이라 한옥은 BlenderKit 로 못 구한다.

**2차 시점 주의:** 씬에 다중 재질 오브젝트가 많다(초가집 11, 남한산성 성벽 2·포좌 3 등). `export_overdare.material_key()` 는 슬롯 0만 보므로 **그대로 익스포트하면 텍스처가 틀린다** → 3차에서 `assemble_v25.split_multi()`(재질 분리) 또는 1텍스처 베이크 후 익스포트. `ovdr_export\hwaseong_v25\` 의 FBX 22개는 **1차 시점** 산출물이다.
5. **BlenderKit 소품 배치** — `props_bk.py`: 다운로드된 5종을 프로토타입 1메시로 접고(`P_BK_*`, 높이 정규화) 복사 배치 후 종류별 1메시로 합침(`소품_BK_*`, 화성_소품/HPR). 깃발 4(담장 암문·대문 양옆), 항아리 7(초가집 옆 장독대), 석등 4(담장 안), 술통 8(성벽 아래·담장 안), 짚단 6(초가집 옆). 주의: 깃발은 **태극기 도안**이라 조선 배경엔 시대 착오 — 사용자 판단으로 교체/삭제. 석등은 일본식 등롱이라 같은 문제.
6. 연자방아(원본 FBX)는 임포터가 알파를 연결해 HASHED 로 보여 점묘처럼 깨져 보였음 → Alpha 링크 해제·OPAQUE (오버데어는 알파를 안 쓰므로 결과 동일).

**2차 종료 시점 씬**: 화성_* 컬렉션 오브젝트 ~90, 삼각형 ~1.1M(무가공). 스냅 `snaps\s2_*.png`. 3차 착수 전 사용자 확인 대기.
7. **재정렬 보정(사용자 "아직 안 된 데 있음")** — 원인 4가지를 고쳤다. ① KCISA 목조 문루를 뺐는데 `화성_성벽`·`화성_소품`에 남아 있던 문루 부속(적심 RammedEarth 28×14×8 m 블록이 새 지붕을 뚫고 나옴, 상층벽 GH_Wall, 초석 Pedestal, 현판 Note·Signboard) 5개 제거. ② 담장 포좌 2개가 모서리에서 떨어져 떠 있던 것을 네 귀 모서리 정중앙 6.4×5.9 m 배스천으로 교체(모서리 3.2 m 홈도 가림). ③ 담장 남문 8 m 틈을 대문 폭(2.8 m)에 맞춰 양쪽 2.6 m 스텁으로 메움. ④ place() 직후 matrix_world 가 갱신 전이라 스케일 복사본이 엉뚱한 곳에 구워지던 버그 → `bpy.context.view_layer.update()` 후 join. `assemble_v25.compound()` 에 반영.
8. **전체 재배치(사용자 "전부 없애고 재배치해")** — `reset_defaults.main()` 한 번으로 씬을 비우고 처음부터 조립하도록 정리했다: 원형 에셋 적재 → `assemble_v25`(배치·합치기·도로) → `gate_house.main()`(KCISA 문루 32 + 부속 5 제거, 절차 문루) → `props_bk.main()`(BlenderKit 소품; 프로토타입은 `protos_bk.blend` 에 저장해 재다운로드 불필요) → 연자방아 알파 해제 → KIT 컬렉션 제외 → 저장. 결과 화성_* 오브젝트 76 / 1.06M tri(무가공). 재현: GUI 에서 `exec(open(r"...\reset_defaults.py", encoding="utf-8").read(), ns); ns["main"]()`.
9. **원형 에셋 전용 재조립(사용자 "무조건 수정 안 한 에셋만")** — `rebuild_raw.py` 가 현재 정본. 모든 에셋을 임포트 그대로 쓰고(용접·합치기·감축·베이크·스케일·재질 편집·메시 원점 이동 전부 없음) 배치는 오브젝트 행렬만 바꾼다(복사본이 임포트 메시를 공유). 임포터가 알파를 BSDF 에 연결하는 에셋(낙안읍성 연자방아, 남한산성 돌계단)은 고치지 않고 **안 쓴다**. 담장은 9×4 모듈, N/S 5번째 모듈 자리에 암문(남북 대칭), E/W 벽은 N/S 벽 끝면과 맞물리게 중심을 3.16 m 안으로 넣어 모서리 홈 없음. 문루는 절차 생성(사용자 요청). 본채는 Sketchfab 툴로 재다운로드한 PaperMouse 집(원본 4K 텍스처 그대로, 루트 행렬만 이동). 소나무·항아리·술통·짚단은 BlenderKit 다운로더로 실치수 그대로 append(`bk_props()`, 비동기 23개: Low Poly Pine Tree 8 / Mud Pots 11 5 / Old Wooden Barrel 6 / Hay Bale 4). 절차 소나무·깃발·석등·연자방아·대문은 이번 판에서 제외. 결과 화성_* 143+ 오브젝트, 680k tri + BlenderKit.
10. **배치 전용(사용자 "생성하지 말고 바꾸지 말고, 에셋 배치만")** — 사용자가 씬을 직접 비운 뒤 `place_only.py` + `rebuild_raw.compound()/bk_props()` + `grass_ground.py` 로 재배치. 장안문은 v24 파생본 대신 **Sketchfab KCISA 원본**(kcisameta, uid 807b2e1a…, 1.675M tri, 재질 50) 을 Sketchfab 툴로 받아 루트만 이동(z +13.48, 회전: 툴 임포트 기준 +90° 후 180° 추가 = 옹성이 −Y 바깥으로). 본채 PaperMouse 원본(툴 임포트, 루트 이동만). 담장 남한산성 원본 모듈 9×4(행렬 배치만). BlenderKit 소나무 8·항아리 5·술통 6·짚단 4 실치수 append. 절차 문루·절차 소나무·지면 큐브·도로·초가집·바위·연자방아·대문 전부 제외. **잔디 바닥**: 산곡 지형과 같은 Poly Haven `aerial_grass_rock` 1k(`JSN_Sangok2\_TexLib\polyhaven`), 4 m 타일, 산곡 틴트(0.80,0.86,0.66), 평면 200×150 m z −0.02.
11. **바닥·나무 세부 구현** — `terrain_v25.py`. 바닥: 200×150 m 2 m 격자(7.5k 면), 성곽·담장·길 밖에만 ±0.3 m 완만한 기복(10 m 페이드), 정점색 "Blend" R=마사토 길(옹성 앞 광장→문루→담장 암문 남북길, 성벽 아래 동서길, 담장 안 길), A=솔잎 낙엽(소나무 반경 6 m). 재질 `M_HWS_Terrain` = 산곡 `sgk_dress.terrain_material()` 를 3세트로 축소(풀 aerial_grass_rock 4 m / 솔잎 brown_mud_leaves_01 3.5 m / 마사토 brown_mud_dry 3 m, 산곡 틴트, Object BOX 투영, 노이즈 색 변조 0.82~1.16, 범프 0.18). 나무: 산곡 소나무 팩(Sketchfab lolipop_1707, CC BY 4.0) `pine_pack_lib.blend` 의 LOD0 계층(big_1/big_2/large_1/medium_1/medium_2/small_1)을 **루트(Sketchfab_model·RootNode·Pine_x)까지 붙여** 회전을 보존한 뒤 계층 복사로 18그루(성 밖 북쪽 숲 8, 양 날개 4, 성 안 6), 회전 랜덤·스케일 0.9~1.1, 뿌리 0.7 m 묻음. 교훈: LOD0 만 붙이고 parent 를 끊으면 팀 루트의 Y-up 회전이 사라져 나무가 눕는다. BlenderKit 저폴리 소나무는 제거. 크기 참고: big 17 m, large 32 m(크면 스케일 0.75 권장), medium 13~14 m, small 4.4 m.
12. **나무 랜덤 산포 + 지면 고퀄리티** — `terrain_v25.py` v2. 지면 1 m 격자(30k 면), fBm 기복(구조물·길 12 m 안 평탄), 정점색 6-way(R 마사토·맨땅 패치 / G 암반 둔덕 / B 젖은 저지 / A 솔잎), 재질은 산곡 6-way(T_MDS 절벽 세트 제외) + 13 m 매크로 풀 샘플을 60 m 노이즈로 섞어 타일 반복 제거. 나무는 `SGK_Master.blend` 의 MST_PINE_XL/L/M/S 마스터를 Poisson 산포(성 밖 북쪽 숲 7.5 m 간격, 가장자리 10 m, 성 안 17 m; 구조물·길 3 m 이격) 126그루, 종류·크기·회전 랜덤, 뿌리 묻기 산곡 FOOT 표. 지면 소품 MST_FERN 70·EULALIA 55·ARTEMISIA 16·BOULDER 8·STUMP 6·DEADTRUNK 3(산곡 마스터). MST_ROCK_A/D 는 10 m 주상절리라 제외. 사고: 파인 팩 계층을 컬렉션 단위로 지우다 PaperMouse 본채가 함께 사라져 재임포트 — 이후 스크립트는 접두사(수목_/지면소품_/지면_)로만 삭제.
13. **떠 있음 보정 + 문 개폐 애니메이션** — KCISA 원본은 가장 낮은 점(CW_003 기초)만 z 0 이고 육축·옹성·성벽 밑동은 z 0.5 라 떠 보였다 → 루트 z −0.55 (밑동 −0.03, 기초 −0.55 매장). 문: 원본 Object_54(MI_T_G_MetalDoor_001, 판·못)·Object_55(MetalDoor_002, 문짝)에 옹성문(y −27)·주문(y −1.5) 두 짝이 함께 들어 있어, 면 중심이 문 평면 박스(y −28.5~−25 / −3~−0.5, x 좌우) 안인 면만 떼어 문짝 오브젝트 8개(짝 4 × 소스 2)로 분리하고 원본에서 그 면을 제거. 힌지 Empty `장안문_문_{옹성|주문}_{좌|우}_힌지` 를 바깥 세로변 밑(좌 x −2.35/−2.89, 우 +2.92/+2.90, z 0.17/−0.03)에 두고 문짝을 자식으로, 힌지는 `장안문_KCISA` 루트의 자식. 키프레임 Z 회전: 1f 0° → 60f ±100°(성 안쪽으로) → 120f 유지 → 180f 0°, 24 fps, 씬 1~180. 옹성문은 중심이 x +0.3 이라 좌짝 2.63 m/우짝 3.07 m 로 약간 비대칭(닫힘 상태 정상, 열림 시 좌측 문설주에 빨간 문 가장자리 한 줄 보임). 오버데어 이식 시엔 문짝 MeshPart 4개를 같은 힌지 CFrame 기준 TweenService 회전으로 옮기면 된다.
14. **문 개폐 겹침 제거** — 통로 실측(z 0.5~3 m 정점): 주문 통로 폭 x −2.64~2.58(y −4~−1), 안쪽 면 y −1.0 이후 개방; 옹성 통로 x −2.22~2.80(y −29.5~−26), y −26~−24 는 x −3.05~3.63 의 넓은 홈, 그 안쪽 x −2.52~3.10. 문짝은 통로보다 0.13~0.3 m 넓어 문설주 홈(rebate)에 앉아 있으므로, 힌지를 문짝 가장자리(홈 속)에 두면 90°에서 첫 0.5 m 가 돌에 박힌다. → 힌지를 **문설주 모서리**(통로 벽 × 안쪽 면 교차점: 주문 (±2.64/2.58, −1.0), 옹성 (−2.22/2.80, −26.0))로 옮기고 열림각 88°. 자식 문짝의 matrix_parent_inverse 를 새 힌지로 갱신해 닫힘 위치는 그대로(검증: 첫 정점 좌표 동일). 열림(60f)에서 문짝 정점의 벽 영역 관통 0개(수치 검산). 열린 문짝은 벽면에서 직각으로 서서 안쪽 허공에 있다(180° 접기는 홈 벽에 닿아 미채택).
15. **"문 받침대" / Build_Base_Down 건** — 문 밑 흰 블록은 KCISA 원본의 문설주 초석(납작 화강석)과 문 앞 둥근 문돌(지도리 받침)로, 텍스처·UV 정상(내가 만든 것이 아님). 사용자가 지운 것을 권한 `Build_Base_Down_Atlas_0` 은 PaperMouse 집의 **몸체(벽·지붕, 24k 면)** 였다 — 지우면 창·문·등롱·의자만 허공에 남는다(house_nobase.png). 재임포트해 복구했으나 사용자가 "없애라는 뜻"이라 확인 → PaperMouse 집 전체 제거(2026-09-09 밤). 담장 안 본채는 현재 비어 있음.
16. **문 밑 돌 제거(사용자 요청 "이 문 기둥 없애줘")** — 문짝 오브젝트(Object_55 조각)에 들어 있던 바닥 부속을 loose-part 단위로 지움: 문 중앙 밑 둥근 문돌(주문 좌·우, 99·115면, 0.3×0.3×0.4 m — 옆에서 보면 반쪽 껍데기로 보이던 것), 문설주 밑 납작 초석(0.49×1.13×0.26, 좌우), 그리고 판정 조건(최대 1.2 m·바닥 0.5 m 이하)에 함께 걸린 문 하단 띠쇠·못 조각(0.1~0.4 m, 총 154 조각). 옹성문도 같은 규칙 적용. 육안으론 문 하단 띠 한 줄이 단순해진 정도(sill2_door.png). 원본 복원은 KCISA 재임포트로만 가능.
17. **문 띄움 보정** — 16번에서 하단 부속을 지우자 문짝 판(Object_55 조각)이 z 1.0, 판재(Object_54)가 z 0.27 에서 시작해 떠 보였다. 각 문짝의 최저 경계 엣지를 지면(주문 −0.03, 옹성 0.17)까지 extrude 해 메움(UV 는 경계 루프 값 복사 → 단색에 가까운 철판 띠). 문 하단이 바닥에 닿고 개폐 애니메이션·힌지는 그대로.
18. **지형 밖 이세계 대책(산곡식 2번)** — `terrain_v25.build_outer()`/`ring_trees()`: 안쪽 200×150 을 감싸는 400×300 m 4 m 셀 띠(5.7k 면, 안쪽 사각형은 구멍), 같은 M_HWS_Terrain, 안쪽 가장자리에서 60 m 에 걸쳐 3.5 m 둔덕 + fBm, 둔덕 위 정점색 암반·낙엽. 소나무 띠 564그루(9 m 간격, 둔덕 높이 따라 묻음). 남은 대책은 이식 때: 투명 Part 경계벽(안쪽 10 m 선)과 Y 낙하 리스폰 Lua. 인스턴스가 690그루라 3차 익스포트 땐 외곽 나무를 줄이거나 합칠 것.
