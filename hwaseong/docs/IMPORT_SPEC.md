# 수원 화성 → OVERDARE 이식 명세서

대상 프로젝트 `onlyoneshot`. 작성 2026-08-21.

**이 문서는 `OVERDARE_맵이식_명세서.md`(JSN_Sangok 편)의 후속이다.**
저쪽은 "블렌더 맵을 이 Studio 에 넣는 일반 규칙"이고, 이 문서는 **화성에서만 다른 것**과
**화성 작업의 현재 상태**를 담는다. 겹치는 규칙은 반복하지 않고 `[JSN §n]` 으로 가리킨다.
저쪽을 먼저 읽어라 — 특히 §1(좌표), §3(지형 충돌), §8(안전 규칙).

같은 방침을 따른다: **실측한 것만 적는다. 설계 단계인 것은 그렇다고 표시한다.
틀린 것으로 판명된 것도 남긴다.**

---

## 0. 지금 상태 — 여기서부터 시작하면 된다

| | 상태 |
|---|---|
| 블렌더 | **끝났다.** 반경 150 m 로 축소 완료 |
| 익스포트 | **`hwaseong_v23` 확정.** 파일 150 / 메시 189 / 삼각형 4,067,320 / 1.68 GB |
| 텍스처 검사 | **통과** (150/150 파일에 텍스처, 이미지 1,410장, 2048px 초과 0) |
| 에셋 발행 | 화성 STATIC_MESH 108개가 올라가 있으나 **유효한 것은 66개뿐** (2장) |
| 레벨 | **화성 인스턴스 0개.** v22 때 넣은 `Hwaseong Place` 88개와 `HwaseongSpawn` 이 지금은 없다 |
| 배치 파일 | `hwaseong_v23\placement_core66.json` — **조회·보정이 끝나 그대로 쓰면 된다** |

**남은 일은 셋뿐이다**: ① 121개 파일 발행(3장) → ② 배치(4장) → ③ 지형 충돌(5장).

```
%USERPROFILE%\Desktop\blender\ovdr_export\hwaseong_v23\
    *.fbx                     150개
    manifest.json             블렌더가 아는 값 (좌표·크기·재질·삼각형)
    before_ids.txt            발행 직전 에셋 3,403개 스냅샷
    core_texture_map.json     MODEL 에셋 29개 → 메시/텍스처 id 대응
    placement_core66.json     ★ JAM·SBK·HPR 66개 배치 지시서 (즉시 사용 가능)
    placement_core66_raw.json 위의 textureId 채우기 전 원본 (참고용)
```

### 0-1. v23 이 v22 와 다른 점 — 맵을 4배에서 1.8배로 줄였다

v22 는 지면이 564 × 576 m 로 **산곡(271 × 294 m)의 4.08배 넓이**였다. 원인은 마을이 아니라
마을을 둘러싼 빈 들판이었다. 세 값을 고쳐 반경 200 → 150 m 로 줄였다 (전부 적용 완료):

| 파일 | 값 | 역할 |
|---|---|---|
| `hwaseong/geo.py:27` | `RADIUS_M = 150.0` | 근본 레버. CTB·CTR·CTP 를 직접 자르고 HGD·VEG 가 따라 줄어든다 |
| `hwaseong/build_hs.py:65` | `pad = 30.0` | 지면 여유. 80 이면 가로·세로에 160 m 씩 붙는다 |
| `hwaseong/terrain.py:136` | `KEEPOUT_CITY = 155.0` | **210 으로 두면 수목이 0그루가 된다** — 줄어든 지면이 통째로 210 m 반경 안에 들어간다 |

결과: 지면 **372 × 384 m**(산곡의 1.79배 넓이, 선형 1.34배), 한옥 마을 본체는 **264 × 297 m**
로 산곡과 거의 같다. 건물은 실치수 그대로라 걸어다니기에 영향이 없다.

`geo.FETCH_M`, `layout.DIST_SCALE` 은 레버가 아니다(전자는 OSM 캐시라 무관, 후자는 남은 배치
항목의 `uv` 가 둘 다 `(0,0)` 이라 무효). **`dem.GRID_M` 은 절대 건드리지 마라** —
`build_hs._build_ground` 와 `dem.surface_at` 이 같은 값을 봐야 도로가 땅에 안 잠긴다.

---

## 1. 화성 고유의 좌표 — JSN 과 다른 네 가지

