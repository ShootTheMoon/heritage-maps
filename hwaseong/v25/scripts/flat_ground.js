// 삐뚤빼뚤한 기울인 슬래브 992장을 버리고, 창덕궁 방식으로 다시 짠다.
//   - 전부 축정렬 평면 (Orientation 0). 인접 판끼리 각이 안 맞을 일이 없다.
//   - 같은 구역의 인접 셀을 큰 사각형으로 병합해서 판 수를 줄인다.
//   - 구역마다 Y 를 조금씩 다르게 줘 동일평면을 안 만든다 (Z-파이팅 방지, 창덕궁 기법).
const fs = require('fs');
const cells = JSON.parse(fs.readFileSync('C:/Work/blender/ovdr_export/hwaseong_v23/collision_parts.json','utf8'));
const zones = JSON.parse(fs.readFileSync('C:/Work/blender/hwaseong_rebuild/hws_zones.json','utf8'));
const Z = new Map(zones.map(z => [z.name, z.zone]));

// 격자 인덱스 정규화
const I0 = Math.min(...cells.map(c => c.grid[0])), J0 = Math.min(...cells.map(c => c.grid[1]));
const NI = Math.max(...cells.map(c => c.grid[0])) - I0 + 1;
const NJ = Math.max(...cells.map(c => c.grid[1])) - J0 + 1;
const grid = Array.from({length: NI}, () => new Array(NJ).fill(null));
for (const c of cells) grid[c.grid[0]-I0][c.grid[1]-J0] = { c, z: Z.get(c.name) || 'inner' };

const PITCH = 1200;
const X0 = Math.min(...cells.map(c => c.surface_center[0])) - PITCH/2;
const ZZ0 = Math.min(...cells.map(c => c.surface_center[2])) - PITCH/2;
const ys = cells.map(c => c.surface_center[1]).sort((a,b)=>a-b);
const yMed = ys[Math.floor(ys.length/2)];
console.log('격자 %d x %d   원점 X %s  Z %s   지표 중앙값 Y %s',
  NI, NJ, X0.toFixed(0), ZZ0.toFixed(0), yMed.toFixed(0));

// 구역별로 최대 사각형 탐욕 병합
function mergeZone(zone) {
  const used = Array.from({length: NI}, () => new Array(NJ).fill(false));
  const rects = [];
  for (let i = 0; i < NI; i++) for (let j = 0; j < NJ; j++) {
    if (used[i][j]) continue;
    const g = grid[i][j];
    if (!g || g.z !== zone) continue;
    // 가로로 최대한 늘린다
    let w = 1;
    while (i + w < NI && grid[i+w][j] && grid[i+w][j].z === zone && !used[i+w][j]) w++;
    // 그 폭을 유지한 채 세로로 늘린다
    let h = 1;
    outer: while (j + h < NJ) {
      for (let k = 0; k < w; k++) {
        const gg = grid[i+k][j+h];
        if (!gg || gg.z !== zone || used[i+k][j+h]) break outer;
      }
      h++;
    }
    for (let a = 0; a < w; a++) for (let b = 0; b < h; b++) used[i+a][j+b] = true;
    rects.push({ i, j, w, h });
  }
  return rects;
}

// 구역 정의. dy 는 서로 다르게 줘서 동일평면을 피한다.
const ZONE = {
  inner: { mat: 'Ground',         col: [112,100, 80], dy:  6, th: 40 },
  outer: { mat: 'Grass',          col: [ 92,108, 70], dy:  8, th: 40 },
  path:  { mat: 'SoilRockGround', col: [134,120, 98], dy: 12, th: 24 },
  road:  { mat: 'Sand',           col: [158,140,110], dy: 16, th: 24 },
  wall:  { mat: 'Rock',           col: [122,120,116], dy: 20, th: 30 },
};

const parts = [];
// 1) 바닥 판 하나. 구멍이 안 생기게 전체를 덮는다.
parts.push({
  name: 'HWS_GND_BASE', mat: 'Ground', col: [104, 94, 76],
  px: X0 + NI*PITCH/2, py: yMed - 200, pz: ZZ0 + NJ*PITCH/2,
  sx: NI*PITCH + 400, sy: 400, sz: NJ*PITCH + 400,
});
// 2) 구역별 병합 사각형
let n = 0;
const stat = {};
for (const [zone, def] of Object.entries(ZONE)) {
  const rects = mergeZone(zone);
  stat[zone] = { cells: 0, rects: rects.length };
  for (const r of rects) {
    let sum = 0, cnt = 0;
    for (let a = 0; a < r.w; a++) for (let b = 0; b < r.h; b++) {
      sum += grid[r.i+a][r.j+b].c.surface_center[1]; cnt++;
    }
    stat[zone].cells += cnt;
    const y = sum / cnt;                       // 이 사각형의 평균 지표 높이
    parts.push({
      name: 'HWS_GND_' + String(n++).padStart(4, '0'),
      mat: def.mat, col: def.col,
      px: X0 + (r.i + r.w/2) * PITCH,
      py: y + def.dy - def.th/2,               // 상면이 y + dy 에 온다
      pz: ZZ0 + (r.j + r.h/2) * PITCH,
      sx: r.w * PITCH + 20, sy: def.th, sz: r.h * PITCH + 20,
    });
  }
}
console.log('\n구역        셀    사각형   압축비');
for (const [k, s] of Object.entries(stat))
  console.log('  %s %4d   %4d    %sx', k.padEnd(7), s.cells, s.rects, (s.cells/Math.max(1,s.rects)).toFixed(1));
console.log('\n총 Part %d 장  (기울인 슬래브 992장 -> %d장, %.0f%% 감소)',
  parts.length, parts.length, 100*(1-parts.length/992));
fs.writeFileSync('C:/Work/blender/hwaseong_rebuild/hws_flat.json', JSON.stringify(parts));
console.log('저장: hws_flat.json');
