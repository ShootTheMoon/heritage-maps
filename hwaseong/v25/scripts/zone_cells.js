// 셀 992장을 재질 구역으로 분류한다.
//   성 안 / 성 밖  : 성벽 폴리라인으로 가른다
//   도로          : 도로 폴리라인까지의 거리 < 반폭 + 여유
//   성벽 접지부    : 성벽선까지의 거리 < 8 m
const fs = require('fs');
const cells = JSON.parse(fs.readFileSync('C:/Work/blender/ovdr_export/hwaseong_v23/collision_parts.json','utf8'));
const osm   = JSON.parse(fs.readFileSync('C:/Work/blender/hwaseong_rebuild/hws_osm.json','utf8'));

// 점-선분 거리 (cm)
function segDist(px,pz, ax,az, bx,bz){
  const dx=bx-ax, dz=bz-az;
  const L=dx*dx+dz*dz;
  let t = L>0 ? ((px-ax)*dx + (pz-az)*dz)/L : 0;
  t = Math.max(0, Math.min(1, t));
  const cx=ax+t*dx, cz=az+t*dz;
  return Math.hypot(px-cx, pz-cz);
}
function polyDist(px,pz, pts){
  let d=Infinity;
  for(let i=1;i<pts.length;i++) d=Math.min(d, segDist(px,pz, pts[i-1][0],pts[i-1][1], pts[i][0],pts[i][1]));
  return d;
}

// 성벽 폴리라인을 하나로 모아 "성 안" 판정용 중심을 잡는다.
// 화성 성곽은 닫힌 고리가 아니라 잘린 조각이라, 장안문 앵커(62000,0)에서
// 성벽까지의 부호를 쓰는 대신 성벽 점들의 무게중심 쪽을 '안'으로 본다.
const wallPts = osm.walls.flat();
const wc = wallPts.reduce((s,p)=>[s[0]+p[0], s[1]+p[1]], [0,0]).map(v=>v/wallPts.length);
console.log('성벽 점 %d개, 무게중심 (%s, %s)', wallPts.length, wc[0].toFixed(0), wc[1].toFixed(0));

const ROAD_PAD = 250;      // 반폭에 더하는 여유 cm
const WALL_BAND = 800;     // 성벽 접지부 폭 cm

const zones = {};
const out = [];
for(const c of cells){
  const X=c.surface_center[0], Z=c.surface_center[2];
  const dWall = osm.walls.length ? Math.min(...osm.walls.map(w=>polyDist(X,Z,w))) : Infinity;
  let dRoad = Infinity, rk = null;
  for(const r of osm.roads){
    const d = polyDist(X,Z,r.p) - r.w*100/2;
    if(d < dRoad){ dRoad = d; rk = r.k; }
  }
  let zone;
  if (dWall < WALL_BAND)            zone = 'wall';
  else if (dRoad < ROAD_PAD)        zone = (rk==='footway'||rk==='path'||rk==='steps') ? 'path' : 'road';
  else                              zone = (Math.hypot(X-wc[0], Z-wc[1]) < 12000) ? 'inner' : 'outer';
  zones[zone] = (zones[zone]||0)+1;
  out.push({ name: c.name, zone, dWall: Math.round(dWall), dRoad: Math.round(dRoad) });
}
console.log('\n구역 분포:');
for(const [k,v] of Object.entries(zones).sort((a,b)=>b[1]-a[1]))
  console.log('  %s %d 장 (%s%%)', k.padEnd(7), v, (100*v/cells.length).toFixed(1));
fs.writeFileSync('C:/Work/blender/hwaseong_rebuild/hws_zones.json', JSON.stringify(out));
console.log('\n저장: hws_zones.json');
