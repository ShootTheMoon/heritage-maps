# JSN_Sangok 오버데어 반입 패키지 — 다른 컴퓨터용

조선 산곡 자연지형 맵. **FBX 30개 + 배치 데이터 2,383행 + 절차서.**

---

## 0. 먼저 — 에셋 ID 는 이 컴퓨터에서 안 통한다

`asset_ids.json` 에 든 숫자는 **원래 컴퓨터의 로컬 에셋 ID**다.
오버데어 로컬 에셋 테이블은 컴퓨터/프로젝트마다 따로 놀기 때문에,
여기서는 **FBX 를 다시 발행해서 새 ID 를 받아야 한다.**

배치 좌표(`placements.csv`)와 형상(FBX)은 그대로 쓴다. ID 만 갈아끼우면 된다.

---

## 1. 순서

### 1-1. FBX 30개 발행

Studio 를 켜고 프로젝트를 연 뒤, **한 번에 파일 하나씩** Bulk Import.

```
10_MASTERS/MST_*_overdare.fbx      11개
01_TERRAIN/STA_TER_*_overdare.fbx  16개
02_STATIC/STA_*_overdare.fbx        3개
```

**폴리곤 한계 30,000 은 파일 단위다.** `bulk_import` 는 넘긴 파일들을 하나로
합치므로, 두 개만 같이 넘겨도 초과한다. 실측:

| 번들 | 총 tris | 결과 |
|---|---:|---|
| 곰솔 단독 | 8,329 | 성공 |
| 바위A 단독 | 26,999 | 성공 |
| 바위A + 곰솔 | 36,329 | 등록 0 |
| 바위 B+C+D | 81,000 | **Studio 크래시** |

같은 파일을 두 번 올리면 교체가 아니라 **중복 발행**이다. 되돌릴 수 없다.

### 1-2. 새 ID 로 배치 데이터 다시 굽기

```
python _scripts/ovd_place_build.py --table "<프로젝트폴더>/UGCLocalAssetTable.json"
```

이게 하는 일:
1. 그 컴퓨터의 에셋 테이블을 읽어 `asset_ids.json` 을 새 ID 로 덮어쓴다
2. `placements.csv` 2,383행을 `06_OVERDARE/_place/place_000.json` ~ `place_011.json`
   (한 파일 200개) 로 굽는다

`items_static.json` 도 새 ID 로 손봐야 한다 (19개뿐이라 손으로 고쳐도 된다).

### 1-3. STATIC 19개 배치

```
overdare_create_instances(itemsFile="06_OVERDARE/items_static.json")
```

전부 `position [0,0,0]` 인데 **이게 정상**이다. STATIC 메시는 월드 좌표를
정점에 구워 넣었으므로 원점에 떨구면 제자리에 조립된다.

검증: `STA_TER_00` 의 `UnitExtent` 가 `3250 × 3380 × 3250` 이어야 한다.
**UnitExtent 는 절반값**이므로 실제 65 × 67.6 × 65 m.

### 1-4. 인스턴스 2,383개 배치

`_place/place_000.json` 부터 12회 호출.

**먼저 2~3개로 스케일을 검증할 것.**

```
python _scripts/ovd_place_build.py --limit 3
```

---

## 2. 미해결 — 스케일

측정된 사실:
- 임포트된 `MeshPart` 의 `Size` 는 메시 실제 크기와 무관하게 **항상 `[100,100,100]`**
- `UnitExtent` 는 메시 고유값이고 **절반값**이다

가설 A (`--scale-mode percent`, 기본값): `Size` 는 백분율 → `100 * 배율`
가설 B (`--scale-mode unit`): `Size` 는 무시 → 마스터를 배율 구간별로 여러 개 발행해야 함

배율이 실제로 필요한 근거: 곰솔 0.55~1.17배(수령 편차), 자갈 0.12~0.36,
**`MST_ROCK_MASS` 는 0.098~0.128배**(원본이 97 m 절벽이라 그대로 쓰면 맵 서쪽 절반을 먹는다).

---

