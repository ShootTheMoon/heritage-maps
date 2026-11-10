# 작업 PC 툴 모음 (gyeongbokgung 폴더)

경복궁 빌드 스크립트와 함께, 이후 모든 맵 작업이 공용으로 쓴 OVERDARE 브리지가 여기 있다:
`ovdr_rpc.ps1`(포트 13377 JSON-RPC) · `ovdr_level.ps1`(.ovdrjm 텍스트 편집·Part/MeshPart JSON) · `ovdr_script.ps1`(레벨 안 스크립트 소스 교체). 산곡 II 의 `sgk_place.ps1` 이 이 셋을 dot-source 한다. 나머지 `vote_*.ps1`·`krm_*.ps1`·`hws_*.ps1` 은 투표·크렘린·화성 작업 때 쓴 일회성 프로브.

하위 패키지 둘은 경복궁 생성기(`hanok` · `roof` · `enclosure`) 옆에 얹어 쓰는 맵별 코드다.

- `hwaseong/` — 수원 화성 절차 생성. KCISA 장안문 모델 수급·감축(`heritage.py`), 화성성역의궤 도설 제원(`uigwe.py` · `build_uigwe.py`), 성곽 부재(`fortress.py`), OSM 발자국 도시(`geo.py` · `city.py`), AWS Terrain Tiles 표고(`dem.py`), 지형 마감(`terrain.py`), 배치(`layout.py`), 조립(`build_hs.py`). 내려받은 `osm/` · `dem/` 캐시는 올리지 않았다.
- `deoksugung/` — 덕수궁. 궁 축 좌표계와 배치(`layout.py`), 출처·신뢰도를 함께 담은 실측값(`measured.py`), 전각 조립(`build_dsg.py`). `__init__.py` 가 말하는 `heritage.py` 는 작업 PC 에도 없다.

`*.js` 는 Node 로 도는 검사기다: `vote_lint.js`(Lua 블록 여닫이) · `vote_uilint.js`(LobbyUI 타이포그래피) · `vote_assert.js`(MapService 산곡 값 대조) · `krm_leak.js`(크렘린 수평 단면 물 채우기로 새는 곳 찾기) · `hws_diff.js`(레벨의 화성 MeshPart 189장을 원본 배치 JSON 과 대조).

스크립트 안의 절대 경로는 `C:\Work\...` 로 바꿔 올렸다.
