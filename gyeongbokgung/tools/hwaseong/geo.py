# -*- coding: utf-8 -*-
"""OSM 수급 · 투영 — 장안문 주변 실측 도시의 좌표 기반.

앵커
    장안문 37.2888318, 127.0142186
    OSM relation 15611203, historic=city_gate. Nominatim 으로 확인했다.

좌표 규약
    사이트 프레임은 **+X = 성벽 방향, -Y = 성 바깥(북)** 이다. KCISA 장안문
    모델이 그렇게 정규화돼 있다(heritage.normalise). 그런데 실제 화성 북벽은
    정동서가 아니라 얼마쯤 틀어져 있다. 그래서 지오 좌표를 그대로 쓰면
    도시가 성문에 대해 비뚤어진다.

    → **성벽 방위각을 재서 그만큼 되돌린 다음** 사이트 프레임에 넣는다.
      wall_bearing() 이 barrier=city_wall way 에서 그 각을 실측한다.
      덕수궁이 OSM 건물 중심점으로 주축 -11.7° 를 잰 것과 같은 방식이다.

Overpass 는 쓰지 않는다. 메인·kumi 미러 둘 다 timeout 이었고
api.openstreetmap.org/api/0.6/map?bbox= 는 정상이었다.
"""

import math
import os
import xml.etree.ElementTree as ET

ANCHOR_LAT, ANCHOR_LON = 37.2888318, 127.0142186
RADIUS_M = 150.0                    # 장안문 중심 최종 도시 반경
# **FETCH_M 은 RADIUS_M 보다 넉넉해야 한다.** bbox 는 ±FETCH_M 짜리 정사각형이라
# 경계에 걸친 건물은 노드 일부가 bbox 밖으로 나가고, 그러면 coords() 가 그
# 노드를 건너뛰어 폴리곤이 찌그러진다. 반경만큼만 받으면 안 된다.
FETCH_M = 290.0

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "osm", "janganmun.osm")

# --- 앵커 목록. 문마다 도시를 따로 만든다.
#     각 도시는 **자기 문을 원점으로, 자기 성벽 방위로** 세운다. 그래야
#     layout.BUILDINGS 가 문을 옮겨도 도시가 문을 따라온다.
#     (팔달문: OSM way 1024560873, historic=city_gate. Nominatim 확인)
ANCHORS = {
    "장안문": (37.2888318, 127.0142186, "janganmun.osm"),
    "팔달문": (37.2775815, 127.0167614, "paldalmun.osm"),
}

# 위도 1도 = 110540 m, 경도 1도 = 111320·cos(위도) m. 200 m 범위에서
# 등거리 근사의 오차는 밀리미터 수준이라 무시한다.
M_PER_DEG_LAT = 110540.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(ANCHOR_LAT))


def anchor_offset(a, b):
    """앵커 a 기준으로 앵커 b 가 몇 미터 떨어져 있는지 (동, 북)."""
    la, lo, _ = ANCHORS[a]
    lb, lb2, _ = ANCHORS[b]
    return ((lb2 - lo) * M_PER_DEG_LON, (lb - la) * M_PER_DEG_LAT)


def bbox(margin_m=FETCH_M):
    dlat = margin_m / M_PER_DEG_LAT
    dlon = margin_m / M_PER_DEG_LON
    return (ANCHOR_LON - dlon, ANCHOR_LAT - dlat,
            ANCHOR_LON + dlon, ANCHOR_LAT + dlat)


def fetch(force=False, anchor=None):
    """OSM XML 을 받아 캐시한다. 캐시가 있으면 네트워크를 타지 않는다.

    빌드가 네트워크에 의존하면 재현이 안 된다 — Overpass 가 실제로 혼잡해서
    막혔던 적이 있다. 캐시 파일은 저장소에 함께 둔다.
    """
    path = CACHE if anchor is None else os.path.join(HERE, "osm", ANCHORS[anchor][2])
    if os.path.exists(path) and not force:
        return path
    import urllib.request
    l, b, r, t = bbox()
    url = ("https://api.openstreetmap.org/api/0.6/map?bbox=%.6f,%.6f,%.6f,%.6f"
           % (l, b, r, t))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "hwaseong-map-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as f, open(path, "wb") as g:
        g.write(f.read())
    return path


# ------------------------------------------------------------------ 파싱


class Osm(object):
    """캐시된 OSM XML 한 벌. 노드/웨이만 쓴다(릴레이션은 이 축척에서 불필요)."""

    def __init__(self, path=None):
        root = ET.parse(path or fetch()).getroot()
        self.nodes = {}
        self.node_tags = {}
        for n in root.findall("node"):
            i = n.get("id")
            self.nodes[i] = (float(n.get("lat")), float(n.get("lon")))
            t = {x.get("k"): x.get("v") for x in n.findall("tag")}
            if t:
                self.node_tags[i] = t
        self.ways = []
        for w in root.findall("way"):
            refs = [nd.get("ref") for nd in w.findall("nd")]
            tags = {x.get("k"): x.get("v") for x in w.findall("tag")}
            self.ways.append({"id": w.get("id"), "refs": refs, "tags": tags})

    def coords(self, way):
        """way 의 노드를 (lat, lon) 리스트로. 빠진 노드는 건너뛴다."""
        return [self.nodes[r] for r in way["refs"] if r in self.nodes]

    def tagged(self, key, value=None):
        for w in self.ways:
            v = w["tags"].get(key)
            if v is not None and (value is None or v == value):
                yield w


