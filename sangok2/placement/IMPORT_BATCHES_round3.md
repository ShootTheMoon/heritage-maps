# SGK 3차 임포트 — 알파 마스터 14개, `SGK3_` 접두 (2026-09-06)

**왜 검은 판이었나**: OVERDARE MeshPart 는 텍스처 알파를 아예 안 쓴다 (1024² 도, Glass 재질도, DoubleSided 도 무관 — 산옥 소나무의 검은 배경도 같은 원인). 잎 카드 사각형이 통째로 그려지고, 알파 0 영역의 RGB(검정)가 그대로 보인 것.
**3차 판의 대응**: (1) 잎 삼각형을 알파 실루엣의 볼록껍질로 **잘라서** 카드 바깥을 기하로 없앰, (2) 아틀라스의 투명 영역을 잎 색으로 **채우고** 가장자리 알파를 미리 합성. Blender 무알파 프리뷰(`04_Previews/noalpha_round3_grid.png`)로 14종 확인.
2차 `SGK_MST_*` 에셋은 버린다 (같은 이름은 새 에셋으로 안 올라가서 접두를 `SGK3_` 로 올렸다. `sgk_export.py` 의 `ALPHA_PREFIX`).

절차: `-Check` 새 파일 14 확인 → **Studio 재시작(에러 팝업 캐시 비우기)** → 세션 1(12) 임포트 → Studio 재시작 → 세션 2(2) 임포트 → **3분 이상 대기 후** `-Resolve` → `-Probe -Apply` → `-Apply` → `-Lua -Apply`

## 세션 1 (12)
- [ ] `10_MASTERS\SGK3_MST_PINE_L1.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_L2.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_L3.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_M1.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_M2.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_M3.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_XL1.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_XL2.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_S1.fbx`
- [ ] `10_MASTERS\SGK3_MST_PINE_S2.fbx`
- [ ] `10_MASTERS\SGK3_MST_SAPLING1.fbx`
- [ ] `10_MASTERS\SGK3_MST_SAPLING2.fbx`

→ Studio 재시작

## 세션 2 (2)
- [ ] `10_MASTERS\SGK3_MST_FERN.fbx`
- [ ] `10_MASTERS\SGK3_MST_PAVILION.fbx`

텍스처는 FBX 에 임베드돼 같이 올라간다 (`SGK3_MST_*_ATL`). 별도 PNG 임포트 불필요.
