# -*- coding: utf-8 -*-
"""RoofProfile 검증 — 블렌더 없이 돈다.

    python test_roofprofile.py

가장 중요한 시험은 T1 이다: 석어당 해체실측 도면에서 **따로 읽은** 두 값
(총 상승 2,550 과 중도리 1,550)이 이 모델 안에서 서로 맞아떨어지는지.
맞으면 모델이 옳고, 안 맞으면 모델이 틀렸다.
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from roofprofile import (RoofProfile, solve_a, solve_H, mulmae_to_deg)

FAIL = []


def check(name, got, want, tol, unit=''):
    ok = abs(got - want) <= tol
    print("  %-42s %8.3f %s (기대 %.3f ±%.3f)  %s"
          % (name, got, unit, want, tol, 'OK' if ok else '**실패**'))
    if not ok:
        FAIL.append(name)
    return ok


print("=" * 78)
print("T1  석어당 — 물매 배분의 자기정합성")
print("=" * 78)
print("""  주의: 이것은 독립 실측과의 대조가 **아니다**.
  도면(EM050289 p.160)이 실제로 준 것은 R·b·H 와 상승의 분해 1,550+1,000 뿐이고,
  중도리의 *수평* 거리는 도면에서 읽지 못했다. 아래는 'a 를 얼마로 놓아야
  단연·장연이 동시에 교과서값이 되는가' 를 보는 시험이다.""")
# EM050289 p.160 종단면도에서 읽은 값들 (전부 실측)
SED_R = 1.825 + 1.740          # 측면 절반 + 처마 = 3.565
SED_H = 2.550                  # 상층 처마 → 용마루
SED_B = 0.540                  # 부연 내밀기
SED_RISE_DAN = 1.550           # 상승 분해의 윗값 (도면)

print("\n     a(m)   단연 물매   장연 물매   판정")
best = None
for a_try in (1.20, 1.40, 1.55, 1.70, 1.80):
    m_dan = 10.0 * SED_RISE_DAN / a_try
    rise_rest = SED_H - SED_RISE_DAN - 0.1 * 4.0 * SED_B
    m_jang = 10.0 * rise_rest / (SED_R - SED_B - a_try)
    ok = abs(m_dan - 10.0) < 0.8 and 4.5 <= m_jang <= 6.0
    print("    %5.2f     %5.2f치     %5.2f치   %s"
          % (a_try, m_dan, m_jang, '둘 다 표준' if ok else ''))
    if ok:
        best = a_try
check("두 물매가 동시에 표준이 되는 a", best or 0.0, 1.55, 0.01, 'm')

# 그 a 를 solve_a 가 재현하는지 (순수 산술 정합성)
a = solve_a(SED_H, SED_R, SED_B, 10.0, 5.3, 4.0)
check("solve_a 산술 정합성", a, 1.550, 0.020, 'm')
H = solve_H(1.550, SED_R, SED_B, 10.0, 5.3, 4.0)
check("solve_H 역방향", H, SED_H, 0.020, 'm')

print("""
  **미해결**: p.160 에서 잰 도리 원형 부재는 용마루 중심에서 1,835 / 1,978 mm
  로, 상층 기둥열(±1,825)에 해당한다 → 주심도리다. 중도리가 이 가구에 있는지
  자체가 미확인이며, 2칸짜리 좁은 상층이면 3도리 가구(중도리 없음)일 수 있다.
  그 경우 이 지붕에는 m_dan=None 단일 경사가 맞다.""")

print()
print("=" * 78)
print("T1b 독립 실측 두 건 — 부연 비")
print("=" * 78)
# 이건 진짜 독립이다. 서로 다른 보고서, 서로 다른 건물, 각각 도면에 적힌 값.
check("석어당 부연/서까래", 0.540 / 1.200, 0.450, 0.005, '')
check("준명당 부연/서까래", 0.490 / 1.279, 0.383, 0.005, '')
print("  → 계획이 말한 1/3~2/5 (0.333~0.400) 를 두 건물이 0.383~0.450 으로 감싼다.")
print("     상한이 0.400 이 아니라 0.45 까지 간다는 것이 새로 확인된 사실이다.")

print()
print("=" * 78)
print("T2  구간별 각도")
print("=" * 78)
p = RoofProfile(R=SED_R, h0=7.835, h1=10.385, b=SED_B,
                m_dan=10.0, m_jang=5.3, m_bu=4.0, jouro=0.0, name='석어당상층')