# ------------------------------------------------------------------ 투영


def to_en(lat, lon):
    """앵커 기준 (동쪽 m, 북쪽 m)."""
    return ((lon - ANCHOR_LON) * M_PER_DEG_LON,
            (lat - ANCHOR_LAT) * M_PER_DEG_LAT)


def wall_bearing(osm, near_m=90.0):
    # near_m 민감도를 재 봤다: 50 m→36.5°, 70 m→29.3°, 90 m→29.3°,
    # 110 m→29.4°, 140 m→27.7°, 200 m→18.9°.
    # 70~110 구간에서 29.3° 로 평평하다 — 50 은 점이 모자라고 200 은 성곽
    # 곡률이 먹는다. 그 평평한 구간 가운데인 90 을 기본값으로 쓴다.
    """barrier=city_wall 에서 성벽 방위각을 잰다.

    돌려주는 값은 **동쪽(+E)에서 반시계로 잰 성벽 진행 방향의 각(도)** 이다.

    처음에 '앵커에 가장 가까운 선분' 으로 했더니 -66.31° 가 나왔고, 그대로
    돌리니 성벽이 X 가 아니라 Y 로 뻗었다 — 가장 가까운 선분은 성벽이 아니라
    **옹성 곡선 조각**이었다. 곡선 위 한 토막은 전체 방향을 대표하지 못한다.

    그래서 앵커 near_m 안의 성벽 점 전체에 **주성분(PCA)** 을 잡는다.
    옹성처럼 튀어나온 부분이 섞여도 직선 성벽 점이 훨씬 많아 주축이 이긴다.
    """
    pts = []
    for w in osm.tagged("barrier", "city_wall"):
        for lat, lon in osm.coords(w):
            e, n = to_en(lat, lon)
            if math.hypot(e, n) <= near_m:
                pts.append((e, n))
    if len(pts) < 3:
        return 0.0
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    syy = sum((p[1] - my) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    # 2x2 공분산의 주고유벡터 각. atan2(2sxy, sxx-syy)/2 가 닫힌 해다.
    ang = math.degrees(0.5 * math.atan2(2.0 * sxy, sxx - syy))
    while ang > 90.0:
        ang -= 180.0
    while ang < -90.0:
        ang += 180.0
    return ang


# 장안문 자체의 실측 bbox. Nominatim 이 돌려준 값이다 (relation 15611203).
# 릴레이션 파싱을 안 하므로 정합 검사에는 이걸 쓴다.
GATE_BBOX = (37.2887194, 37.2890772, 127.0139226, 127.0143856)   # lat0,lat1,lon0,lon1


class Projector(object):
    """지오 좌표 → 사이트 로컬 좌표.

    1) 앵커 기준 동/북 미터로 옮기고
    2) 성벽이 X 축과 나란해지도록 -bearing 만큼 돌리고
    3) 사이트 규약(+X 성벽방향, -Y 북)으로 부호를 맞춘다.
    """

    def __init__(self, bearing_deg):
        self.bearing = bearing_deg
        r = math.radians(-bearing_deg)
        self.c, self.s = math.cos(r), math.sin(r)

    def __call__(self, lat, lon):
        e, n = to_en(lat, lon)
        x = e * self.c - n * self.s
        y = e * self.s + n * self.c
        return (x, -y)          # 북(+y) → 사이트 -Y

    def poly(self, latlons):
        return [self(*p) for p in latlons]

    def inverse(self, x, y):
        """사이트 로컬 (x, y) → (위도, 경도). dem.py 가 표고를 뽑을 때 쓴다."""
        n = -y                       # 사이트 -Y 가 북이었다
        e = x * self.c + n * self.s  # 회전 되돌리기 (R(-θ) 의 전치)
        nn = -x * self.s + n * self.c
        return (ANCHOR_LAT + nn / M_PER_DEG_LAT,
                ANCHOR_LON + e / M_PER_DEG_LON)


def load(anchor="장안문"):
    """앵커별 (osm, projector). 호출부는 이것만 쓰면 된다.

    앵커를 바꾸면 투영 원점과 성벽 방위가 그 문 기준으로 다시 잡힌다 —
    도시는 **자기 문을 원점으로** 만들어야 layout 이 문을 옮길 때 따라온다.
    """
    lat, lon, fname = ANCHORS[anchor]
    _use_anchor(lat, lon)
    o = Osm(fetch(anchor=anchor))
    return o, Projector(wall_bearing(o))


def _use_anchor(lat, lon):
    """모듈 전역 앵커를 갈아끼운다. to_en/Projector 가 이걸 본다."""
    global ANCHOR_LAT, ANCHOR_LON, M_PER_DEG_LON, CACHE
    ANCHOR_LAT, ANCHOR_LON = lat, lon
    M_PER_DEG_LON = 111320.0 * math.cos(math.radians(lat))