정본은 `gyeongbokgung\export_overdare.py` 로 JSN 과 같다 [JSN §1]. 다른 것만 적는다.

### 1-1. `FLOOR_Y = 5000` 이 붙는다

```
X = bx * 100
Y = bz * 100 + 5000      ← JSN 에는 이 항이 없다
Z = -by * 100
```

`sites.py` 의 HSF 항목이 `floor_y_cm 5000`, `origin_m (1200, 0, 0)`, `axis_deg 0` 이다.
장안문 문루 중심이 매니페스트 좌표로 **(120000, 5000, 0)** 이 된다.
`manifest.calibration` 에 이 규약이 박혀 있으니 헷갈리면 거기를 본다.

### 1-2. `Orientation` 은 **예외 없이 (0,0,0)** 이다

JSN 의 `ZXY` 분해도, `Y180` 보정도 **여기서는 쓰지 않는다.** 익스포터가 오브젝트마다
`matrix_world` 를 메시에 구워서 내보내기 때문에 회전이 이미 정점에 들어가 있다.

> **부재 하나가 틀어져 보인다고 그것만 돌려서 맞추지 마라.** 그러면 좌표계 오류가
> 검증을 통과해 버린다. 틀어졌다면 원인은 익스포트나 축 규약이고, 회전으로 덮으면
> 다음 그룹에서 같은 문제가 다시 나온다. (`ovdr_place.ps1` V3 주석)

### 1-3. `Size` 는 cm 실치수다 — `size_literal_cm` 을 그대로 쓴다

JSN §1-4 와 같은 결론이고, 그 실측(`Size=100` 인 지형 타일이 1 m 큐브로 렌더된 건)으로
확정됐다. 배치 파일의 `size_mode` 가 `"LITERAL_CM"` 으로 채워져 있다.

```
Size = size_literal_cm          ← 이것
Size ≠ size_unit_ratio          ← 미확정이던 시절의 대안. 남겨만 뒀다. 쓰지 마라
검산: Size / (2 × UnitExtent) = 1.0
```

`size_unit_ratio` 필드는 하위호환으로 남아 있을 뿐이다. **`size_mode` 를 보고 골라라.**

### 1-4. `ΔX` 는 **−58,000** 이다 (−70,000 아님)

매니페스트 좌표를 레벨 좌표로 옮기는 보정:

```
ΔX = -58000     ΔY = -5000     ΔZ = 0
```

- **ΔY = −5000**: 매니페스트의 `FLOOR_Y` 를 되돌린다. 이 프로젝트의 지면은 Y 0 이다
  (`GND_Base` 윗면 0). 보정 후 화성 지표면이 **Y −389 ~ +400 cm** 에 온다.
- **ΔX 가 −70000 이 아닌 이유**: 레벨에 있던 `PLACE NEW MAP CENTER HERE` 표지판이
  X=50000 이라 처음에 −70000 을 썼다. 그런데 축소한 v23 도 폭이 372 m 라 서쪽 끝이
  X 30,800 까지 내려와 **창덕궁(27,000~33,000)과 22 m 겹쳤다.** 표지판은 지금 레벨에
  없다. 창덕궁 동쪽 끝에서 98 m 떼는 값으로 옮겼다.

보정 후 점유 범위와 이웃과의 거리 (2026-08-21 레벨 실측):

| | X | Y | Z |
|---|---|---|---|
| **화성 (보정 후)** | **42,800 ~ 80,000** | **−1,189 ~ 2,211** | **−19,200 ~ 19,200** |
| Changdeokgung Place | 27,000 ~ 33,000 | 4,960 ~ 5,010 | −2,920 ~ 3,080 |
| JSN_Sangok | −73,649 ~ −46,546 | −2,389 ~ 8,561 | −15,916 ~ 13,513 |
| Lobby / GND_Base / WarCitySpawn / Wakizashi | −2,734 ~ 2,266 | | |

여유: 창덕궁 **98 m**, 그 외 전부 **400 m 이상**. **겹치는 것이 없다.**

> **`placement_core66.json` 의 `cframe` 에는 이 보정이 이미 들어가 있다. 또 더하지 마라.**
> 나머지 그룹은 `make_placement.py` 가 `DELTA` 상수로 자동 적용한다.

---

## 2. 에셋 — 무엇이 살아 있고 무엇이 죽었는가

`UGCLocalAssetTable.json` 실측 (2026-08-21, 전체 3,403개):

