// 크렘린에서 「밖으로 새는 곳」을 찾는다.
//
// 방법 : 플레이어 높이의 수평 단면을 격자로 뜨고, 궁전 안에서 물 채우기(flood fill)를 한다.
//        물이 경기구역 밖까지 흘러나가면 그 경로가 구멍이다.
//
// ★ 캐릭터는 캡슐 높이 205 cm, 반지름 30 cm 다 (MovementSpeedServer 실측).
//   그래서 "사람이 지나갈 수 있는가" 는 폭 60 cm 이상이 뚫려 있는가와 같다.
//   격자를 25 cm 로 잡고, 물이 지나가려면 연속 3칸(75cm)이 필요하다고 보지 않고
//   단순 4방향으로 흘린다 -- 즉 이 검사는 **낙관적**이다(새는 곳을 놓치지 않는다).
//
//   node krm_leak.js [층높이...]      예: node krm_leak.js 100 300 700 1100

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, 'kremlin', 'KRM_work', 'krm_collision.json');
// PowerShell 이 UTF-8 BOM 을 붙여 저장한다. JSON.parse 는 BOM 을 못 먹으니 떼고 읽는다.
const parts = JSON.parse(fs.readFileSync(SRC, 'utf8').replace(/^﻿/, ''))
    .filter(p => p.collide && (p.name.startsWith('KRM_COL') || p.name.startsWith('KRM_Corridor')));

// 검사할 높이(층). 기본은 바닥 바로 위 / 허리 / 회랑 / 터렛 난간 근처.
const LEVELS = (process.argv.slice(2).map(Number).filter(Number.isFinite));
const HEIGHTS = LEVELS.length ? LEVELS : [60, 150, 400, 700, 1100];

// 격자 : 경기구역보다 넓게 잡아 밖으로 새는 걸 볼 수 있게 한다.
const CELL = 25;
const X0 = 95400, X1 = 105900;
const Z0 = -2500, Z1 = 2500;
const NX = Math.ceil((X1 - X0) / CELL);
const NZ = Math.ceil((Z1 - Z0) / CELL);

// 경기구역 (MapService.krm.rect 와 같아야 한다)
const ARENA = { minX: 95800, maxX: 105500, minZ: -2200, maxZ: 2200 };

function solidAt(p, wx, wy, wz) {
    // 파츠 로컬 좌표로 옮긴다. yaw 만 있다(pitch/roll 은 0).
    const dy = wy - p.y;
    if (Math.abs(dy) > p.sy / 2) return false;
    const dx = wx - p.x, dz = wz - p.z;
    const a = -p.yaw * Math.PI / 180;
    const lx = dx * Math.cos(a) - dz * Math.sin(a);
    const lz = dx * Math.sin(a) + dz * Math.cos(a);
    return Math.abs(lx) <= p.sx / 2 && Math.abs(lz) <= p.sz / 2;
}

let anyLeak = false;

for (const H of HEIGHTS) {
    // 이 높이를 실제로 지나는 파츠만 추린다 (전부 훑으면 느리다)
    const hit = parts.filter(p => Math.abs(H - p.y) <= p.sy / 2);

    const solid = new Uint8Array(NX * NZ);
    for (const p of hit) {
        // 파츠의 XZ 경계상자를 구해 그 안만 검사한다
        const r = (Math.abs(p.sx) + Math.abs(p.sz)) / 2 + CELL;
        const ix0 = Math.max(0, Math.floor((p.x - r - X0) / CELL));
        const ix1 = Math.min(NX - 1, Math.ceil((p.x + r - X0) / CELL));
        const iz0 = Math.max(0, Math.floor((p.z - r - Z0) / CELL));
        const iz1 = Math.min(NZ - 1, Math.ceil((p.z + r - Z0) / CELL));
        for (let ix = ix0; ix <= ix1; ix++) {
            const wx = X0 + ix * CELL + CELL / 2;
            for (let iz = iz0; iz <= iz1; iz++) {
                if (solid[iz * NX + ix]) continue;
                const wz = Z0 + iz * CELL + CELL / 2;
                if (solidAt(p, wx, H, wz)) solid[iz * NX + ix] = 1;
            }
        }
    }

    // 궁전 한가운데(VLA 중심)에서 물을 붓는다
    const sx = Math.floor((100000 - X0) / CELL);
    const sz = Math.floor((0 - Z0) / CELL);
    if (solid[sz * NX + sx]) {
        console.log(`\n=== Y ${H} : 시작점(100000, 0)이 막혀 있다. 이 높이는 바닥/천장 안이다 ===`);
        continue;
    }

    const seen = new Uint8Array(NX * NZ);
    const q = [sz * NX + sx];
    seen[q[0]] = 1;
    let head = 0, filled = 0;
    const leaks = [];
    while (head < q.length) {
        const c = q[head++]; filled++;
        const ix = c % NX, iz = (c - ix) / NX;
        const wx = X0 + ix * CELL + CELL / 2;
        const wz = Z0 + iz * CELL + CELL / 2;
        // 경기구역 밖으로 나갔으면 샜다
        if (wx < ARENA.minX || wx > ARENA.maxX || wz < ARENA.minZ || wz > ARENA.maxZ) {
            leaks.push({ x: Math.round(wx), z: Math.round(wz) });
        }
        const nb = [];
        if (ix > 0) nb.push(c - 1);
        if (ix < NX - 1) nb.push(c + 1);
        if (iz > 0) nb.push(c - NX);
        if (iz < NZ - 1) nb.push(c + NX);
        for (const n of nb) {
            if (seen[n] || solid[n]) continue;
            seen[n] = 1; q.push(n);
        }
    }

    console.log(`\n=== Y ${H} ===  이 높이를 지나는 콜리전 ${hit.length}장 / 물이 찬 칸 ${filled}`);
    if (leaks.length === 0) {
        console.log('  샌 곳 없음 — 경기구역 안에 갇힌다');
        continue;
    }
    anyLeak = true;

    // 샌 곳을 변별로 묶어 구간으로 보고한다
    const side = { W: [], E: [], S: [], N: [] };
    for (const p of leaks) {
        if (p.x < ARENA.minX) side.W.push(p);
        else if (p.x > ARENA.maxX) side.E.push(p);
        else if (p.z < ARENA.minZ) side.S.push(p);
        else side.N.push(p);
    }
    console.log(`  ⚠ 경기구역 밖으로 샌 칸 ${leaks.length} 개`);
    for (const [k, arr] of Object.entries(side)) {
        if (!arr.length) continue;
        const xs = arr.map(p => p.x), zs = arr.map(p => p.z);
        console.log(`     ${k}쪽 ${String(arr.length).padStart(5)}칸   X ${Math.min(...xs)}~${Math.max(...xs)}  Z ${Math.min(...zs)}~${Math.max(...zs)}`);
    }
    // 경계를 넘은 지점 중 가장 안쪽(=구멍 입구)을 몇 개 보여준다
    const mouth = leaks
        .filter(p => p.x >= ARENA.minX - CELL * 2 && p.x <= ARENA.maxX + CELL * 2
                  && p.z >= ARENA.minZ - CELL * 2 && p.z <= ARENA.maxZ + CELL * 2)
        .slice(0, 16);
    if (mouth.length) {
        console.log('     구멍 입구 표본 : ' + mouth.map(p => `(${p.x},${p.z})`).join(' '));
    }
}

console.log('');
process.exit(anyLeak ? 1 : 0);
