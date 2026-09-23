# 창덕궁 작업 — GitHub 공개 현황 점검

작성 2026-09-08. 창덕궁(CDG) 맵 세션에서 나온 것 중 **무엇이 이미 공개돼 있고 무엇이 빠졌는지**를
실제 리포를 조회해서 확인한 기록.

---

## 결론

**새 리포는 필요 없다.** 코드도 문서도 이미 올라가 있다. 남은 건 **빠진 발견 사실을 채우는 것**뿐이다.

---

## ★ 정정 — 이전 판단이 틀렸다

이 세션 앞부분에서 "Desktop 어디에도 git 저장소가 없다 → 새 리포 `khs-heritage-to-game-pipeline`를
만들자"고 했다. **틀렸다.** 로컬 폴더에 `.git`이 있는지만 봤고, 원격을 확인하지 않았다.

실제로는 조직 `ShootTheMoon`(계정 `Seungpyo1007`)에 공개 리포 8개가 있고, 창덕궁 작업은
그중 2개에 **이미 들어가 있다.**

---

## 확인된 현재 상태 (`gh` 조회, 2026-09-08)

### `ShootTheMoon/overdare-map-pipeline` — 코드 (MIT)

CDG 스크립트 **19개 전부** `blender/heritage/` 에 게시됨:

```
cdg_assemble  cdg_audit   cdg_bbox    cdg_bnd     cdg_diag
cdg_extract   cdg_fixmat  cdg_ground  cdg_lighten cdg_master_render
cdg_matmap    cdg_planartest  cdg_probe  cdg_probe_pt  cdg_reduce
cdg_render    cdg_shelltest   cdg_unembed  cdg_uvtest
```

경로 치환도 규칙대로 되어 있다 — `ROOT = r"C:\Work\blender\CDG_Changdeokgung"`.
사용자명 유출 없음. 총 69개 파일.

### `ShootTheMoon/heritage-maps` — 문서·프리뷰 (KOGL 제1유형)

- `changdeokgung/docs/SOURCE_FACTS.md`
- `previews/changdeokgung/` — MAP_aerial, aerial2, court_eye, gwollaegaksa_eye,
  seonwonjeon_eye, top, top_guides (jpg 7장)

---

## 빠진 것 (우선순위 순)

### 1. `SOURCE_FACTS.md` 가 세션 후반 발견을 담고 있지 않다 ★

현재 문서는 **17개 에셋 / 목표 1.2 M** 기준이다. 최종은 **42개 에셋 / 6.64 M**(사용자 지시:
최대한 유지)이고, 아래가 통째로 빠져 있다.

**(a) 감축 정체 현상 — 이 세션에서 가장 값진 발견**

인정전은 약 **36,000개의 분리된 개별 입체**로 구성돼 있다(주두 `MI_Capital01B` 9,858개,
녹색 목부재 `MI_GreenWood` 25,656개, 공포 `MI_Gongpo01E` 812개). Blender의 COLLAPSE 데시메이트는
분리된 컴포넌트를 병합하지 못해 **조각당 약 36 트라이앵글에서 바닥**을 친다. 이 세 머티리얼만으로
**하한 약 620,000**이고, 요청 비율을 아무리 낮춰도 내려가지 않는다.

측정으로 **배제한 대안** (남이 같은 삽질을 반복하지 않도록 반드시 같이 적을 것):

| 시도 | 결과 |
|---|---|
| 거리 병합(remove_doubles) 선처리 | **악화** 0.29 → 0.42 |
| `UNSUBDIV` | 무효 (0.99) |
| UV 레이어 제거 | 변화 없음 — UV 보존이 원인이 아니다 |
| `use_collapse_triangulate` 토글 | 변화 없음 |
| 30° `DISSOLVE` + `use_dissolve_boundaries` 선처리 | **유일하게 효과** 0.29 → 0.18 |