| 그룹 | 뜻 | 발행됨 | v23 필요 | 상태 |
|---|---|---|---|---|
| **JAM** | 장안문 문루 | 32 | 32 | **그대로 쓴다** — 반경과 무관 |
| **SBK** | 성벽·옹성 | 28 | 28 | **그대로 쓴다** |
| **HPR** | 소품(홍이포·깃발) | 6 | 6 | **그대로 쓴다** |
| CTB | 도시 한옥 | 20 | 111 | v22 잔재. **버린다** |
| VEG | 성 밖 수목·바위 | 15 | 6 | v22 잔재. **버린다** |
| CTR | 흙길·갓길 | 3 | 3 | v22 잔재. **버린다** |
| CTP | 가로수 | 3 | 2 | v22 잔재. **버린다** |
| HGD | 지면 | 1 | 1 | v22 잔재. **버린다** |
| 합계 | | **108** | **189** | 유효 66 / 폐기 42 / 신규 123 |

JAM·SBK·HPR 은 `hwaseong.blend` 의 KCISA 스캔을 `_append` 로 가져다 쓰고 배치도 `uv (0,0)`
이라 반경·pad 와 무관하다. **v22 발행분의 지오메트리가 v23 과 동일하다. 66개를 다시
올리면 되돌릴 수 없는 중복 발행이다** [JSN §8].

버리는 42개는 **지우지 않는다** — 발행 취소가 없다. 그냥 배치에서 참조하지 않는다.
이름이 같은 새 에셋이 올라오면 `make_placement.py` 가 `createdTime` 최신을 골라
로그로 남긴다(`latest_asset()`). 이 프로젝트엔 이미 동명 STATIC_MESH 가 98개 있으므로
**이름 매칭은 금지다** [JSN §2].

### 2-1. 화성에서 실측된 발행 규칙 (v22, 파일 4개로 확인)

`SBK_08` `CTR_01` `HPR_01` `VEG_01` 을 GUI 로 올리고 에셋 테이블을 읽었다:

| 파일 | 매니페스트 메시 | 신규 STATIC_MESH | 신규 TEXTURE | 신규 MODEL |
|---|---|---|---|---|
| SBK_08 | 7 | **7** | 7 | 1 |
| CTR_01 | 3 | **3** | 8 | 1 |
| HPR_01 | 2 | **2** | 2 | 1 |
| VEG_01 | 1 | **1** | 3 | 1 |

- **발행 단위는 메시다. 머티리얼이 아니다.** STATIC_MESH 수가 매니페스트 메시 수와 정확히
  일치한다. "다중 머티리얼 FBX 하나가 머티리얼 수만큼 쪼개진다"는 가설(M4)은 **거짓**이다.
  → `expected_asset_name` 매칭이 그대로 성립한다. 가장 컸던 위험이 해소됐다.
- **텍스처는 별도 TEXTURE 에셋으로 발행된다**(M3 참). 파일마다 메시보다 **먼저** 올라간다.
  이름이 살아 있는 것(`MI_T_G_Stair_001_baseColor`)과 임시 파일명(`tmpzhv2wtmz`)이 섞여
  **이름으로는 못 짝짓는다.**
- **파일마다 `MODEL` 에셋이 하나씩 생긴다.** 이 MODEL 이 메시-텍스처 대응을 들고 있어서
  `core_texture_map.json` 을 여기서 뽑았다. 4-3 참조.

에셋 이름 규칙 (매니페스트 `expected_asset_name`):
- 파일에 메시가 1개면 → 파일 스템 (`CTB_97`)
- 여러 개면 → `스템_슬러그` (`SBK_08_G_Stair_001_01_09f506`)

---

## 3. 발행 — 아직 사람이 GUI 로 해야 한다

**FBX 업로드 RPC 는 없다** [JSN §2]. Studio GUI 의 Bulk Import 로 파일을 하나씩 올린다.

### 3-1. 올릴 것 — 121개 파일

| 순서 | 그룹 | 파일 | 메시 | 삼각형 | MB | 최대 tris |
|---|---|---|---|---|---|---|
| 1 | HGD 지면 | 1 | 1 | 2,236 | 8 | 2,236 |
| 2 | CTR 흙길 | 1 | 3 | 8,244 | 28 | 5,080 |
| 3 | CTP 가로수 | 2 | 2 | 43,318 | 3 | 21,659 |
| 4 | VEG 수목 | 6 | 6 | 126,543 | 39 | 23,136 |
| 5 | CTB 한옥 | 111 | 111 | 3,297,117 | 1,533 | **29,905** |
| | 합계 | **121** | **123** | 3,477,458 | 1,611 | |