## 3. 충돌 — FBX 에 넣지 말 것

오버데어는 **UCX 규약을 구현하지 않는다.** 단독 `UCX_*.fbx` 는 발행 실패,
렌더 파일 안의 `UCX_` 메시는 **Studio 크래시**(`LevelActor.cpp:583`).

엔진 `Part` 를 쓴다 (발행 에셋 0개). `Transparency 1`, `CanCollide true`,
`Anchored`, `Static`. 바위·나무는 **회전 박스** — 45° 돌아간 물체를 축정렬
박스로 감싸면 40% 이상 부풀어 통로를 막는다.

지형 반입 시 뜨는 `Convex hull generation produced zero convex particles,
collision will fail` 경고는 **정상이다.**

---

## 4. 이 패키지에 든 것

| | |
|---|---|
| `10_MASTERS/` | 마스터 FBX 11개 (곰솔·억새·쑥·자갈·바위 A~F·주상절리 암괴) |
| `01_TERRAIN/` | 지형 타일 FBX 16개 (4×4, 월드 좌표 구움) |
| `02_STATIC/` | 계류·지류 수면 + 석단 FBX 3개 |
| `placements.csv` | 인스턴스 2,383행 (좌표 변환 이미 적용됨) |
| `_place/` | 위 CSV 를 배치용 JSON 으로 구운 것 12파일 |
| `items_static.json` | STATIC 19개 배치 |
| `asset_ids.json` | **원본 컴퓨터의 ID — 여기서는 못 씀.** 형식 참고용 |
| `IMPORT_GUIDE.md` | 임포트 절차서 (처음부터) |
| `PLACEMENT_SPEC.md` | 배치 명세 |
| `IMPORT_ORDER.md` `PLAN.md` | 반입 순서 / 파이프라인 계획 |
| `_scripts/` | 재생성 스크립트 (Blender 원본을 고칠 때만 필요) |
| `05_Documentation/` | 맵 명세서·보행성 감사·고증 메모 |

### 블렌더 원본 (FULL 압축본에만 들어 있음)

| | |
|---|---|
| `00_Source_Blender/JSN_Master_OVD.blend` | 맵 원본 (2,398 오브젝트 / 유니크 메시 15개) |
| `_TexLib/` | 지형 PBR 4세트 (T_Ground01A / 02A / Stone01B / Sand_ColorB) |
| `_extracted/` | KHS 원본 스캔 — 주상절리 암석 A~F + 암괴 + 식생 |
| `06_OVERDARE/_texwork/` | 512 텍스처 14장 + 아틀라스 3장 + 지형 베이크 소스 |
| `04_Previews/` | 렌더·워크스루 프리뷰 |

`.blend` 는 zstd 압축본이라 텍스처가 팩돼 있는지 밖에서는 확인이 안 된다.
**핑크(누락) 재질이 뜨면** `_TexLib` 과 `_extracted` 를 같은 상대 경로에 두고
`File > External Data > Find Missing Files` 를 돌리면 된다.
`_scripts/jsn_live.py` 는 `_TexLib` 을 먼저 보고 없으면 원본 컴퓨터의 창덕궁·
소쇄원 경로로 떨어지게 돼 있으므로, `_TexLib` 만 제자리에 있으면 재실행도 된다.

두 가지 압축본이 있다:

| 압축본 | 크기 | 용도 |
|---|---:|---|
| `JSN_Sangok_OVERDARE_import_*.zip` | 54 MB | 반입만 시도 (FBX + 배치 + 문서) |
| `JSN_Sangok_FULL_*.zip` | 1.34 GB | 위 + 블렌더 원본 + 텍스처 + 원본 스캔 |

---

## 5. 알려진 한계

- 지형이 **전 구역 60° 미만**이다. 통행 불가 경사가 0.0%, 50~60°가 0.2%.
  능선·고개·지류의 전술 구조는 **시각적일 뿐** 실제 이동 제약이 아니다.
  유일한 실제 차단은 바위 프롭 3.2%
- 충돌 Part 는 아직 안 만들었다
