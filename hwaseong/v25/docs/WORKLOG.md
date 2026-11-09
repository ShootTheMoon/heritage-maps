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

## 19. 재배치 결과 (2026-09-09)
- FBX 오브젝트 변환 베이크본(_rebatch0/1/2, JAM 65) 재임포트 후 컨테이너 `Workspace.HWS_Hwaseong` (guid B4338267BDBF786024208D23092BF329) 신규 생성.
- 투입: 정적 103 (items_static.json) + 인스턴스 941 (_place/place_000..004) + 충돌 슬랩 541 (_collision/items_col_000..002). 저장 완료.
- 눈높이 확인(성 밖 Z+5000 / 성 안 Z−4500): 옹성·문루·성벽 방향·텍스처 정상. 스크린샷 Screenshots/Agent/20260909_0750*.png
- 미완: 문짝 8 (`_rebatch_doors`) 는 아직 구버전 에셋 → 재임포트 후 `python hws_place.py UGCLocalAssetTable.json` 재실행, HWS_DOOR_* 8개 MeshId 갱신. 주문(MG) 문짝이 홍예 상단에 떠 보이는 것이 이 때문.

## 20. 문짝 교체 (2026-09-09 07:57)
- 베이크본 문짝은 Studio 에 한글 이름(HWS_DOOR_주문/옹성_좌/우_P54/55, 07:32 임포트)으로 등록됨 → hws_place.py 가 ASCII stem 을 한글로 바꿔 조회(ASCII 구버전 ID 는 버림).
- HWS_DOOR_* 8개 삭제 후 items_doors.json 으로 재생성, 저장. 홍예 안에 정상 위치.
- 주의: 베이크 시점 프레임이 열린 상태라 문짝이 **열린 자세(약 88°)** 로 굽혀 있음. Lua 트윈은 힌지(manifest_v25_doors.json) 기준 −88° 회전이 닫힘. 닫힘을 기본으로 원하면 frame 1 에서 재익스포트 + 재임포트 필요.

## 21. 문짝 진짜 원인 = 백페이스 컬링 (2026-09-09 08:49)
- 문짝은 한 겹 면이라 안쪽에서 보면 컬링돼 안 보였고, 보이던 붉은 기둥은 KCISA 원본 문 기둥이었다. 레이 프로브(centerHit)로 확인.
- 해결: HWS_DOOR_* 8개 `DoubleSided = true`. hws_place.py 가 문짝에 doubleSided 를 넣도록 수정. 최종 에셋은 HWS_DR4_*(bbox 중심 원점, ASCII 노드명, frame 1 닫힘).
- 저장 완료. 다음: Lua 문 트윈(힌지 = manifest_v25_doors.json pivot_world_m, 닫힘 0° → 열림 ±88°).

## 22. 문 개폐 스크립트 (2026-09-09 09:02)
- ServerScriptService/HwsDoorServer (Lua/HwsDoorServer.lua). Heartbeat 루프, 힌지 기준 CFrame 회전, 플레이어 9 m 접근 시 열림·이탈 시 닫힘, 88°, smoothstep.
- 문짝 8장은 Mobility=Movable (Static 이면 CFrame 대입 거부), DoubleSided=true. hws_place.py 반영.
- 검증: DEBUG_FORCE_OPEN 으로 재생 → Sandbox.log 에 8장 모두 중심이 −Z(성 안)로 2.1 m 이동·yaw ±88°. 확인 후 false.
- 남은 것: MapService hws 항목을 새 컨테이너(HWS_Hwaseong, rect X −77384..−38652)로 갱신, 경계 벽 4장·스폰, 낙하 리스폰.

## 23. 물리 충돌 수정 (2026-09-10)
- 증상: 지면에서 바로 떨어지고 담장·소품이 통과됨.
- 원인 1: 충돌 슬랩 COL_HWS_* 541장이 **Shape=Cylinder** 로 생성돼 있었다(overdare MCP create 에 shape 를 안 주면 Cylinder). 산곡 COL_TER_* 는 Block. → 전부 Block + Movable 로 일괄 수정(update_instance guids). hws_stage3.py·_collision JSON 에 shape/mobility 추가.
- 원인 2: 마스터 인스턴스(담장·여장·소품·바위)가 canCollide=False 로 배치됨. → 담장·여장 78 + 소품 15 + 바위 8 을 CanCollide=true. hws_place.py `SOLID` 목록으로 반영. 소나무·풀은 성능 때문에 그대로 통과.
- 다른 PC 에서 보려면 `onlyonetap\onlyoneshot.ovdrjm` 을 동기화해야 한다(레벨 파일에만 반영).