print("  " + p.describe())
check("용마루 근처 경사 (단연)", p.slope_deg(0.3 * p.a), 45.0, 0.6, '°')
check("중간 경사 (장연)", p.slope_deg((p.a + p.r_eave) / 2), 27.9, 0.6, '°')
check("처마 끝 경사 (부연)", p.slope_deg(p.R - 0.05), 21.8, 0.6, '°')
check("처마 높이 z(R)", p.z(p.R), 7.835, 0.005, 'm')
check("용마루 높이 z(0)", p.z(0.0), 10.385, 0.005, 'm')

print()
print("=" * 78)
print("T3  기존 모델과의 비교 — D1 이 실제로 얼마나 틀렸나")
print("=" * 78)
CONC = 1.42
h0, h1, hd = 7.835, 10.385, SED_R


def old_z(r):
    return h0 + (h1 - h0) * ((1.0 - abs(r) / hd) ** CONC)


def old_slope(r):
    e = 1e-4
    r0, r1 = max(0.0, r - e), min(hd, r + e)
    return math.degrees(math.atan((old_z(r0) - old_z(r1)) / (r1 - r0)))


print("   r(m)   기존각    신규각    부재")
for frac, tag in ((0.02, '용마루 근처'), (0.20, '단연'), (0.435, '중도리'),
                  (0.70, '장연'), (0.97, '처마 끝')):
    r = frac * hd
    print("  %5.2f   %6.1f°   %6.1f°   %s" % (r, old_slope(r), p.slope_deg(r), tag))
print()
print("  → 기존 모델은 처마에서 %.1f°, 실측은 21.8°. 평평해야 할 곳이 가파르고"
      % old_slope(0.97 * hd))
print("    가팔라야 할 곳이 평평하다. 이것이 '부풀고 물렁하다'의 정체다.")

print()
print("=" * 78)
print("T4  하층지붕(상첨) — 단연 없는 단일 경사가 정상 동작하는가")
print("=" * 78)
sk = RoofProfile(R=3.2, h0=4.58, b=0.45, m_dan=None, m_jang=5.0, m_bu=4.0,
                 jouro=0.0, name='석어당하층')
print("  " + sk.describe())
check("꺾임 없음 (a=0)", sk.a, 0.0, 1e-9, 'm')
check("전 구간 동일 경사", sk.slope_deg(0.3 * sk.R) - sk.slope_deg(0.6 * sk.R),
      0.0, 0.2, '°')

print()
print("=" * 78)
print("T5  기존 치수표 검사 — assert_sane 이 어디서 걸리나")
print("=" * 78)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'deoksugung'))
try:
    from deoksugung.layout import SED, JMD, JJD, DHM, BDG
except Exception:
    from layout import SED, JMD, JJD, DHM, BDG

F = 0.40                       # 부연/서까래 비. 실측 0.383~0.45 의 중앙
CASES = [
    ('석어당 상층', sum(SED['up_bays_y']) / 2, SED['eave_out_up'],
     SED['up_eave'], SED['up_ridge']),
    ('준명당', sum(JMD['bays_y']) / 2, JMD['eave_out'], JMD['eave'], JMD['ridge']),
    ('즉조당', sum(JJD['bays_y']) / 2, JJD['eave_out'], JJD['eave'], JJD['ridge']),
    ('대한문', sum(DHM['bays_y']) / 2, DHM['eave_out'], DHM['eave'], DHM['ridge']),
    ('복도각', BDG['depth'] / 2, BDG['eave_out'], BDG['eave'], BDG['ridge']),
]
for name, half, eo, ev, rg in CASES:
    R = half + eo
    b = eo * F / (1.0 + F)
    pr = RoofProfile(R=R, h0=ev, h1=rg, b=b, jouro=0.0, name=name)
    bad = pr.assert_sane(strict=False)
    print("  %-10s a/R=%5.2f  지름 %4.1f치  %s"
          % (name, pr.a / pr.R, pr.jireum_mulmae(),
             '; '.join(bad) if bad else 'OK'))

print()
print("  실측을 넣은 석어당 상층:")
pm = RoofProfile(R=SED_R, h0=7.835, h1=10.385, b=SED_B, jouro=0.0,
                 name='석어당(실측)')
print("    a/R=%.2f 지름 %.1f치  %s"
      % (pm.a / pm.R, pm.jireum_mulmae(),
         '; '.join(pm.assert_sane(strict=False)) or 'OK'))

print()
print("=" * 78)
print("T6  h1 유도 — 잘못 찍은 용마루 높이에 곡선을 맞추지 않는다")
print("=" * 78)
d = RoofProfile(R=SED_R, h0=7.835, b=SED_B, jouro=0.0, name='석어당(유도)')
print("  " + d.describe())
check("유도된 용마루 높이", d.h1, 10.385, 0.10, 'm')

print()
print("=" * 78)
if FAIL:
    print("실패 %d건: %s" % (len(FAIL), ', '.join(FAIL)))
    sys.exit(1)
print("전부 통과")