단, 그 선처리를 **무조건 걸면 지붕이 파괴된다.** `MI_Giwa`는 원래 0.0200까지 깨끗이 내려가는데
선처리를 걸면 0.0044로 무너져 기와면이 사라지고 서까래가 비친다. → plain collapse가 **실제로
정체했을 때만** 재시도하는 적응형으로 바꿔야 하고, 지붕 티어에는 **절대 하한**을 따로 줘야 한다.
(근거 스크립트는 이미 공개돼 있다: `cdg_shelltest.py`, `cdg_planartest.py`, `cdg_uvtest.py`, `cdg_bnd.py`)

**(b) KHS 데이터셋에 벤더 규약이 2종이다**

| | wave 1–3 (17개) | wave 4 = 궐내각사 (25개) |
|---|---|---|
| 메시 | Geometry 노드 1개 (통짜) | 다중 오브젝트 |
| 머티리얼명 | `MI_Giwa` | `M_`, `MI_`, `N_`, `Ml_`, `M_TWJ_`, `Giwa_MTL`, `lambert2`, `BOT3` |
| 텍스처 | 내장 + 동일 이름 `T_*_BC.png` | **내장 없음.** 미배포 `..\module\tri\texture\MI_<Mat>_BaseColor.png` 참조 |

→ 해결 불가 이미지 760장이 생기고 궐내각사 건물이 전부 **자홍색**(Blender의 텍스처 없음 색)으로
렌더된다. zip 안의 `T_<Name>_BC.png`가 맞는 텍스처이므로 **머티리얼 이름에서 링크를 복원**한다
(`M_Capital01A` → `T_Capital01A_BC.png`). `cdg_matmap.py`가 접두사 제거 → 정확 →
어간 → 최근접 변형 → 키워드 → 중립 순으로 **548/548 매핑**, 82% 정확 일치, 중립 폴백은
트라이앵글 기준 1%.

**(c) 추가로 확정된 함정**

- **OVERDARE는 FBX 1개당 메시 200개 제한**도 있다 (`Maximum allowed mesh count: 200`).
  기존 README의 30,000 트라이앵글 표에 이 줄이 없다.
- **뷰포트 `shading.type = 'RENDERED'`가 GPU 드라이버를 죽인다.**
  435만 트라이앵글 × 패킹 텍스처 1,286장(약 4 GB) → `nvoglv64.dll`에서
  `EXCEPTION_ACCESS_VIOLATION`. **SOLID + color_type='TEXTURE'**를 쓸 것.
- **어셈블이 텍스처를 전부 패킹해 마스터 blend가 8.83 GB가 된다.** 드라이브가 100%가 되면
  그 다음 저장이 **에러 없이 조용히 실패**한다(지형이 그냥 사라짐). 512 라이브러리 참조로
  바꾸고 고아 이미지를 정리하면 **8.83 GB → 0.24 GB**.
- **`img.has_data`는 유효성 판별에 쓰면 안 된다** — 정상 디스크 이미지에도 False가 나온다.
  이 함정으로 두 번 오진했다.
- **zip 헤더 `PolygonVertexIndex` 파싱은 다중 오브젝트 FBX에서 최대 42% 과소 계측**한다.
  Blender 실측만 신뢰할 것.

### 2. 실험 스크립트는 올라갔는데 그게 증명한 결론이 없다

`cdg_shelltest` / `cdg_planartest` / `cdg_uvtest` / `cdg_bnd` 4개는 리포에 있지만,
**무엇을 반증했는지 적힌 곳이 없다.** 결론 없는 실험 코드는 읽는 사람에게 죽은 무게다.
위 1-(a) 표를 `SOURCE_FACTS.md`에 넣으면 이 4개가 비로소 근거로 살아난다.

### 3. FBX 헤더 파서가 저장되지 않았다