**JAM·SBK·HPR 의 19+8+2 = 29개 파일은 올리지 않는다.**

파일당 30,000 삼각형 상한 아래다(최대 29,905, 여유 95). 상한은 메시가 아니라 **파일 단위**다.
1→4 를 먼저 하는 이유: 지면·도로가 못 들어가면 CTB 111개가 통째로 의미 없어진다.
`CTR_01`(28 MB, 장당 3.4 MB)은 v22 에서 이미 통과했다.

### 3-2. 절차

```powershell
. %USERPROFILE%\Desktop\blender\gyeongbokgung\ovdr_place.ps1
Save-OvdrBeforeIds -Out %USERPROFILE%\Desktop\blender\ovdr_export\hwaseong_v23
```

**이걸 먼저 돌리지 않으면 어떤 에셋이 새로 들어왔는지 구분할 방법이 없다.**
(v22 때 빼먹어서 `createdTime` 으로 창을 역추적해야 했다.)
`before_ids.txt` 가 이미 있으면 그때 스냅샷이니 **날짜를 확인하고 신선하면 재사용**한다 —
현재 파일은 3,403줄로 지금 에셋 테이블과 일치하므로 그대로 쓸 수 있다.

그다음 Studio GUI → Bulk Import → 파일 하나 → 등록 완료 대기 → 다음.
`NO_FILE_DIALOG` 로 실패하면 그냥 재시도한다. **임포트 실패는 안전하다** — 발행이 안 되므로
중복 걱정이 없다. `UCX_` 접두 메시는 Studio 를 크래시시키는데 우리 익스포트엔 없다.

### 3-3. 중단 규칙

> **처음 5개 파일마다** `UGCLocalAssetTable.json` 의 contentId 집합 차이를 기록한다.
> (파일 → 신규 STATIC_MESH 수)가 매니페스트 메시 수와 어긋나면 **즉시 멈추고 보고한다.**
> 남은 116개는 되돌릴 수 없다.

### 3-4. ID 매핑은 두 방법으로 교차검증한다 [JSN §2]

(a) `before_ids.txt` 와의 contentId 집합 차이 + `createdTime` 순서 짝짓기
(b) FBX 에 박힌 텍스처 파일명과 TEXTURE 에셋 이름 대조
    (`check_export_textures.py` 가 FBX 를 직접 열어 목록을 뽑는다)

JSN 은 30/30 일치를 확인하고 나서야 배치에 들어갔다. **이 교차검증은 생략하지 마라.**
`make_placement.py` 가 `missing` 또는 `ambiguous` 를 0 이 아닌 값으로 내면 **배치하지 않는다.**

---

## 4. 배치

### 4-1. 지금 바로 쓸 수 있는 것

```
ovdr_export\hwaseong_v23\placement_core66.json      JAM 32 + SBK 28 + HPR 6 = 66개
    size_mode        "LITERAL_CM"
    origin_delta_cm  {X: -58000, Y: -5000, Z: 0}     ← 이미 cframe 에 반영됨
    counts           missing 0 / ambiguous 0
    bounds_cm        X 53,619~70,008  Y −54~2,211  Z −2,856~3,193
```

발행이 끝나면 나머지를 만든다:

```
python gyeongbokgung\make_placement.py ^
    --manifest %USERPROFILE%\Desktop\blender\ovdr_export\hwaseong_v23\manifest.json ^
    --groups-only HGD,CTR,CTP,VEG,CTB ^
    --out %USERPROFILE%\Desktop\blender\ovdr_export\hwaseong_v23\placement_rest123.json
```

`textureId` 는 빈 문자열로 나온다 — 4-3 을 보고 채운다.

### 4-2. `items[]` 하나 → `MeshPart` 하나

