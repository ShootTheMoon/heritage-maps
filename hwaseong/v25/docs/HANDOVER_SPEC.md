# 화성 v25 인계 명세서 (2026-09-09 09:05, 다음 PC 용)

## 0. 지금 상태 한 줄
Studio 프로젝트 `onlyoneshot` 의 `Workspace.HWS_Hwaseong` 컨테이너에 화성 v25 가 **전부 배치·저장**돼 있다
(정적 103 + 식생·소품 인스턴스 941 + 충돌 슬랩 541 + 문짝 8). 문 개폐 스크립트 `HwsDoorServer` 동작 확인.
**남은 것은 Lua 만**: MapService 등록, 스폰·경계 벽, 낙하 리스폰, 실기 플레이 확인.

## 1. 파일 위치 (이 PC 기준, 다른 PC 는 프로젝트 폴더를 동기화해서 쓸 것)
| 무엇 | 경로 |
|---|---|
| Studio 프로젝트 | `C:\Users\HSP\Desktop\onlyonetap\onlyoneshot.ovdrjm` (Lua 소스는 `onlyonetap\Lua\*.lua`) |
| 문 스크립트 | `onlyonetap\Lua\HwsDoorServer.lua` = ServerScriptService/HwsDoorServer (guid 1423747F605EA6EC986D79E90192A164) |
| 맵 정의 | `onlyonetap\Lua\MapService_1.lua` = ReplicatedStorage/MapService |
| 익스포트 산출물 | `C:\Users\HSP\Desktop\blender\ovdr_export\hwaseong_v25\` (01_JAM 65, 02_DOORS, 03_TERRAIN 30, 10_MASTERS 6, _place, _collision, items_static.json, items_doors.json, scene_dump.json, texture_map.json, manifest_*.json) |
| 배치 스크립트 | `blender\hwaseong_rebuild\v25\hws_place.py` (scene_dump → items JSON, UGCLocalAssetTable 로 ID 해석) |
| 익스포터 | `blender\hwaseong_rebuild\v25\hws_export.py` (JAM/DOORS), `hws_stage3.py` (마스터·지형·슬랩) |
| Blender 씬 | `blender\hwaseong_rebuild\v25\hwaseong_v25.blend` |
| 진행 일지 | `ovdr_export\hwaseong_v25\README_v25.md` 1~22 항 |
| 에셋 테이블 | `onlyonetap\UGCLocalAssetTable.json` (UTF‑16). 이 PC 에서 임포트한 ID 는 이 파일에만 있다 → **다른 PC 에서는 Studio 가 서버에서 내려받아 채운다. 배치는 이미 끝났으니 ID 재해석은 불필요** |

## 2. 좌표·규약 (산곡 그대로)
- Blender(m) → 엔진(cm): `X = x·100 − 58000`, `Y = z·100`, `Z = −y·100`. 정적물 orientation `(0, −180, 0)`, position = bbox 중심, Size = bbox(cm).
- 화성 점유 범위: 엔진 X **−77384 … −38652**, Z 약 −9600 … +9600 (지면 외곽 포함). 산곡은 X −38000…−22000 → 겹치지 않음. 창덕궁·크렘린과도 무관.
- 장안문 문루 중심 = (−58000, 0, 0). 성벽은 X 축 방향. **성 밖(옹성 쪽) = +Z**, 성 안 = −Z.
- 지면 높이: 잔디 지형은 Y ≈ 0 근처(기복 ±1 m). 충돌은 `COL_HWS_0000..0540` Part 슬랩(Unlit·투명)이 담당. 지형 메시 CanCollide=false.
- 카메라 툴(`overdare_camera`) 입력 (X,Y,Z) 는 엔진 (Z, Y, −X) 로 들어간다 → position=(−ez, ey, ex).

## 3. Studio 컨테이너 구성 (`Workspace.HWS_Hwaseong`, guid B4338267BDBF786024208D23092BF329)
| 접두 | 개수 | 내용 |
|---|---|---|
| `HWS_JAM_NN_*` | 65 | KCISA 장안문(Sketchfab 원본) 재질별 조각. 문루·육축·옹성·계단 |
| `HWS_DOOR_{OS,MG}_{L,R}_P5{4,5}` | 8 | 문짝. **Mobility=Movable, DoubleSided=true**. 에셋 HWS_DR4_* |
| `HWS_TER_rc` / `HWS_OUT_rc` | 20 + 10 | 잔디 지형 40 m 타일 + 외곽 지평 타일 |
| `HWS_담장_*`, `HWS_여장_*`, `HWS_암문_*` | ~50 | 남한산성 국가유산 모듈(마스터 인스턴스) |
| `HWS_소품_*` | ~10 | BlenderKit 건초·항아리·통 |
| `HWS_수목_소나무_*` 126, `HWS_수목_외곽소나무_*` 564 | 690 | 산곡 MST 소나무 마스터 재사용 |
| `HWS_지면소품_*` | ~150 | 산곡 MST 풀·고사리·바위·그루터기 |
| `COL_HWS_NNNN` | 541 | 충돌 슬랩 Part (안쪽 16 m 쿼드트리, 외곽 32 m) |

## 4. 문 개폐 (완료)
- `HwsDoorServer`: Heartbeat 루프, 힌지 기준 CFrame 회전, 플레이어 9 m 접근 시 88° 안쪽(−Z)으로 열림, 이탈 시 닫힘. TweenService 미사용.
- 힌지(엔진 cm): OS_R (−57720, 17, 2600) / OS_L (−58222, 17, 2600) / MG_R (−57742, −3, 100) / MG_L (−58264, −3, 100). 우측 openDeg −88, 좌측 +88.
- 검증 방법: `CFG.DEBUG_FORCE_OPEN = true` 로 재생 → `%LOCALAPPDATA%\Sandbox\Saved\Logs\Sandbox.log` 의 `[HwsDoor] open …` 줄. 끝나면 false.
- 컨테이너가 Workspace 에 없으면(다른 맵) 스스로 쉬고 3초마다 재탐색 → 맵 스왑과 호환.

## 5. 남은 작업 (순서대로)
1. **MapService `hws` 항목 교체** (`MapService_1.lua` 133행 부근). 현재 값은 옛 화성(Hwaseong Place, X 52200…70600). 바꿀 값:
   - `containers = { "HWS_Hwaseong" }` (슬랩이 같은 컨테이너 안이라 하나면 된다. `Hwaseong Collision` 은 옛 것 → ServerStorage 에 남아 있으면 삭제)
   - `rect = { minX = −72000, maxX = −44000, minZ = −7000, maxZ = 7000 }` (경기구역 후보. 성벽 ±70 m, 성 밖 40 / 성 안 60 m 설계. 걸어 보고 조정)
   - `center = { x = −58000, z = 0 }`, `groundY = 0`, `snapRise = 3000`, `rayTop = 9000`, `rayLen = 22000`
   - `zoneRadius = 2200`, `minSpawnDist = 4400`, `edgeMargin = 2400`, `moveScale = 0.85`, `seam = { enabled = false }`
   - `label = "HWASEONG"`, `sub = "JANGANMUN / 140 x 100m"`
   - `M.ORDER` 에 `"hws"` 추가하면 투표에 나온다. `M.DEBUG_FORCE = "hws"` 로 부팅 즉시 스왑해 시험 가능(끝나면 nil).
2. **스폰·경계 벽 4장을 컨테이너 안에 배치** (이름은 MapService 가 요구): `HWS_Spawn_Red`, `HWS_Spawn_Blue`, `HWS_Bound_North/South/East/West`.
   - 스폰 후보: Red = 성 밖 (−58000, 150, 3500 근처, 옹성 앞), Blue = 성 안 (−58000, 150, −3500). 산곡 스폰 Part 를 복제해 이름만 바꾸는 게 빠르다(`overdare_duplicate_instance`).
   - 경계 벽: rect 네 변에 얇은 Part. BoundaryServer 가 ServerStorage 로 치우므로 색·투명 무관. 산곡 SGK_Bound_* 를 복제·이동.
3. **낙하 리스폰**: 슬랩 밖(외곽 지평 타일 위)은 걷지 못하고 떨어진다. 옵션 A: 외곽 32 m 슬랩이 이미 깔려 있으니 rect 를 슬랩 범위 안으로 잡으면 경계 시스템이 처리. 옵션 B: Y < −2000 이면 스폰으로 되돌리는 4줄을 BoundaryServer 루프에 추가.
4. **플레이 확인**: 지형 슬랩 방향(경사 부호) 실측 — 산곡 규약(rz = −asin(nx), rx = atan2(nz, ny))을 그대로 썼지만 화성에서 걸어 본 적은 없다. 언덕에서 뚫리면 `hws_stage3.py` 슬랩 부호를 뒤집어 `_collision` 재생성 → COL_HWS_* 삭제 후 재배치.
5. fps: 화성을 Workspace 에 두면 산곡처럼 인스턴스 수(1,700)가 부하다. 문제 되면 외곽소나무 564 를 절반으로.

## 6. 함정 (이번에 시간을 날린 것들)
- **판형 메시가 안 보이면 위치가 아니라 컬링**이다. `DoubleSided=true`. 먼저 `overdare_camera` lookAt + screenshot 의 `centerHit` 로 존재 확인.
- **움직일 파츠는 Mobility=Movable**. Static 이면 Lua 의 CFrame 대입이 `static instance` 로 거부된다.
- Studio 는 FBX 오브젝트 변환을 무시한다 → 정적물은 `matrix_world` 를 정점에 굽고 항등으로 내보낸다(hws_export.export_one). 문짝은 bbox 중심을 원점으로(centre=True).
- 텍스처 파일명이 메시 이름과 같으면 임포트 실패(Code 1315). 0‑tri 메시도 실패(JAM_46/47 제외).
- 임포트한 에셋 이름에 한글이 있으면 테이블에는 한글로 남지만 사용은 된다. 그래도 ASCII 로.
- MeshId/TextureId 는 `ovdrassetid://` 접두 + Material Basic + Color(200,200,200) 이어야 텍스처가 보인다.
- Studio 재시작은 사용자가 원치 않는다. 임포트는 사용자가 GUI 로 폴더 Ctrl+A. `level.apply` RPC 는 자주 10 s 타임아웃 나지만 대개 적용된다 → `overdare_find` 로 재확인.
- 로그는 `Sandbox.log` 의 `LogLuaMachine` 채널만 믿는다. 플레이 중 스크린샷은 플레이어 카메라라 맵 확인용으로 못 쓴다.

## 7. 재현 명령 (필요할 때만)
```
# 에셋 ID 재해석 → items_static.json / _place / items_doors.json
"C:\Program Files (x86)\Steam\steamapps\common\Blender\5.2\python\bin\python.exe" hws_place.py C:\Users\HSP\Desktop\onlyonetap\UGCLocalAssetTable.json
# 배치(청크마다) : overdare_create_instances itemsFile=<json> parent=B4338267BDBF786024208D23092BF329
# 문짝 재익스포트(닫힘·중심 원점) : Blender GUI 에서 hws_export.main() with sys.argv=["blender","--","doors"]
```