**Blender 없이** FBX의 폴리곤 수·텍스처 장수·내장 용량을 재는 파서를 세션 중에 bash 인라인으로
썼고 파일로 남기지 않았다. 단독 도구로서 이 세션 산출물 중 재사용성이 가장 높다
(325 GB 데이터셋에서 뭘 쓸지 고를 때 필수). `tools/fbx_stats.py`로 복원할 것.

### 4. 배치 감사 결과가 어디에도 기록되지 않았다

정량 감사(`cdg_audit.py`)로 겹침을 찾았고, 검증 에이전트들이 **11건을 CONFIRMED**로 확정했다.
대표적으로:

- **내칠당이 구선원전 안에 91% 매몰** — 손으로 찍은 (−95, 22)가 원인.
  미사용 OSM way `612979880`(내찰당, −68.9, 9.2)이 맞는 자리. KHS 내칠당 ↔ OSM 내찰당은
  한 음절 차이이고, 같은 권역에 KHS 만우문 ↔ OSM 만무문 선례가 이미 있다.
- **구선원전이 180° 역방향** — 문짝 면적의 71%가 북쪽, 벽 면적의 70%가 남쪽인데
  마당은 남쪽이다.
- **인정전이 90° 회전** — 월대·계단·드무가 전부 +X 쪽에 있어 인정문에서 보면 측면이 보인다.
- 무명2가 양지당 안에 47%, 구선원전남행각이 10.9 m 동쪽으로 밀림.

**이 수정들은 아직 적용되지 않았다.** 문서에 남기지 않으면 통째로 유실된다.

### 5. Sketchfab 나무의 CC-BY 출처표시

절차적 나무(원뿔 스택)를 Sketchfab CC-BY 모델로 교체했다 —
"Pine Tree – Low Poly Stylized Tree" by **Jimmy_Johansson**, 2,640 트라이앵글
(72-tri 기둥 + 2,568-tri 알파 카드 잎). 링크드 인스턴스로 1,814그루 배치.
**CC BY-NC 모델은 의도적으로 배제**했다(UGC 플랫폼은 수익화 가능성이 있어 NC와 충돌).
이 출처표시는 현재 로컬 `ATTRIBUTION.txt`에만 있고 리포에는 없다.

---

## 제약 (건드릴 때 지킬 것)

- **로컬에 원본이 없다.** 2026-09-08 기준 `Desktop\blender`는 비어 있고 CDG_Changdeokgung(20 GB)은
  Google Drive `overdare > GameDev > Maps`에만 있다. KHS 원본 폴더도 로컬에 없다.
  → 위 작업은 **문서 편집이 대부분**이라 Drive 내려받기 없이 가능하다.
- **LFS 예산**: free 조직 1 GB 중 약 422 MB 사용 중. 문서·스크립트는 LFS를 안 쓰므로 영향 없음.
  FBX/blend를 올릴 생각이면 Releases를 쓸 것.
- **경로 치환**: `C:\Users\29\Desktop` → `C:\Work`. sed는 백슬래시 때문에 실패하니 파이썬으로.
- **라이선스 분리 유지**: KOGL 제1유형(국가유산청) / CC-BY(Sketchfab) / ODbL(OSM) / MIT(코드).
  나무 출처표시는 `heritage-maps` 쪽 CC-BY 항목으로 간다.

---

## 권장 순서

1. `heritage-maps/changdeokgung/docs/SOURCE_FACTS.md` 갱신 — 위 1-(a)(b)(c) 반영, 42개 에셋 기준으로 정정
2. `heritage-maps/changdeokgung/docs/PLACEMENT_AUDIT.md` 신규 — 위 4번 (감사 방법 + 확정 11건)
3. `overdare-map-pipeline/README.md`에 200 메시 제한 한 줄 추가
4. `overdare-map-pipeline/tools/fbx_stats.py` 복원
5. `heritage-maps` CC-BY 출처에 Sketchfab 나무 추가

1·2번만 해도 이 세션의 값진 부분은 보존된다.
