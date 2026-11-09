# -*- coding: utf-8 -*-
"""지붕 종단면 물매 — 3구간 꺾임 모델.

**bpy 를 import 하지 않는다.** 블렌더 없이 실측값으로 단위 검증하기 위해서다.
지붕 기하의 핵심 결정이 전부 여기 있으므로, 여기가 틀리면 나머지가 다 틀린다.

--------------------------------------------------------------------------
왜 다시 쓰는가
--------------------------------------------------------------------------
기존 roof.py 는 이렇게 했다:

    def prof(t):     return t ** concavity          # concavity = 1.42
    def z_slope(y):  return h0 + span * prof(1.0 - abs(y) / hd)

t=0(처마)에서 미분하면 1.42·t^0.42 → 0. **지붕면이 처마에 0° 로 닿고**
용마루로 갈수록 가팔라진다. 실제는 정반대이고 꺾임이 있다.

--------------------------------------------------------------------------
물매(勿每)
--------------------------------------------------------------------------
물매는 "자당 치" 로 잰다. 10치 = 1자 = 45°, 5치 = 26.57°.
slope = m / 10.

    구간            부재    물매      각도
    용마루→중도리   단연    10치      45.0°
    중도리→서까래끝 장연    5~5.3치   26.6~28.0°
    서까래끝→부연끝 부연    4치       21.8°

--------------------------------------------------------------------------
실측 근거 (deoksugung/measured.py 참조)
--------------------------------------------------------------------------
석어당 2015 해체실측 종단면도(p.160)에서:
    R(반쪽 수평거리) 3.565 = 측면 절반 1.825 + 처마 1.740
    H(총 상승)       2.550
    b(부연 내밀기)   0.540
아래 solve_a() 에 넣으면 a = 1.555 가 나오고, **도면의 1,550 과 5mm 차**다.
이 일치가 이 모델을 채택한 근거다. test_profile() 이 회귀로 지킨다.
"""

import math

# 물매 기본값 — 실측이 없을 때만 쓴다
M_DAN = 10.0
M_JANG = 5.3
M_BU = 4.0


def mulmae_to_deg(m):
    """물매(치/자) → 각도(도)."""
    return math.degrees(math.atan(m / 10.0))


def deg_to_mulmae(deg):
    return 10.0 * math.tan(math.radians(deg))


def solve_a(H, R, b, m_dan=M_DAN, m_jang=M_JANG, m_bu=M_BU):
    """총 상승 H 를 만족하는 중도리 수평거리 a 를 푼다.

        H = 0.1·[ m_dan·a + m_jang·(R−b−a) + m_bu·b ]
      → a = [ H − 0.1·(m_jang·(R−b) + m_bu·b) ] / [ 0.1·(m_dan − m_jang) ]

    m_dan == m_jang 이면 꺾임이 없어 풀 수 없다 (하층지붕이 그렇다).
    그 경우 RoofProfile 이 m_dan=None 으로 단일 경사를 쓴다.
    """
    denom = 0.1 * (m_dan - m_jang)
    if abs(denom) < 1e-9:
        raise ValueError("단연과 장연 물매가 같으면 중도리 위치가 정해지지 않는다")
    return (H - 0.1 * (m_jang * (R - b) + m_bu * b)) / denom


def solve_H(a, R, b, m_dan=M_DAN, m_jang=M_JANG, m_bu=M_BU):
    """중도리 위치 a 에서 총 상승 H 를 **유도**한다.

    h1 을 입력으로 받는 대신 이걸 쓰면, 잘못 찍은 용마루 높이에 곡선을
    맞추는 일이 없어진다 — 석어당이 피라미드가 된 직접 원인이었다.
    """
    return 0.1 * (m_dan * a + m_jang * (R - b - a) + m_bu * b)


