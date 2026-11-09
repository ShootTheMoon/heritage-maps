# Phase 0 에셋 실측 (2026-09-04)

Blender 5.2.1, 임포트 축 -Z/Y, 모든 KHS 킷 min_z ≈ 0.

## 소쇄원 킷 (`C:\Users\29\Desktop\blender\SSW_Soswaewon\_extracted\`)
| 에셋 | 파일 | tris | 치수 (m) | 재질 | 판정 |
|---|---|---|---|---|---|
| 초정 (정자) | Chojeong_Pavilion | 12,392 | 4.76×4.73×3.85 | 5 | 그대로. 재질 5→1 아틀라스. 처마 밑 헤드룸은 Phase 2에서 측정 |
| 투죽위교 (다리) | Tujugwigyo | 9,128 | **4.99**×1.44×0.92 | 3 | 길이 4.99 m < 계류 상폭 6 m → **다리 자리 상폭 4.5 m로 좁힘** |
| 담장 | Stonewall | **16,364 / 3 m** | 3.0×0.79×3.3 | 2 | 9 m 조인 = 49k → 평면 데시메이트로 ≤5k/장 필요. 0.6배 → 1.8×0.47×2.0 |
| 화계 (석축) | Hwagye | 42,847 | 15.2×12.3×2.1 | 3 | 무거움 → 석축 5×5는 절차 박스+석재 텍스처로 대체 (킷은 참조) |
| 자연석계단 | Stair | 6,308 | 4.5×2.6×1.9 | 2 | 참조만; 계단은 절차 슬랩 |
| 대봉대 | Daebongdae | 10,072 | 3.6×3.6×3.5 | 4 | 예비 (정자 대체 후보) |

## 소나무 — PolyHaven `pine_tree_01` **탈락**
LOD0 나무 1개 = 4.2M~7.0M tris (침엽을 실제 지오메트리로 모델링), FBX 648 MB, 파일에 LOD1+ 없음.
MCP `download_polyhaven_asset`는 임포트 후 임시폴더를 지워서 텍스처 파일이 디스크에 남지 않는다
(로드 안 된 이미지는 size 0×0으로 유실). → PolyHaven은 **텍스처만** 쓰고, 모델은 API로 직접 받아 확인 후 쓸 것.

## 소나무 — Sketchfab "Pine trees pack (lowpoly, game ready, LODs)" **채택** (CC-BY, lolipop_1707)
라이브러리: `_TexLib\sketchfab\pine_pack_lib.blend` (4.9 MB, 텍스처 외부 `_TexLib\sketchfab\pine_pack\`).
재질 2개 공유(Bark_Mat 1024×2048, Clusters_Mat 2048² 알파 카드) → 익스포트 시 나무당 1아틀라스로 합침.

| 나무 | 실제 높이 (m) | LOD0 tris | LOD1 | LOD2 | 용도 |
|---|---|---|---|---|---|
| Pine_large_1/2/3 | 30.9 / 30.5 / 28.7 | 11,844 / 11,710 / 10,142 | ≈6k | ≈3k | 산벽 XL (외곽만) |
| Pine_big_1/2/3 | 15.6 / 15.1 / 18.4 | 4,502 / 4,793 / 5,485 | ≈2.7k | ≈1.4k | **주력 L** (숲 사분면·띠) |
| Pine_medium_1/2/3 | 12.4 / 11.8 / 9.6 | 4,425 / 3,967 / 2,923 | ≈2.2k | ≈1.1k | **주력 M** (레인 가장자리) |
| Pine_small_1/2/3 | 4.0 / 3.7 / 4.3 | 2,136 / 1,912 / 2,333 | | | 하층 |
| Pine_sapling_1/2/3 | 1.3~1.5 | 587~646 | | | 하층 |
| *_Billboard_LOD3 | | 16 | | | 미사용 |

마스터 계획: MST_PINE_L ×3(big), MST_PINE_M ×3(medium), MST_PINE_XL ×2(large, 산벽), MST_PINE_S ×2(small), MST_SAPLING ×2
→ 소나무 마스터 12개, 전부 ≤12k tris. 이전 곰솔(17k→8k 데시메이트)보다 가볍고 실루엣이 적송(장간·상부 수관)에 가깝다.
수피는 Bark_Mat 베이스컬러에 Z-그라디언트 적갈 틴트(`tune_pine :1180` 방식).

## 기존 발행 에셋 (onlyoneshot `UGCLocalAssetTable.json`, **UTF-16**)
MST_EULALIA / MST_ARTEMISIA / MST_ROCK_A~F / STA_* 79건 존재 (STATIC_MESH + MODEL 쌍 + TEXTURE). 억새·물쑥·주상절리 A/D/E는 재발행 없이 재사용.
