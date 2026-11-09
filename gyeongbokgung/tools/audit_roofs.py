# -*- coding: utf-8 -*-
"""전 건물 지붕 물매 감사 — 치수표를 검증 가능한 데이터로 만든다.

    python audit_roofs.py          (블렌더 불필요)

제원은 **build.py / deoksugung/layout.py 에서 직접 읽는다.** 손으로 옮겨 적으면
표가 바뀌었을 때 감사가 조용히 낡는다 (그리고 실제로 내가 한 번 그렇게 틀렸다 —
사정전 제원을 지어내 쓰는 바람에 멀쩡한 표를 틀렸다고 보고했다).

R 의 정의: **용마루 → 부연 끝의 수평거리.** 지붕 빌더가 실제로 쓰는 값과 같아야
한다. build_hip_gable_roof(name, coll, RW, RD, ...) 의 RD/2 다.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from roofprofile import RoofProfile     # noqa: E402

F = 0.40        # 부연/서까래 비. 실측 석어당 0.450 / 준명당 0.383 의 중앙


def load_table(path, names):
    """bpy import 없이 dict 리터럴만 뽑아 온다."""
    src = open(path, encoding='utf-8').read()
    out = {}
    for n in names:
        m = re.search(r'^%s\s*=\s*dict\((.*?)^\)' % n, src, re.S | re.M)
        if not m:
            continue
        body = m.group(1)
        body = re.sub(r'#.*', '', body)                 # 주석 제거
        try:
            out[n] = eval("dict(%s)" % body, {'dict': dict})
        except Exception as e:
            print("  %s 파싱 실패: %s" % (n, e))
    return out


HERE = os.path.dirname(os.path.abspath(__file__))
G = load_table(os.path.join(HERE, 'build.py'), ['GJ', 'SJ'])
D = load_table(os.path.join(HERE, 'deoksugung', 'layout.py'),
               ['SED', 'JMD', 'JJD', 'DHM', 'BDG'])

GJ, SJ = G['GJ'], G['SJ']
SED, JMD, JJD, DHM, BDG = D['SED'], D['JMD'], D['JJD'], D['DHM'], D['BDG']

# 근정전 상층은 **고주 칸(내진주)** 위에 얹힌다. bays_y 전체가 아니라
# 안쪽 3칸이다 — build.py 의 iD = iys[-1] - iys[0] 과 같아야 한다.
gj_iD = sum(GJ['bays_y'][1:-1])
gj_iW = sum(GJ['bays_x'][1:-1])

CASES = [
    # 이름,           깊이(기둥열),      처마내밀기,          처마고,        용마루,  꺾임
    ('근정전 상층', gj_iD,                GJ['eave_out_up'],  GJ['up_eave'],  GJ['up_ridge'], True),
    ('근정전 하층', sum(GJ['bays_y']),    GJ['eave_out_low'], GJ['low_eave'], GJ['low_top'],  False),
    ('사정전',      sum(SJ['bays_y']),    SJ['eave_out'],     SJ['eave'],     SJ['ridge'],    True),
    ('석어당 상층', sum(SED['up_bays_y']), SED['eave_out_up'], SED['up_eave'], SED['up_ridge'], True),
    ('석어당 하층', sum(SED['bays_y']),   SED['eave_out_low'], SED['low_eave'], SED['low_top'], False),
    ('준명당',      sum(JMD['bays_y']),   JMD['eave_out'],    JMD['eave'],    JMD['ridge'],   True),
    ('즉조당',      sum(JJD['bays_y']),   JJD['eave_out'],    JJD['eave'],    JJD['ridge'],   True),
    ('대한문',      sum(DHM['bays_y']),   DHM['eave_out'],    DHM['eave'],    DHM['ridge'],   True),
    ('복도각',      BDG['depth'],         BDG['eave_out'],    BDG['eave'],    BDG['ridge'],   True),
]

print("=" * 96)
print("지붕 물매 감사   (R = 용마루→부연끝 수평거리, 부연비 %.2f)" % F)
print("실측 기준: 석어당 지름 7.2치(추론) / 준명당 6.4~7.5치 / 통상 5~8치")
print("=" * 96)
print("%-12s %6s %6s %6s %6s  %5s  %6s  %s"
      % ('건물', '깊이', '처마', 'R', 'H', 'a/R', '지름', '판정'))
print("-" * 96)

bad = []
for name, depth, eo, ev, rg, has_break in CASES:
    R = depth / 2.0 + eo
    H = rg - ev
    b = eo * F / (1.0 + F)
    p = RoofProfile(R=R, h0=ev, h1=rg, b=b, jouro=0.0,
                    m_dan=(10.0 if has_break else None), name=name)
    msgs = p.assert_sane(strict=False)
    tag = '; '.join(msgs) if msgs else 'OK'
    print("%-12s %6.2f %6.2f %6.2f %6.2f  %5.2f  %5.1f치  %s"
          % (name, depth, eo, R, H, p.a / p.R, p.jireum_mulmae(), tag))
    if msgs:
        bad.append((name, depth, eo, ev, rg, has_break, p))

print()
print("=" * 96)
print("배치 — 이웃 지붕 간섭 (U 축)")
print("=" * 96)
# layout.check_roof_clearance 를 그대로 쓴다 — 여기서 따로 구현하면 두 벌이
# 갈라진다 (실제로 갈라져서, 1차원 판본이 없는 간섭을 3.71 m 라고 보고했다).
sys.path.insert(0, os.path.join(HERE, 'deoksugung'))
from deoksugung import layout as L                # noqa: E402
for n in ('준명당', '즉조당', '석어당', '대한문'):
    e = L.roof_extent(n)
    print("  %-6s U=%+8.2f V=%+7.2f   반치수 U %5.2f  V %5.2f"
          % (n, L.UV[n][0], L.UV[n][1], e[0], e[1]))
_clash = L.check_roof_clearance()
if not _clash:
    print("  → 간섭 없음 (두 축 모두 겹치는 쌍이 없다)")
for a2, b2, du, dv in _clash:
    print("  → %s ↔ %s 간섭   U %.2f m, V %.2f m" % (a2, b2, du, dv))

print()
if not bad:
    print("물매: 전부 통과.")
else:
    print("=" * 96)
    print("걸린 건물 — h1 을 유도하면 얼마가 되는가")
    print("=" * 96)
    for name, depth, eo, ev, rg, has_break, p in bad:
        R = depth / 2.0 + eo
        b = eo * F / (1.0 + F)
        d = RoofProfile(R=R, h0=ev, b=b, jouro=0.0,
                        m_dan=(10.0 if has_break else None),
                        name=name + '(유도)')
        print("  %-12s 용마루 %6.2f → %6.2f  (%+.2f m)  지름 %.1f→%.1f치  %s"
              % (name, rg, d.h1, d.h1 - rg, p.jireum_mulmae(),
                 d.jireum_mulmae(),
                 '; '.join(d.assert_sane(strict=False)) or 'OK'))
