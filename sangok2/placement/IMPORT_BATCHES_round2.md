# SGK 2차 임포트 — 알파 아틀라스 13개 (2026-09-06)

1차 임포트 후 실측: **1024×2048 텍스처는 Studio 가 알파를 버린다** (소나무 잎·정자 지붕이 검은 판, 1024² FERN 은 정상).
→ 13개 마스터를 1024×1024 아틀라스로 다시 굽고 `SGK_` 접두 이름으로 재익스포트. 1차에 올라간 MST_PINE_* / MST_SAPLING* / MST_PAVILION 에셋은 그냥 버린다(재사용 안 함).

절차: `sgk_place.ps1 -Check` 0 확인 → `-Snapshot` → 세션 1(12) 임포트 → Studio 재시작 → 세션 2(3) 임포트 → `-Resolve` → `-Probe -Apply` → `-Apply` → `-Lua -Apply`

## 세션 1 (12)
- [ ] `10_MASTERS\SGK_MST_PINE_L1.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_L2.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_L3.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_M1.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_M2.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_M3.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_XL1.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_XL2.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_S1.fbx`
- [ ] `10_MASTERS\SGK_MST_PINE_S2.fbx`
- [ ] `10_MASTERS\SGK_MST_SAPLING1.fbx`
- [ ] `10_MASTERS\SGK_MST_SAPLING2.fbx`

→ Studio 재시작

## 세션 2 (1)
- [ ] `10_MASTERS\SGK_MST_PAVILION.fbx`