class RoofProfile(object):
    """r(용마루에서 잰 수평거리) → z.

    r=0 이 용마루, r=R 이 부연 끝(처마선)이다.
    기존 z_slope(y) 는 r = |y| 로 대응한다.
    """

    def __init__(self, R, h1=None, h0=None, b=0.0, *,
                 m_dan=M_DAN, m_jang=M_JANG, m_bu=M_BU,
                 a=None, a_frac=0.435, jouro=0.03, name='?'):
        """
        R      반쪽 수평거리 (용마루 → 부연 끝)
        h1,h0  용마루 높이, 처마 높이. **둘 중 하나는 None 이어도 된다.**
               h1=None 이면 물매에서 유도한다 (권장).
        b      부연 내밀기. 0 이면 홑처마.
        m_dan  단연 물매. **None 이면 꺾임 없는 단일 경사** (하층지붕/상첨).
        a      중도리 수평거리를 직접 줄 때. 없으면 h1 에서 푼다.
        a_frac h1 도 a 도 없을 때 R 대비 중도리 위치. 기본 0.435 는 석어당 실측.
        jouro  구간 **안에서만** 더하는 오목 처짐(m). 구간을 넘기면 꺾임이 뭉개진다.
        """
        self.name = name
        self.R = float(R)
        self.b = max(0.0, min(float(b), self.R * 0.9))
        self.m_jang = float(m_jang)
        self.m_bu = float(m_bu if b > 0 else m_jang)
        self.jouro = float(jouro)
        self.single = (m_dan is None)
        self.m_dan = float(m_jang if self.single else m_dan)

        if self.single:
            # 하층지붕에는 단연이 없다. 누락이 아니라 올바른 특수 케이스다.
            self.a = 0.0
            H = solve_H(0.0, self.R, self.b, self.m_dan, self.m_jang, self.m_bu)
        elif a is not None:
            self.a = float(a)
            H = solve_H(self.a, self.R, self.b, self.m_dan, self.m_jang, self.m_bu)
        elif h1 is not None and h0 is not None:
            H = float(h1) - float(h0)
            self.a = solve_a(H, self.R, self.b, self.m_dan, self.m_jang, self.m_bu)
        else:
            self.a = a_frac * self.R
            H = solve_H(self.a, self.R, self.b, self.m_dan, self.m_jang, self.m_bu)

        self.H = H
        if h0 is not None:
            self.h0 = float(h0)
            self.h1 = self.h0 + H
        elif h1 is not None:
            self.h1 = float(h1)
            self.h0 = self.h1 - H
        else:
            self.h0 = 0.0
            self.h1 = H

        # 구간 경계 — 격자가 반드시 지나야 하는 r
        self.r_eave = self.R - self.b          # 서까래 끝
        self._breaks = [0.0, self.a, self.r_eave, self.R]

    # ------------------------------------------------------------ 질의

    def drop(self, r):
        """용마루에서 r 만큼 나갔을 때의 하강량."""
        r = max(0.0, min(float(r), self.R))
        a, re = self.a, self.r_eave
        if r <= a:
            d = 0.1 * self.m_dan * r
            seg = (0.0, a)
        elif r <= re:
            d = 0.1 * self.m_dan * a + 0.1 * self.m_jang * (r - a)
            seg = (a, re)
        else:
            d = (0.1 * self.m_dan * a + 0.1 * self.m_jang * (re - a)
                 + 0.1 * self.m_bu * (r - re))
            seg = (re, self.R)
        # 조로 — 구간 안에서만. 양 끝에서 0 이므로 꺾임 각은 보존된다.
        lo, hi = seg
        if self.jouro > 0.0 and hi - lo > 1e-9:
            t = (r - lo) / (hi - lo)
            d += self.jouro * math.sin(math.pi * t) * min(1.0, (hi - lo) / 2.0)
        return d

    def z(self, r):
        return self.h1 - self.drop(r)

    def slope_deg(self, r):
        """r 에서의 국소 경사각. 검증용."""
        e = 1e-4
        r0, r1 = max(0.0, r - e), min(self.R, r + e)
        if r1 - r0 < 1e-9:
            return 0.0
        return math.degrees(math.atan((self.drop(r1) - self.drop(r0)) / (r1 - r0)))

    def r_at_z(self, z):
        """z 가 되는 r. drop 이 단조증가라 이분법으로 푼다.

        합각 밑변 위치(yg)를 구하는 데 쓴다. 기존 코드는 곡선의 역함수를
        닫힌 식으로 썼지만 3구간 모델에는 닫힌 역함수가 없다.
        """
        target = self.h1 - z
        if target <= 0.0:
            return 0.0
        if target >= self.drop(self.R):
            return self.R
        lo, hi = 0.0, self.R
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if self.drop(mid) < target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def breaks(self):
        """격자가 지나야 할 r 목록. 중복·범위 밖은 제거한다."""
        out = []
        for v in self._breaks:
            v = max(0.0, min(v, self.R))
            if not out or abs(v - out[-1]) > 1e-6:
                out.append(v)
        return out

    def jireum_mulmae(self):
        """지름물매 — 용마루~부연끝을 잇는 현(弦)의 물매."""
        return 10.0 * self.H / self.R if self.R > 0 else 0.0

    # ------------------------------------------------------------ 검사

    def assert_sane(self, strict=True):
        """기하학적으로 불가능하거나 눈에 띄게 이상한 조합을 잡는다.

        치수표를 튜닝 손잡이가 아니라 **검증 가능한 데이터**로 만든다.
        """
        msgs = []
        if not self.single:
            f = self.a / self.R if self.R else 0.0
            if f < 0.10:
                msgs.append("중도리가 용마루에 너무 붙음 a/R=%.2f — "
                            "지붕이 뾰족해진다" % f)
            elif f > 0.55:
                msgs.append("중도리가 처마에 너무 붙음 a/R=%.2f — "
                            "단연 구간이 거의 없다" % f)
            if self.m_dan <= self.m_jang:
                msgs.append("단연(%.1f치)이 장연(%.1f치)보다 완만하다 — 꺾임이 반대"
                            % (self.m_dan, self.m_jang))
        if self.b > 0 and self.m_bu > self.m_jang:
            msgs.append("부연(%.1f치)이 장연(%.1f치)보다 급하다" % (self.m_bu, self.m_jang))
        jm = self.jireum_mulmae()
        if not (3.5 <= jm <= 9.0):
            msgs.append("지름물매 %.1f치가 범위(3.5~9.0) 밖" % jm)
        if msgs and strict:
            raise ValueError("[%s] " % self.name + " / ".join(msgs))
        return msgs

    def describe(self):
        return ("%-10s R=%.3f a=%.3f (a/R=%.2f) H=%.3f  "
                "단연 %.1f치/%.1f°  장연 %.1f치/%.1f°  부연 %.1f치/%.1f°  "
                "지름 %.1f치"
                % (self.name, self.R, self.a, self.a / self.R if self.R else 0,
                   self.H,
                   self.m_dan, mulmae_to_deg(self.m_dan),
                   self.m_jang, mulmae_to_deg(self.m_jang),
                   self.m_bu, mulmae_to_deg(self.m_bu),
                   self.jireum_mulmae()))
