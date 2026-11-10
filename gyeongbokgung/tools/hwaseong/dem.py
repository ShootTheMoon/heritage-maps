# -*- coding: utf-8 -*-
"""지형 표고 — AWS Terrain Tiles (terrarium).

`s3://elevation-tiles-prod` 는 **공개·무인증**이다. VWorld 처럼 키를 받을
필요가 없어서 이걸 쓴다. terrarium 인코딩:

    height_m = (R*256 + G + B/256) - 32768

측정값: 장안문 앵커 표고 **61.0 m**, 반경 600 m 안 54.5~70.0 m —
**15.5 m 기복**이다. 완만하지만 평면은 아니다.

높이는 **앵커(장안문)를 0 으로 정규화**해서 돌려준다. 기존 좌표 규약이
지면 z=0 을 전제로 세워져 있어서, 절대 표고를 그대로 쓰면 전부 61 m 위로
떠 버린다.

타일은 hwaseong/dem/ 에 캐시한다 — 빌드가 네트워크를 타면 재현이 안 된다.
"""

import math
import os

Z = 14                      # 타일당 약 1,946 m / 256 px → 7.6 m/px
BASE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "dem")
SPAN_M = 900.0              # 앵커 기준 이만큼 덮는 타일을 받는다
EXAGGERATION = 1.0          # 기복 과장. 1.0 = 실제
GRID_M = 12.0               # 지면 메시 격자. build_hs._build_ground 와 공유한다


def tile_xy(lat, lon, z=Z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    r = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(r)) / math.pi) / 2.0 * n
    return x, y


def _fetch(tx, ty, z=Z):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "%d_%d_%d.png" % (z, tx, ty))
    if os.path.exists(path):
        return path
    import urllib.request
    url = "%s/%d/%d/%d.png" % (BASE, z, tx, ty)
    req = urllib.request.Request(url, headers={"User-Agent": "hwaseong-map/1.0"})
    with urllib.request.urlopen(req, timeout=90) as f, open(path, "wb") as g:
        g.write(f.read())
    return path


class Dem(object):
    """앵커 주변 타일을 읽어 (로컬 x, y) → 높이(m) 로 답한다."""

    def __init__(self, projector, anchor_lat, anchor_lon, exagg=EXAGGERATION):
        import bpy
        self.P = projector
        self.lat0, self.lon0 = anchor_lat, anchor_lon
        self.exagg = exagg
        self.tiles = {}          # (tx,ty) -> (W, H, [float])
        self._nodes = {}         # 격자 교점 높이 캐시

        dlat = SPAN_M / 110540.0
        dlon = SPAN_M / (111320.0 * math.cos(math.radians(anchor_lat)))
        xs, ys = [], []
        for la in (anchor_lat - dlat, anchor_lat + dlat):
            for lo in (anchor_lon - dlon, anchor_lon + dlon):
                tx, ty = tile_xy(la, lo)
                xs.append(int(tx))
                ys.append(int(ty))
        for tx in range(min(xs), max(xs) + 1):
            for ty in range(min(ys), max(ys) + 1):
                p = _fetch(tx, ty)
                im = bpy.data.images.load(p, check_existing=True)
                # **Non-Color 로 읽어야 한다.** sRGB 로 두면 픽셀에 감마가
                # 먹어 표고가 통째로 틀어진다.
                im.colorspace_settings.name = 'Non-Color'
                W, H = im.size
                self.tiles[(tx, ty)] = (W, H, list(im.pixels))
        self.base = self._raw(anchor_lat, anchor_lon)
        print("DEM: 타일 %d장 (z=%d), 앵커 표고 %.1f m, 과장 %.2f"
              % (len(self.tiles), Z, self.base, exagg))

    def _raw(self, lat, lon):
        tx, ty = tile_xy(lat, lon)
        key = (int(tx), int(ty))
        t = self.tiles.get(key)
        if t is None:
            return self.base if hasattr(self, "base") else 0.0
        W, H, px = t
        fx = (tx - int(tx)) * W
        fy = (ty - int(ty)) * H
        x0, y0 = int(fx), int(fy)
        ax, ay = fx - x0, fy - y0

        def at(ix, iy):
            ix = max(0, min(W - 1, ix))
            iy = max(0, min(H - 1, iy))
            i = ((H - 1 - iy) * W + ix) * 4      # PNG 는 위가 0, Blender 는 아래가 0
            r, g, b = px[i], px[i + 1], px[i + 2]
            return (r * 255.0 * 256.0 + g * 255.0 + b * 255.0 / 256.0) - 32768.0

        # 이중선형 — 7.6 m/px 를 그대로 쓰면 계단이 보인다
        h00, h10 = at(x0, y0), at(x0 + 1, y0)
        h01, h11 = at(x0, y0 + 1), at(x0 + 1, y0 + 1)
        return ((h00 * (1 - ax) + h10 * ax) * (1 - ay)
                + (h01 * (1 - ax) + h11 * ax) * ay)

    def height_at(self, x, y):
        """사이트 로컬 (x, y) m → 앵커 기준 높이 m. **연속면**이다.

        지면 메시는 GRID_M 격자라 이 연속면과 최대 수십 cm 어긋난다.
        지면 **위에** 놓이는 것(도로·건물·나무)은 surface_at 을 써야 한다.
        """
        lat, lon = self.P.inverse(x, y)
        return (self._raw(lat, lon) - self.base) * self.exagg

    # ---------------------------------------------------------- 지면 격자
    #
    # 처음엔 지면도 그 위의 것도 전부 height_at 을 썼다. 그런데 지면은
    # 12 m 격자를 **선형 보간**한 삼각형 면이고 height_at 은 그 사이를
    # 곡선으로 지난다. 도로 여유가 5 cm 뿐이라 오목한 칸마다 도로가 땅
    # 밑으로 잠겼다(장안문 앞 얼룩). 두 쪽이 **같은 면**을 보게 한다.

    def node(self, i, j):
        """격자 교점 (i, j) 의 높이. 지면 메시가 실제로 쓰는 값."""
        k = (i, j)
        h = self._nodes.get(k)
        if h is None:
            h = self.height_at(i * GRID_M, j * GRID_M)
            self._nodes[k] = h
        return h

    def surface_at(self, x, y):
        """지면 메시 위 정확한 높이. 삼각화 방향까지 맞춘다.

        bmesh 는 쿼드를 (0,0)-(1,1) 대각으로 가른다. 그 두 삼각형의
        평면식을 그대로 쓴다 — 쌍선형으로 근사하면 대각선에서 다시 뜬다.
        """
        S = GRID_M
        i, j = int(math.floor(x / S)), int(math.floor(y / S))
        u, v = x / S - i, y / S - j
        h00, h10 = self.node(i, j), self.node(i + 1, j)
        h01, h11 = self.node(i, j + 1), self.node(i + 1, j + 1)
        if v <= u:
            return h00 + (h10 - h00) * u + (h11 - h10) * v
        return h00 + (h11 - h01) * u + (h01 - h00) * v


_CACHED = {}


def get(anchor="장안문"):
    """앵커별 Dem 을 만들어 캐시한다. 실패하면 None (지형은 평면으로 남는다)."""
    if anchor in _CACHED:
        return _CACHED[anchor]
    try:
        from . import geo
        o, P = geo.load(anchor)
        lat, lon, _ = geo.ANCHORS[anchor]
        d = Dem(P, lat, lon)
    except Exception as e:
        print("DEM 사용 불가(평면 유지): %s" % e)
        d = None
    _CACHED[anchor] = d
    return d