## 24. 문 개폐 트리거 변경 (2026-09-10)
- 근접 트리거 → **점령지 열림 연동**. HwsDoorServer.zoneOpen() 이 Workspace.CaptureZone/ZoneSeg 의 Transparency < 1 을 열림으로 본다(CaptureServer 는 숨김 1, 표시 0.1~0.6). CaptureServer 는 수정하지 않았다.
- 결과: 카운트다운·대기 중 닫힘, 첫 점령지가 열리면 8장 모두 안쪽 88°로 열림, 경기 종료 링(0.1)도 열린 상태로 남다가 다음 판 대기에서 닫힘. `USE_PROXIMITY = true` 로 옛 방식 복귀 가능.

## 25. 문 속도·투사체 통과 (2026-09-10)
- 문: SPEED 1.6 → 0.25 (완전 개폐 4초).
- 쿠나이(attack 3)가 성벽을 통과: hws_place.py 가 모든 HWS 메시에 `canQuery: False` 를 줬고, ViewmodelController.castSolid 는 Raycast 로 벽을 판정한다 → CanQuery=false 파츠는 레이가 그냥 지나간다. 충돌 있는 174장(JAM 65·담장/여장 78·소품 15·바위 8·문 8) 을 CanQuery=true 로. hws_place.py 는 canQuery = canCollide 로 수정. 나무·풀·지형 타일은 그대로 false(쿠나이가 풀에 막히면 안 된다 — 산곡 규칙).

## 26. 점령 불가 (2026-09-10)
- 원인: MapService hws.center 가 문루 정중앙(−58000, 0). CaptureServer.groundY 가 Y 9000 에서 아래로 쏘아 문루 지붕(~20 m)에 맞아 링이 지붕 위에 열림 → 땅의 플레이어는 HEIGHT 10 m 밖. 무작위 자리도 rayTop 9000 이라 성벽·여장 위에 걸릴 수 있었다.
- 수정: center → (−58000, −4000) 성 안 마당. rayTop 400 / rayLen 1200 으로 지면 근처만 인정(크렘린과 같은 방식). 스폰·경계 벽은 이미 사용자가 배치(HWS_Spawn_*, HWS_Bound_*).
- 26-1. 링이 성벽 위에 뜨는 건: 담장 윗면이 399 cm 로 rayTop 400 바로 아래였다. rayTop 200 / rayLen 1000 으로 내림.
- 26-2. 링이 성벽과 겹침: zoneRadius 2200→1100, MapService hws.zones 추가(성 안 마당 X −60500..−55500 Z −4800..−3200 / 성 밖 들판 X −64000..−52000 Z 4100..5350, 중심 범위). CaptureServer.pickSpot 이 zones 가 있으면 그 안에서만 추첨(다른 맵은 기존 rect 방식). minSpawnDist 2500.
- 26-3. zoneRadius 2000 확정(18·15·16 시험 후 사용자 결정). zones(중심): 성 안 X −59600..−56400 Z −4080..−3920 · 성 밖 서 X −65000..−62500 / 동 X −54000..−51500, Z 4300..4500.
- 28. 사용자 피드백: 화성에 지면 틈새가 보인다. 산곡 리메이크처럼 세밀하게 안 한 탓. 다음 맵은 산곡 수준(타일 경계 베이크·이음선 점검)으로.
- 27. 사용자 요청: 소나무 690그루 CanCollide=true (몸은 막힘). CanQuery 는 false 유지 → 쿠나이·화살은 나무를 통과(산곡 규칙). hws_place.py SOLID 에 소나무 추가, QUERY 목록 분리.
- 29. 지면 선(사용자 스크린샷): 슬랩을 마젠타로 켜 보니 넓은 영역에서 슬랩 윗면이 잔디 위로 튀어나와 있었다(두께 100, 중심 −50 → 윗면 0, 잔디는 −0.3~+0.3 기복). 541장 두께 40 으로(윗면 −30) → 잔디 아래로 완전히 들어감. 눈높이 편집기 스크린샷에서 선 사라짐 확인 필요. 살구색 판은 HWS_Bound_* 경계 벽(편집기에서만 보임, 런타임엔 BoundaryServer 가 ServerStorage 로 치움) — 이상 아님. _collision JSON 두께도 40 으로 갱신.

