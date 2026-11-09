# -*- coding: utf-8 -*-
"""익스포트한 FBX 에 텍스처가 실제로 실렸는지 전수 검사한다.

왜 필요한가
    v19 에서 279개 파일 중 235개가 텍스처 없이 나갔는데 매니페스트만 보면
    멀쩡해 보였다. 원인은 split_mesh_lossless 가 조각 메시에 머티리얼 슬롯을
    안 옮긴 것이었고(경복궁·덕수궁은 팔레트 단색이라 증상이 안 보였다),
    두 번째 원인은 terrain._tint 가 이미지와 Base Color 사이에 노드를 끼워
    FBX 익스포터가 diffuse 를 못 찾은 것이었다.

    둘 다 **FBX 를 직접 열어 보기 전에는 안 보인다.** 그래서 이 검사가 있다.

쓰는 법
    python check_export_textures.py <익스포트 디렉터리>

판정
    - 텍스처가 없어야 정상인 그룹: 없다. 화성은 전부 텍스처를 쓴다.
    - 4096 이상은 0 이어야 한다 (IMPORT_GUIDE.md: "4K 는 임포터를 죽인다").
"""
import collections
import glob
import os
import struct
import sys

MAX_PX = 2048          # 이보다 크면 임포터가 위험하다


def _jpeg_dims(b, i):
    """SOI 위치 i 에서 SOF 마커를 찾아 (w, h). 아니면 None."""
    # 압축 지오메트리 안에서도 FFD8FF 가 우연히 나올 수 있다. 실제 JPEG 는
    # SOI 직후 APPn(JFIF/Exif), DQT 또는 COM 마커로 시작한다. 그 외 값이면
    # 뒤쪽의 우연한 SOF 바이트를 이미지로 오인하지 말고 즉시 버린다.
    if i + 4 > len(b):
        return None
    first_marker = b[i + 3]
    if not (0xE0 <= first_marker <= 0xEF or first_marker in (0xDB, 0xFE)):
        return None
    p, n = i + 2, len(b)
    while p < n - 9:
        if b[p] != 0xFF:
            p += 1
            continue
        mk = b[p + 1]
        if mk in (0xD8, 0x01) or 0xD0 <= mk <= 0xD7:
            p += 2
            continue
        if p + 4 > n:
            break
        ln = struct.unpack(">H", b[p + 2:p + 4])[0]
        if ln < 2:
            return None
        if 0xC0 <= mk <= 0xCF and mk not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", b[p + 5:p + 9])
            return w, h
        p += 2 + ln
    return None


def _sane(d):
    # 압축 지오메트리 안에도 0xFFD8FF 가 우연히 나온다. 헤더가 해석되고
    # 크기가 상식 범위일 때만 진짜 이미지로 센다.
    return d and 32 <= d[0] <= 8192 and 32 <= d[1] <= 8192


def images_in(path):
    """FBX 하나에 임베드된 이미지들의 (w, h) 목록."""
    b = open(path, "rb").read()
    out = []
    i = 0
    while True:
        i = b.find(b"\xff\xd8\xff", i)
        if i < 0:
            break
        d = _jpeg_dims(b, i)
        if _sane(d):
            out.append(d)
        i += 3
    j = 0
    while True:
        j = b.find(b"\x89PNG\r\n\x1a\n", j)
        if j < 0:
            break
        w, h = struct.unpack(">II", b[j + 16:j + 24])
        if _sane((w, h)):
            out.append((w, h))
        j += 8
    return out


def main(d):
    files = sorted(glob.glob(os.path.join(d, "*.fbx")))
    if not files:
        print("FBX 가 없다: %s" % d)
        return 1
    per = collections.defaultdict(lambda: [0, 0, 0, 0])   # 파일, 텍스처有, 이미지, 초과
    res = collections.Counter()
    naked, oversized = [], []
    for p in files:
        g = os.path.basename(p).rsplit("_", 1)[0]
        dims = images_in(p)
        s = per[g]
        s[0] += 1
        s[2] += len(dims)
        if dims:
            s[1] += 1
        else:
            naked.append(os.path.basename(p))
        for wh in dims:
            res[wh] += 1
            if max(wh) > MAX_PX:
                s[3] += 1
                oversized.append((os.path.basename(p), wh))

    print("%-5s %6s %10s %8s %8s" % ("그룹", "파일", "텍스처있음", "이미지", "초과"))
    for g in sorted(per):
        a = per[g]
        flag = "  <-- 텍스처 없음" if a[1] == 0 else ""
        print("%-5s %6d %10d %8d %8d%s" % (g, a[0], a[1], a[2], a[3], flag))

    tot = [sum(v[i] for v in per.values()) for i in range(4)]
    print("\n합계: 파일 %d / 텍스처 있는 파일 %d / 이미지 %d / %dpx 초과 %d"
          % (tot[0], tot[1], tot[2], MAX_PX, tot[3]))
    print("해상도 분포:", dict(sorted(res.items(), key=lambda kv: -max(kv[0]))))

    bad = 0
    if naked:
        bad += 1
        print("\n[실패] 텍스처 없는 파일 %d개" % len(naked))
        for f in naked[:15]:
            print("   ", f)
        if len(naked) > 15:
            print("    ... 외 %d개" % (len(naked) - 15))
    if oversized:
        bad += 1
        print("\n[실패] %dpx 초과 %d건 — 임포터가 죽을 수 있다" % (MAX_PX, len(oversized)))
        for f, wh in oversized[:15]:
            print("    %-14s %dx%d" % (f, wh[0], wh[1]))
    if not bad:
        print("\n[통과] 모든 파일에 텍스처가 있고 %dpx 를 넘는 것이 없다." % MAX_PX)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