| MeshPart 속성 | 필드 | 비고 |
|---|---|---|
| `Name` | `name` | |
| `MeshId` | `meshId` | `ovdrassetid://` 가 이미 붙어 있다 |
| `TextureId` | `textureId` | 4-3 |
| `CFrame.Position` | `cframe` | **원점 보정 적용됨. 또 더하지 마라** |
| `CFrame.Orientation` | `orientation` | 전부 0. **예외 없음** (1-2) |
| `Size` | `size_literal_cm` | cm 실치수 (1-3) |
| `Color` | `color` | 텍스처 있는 메시는 255. **200 으로 두지 마라 — 텍스처가 78% 로 어두워진다**(200/255) |
| `Material` | `material` | 텍스처 메시는 `Basic` |
| `Transparency` | `transparency` | |
| `Anchored` | `anchored` | 전부 true |
| `CanCollide` | `canCollide` | **전부 false** — 5장을 읽어라 |
| `CollisionProfile` | `collisionProfile` | `NoCollision` |
| `CastShadow` | `castShadow` | |
| `DoubleSided` | `doubleSided` | **VEG·CTP 만 true** — 소나무 잎이 알파 카드라 단면이면 절반 사라진다 |

부모는 `Workspace` 아래 `Model` 하나를 만들어 `parent_model`(`Hwaseong Place`)로 쓴다.
`Changdeokgung Place` / `JSN_Sangok` 관례와 같다. 통째로 지우려면 이 Model 만 비우면 된다.

생성 경로: **`.ovdrjm` 국소 편집 + `level.apply`**. `instance.create` 는 속성을 안 받는다
[JSN §0]. `ovdr_level.ps1` 의 `New-OvdrMeshPartJson` / `Add-OvdrInstances` 를 쓴다.
JSON 형태는 `JSN_Sangok\_ovdr\regen_batches.py` 의 `mesh_item()` 이 그대로 참고가 된다
(단 회전 보정 부분은 화성에 해당 없음 — 1-2).

### 4-3. `TextureId` — MODEL 에셋에서 뽑는다

임포트할 때 텍스처가 별도 TEXTURE 에셋으로 발행되고 **MeshPart 에 자동으로 안 물린다**(M3 참).
이름으로는 못 짝짓는다(2-1). **파일마다 생기는 `MODEL` 에셋이 메시-텍스처 대응을 들고 있다.**

`core_texture_map.json` 이 JAM·SBK·HPR 29개 파일에 대해 그 대응을 뽑아 둔 결과물이고,
`placement_core66.json` 의 `textureId` 는 여기서 채운 값이다. 나머지 121개 파일도
**같은 방법으로** 뽑는다 — 발행 후 MODEL 에셋을 읽어 메시 id → 텍스처 id 표를 만든 뒤
`placement_rest123.json` 의 빈 `textureId` 에 채운다.

배치 직후 한 개를 읽어 `TextureId` 가 살아 있는지 확인한다. 비어 있으면 회색으로 들어간다.

---

## 5. 지형 충돌 — **메시로는 못 걷는다** [JSN §3]

> **이건 화성에서 아직 안 해봤다. 아래 5-1 은 실측, 5-2 는 화성용 설계다.**
> JSN 에서 확인된 사실: "MeshPart 에 `CanCollide=true` 를 켜면 걸어다닐 수 있다"는 **틀렸다.**
> 로그상 `QueryAndPhysics` 로 잡히지만 **플레이어는 그냥 뚫고 떨어진다.**
> MeshPart 에는 `CollisionFidelity` 같은 속성이 없고, 엔진이 높이맵을 볼록 덩어리 ~30개로
> 쪼개 버려서 골짜기는 메워지고 능선은 뭉개진다.

따라서 1차 배치에서 **`CanCollide` 는 전부 false** 로 둔다. 걸어다니게 만드는 것은
별도 `Part` 층이다.

### 5-1. 화성 지면의 실측 형상

| | 값 |
|---|---|
| 지면 메시 `HGD_01` | 삼각형 2,236, 372 × 384 m |
| 격자 | **12 m 정방** (`dem.GRID_M`), **31 × 32 = 992 셀** |
| 지표면 높이 (보정 후) | Y **−389 ~ +400 cm** — 기복 **7.9 m** |
| 평균 경사 | 약 2%. 산곡(표고 80 m, 최대경사 65°)과 비교가 안 되게 평탄하다 |

### 5-2. 화성은 쿼드트리가 필요 없다 — 격자 그대로 992장

JSN 은 지형이 임의 메시라 `obj.ray_cast` 로 257×257 높이맵을 뜨고 적응 분할했다.
**화성은 그럴 필요가 없다.** 지면이 애초에 `dem.node(i,j)` 를 그대로 꽂아 만든 12 m 정방
격자이고, `dem.surface_at(x, y)` 가 그 삼각화 방향까지 똑같이 재현하는 해석식이다.
**셀 하나당 슬래브 하나를 그대로 얹으면 잔차가 원리적으로 cm 급이다.**