- 30. 스폰 대문 앞: HWS_Spawn_Red (−58000,30,4300) 옹성 앞, HWS_Spawn_Blue (−58000,30,−4800) 성 안 마당. 첫 링 center → (−63500, 4400) 서쪽 들판(Blue 스폰과 겹치지 않게).
- 31. 타일 이음선(길고 곧은 밝은 선): T_HWS_TER_*.png 가장자리 8~10 px 가 안쪽보다 ~8 % 밝음(UV pad 8 = bake margin 8, 바이리니어가 여백을 물었다). rebake_tiles.py 로 UV inset 24 px·margin 48(EXTEND) 재베이크 → HWS_TER2_*/HWS_OUT2_* 30장 임포트 후 기존 30 인스턴스의 MeshId/TextureId 만 교체(swap_plan.json). 위치·이름은 그대로.
- 32. (2026-09-12) TER2 적용 후에도 선이 남음 → 산곡 이음선 처방 이식. rebake_tiles3.py: ① 베이크 메시를 타일 밖 PAD 24 px 만큼 월드로 확장해 구움(M_HWS_Terrain 은 Object 좌표·월드 버텍스 필드라 연속) → 여백 텍셀 = 이웃 타일의 실제 땅, ② 노멀 = relief()/berm() 해석 기울기(타일 경계 두 정점이 비트 단위 동일). 경계 31쌍 dRGB 0.00~0.04/255(짧은 끝줄 5쌍만 2~6 = 텍셀 크기 차). 산출 _rebatch_tiles3\HWS_TER3_*/HWS_OUT3_* 30장. 임포트 후 swap3.py → swap_plan3.json → 30 인스턴스 MeshId/TextureId 교체.
- 33. (2026-09-12) TER3 적용 후에도 사용자 "선 그대로" — 파일은 연속인데 Studio 가 메시마다 음영을 달리 줘서 곧은 경계는 결국 선으로 읽힌다. rebake_tiles4.py: 안쪽 20장을 1 m 칸 단위로 노이즈 굴곡(4 m/12 m + 1.5 m/4 m)+칸별 지터 ±1.5 m 로 소유 타일을 정해 경계를 뒤엉킨 띠(최대 ~7 m)로. 공유 정점 동일 → 틈 없음. 타일이 41~48 m 로 커져 위치·크기가 바뀜 → swap4.py 가 items4.json(이름 HWS_TER_ij 유지) + delete4.json(기존 20 guid). 외곽 HWS_OUT_* 는 그대로.
  - 적용: items4.json 20개 생성 → 옛 20 guid 를 .ovdrjm 에서 삭제(백업 onlyoneshot.ovdrjm.bak_ter4) → apply·저장. HWS_TER_ 20개 확인, 12 m 높이 스크린샷에서 X −64000/Z 3000 경계 선 안 보임.
  - 사용자: "선도 울퉁불퉁 되버렸다" → 메시 단위 밝기 차가 원인 확정(경계 모양을 그대로 따라감). 산곡도 해결한 적 없음(동기화 메모 10항: 12 % 단차, 실기 확인 보류). 산곡에서 안 보이는 건 진한 바닥 얼룩·언덕 + 타일 바운드가 전부 4.3~11.7 m 로 큼. 산곡 투명 물체 = 충돌 Part(Unlit·1)·경계벽·개울 물(0.45) 뿐, 이음선용 아님.
- 34. (2026-09-12) TER5 "고도화": rebake_tiles5.py. ① 안쪽 4장(A x−100..4/y−70..16, B x4..100, C·D y16..80) — 경계를 도로 가장자리(x=4, y=16)에만 → 노출 경계 1,200 m → ~74 m. ② 4장 바운드 동일(104×(ZHI+4.5)×86 m): 땅속 −4.5 m·최고점에 1 mm 삼각형. ③ 텍스처 2048², PAD 24 월드 연속, 해석 노멀. ④ 약한 월드 얼룩(±7 % 밝기, 10 % 마른 풀 톤) + 실제 나무·고사리 위치로 솔잎 낙엽(이전 헤드리스 베이크는 _TREES 가 비어 낙엽 0). ⑤ 노출 구간(y=16 |x|>70, x=4 y>66)에 산곡 소형 식물 마스터 산포 → seam_props5.json. 임포트 후 swap5.py → items5.json(HWS_TER_A..D) + delete5.json(HWS_TER_ij 20).
  - 결과: 경계선은 안 보였으나 잔디가 크게 흐려짐(파일은 4.8 cm/텍셀인데 Studio 에서 ~10 cm 처럼 보임 → 2048 텍스처를 1024 로 줄여 쓰는 것으로 추정). 사용자: "고도화 = 모델 2000개". TER5 철회.
