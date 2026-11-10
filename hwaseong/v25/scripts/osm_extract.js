// janganmun.osm 에서 성벽선과 도로를 뽑아 엔진 좌표(XZ, cm)로 투영한다.
//
// 좌표 체인 (geo.py 를 그대로 옮긴 것, 장안문=엔진(62000,0) 으로 검산됨):
//   to_en  : (lon-ANCHOR_LON)*M_PER_DEG_LON , (lat-ANCHOR_LAT)*M_PER_DEG_LAT
//   회전   : bearing 만큼 -회전해 성벽을 X 축에 맞춘다 (PCA, 앵커 90 m 안)
//   사이트 : (x, -y)  -- 북(+y) 이 사이트 -Y
//   배치   : bx = 1200 + x ,  by = 0 + y      (layout.SITE_ORIGIN)
//   엔진   : X = bx*100 - 58000 ,  Z = -by*100
const fs = require('fs');
const SRC = 'C:/Work/blender/gyeongbokgung/hwaseong/osm/janganmun.osm';
const OUT = 'C:/Work/blender/hwaseong_rebuild/hws_osm.json';

const ANCHOR_LAT = 37.2888318, ANCHOR_LON = 127.0142186;
const M_PER_DEG_LAT = 110540.0;
const M_PER_DEG_LON = 111320.0 * Math.cos(ANCHOR_LAT * Math.PI / 180);
const SITE_ORIGIN = [1200.0, 0.0];

const xml = fs.readFileSync(SRC, 'utf8');

const nodes = new Map();
for (const m of xml.matchAll(/<node id="(\d+)"[^>]*?lat="([-\d.]+)"[^>]*?lon="([-\d.]+)"/g))
  nodes.set(m[1], [parseFloat(m[2]), parseFloat(m[3])]);

const ways = [];
for (const m of xml.matchAll(/<way id="(\d+)"[\s\S]*?<\/way>/g)) {
  const body = m[0];
  const refs = [...body.matchAll(/<nd ref="(\d+)"/g)].map(x => x[1]);
  const tags = {};
  for (const t of body.matchAll(/<tag k="([^"]*)" v="([^"]*)"/g)) tags[t[1]] = t[2];
  ways.push({ id: m[1], refs, tags });
}
console.log('노드 %d  way %d', nodes.size, ways.length);

const toEN = (lat, lon) => [(lon - ANCHOR_LON) * M_PER_DEG_LON, (lat - ANCHOR_LAT) * M_PER_DEG_LAT];

// 성벽 방위각 -- 앵커 90 m 안의 city_wall 점들에 PCA
const wp = [];
for (const w of ways) {
  if (w.tags['barrier'] !== 'city_wall') continue;
  for (const r of w.refs) {
    const c = nodes.get(r); if (!c) continue;
    const [e, n] = toEN(c[0], c[1]);
    if (Math.hypot(e, n) <= 90.0) wp.push([e, n]);
  }
}
let bearing = 0;
if (wp.length >= 3) {
  const mx = wp.reduce((s, p) => s + p[0], 0) / wp.length;
  const my = wp.reduce((s, p) => s + p[1], 0) / wp.length;
  let sxx = 0, syy = 0, sxy = 0;
  for (const p of wp) { sxx += (p[0]-mx)**2; syy += (p[1]-my)**2; sxy += (p[0]-mx)*(p[1]-my); }
  bearing = 0.5 * Math.atan2(2*sxy, sxx - syy) * 180 / Math.PI;
  while (bearing > 90) bearing -= 180;
  while (bearing < -90) bearing += 180;
}
console.log('성벽 방위각 %s도  (city_wall 점 %d개, 기대 29.3)', bearing.toFixed(2), wp.length);

const r = -bearing * Math.PI / 180, C = Math.cos(r), S = Math.sin(r);
function toEngine(lat, lon) {
  const [e, n] = toEN(lat, lon);
  const x = e * C - n * S, y = e * S + n * C;
  const sx = x, sy = -y;                      // 사이트 로컬
  const bx = SITE_ORIGIN[0] + sx, by = SITE_ORIGIN[1] + sy;
  return [bx * 100 - 58000, -by * 100];       // 엔진 X, Z (cm)
}
const a = toEngine(ANCHOR_LAT, ANCHOR_LON);
console.log('검산: 장안문 앵커 -> 엔진 (%s, %s)  기대 (62000, 0)', a[0].toFixed(0), a[1].toFixed(0));

// 관심 대상 추출
const BOX = { x0: 42000, x1: 81000, z0: -20000, z1: 20000 };
const inBox = p => p[0] >= BOX.x0 && p[0] <= BOX.x1 && p[1] >= BOX.z0 && p[1] <= BOX.z1;

const out = { bearing, walls: [], roads: [] };
const ROADW = { motorway:12, trunk:11, primary:10, secondary:9, tertiary:7.5,
                residential:5.5, unclassified:5, service:4, living_street:5,
                pedestrian:3.6, footway:1.8, path:1.5, steps:1.5, track:3 };
for (const w of ways) {
  const pts = w.refs.map(x => nodes.get(x)).filter(Boolean).map(c => toEngine(c[0], c[1]));
  if (pts.length < 2) continue;
  if (!pts.some(inBox)) continue;
  if (w.tags['barrier'] === 'city_wall') out.walls.push(pts.map(p => [Math.round(p[0]), Math.round(p[1])]));
  else if (w.tags['highway']) {
    const wid = ROADW[w.tags['highway']] || 4;
    out.roads.push({ w: wid, k: w.tags['highway'], p: pts.map(p => [Math.round(p[0]), Math.round(p[1])]) });
  }
}
const seg = a2 => a2.reduce((s, x) => s + (Array.isArray(x) ? x.length : x.p.length) - 1, 0);
console.log('\n성벽 way %d (선분 %d)   도로 way %d (선분 %d)',
  out.walls.length, seg(out.walls), out.roads.length, seg(out.roads));
const byk = {};
for (const r2 of out.roads) byk[r2.k] = (byk[r2.k] || 0) + 1;
console.log('도로 종류:', JSON.stringify(byk));
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('저장:', OUT, (fs.statSync(OUT).size/1024).toFixed(0) + ' KB');
