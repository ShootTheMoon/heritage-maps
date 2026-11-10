// 레벨의 화성 MeshPart 189장을 원본 배치 JSON 과 대조한다.
//
// placement_core66.json + placement_rest123.json 이 임포트 당시의 정본이다.
// 여기에 meshId / cframe / size_literal_cm 이 전부 들어 있으므로
// 재임포트 없이 이 값으로 되돌리면 "처음 임포트했던 그대로" 가 된다.
//
//   node hws_diff.js <레벨에서 뽑은 json>

const fs = require('fs');
const path = require('path');

const PKG = 'C:/Work/blender/ovdr_export/hwaseong_v23';
const rd = f => JSON.parse(fs.readFileSync(f, 'utf8').replace(/^﻿/, ''));

const core = rd(path.join(PKG, 'placement_core66.json'));
const rest = rd(path.join(PKG, 'placement_rest123.json'));

console.log('core66 :', 'placement_scale =', core.placement_scale ?? '(없음)',
    '| origin_delta_cm =', JSON.stringify(core.origin_delta_cm),
    '| size_mode =', core.size_mode);
console.log('rest123:', 'placement_scale =', rest.placement_scale ?? '(없음)',
    '| scale_pivot_cm =', JSON.stringify(rest.scale_pivot_cm),
    '| size_mode =', rest.size_mode);
console.log('bounds core66 :', JSON.stringify(core.bounds_cm));
console.log('bounds rest123:', JSON.stringify(rest.bounds_cm));

const want = new Map();
for (const src of [core, rest]) {
    const arr = src.items || src.parts || src.placements || [];
    for (const it of arr) want.set(it.name, it);
}
console.log('\n원본 배치 항목 :', want.size);

const lvlPath = process.argv[2];
if (!lvlPath) { console.log('\n(레벨 덤프를 안 줬다. 원본 쪽만 요약했다.)'); process.exit(0); }
const lvl = rd(lvlPath);

let matched = 0, missing = [], ratios = [];
for (const p of lvl) {
    const w = want.get(p.name);
    if (!w) { missing.push(p.name); continue; }
    matched++;
    const r = {
        name: p.name,
        sx: w.size_literal_cm.X / (p.sx || 1),
        sy: w.size_literal_cm.Y / (p.sy || 1),
        sz: w.size_literal_cm.Z / (p.sz || 1),
        dx: w.cframe.X - p.x, dy: w.cframe.Y - p.y, dz: w.cframe.Z - p.z,
    };
    ratios.push(r);
}
console.log('레벨에서 찾은 것 :', lvl.length, '| 원본과 이름이 맞은 것 :', matched,
    '| 원본에 없는 것 :', missing.length);
if (missing.length) console.log('  없는 이름 표본 :', missing.slice(0, 6).join(', '));

const med = a => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
console.log('\n== 원본 / 지금 크기 비율 ==');
console.log('  X 중앙값', med(ratios.map(r => r.sx)).toFixed(4),
    ' Y', med(ratios.map(r => r.sy)).toFixed(4),
    ' Z', med(ratios.map(r => r.sz)).toFixed(4));

// 비율이 제각각이면 단순 배율이 아니다 -- 그럼 값을 통째로 덮어써야 한다
const uniq = new Set(ratios.map(r => r.sx.toFixed(3)));
console.log('  서로 다른 X 비율 :', uniq.size, uniq.size <= 3 ? '(균일한 배율이다)' : '(제각각이다 — 통째로 덮어써야 한다)');
if (uniq.size <= 6) console.log('   ', [...uniq].join(', '));

console.log('\n== 원본 - 지금 위치 차이 ==');
console.log('  X 중앙값', med(ratios.map(r => r.dx)).toFixed(1),
    ' Y', med(ratios.map(r => r.dy)).toFixed(1),
    ' Z', med(ratios.map(r => r.dz)).toFixed(1));
const maxd = Math.max(...ratios.map(r => Math.max(Math.abs(r.dx), Math.abs(r.dy), Math.abs(r.dz))));
console.log('  최대 차이', maxd.toFixed(1), 'cm');