- 35. (2026-09-12) TER3 20장 복원(_rebatch_tiles3\items_ter3_restore.json, 원래 위치·크기 + TER3 ID) + 산곡 소형 식물 2,000개(HWS_지면소품_grass_NNNN, 고사리 위주·쑥 소형·억새 드묾, 추가 임포트 없음). grass2000.py: 타일 경계선(x=−60/−20/20/60, y=−30/10/50) 따라 약 1 m 간격 + 마당, 도로·광장 제외. 경기구역 = HWS_Bound 벽 X −67000..−49000, Z −6500..6500 (블렌더 x ±90, y ±65) → 밖으로 나간 것 제외 후 GRASS_TOPUP=776 으로 채워 2,000. 대량 배치는 create_instances(200개마다 guid 200줄 반환) 대신 .ovdrjm 에 같은 메시의 기존 인스턴스를 복제해 삽입(새 guid·ObjectKey, json 파싱 검증, 백업 .bak_grass/.bak_topup) → apply 1회. TER5 A–D·seam 138 삭제. fps 확인 필요(인스턴스 +2,000).
  - 35-1. 경계 ±0.7 m·88 % 로 뿌렸더니 경계 위에 "심은 줄"이 생겨 오히려 선이 드러남 → GRASS_SIGMA 2.5 m(±5 m)·GRASS_SEAM_SHARE 0.6, 경기구역 밖 경계선(x=±100, y=−70) 제외해 재생성: 경계 띠 938 + 마당 1,062 = 2,000. regrass 로 전량 교체(백업 .bak_regrass). 눈높이에서 줄 사라짐, 경계 바로 위 발밑에만 옅은 선이 남을 수 있음.
- 36. (2026-09-12) 사용자: "선이 매우 선명, 밖쪽 튀어나온 부분은 안 보임" → 원인은 평평함(FLAT 구역 relief=0 이라 타일이 한 톤, 메시별 밝기 차가 그대로 선). TER6: terrain6.py 가 relief 에 ±15 cm·3~8 m 기복(bump) 추가 — 도로·광장·가장자리 4 m 는 0 으로 페이드, 담장 옆 1.5 m 는 올라가기만(밑동 틈 방지). 평균 0·±15 cm 라 슬랩 윗면(−30)보다 늘 위 → 슬랩 재생성 불필요. rebake_tiles6.py(1024, 동일 바운드 40 m, 낙엽·약한 얼룩) → _rebatch_tiles6 20장 + deltas6.json(풀·소품·소나무 Y 보정). 임포트 후 patch6.py → apply.
  - 적용: 첫 apply 에서 지형이 사라짐 = UnitExtent 누락. Studio 는 Size/UnitExtent 로 스케일하는데 옛 평평 타일 값(Y 0.0005)이 남아 세로 ~50만 배로 늘어났다(하늘의 올리브 띠). UnitExtent = (Size.X/2, Size.Y/2, −Size.Z/2) 로 고침(백업 .bak_ue6), patch6.py 에도 반영. 사용자: "선 없어짐 좋았다".
- 37. (2026-09-12) 외곽 10장도 같은 처리(사용자 "밖부분도 똑같이"): terrain6.bump_outer(±15 cm, 안쪽 지형 4 m 앞에서 0) + berm, 4 m → 1 m 격자(안쪽 구멍 셀 단위 제외), 바운드 100×H×100 동일, 1024, 외곽 소나무 낙엽. rebake_outer6.py → _rebatch_out6 (HWS_OUT6_ij) + deltas_out6.json. 임포트 후 patch_out6.py(UnitExtent 포함) → apply.
  - 적용·저장(백업 .bak_out6): 외곽 10장 교체, 외곽 소나무·풀 512 재안착. 60 m 전경에서 안쪽·외곽·경계 모두 타일 선 안 보임. 남은 확인: 실기 걷기, fps(인스턴스 ~3,700).
- 38. (2026-09-12) 게임 안 정리(사용자: "게임에 있는 것만, 최적화 목적, 로컬 백업은 둬도 됨"). ① Workspace 바로 아래 떠돌던 HWS_TER6_00..43 Model 20개(+MeshPart 20) 삭제 — TER6 를 GUI 로 임포트할 때 레벨에 한 벌씩 놓인 복제본, 월드 원점 근처 X +20~+180 m 에 지형 20장이 깔려 있었다(다른 라운드 임포트는 복제본 없음). ② 경기구역 경계벽(X −67000..−49000, Z ±6500)에서 5 m 이상 밖의 COL_HWS 슬랩 194장 삭제(도달 불가·투명) → 347장 남음. 인스턴스 8,545 → 8,311. 백업 .bak_stray. 외곽 소나무 557 은 보이는 풍경이라 유지.
  - 같은 날 산옥: 투명 충돌 상자 3개 삭제(사용자 "그냥 지우기") — COL_Pavilion(정자 겉 bbox 통째로 막음), COL_SGK_WallL_±6_±27(ㄱ자 담 bbox 가 안쪽 모서리까지 막음). 백업 .bak_col3.
