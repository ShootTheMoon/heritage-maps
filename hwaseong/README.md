# 수원 화성 — 장안문 권역

국가유산청(KCISA) 실측 스캔으로 지은 장안문과 그 주변 한옥 마을.
`onlyoneshot` 레벨에 반입하는 것까지가 범위다.

> **이 폴더는 2026-08 작업분이다.** 반경 150 m 축소(v23)까지의 명세와 그때 만든 검사
> 도구들이다. 이후 팔달문 권역 절차 생성은 [`docs/plans/hwaseong-paldalmun-layout.md`](../docs/plans/hwaseong-paldalmun-layout.md)
> 로 갈라졌고, v25 재빌드(장안문 아레나, 2026-09)는 [`v25/`](v25/) 에 있다.

| | |
|---|---|
| 범위 | 장안문 문루 · 성벽 · 홍이포 · 도시 한옥 · 흙길 · 수목 · 지면 |
| 크기 | 372 × 384 m (산곡의 선형 1.34배) |
| 익스포트 | 파일 150 / 메시 189 / 삼각형 4,067,320 |
| 레벨 좌표 | X 42,800 ~ 80,000 · Z ±19,200 |

---

## 읽는 순서

| 문서 | 내용 |
|---|---|
| [`docs/IMPORT_SPEC.md`](docs/IMPORT_SPEC.md) | **본문.** 좌표 규약, 발행 절차, 배치, 지형 충돌, 검증, 틀렸던 것 전부 |
| [`docs/HANDOVER_PROMPT.md`](docs/HANDOVER_PROMPT.md) | 배치 담당에게 그대로 넘기는 작업 지시서 |
| [`docs/POSTMORTEM_RUINS.md`](docs/POSTMORTEM_RUINS.md) | 건물이 폐가처럼 부서진 건의 진단 기록 |

일반 규칙(JSN_Sangok 편)은 [overdare-map-pipeline](https://github.com/ShootTheMoon/overdare-map-pipeline)
쪽에 있다. `IMPORT_SPEC.md` 가 `[JSN §n]` 으로 가리키는 게 그것이다.

---

## 이 맵이 다른 맵과 다른 네 가지

같은 조직 안에서도 맵마다 규약이 다르다. 산곡 레시피를 화성에 그대로 쓰면 터진다.

| | JSN_Sangok | **화성** |
|---|---|---|
| Y 축 | `Y = bz * 100` | **`Y = bz * 100 + 5000`** (FLOOR_Y) |
| 회전 | `M·R_b·Mᵀ` → `to_euler('ZXY')` + 월드 Y 180° 보정 | **`Orientation = (0,0,0)` 예외 없음** |
| 피벗 | 마스터가 바닥 중앙이라 로컬 up 으로 h/2 올림 | **각자의 bbox 중심 그대로** |
| 원점 델타 | `OFFSET = -60000` (X 만) | **ΔX −58000 / ΔY −5000 / ΔZ 0** |

화성 익스포터는 오브젝트마다 `matrix_world` 를 메시 정점에 굽는다. 회전이 이미
정점에 들어가 있고 임포터는 각 메시를 자기 bbox 중심으로 재중심화하므로,
**Orientation 을 주면 조각마다 제자리에서 돌아 조립이 흩어진다.**

실제로 이 사고가 났다. 189개 전부에 산곡의 Y 180° 보정이 들어가 건물이 폐가처럼
부서졌다. 기록은 `POSTMORTEM_RUINS.md` 에 있다.

ΔX 가 −58000 인 것도 사고에서 나온 값이다. 레벨의 `PLACE NEW MAP CENTER HERE`
표지판(X 50000)을 따라 −70000 을 쓰면 맵 서쪽 끝이 X 30,800 까지 내려와
**창덕궁(27,000~33,000)과 22 m 겹친다.**

---

## 도구

전부 단독 실행이다. `make_placement.py` 만 순수 파이썬이고 나머지는 블렌더가 필요하다.

| | |
|---|---|
| [`tools/make_placement.py`](tools/make_placement.py) | 매니페스트 + 오버데어 에셋 테이블 → **해석이 끝난 배치 지시서**. contentId 조회, 원점 보정, 팔레트 색을 한 번에 푼다. 동명 에셋은 `createdTime` 최신을 고르고 로그를 남긴다 |
| [`tools/check_export_textures.py`](tools/check_export_textures.py) | FBX 를 직접 열어 임베디드 이미지를 **JPEG SOF / PNG IHDR 헤더로** 검증. 생바이트 매직 탐색은 압축된 지오메트리에서 오탐이 난다 |
| [`tools/check_shells.py`](tools/check_shells.py) | 연결 껍질 수로 **메시가 갈렸는지** 판정. 눈으로도 치수로도 안 보이는 결함을 잡는다 |
| [`tools/check_fbx_roundtrip.py`](tools/check_fbx_roundtrip.py) | FBX 를 되열어 매니페스트와 대조. 익스포트가 범인인지 가른다 |
| [`tools/rebake_hanok.py`](tools/rebake_hanok.py) | 용접 → 데시메이트 → 텍스처 축소 재베이크. 기와가 칼날처럼 튀어나오는 걸 고친다 |

### 진단 순서

값만 다시 읽어 대조하는 건 검증이 아니다. **독립적인 경로로 재야** 한다.

```
1. check_export_textures.py   텍스처가 실렸나
2. check_fbx_roundtrip.py     치수가 맞나          → 틀리면 익스포터
3. check_shells.py            위상이 멀쩡한가      → 면/껍질 2면 갈린 것
4. 레벨에서 Orientation·Size  → 둘 다 멀쩡하면 배치
```

화성에서 이 순서로 돌려 1·2 는 완벽, 3 에서 갈림을 발견, 4 에서 Y 180° 오적용을
찾았다. 3번이 없었으면 "배치는 맞는데 왜 이러지"에서 멈췄다.

---

## 되풀이하지 말 것

`IMPORT_SPEC.md` §8 에 전부 있고, 특히 비싸게 배운 셋:

- **데시메이트는 최종 면 수가 아니라 ratio 가 문제다.** 0.45 는 멀쩡하고 0.30 은 갈린다.
  용접(`WELD_M 0.008`)을 먼저 하지 않으면 어떤 ratio 로도 갈린다.
- **FBX 익스포터는 Base Color 에 직결된 이미지만 내보낸다.** 색보정 노드를 하나
  끼우면 diffuse 가 통째로 빠진다. 보정은 **이미지 픽셀에 굽는다**.
- **`bm.to_mesh()` 는 면의 `material_index` 만 옮기고 머티리얼 슬롯은 안 옮긴다.**
  이걸로 279개 중 235개가 텍스처 없이 나갔다. 옮길 때 **쓰는 슬롯만** 옮긴다 —
  통째로 복사하면 같은 텍스처가 조각마다 중복 임베드돼 455 MB 가 3.34 GB 가 된다.

---

## 출처

> 출처: 국가유산청, 국가유산 3D 데이터 (KOGL 제1유형)

지면 표고는 AWS Terrain Tiles(terrarium, 공개·무인증), 지표 텍스처는 Poly Haven(CC0).
FBX·텍스처·`.blend` 는 용량 때문에 이 리포에 없다.