```
셀 (i, j) 의 네 꼭짓점 높이 = dem.node(i,j), node(i+1,j), node(i,j+1), node(i+1,j+1)
  1. 네 점에 최소자승 평면 z = a·x + b·y + c
  2. 법선  블렌더 (-a, -b, 1)  →  엔진 (-a, 1, b)  정규화
  3. 회전  Vector((0,1,0)).rotation_difference(N).to_matrix().to_euler('ZXY')
     ※ Part 는 임포트 에셋이 아니므로 1-2 의 "Orientation 0" 규약이 아니라
       JSN §3-2 의 Part 규약을 따른다. 180도류 보정은 넣지 않는다.
  4. 한 변  = 1200 / cosθ + 60 cm   (경사 투영 보정 + 이웃과 겹침)
     두께  = clamp(2 × 잔차 × 100 + 200, 300, 3000) cm
     중심  = 평면 위 점 − N × (두께/2)      → 윗면이 지면에 정확히 온다
  5. 좌표에는 1-4 의 ΔX/ΔY/ΔZ 를 그대로 적용한다
```

예상 **992장** (JSN 은 1,669장). 산출 형식은 `JSN_Sangok\_ovdr\collision_parts.json` 과
같게 한다 — `{"name", "pos"[3], "ori"[3], "size"[3]}` 배열.

**넣는 순서** [JSN §3-2]: 처음엔 `Transparency 0` + 눈에 띄는 색으로 넣고 `game.screenshot`
으로 지형에 붙었는지 **그림으로 확인**한다. 확인되면 `Transparency 1` 로 돌린다.
**처음부터 투명하게 넣으면 틀려도 안 보인다.**

### 5-3. 지면 외의 충돌

| 그룹 | 권고 | 근거 |
|---|---|---|
| HGD 지면 | MeshPart 는 false, **Part 슬래브 992장** | 5-2 |
| SBK 성벽 · JAM 문루 | 박스에 가까우니 `CanCollide=true` 를 **시험해 본다** | JSN 은 바위(볼록에 가까움)는 켜도 됐다. **화성에서 미검증** |
| CTB 한옥 | 성능을 보고 마지막에 결정 | 111개 파일 |
| VEG · CTP 수목 | **끈 채로 둔다** | 알파 카드는 볼록 분해가 무의미하다 |

---

## 6. 검증

### 6-1. 값 대조 (`ovdr_readback.ps1` / `Test-OvdrPlacement`)

| # | 검사 | 통과 기준 | 실패하면 |
|---|---|---|---|
| V1 | `items` 가 전부 인스턴스로 있는가 | 66/66, 123/123 | 누락 slug 보고 |
| V2 | `CFrame.Position` = `cframe` | 1.0 cm 이내 | 원점 보정을 두 번 더했는지 확인 |
| V3 | `Orientation` | 전부 0 (0.5° 이내) | **부재별로 돌려서 맞추지 마라** (1-2) |
| V4 | `Size` = `size_literal_cm` | 0.5% 이내 | |
| V5 | `Size / (2 × UnitExtent)` | 1.0 ±1% | `(50,50,−50)` 이면 **판정 무효** — Studio 가 메시를 아직 안 읽었다. `level.apply` → `level.save.file` 후 재측정 |
| V6 | `MeshId` 가 비었거나 다른 slug 가 같은 id 를 물었는가 | 0건 | 에셋 매핑 재실행 |
| V7 | `CanCollide` / `CollisionProfile` | 전부 false / NoCollision | |
| V8 | `TextureId` | 전부 비어 있지 않음 | 4-3 |

> **값을 다시 읽어 대조하는 건 검증이 아니다. 내가 쓴 값을 내가 읽는 것일 뿐이다.**
> 반드시 아래를 같이 한다. [JSN §5]

### 6-2. 그림으로 볼 것 — `game.screenshot` 은 **사용자가 지금 보는 뷰포트**를 찍는다

에디터 카메라는 RPC 로 못 움직인다. 사용자가 문제를 보고 있으면 그 화면을 바로 받을 수 있다.
**이걸 먼저 써라.**

