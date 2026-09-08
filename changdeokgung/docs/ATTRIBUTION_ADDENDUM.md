# 창덕궁 — 제3자 에셋 출처표시 (식생)

KOGL 제1유형(국가유산청) 본문과 **분리해서** 관리한다. 라이선스가 다르다.

## 수목

**"Pine Tree – Low Poly Stylized Tree"** by **Jimmy_Johansson**
- 출처: https://sketchfab.com/3d-models/071914806126487b9f5067693b39f335
- 라이선스: **CC BY 4.0**
- 제원: 2,640 트라이앵글 (72-tri 기둥 + 2,568-tri 알파 카드 잎), 텍스처 512/256 px
- 변경 사항: 트랜스폼 베이크, 바닥을 z=0에 정렬, 블렌드 모드 BLEND → **CLIP**,
  텍스처 PNG 재출력, 지형 위에 **링크드 인스턴스**로 1,814그루 배치

### 인스턴스로 넣는 이유

2,640 트라이앵글 × 1,814그루 = 4.8 M. 이미 6.6 M인 맵에 실체 지오메트리로 넣을 수 없다.
링크드 듀플리케이트로 두면 씬은 메시 **1개**만 들고 있고, 출하 형태도 같다 —
OVERDARE는 나무 MeshPart 하나를 임포트해서 복제하므로 **몇 그루를 심든 익스포트 비용은 2,640 트라이앵글**이다.
배치는 `TREE_PLACEMENTS.csv`(x, y, z, scale, yaw_rad)로 따로 나간다.

### 라이선스 위생 — 기록해 둘 것

**CC BY-NC 모델은 의도적으로 배제했다.** 검토 중 탈락:
- "Old Pine Tree (Low Poly)" by strix567 — BY-NC
- "Birch Tree (Low Poly)" by strix567 — BY-NC

UGC 플랫폼 빌드는 수익화 가능성이 있어 NC 조항이 그것과, 그리고 위 KOGL 표기와 충돌한다.
**식생은 CC-BY 또는 CC0만 쓴다.**

### 폐기된 자체 제작 텍스처

`T_CDG_PineNeedle_BC.png` / `T_CDG_Leaf_BC.png` / `T_CDG_Bark_BC.png` (PIL 256px 노이즈)는
절차적 원뿔 나무 시절 산물이다. 더 이상 쓰지 않는다.