| 볼 것 | 기대 | 아니면 |
|---|---|---|
| 장안문 옹성의 방향 | 반원이 **성 바깥(도시 쪽)**으로 튀어나온다 | Z 부호가 뒤집혔다. 대칭 물체로는 못 가린다 |
| 성벽·문루가 지면에 얹혀 있는가 | 격자를 뚫고 내려가지 않는다 | 1-1 의 `FLOOR_Y` 를 두 번 뺐는지 확인 |
| 문루 크기 | 2층 문루 폭 약 30 m (사람 키의 20배) | `size_mode` 오적용 |
| 지붕 두께 | 종잇장이 아니다 | Solidify 미적용 |
| 소나무 잎 | 온전하다 | `DoubleSided` 가 false |
| 창덕궁과의 거리 | 화성 서쪽 끝과 98 m | 1-4 |
| 산곡과 나란히 놓고 크기 | 선형 1.3배 정도 | |

### 6-3. 그 밖에

- **정점 예산**: 화면당 7만 정점 권고. 배치 후 `game.play` 로 프레임타임 실측.
- **다른 인스턴스를 안 건드렸는지**: 백업과 blockwise diff. 인스턴스별 이름 → 블록 해시 대조.
  `ObjectKey` 는 저장 때마다 재부여되므로 그것만 다른 건 정상이다. [JSN §8]

---

## 7. 재사용할 것 — 새로 짜지 마라

| 경로 | 역할 |
|---|---|
| `gyeongbokgung\ovdr_rpc.ps1` | `Invoke-OvdrRpc`. 포트 13377, raw TCP 줄바꿈 구분 JSON-RPC |
| `gyeongbokgung\ovdr_level.ps1` | `.ovdrjm` 국소 편집. `New-OvdrMeshPartJson`, `Add-OvdrInstances` 등 |
| `gyeongbokgung\ovdr_place.ps1` | `Save-OvdrBeforeIds`, 에셋 매핑, `Test-OvdrPlacement` |
| `gyeongbokgung\ovdr_readback.ps1` | 되읽기 검증 |
| `gyeongbokgung\export_overdare.py` | **좌표 규약 정본** |
| `gyeongbokgung\make_placement.py` | 매니페스트 + 에셋 테이블 → 배치 지시서. `DELTA` 여기 |
| `gyeongbokgung\check_export_textures.py` | FBX 를 직접 열어 임베디드 텍스처를 SOF/IHDR 로 검증 |
| `JSN_Sangok\_ovdr\regen_batches.py` | 배치 JSON 생성 예시 (`mesh_item`, 기준자 Part) |
| `JSN_Sangok\_ovdr\collision_parts.json` | 충돌 슬래브 산출 형식 예시 (1,669장) |

**`.ps1` 은 UTF-8 BOM 필수** — 없으면 PS 5.1 이 949 로 읽어 한글이 깨지고
`Missing closing '}'` 같은 엉뚱한 파서 에러를 낸다 [JSN §6].

---

## 8. 화성에서 실제로 틀렸던 것 — 반복 금지

| 증상 | 진짜 원인 | 처방 |
|---|---|---|
| **FBX 279개 중 235개에 텍스처가 하나도 없었다** | `split_mesh_lossless` 가 새 메시를 만들면서 머티리얼 슬롯을 안 옮겼다. `bm.to_mesh()` 는 면의 `material_index` 만 옮기고 `nm.materials` 는 안 옮긴다 | 쓰는 슬롯만 옮기고 `material_index` 재매핑 (`export_overdare.py:226`) |
| 그 수정이 익스포트를 **455 MB → 3.34 GB** 로 키웠다 | 원본 슬롯을 통째로 복사했다. 사랑채는 머티리얼 15종인데 조각이 189개 | 위와 같음 — **쓰는 것만** 옮긴다 |
| 지면·갓길·바위만 diffuse 가 빠졌다 | `terrain._tint()` 가 이미지와 Principled `Base Color` 사이에 MixRGB 를 끼웠다. **FBX 익스포터는 Base Color 에 직결된 이미지만 내보낸다** | 보정을 노드가 아니라 **이미지 픽셀에 굽는다** (numpy `foreach_get`/`foreach_set`) |
| 기와가 칼날처럼 튀어나왔다 | 데시메이션. **최종 면 수가 아니라 ratio 가 문제였다** — 0.45 는 멀쩡하고 0.30 은 갈렸다 | 원본 재다운로드 → 용접 → ratio 0.45 (`rebake_hanok.py`) |
| 사랑채가 0.866배로 나왔다 | `_join` 이 부모가 있는 오브젝트에 `matrix_world = 단위행렬` 을 넣어 부모 변환이 되살아났다 | 굽기 전에 부모를 먼저 끊는다 |
| 도로가 땅에 잠겼다 | 지면은 12 m 삼각 격자인데 도로는 연속 DEM 을 샘플링했다. 차이가 5 cm 여유를 넘었다 | `dem.surface_at()` 이 **삼각화 방향까지 같게** 재현하고, 모든 배치가 이걸 부른다 |
| 지면에 얼룩진 그림자 | 기하가 아니라 **가상 섀도우맵 페이지 고갈**. 해상도를 **올렸더니 더 나빠졌다** | `shadow_maximum_resolution = 0.05` |
| 타일 크기를 2.5→20→170 m 로 바꿔도 그림이 똑같았다 | Poly Haven 애드온의 Mapping 노드가 `vector_type='TEXTURE'` 라 Scale 이 **나눗셈**으로 작동 | `mp.vector_type = 'POINT'` |
| 도로가 톱니처럼 삐죽했다 | 0.16 m 격자 좌표 해시가 2.5 m 정점 간격에서 백색잡음이 됐다 | 22 m 파장 smooth value noise |
| 배치 안 한 건물이 씬에 남았다 | `build_uigwe.build_all()` 이 무조건 실행됐다 | `layout.BUILDINGS` 가 안 부르면 만들지도 않는다 |
| **맵이 산곡의 4배였다** | 마을이 아니라 빈 들판. `pad=80` 이 가로·세로에 160 m 씩 붙였다 | 0-1 의 세 값 |
| **창덕궁과 겹치는 배치 파일을 넘겼다** | 겹침을 **명세서에 적어 놓고도 파일은 그대로 넘겼다** | 1-4. **문제를 문서화하는 것은 해결이 아니다. 넘기기 전에 고친다** |

---

## 9. 안전 규칙 [JSN §8 + 화성 추가]

- **발행된 에셋은 어떤 경우에도 다시 올리지 않는다.** 특히 **JAM 19 · SBK 8 · HPR 2 = 29개
  파일**은 v23 에도 유효하니 절대 올리지 마라 (2장).
- **`level.publish` 를 부르지 않는다.**
- **플레이 중에 편집하지 않는다** — 항상 `game.stop` 먼저.
- **매 단계 전에 백업** — `%USERPROFILE%\Desktop\ovdr_backup\hwaseong_step<N>_<이름>.ovdrjm`.
  되돌리기는 파일 복사 → `level.apply` → `level.save.file`. 백업이 **신선한지 확인하고** 쓴다.
- **`.ovdrjm` 은 UTF-16LE + BOM.** 전체를 `ConvertFrom-Json`/`ConvertTo-Json` 왕복시키면
  데이터가 훼손된다. **국소 문자열 치환만** 한다.
- **작업 대상 밖의 인스턴스를 건드리지 않는다** — `JSN_Sangok` 3,396개, `Lobby`,
  `Changdeokgung Place`, `Wakizashi_*`, `GND_Base`, `WarCitySpawn`.
- 배치는 되돌릴 수 있고 **발행만 되돌릴 수 없다.** 규약이 헷갈리면 프로브를 놓았다 지워라 —
  임포트 예산을 전혀 쓰지 않는다.

---

## 10. 아직 모르는 것

| 항목 | 어떻게 확정하나 |
|---|---|
| 121개 파일 발행 시 신규 에셋 수 | 3-3 의 중단 규칙으로 첫 5개에서 검증 |
| CTB 111개(1.5 GB)를 임포터가 견디는가 | 순서대로 올리다 막히면 그때 텍스처 1024→512 를 검토 |
| 성벽·문루에 `CanCollide=true` 가 통하는가 | 5-3. **켜고 실제로 서 봐야 안다** |
| 992장 Part 층의 프레임 비용 | 넣고 `game.play` |
| 사랑채 189조각의 최종 인상 | 연속된 10채 이상을 붙여 봐야 안다 |
| 화면당 정점 예산 | 배치 후 실측 |

미해결로 남은 JSN 항목 중 **타일 이음매**[JSN §4]는 화성에 해당하지 않는다 —
지면이 `HGD_01` 한 장(2,236 삼각형)이라 애초에 쪼개지 않았다.
