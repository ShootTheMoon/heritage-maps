// 2단계 검증 : MapService 의 산곡 값이 원래 하드코딩 상수와 같은가.
//
// 이 단계의 존재 이유가 이 대조다. 배선만 갈아끼우고 값은 한 자리도 안 바꿨다는 걸
// 증명하지 못하면, 나중에 산곡에서 뭔가 이상할 때 그게 배선 탓인지 값 탓인지 알 수 없다.
//
// 원본은 편집 전에 떠 둔 사본에서 읽는다. 편집본에서 읽으면 내가 쓴 값을 내가 읽는 것뿐이다.
//
//   node vote_assert.js <원본디렉터리> <MapService.lua>
//     원본디렉터리에 CaptureServer.orig.lua / TeamServer.orig.lua / SeamFiller.orig.lua

const fs = require('path') && require('fs');
const path = require('path');

const origDir = process.argv[2];
const msPath = process.argv[3];
if (!origDir || !msPath) {
    console.error('usage: node vote_assert.js <origDir> <MapService.lua>');
    process.exit(2);
}

const read = (p) => fs.readFileSync(p, 'utf8');
const cap = read(path.join(origDir, 'CaptureServer.orig.lua'));
const team = read(path.join(origDir, 'TeamServer.orig.lua'));
const seam = read(path.join(origDir, 'SeamFiller.orig.lua'));
const ms = read(msPath);

// MapService 의 jsn 블록만 잘라 낸다 (hws / krm 값에 속지 않도록)
const jsnStart = ms.indexOf('\tjsn = {');
const hwsStart = ms.indexOf('\thws = {');
if (jsnStart < 0 || hwsStart < 0) { console.error('MapService 에서 jsn 블록을 못 찾았다'); process.exit(2); }
const jsn = ms.slice(jsnStart, hwsStart);

const rows = [];
function check(label, got, want) {
    const ok = String(got) === String(want);
    rows.push({ label, got, want, ok });
}

// --- 원본에서 뽑기 ---
const g = (src, re, n = 1) => { const m = re.exec(src); return m ? m[n] : '(못찾음)'; };

// CaptureServer 원본 상수
const oRadius = g(cap, /RADIUS = (\d+),/);
const oMinSpawn = g(cap, /MIN_SPAWN_DIST = (\d+),/);
const oEdge = g(cap, /local EDGE_MARGIN = (\d+)/);
const oGroundFb = g(cap, /groundY\(CENTER_X, CENTER_Z\) or (\d+)/);
const oRayTop = g(cap, /Vector3\.new\(x, (\d+), z\), Vector3\.new\(0, -(\d+), 0\)/, 1);
const oRayLen = g(cap, /Vector3\.new\(x, (\d+), z\), Vector3\.new\(0, -(\d+), 0\)/, 2);
const oMapName = g(cap, /local MAP_NAME = "([^"]+)"/);

// TeamServer 원본 상수
const oSpawnRed = g(team, /local SPAWN_RED = "([^"]+)"/);
const oSpawnBlue = g(team, /local SPAWN_BLUE = "([^"]+)"/);
const oTeamRayTop = g(team, /Vector3\.new\(x, (\d+), z\), Vector3\.new\(0, -(\d+), 0\), rp\)/, 1);
const oTeamRayLen = g(team, /Vector3\.new\(x, (\d+), z\), Vector3\.new\(0, -(\d+), 0\), rp\)/, 2);
const oTeamMap = g(team, /Workspace:FindFirstChild\("([^"]+)"\)/);

// SeamFiller 원본 상수
const oTile = g(seam, /local TILE = (\d+)/);
const oXb = g(seam, /local X_BOUNDS = \{ ([^}]+)\}/).trim();
const oZb = g(seam, /local Z_BOUNDS = \{ ([^}]+)\}/).trim();
const oXmm = g(seam, /local X_MIN, X_MAX = ([^\r\n]+)/).trim();
const oZmm = g(seam, /local Z_MIN, Z_MAX = ([^\r\n]+)/).trim();

// --- MapService jsn 에서 뽑기 ---
const j = (re, n = 1) => { const m = re.exec(jsn); return m ? m[n] : '(못찾음)'; };
const mRadius = j(/zoneRadius = (\d+)/);
const mMinSpawn = j(/minSpawnDist = (\d+)/);
const mEdge = j(/edgeMargin = (\d+)/);
const mGroundY = j(/groundY = (-?\d+)/);
const mRayTop = j(/rayTop = (\d+)/);
const mRayLen = j(/rayLen = (\d+)/);
const mContainer = j(/containers = \{ "([^"]+)"/);
const mSpawnRed = j(/spawnRed = "([^"]+)"/);
const mSpawnBlue = j(/spawnBlue = "([^"]+)"/);
const mTile = j(/tile = (\d+)/);
const mXb = j(/xb = \{ ([^}]+)\}/).trim();
const mZb = j(/zb = \{ ([^}]+)\}/).trim();
const mXmin = j(/xmin = (-?\d+)/), mXmax = j(/xmax = (-?\d+)/);
const mZmin = j(/zmin = (-?\d+)/), mZmax = j(/zmax = (-?\d+)/);

check('CFG.RADIUS',        mRadius,   oRadius);
check('CFG.MIN_SPAWN_DIST', mMinSpawn, oMinSpawn);
check('EDGE_MARGIN',       mEdge,     oEdge);
check('지면 폴백',          mGroundY,  oGroundFb);
check('레이캐스트 top (Capture)', mRayTop, oRayTop);
check('레이캐스트 len (Capture)', mRayLen, oRayLen);
check('레이캐스트 top (Team)',    mRayTop, oTeamRayTop);
check('레이캐스트 len (Team)',    mRayLen, oTeamRayLen);
check('맵 컨테이너 (Capture)',    mContainer, oMapName);
check('맵 컨테이너 (Team)',       mContainer, oTeamMap);
check('SPAWN_RED',         mSpawnRed,  oSpawnRed);
check('SPAWN_BLUE',        mSpawnBlue, oSpawnBlue);
check('SeamFiller TILE',   mTile,      oTile);
check('SeamFiller X_BOUNDS', mXb,      oXb);
check('SeamFiller Z_BOUNDS', mZb,      oZb);
check('SeamFiller X_MIN,X_MAX', `${mXmin}, ${mXmax}`, oXmm);
check('SeamFiller Z_MIN,Z_MAX', `${mZmin}, ${mZmax}`, oZmm);

let bad = 0;
console.log('\n산곡 값 대조 (MapService.jsn  vs  편집 전 원본)\n');
for (const r of rows) {
    if (r.ok) {
        console.log(`  OK    ${r.label.padEnd(26)} ${r.got}`);
    } else {
        bad++;
        console.log(`  DIFF  ${r.label.padEnd(26)} MapService=${r.got}   원본=${r.want}`);
    }
}
console.log('');
if (bad) {
    console.log(`  ${bad}건 불일치 -- 산곡 동작이 바뀐다. 고치고 다시 확인해라.`);
    process.exit(1);
}
console.log(`  ${rows.length}건 전부 일치. 산곡은 배선 전과 똑같이 돈다.`);

// 경기구역 rect 는 원본에 없던 값이다 (원본은 벽에서 읽었다).
// 그래서 대조 대상이 아니라 "폴백으로만 쓰인다" 는 사실만 확인한다.
const mRect = /rect = \{ minX = (-?\d+), maxX = (-?\d+), minZ = (-?\d+), maxZ = (-?\d+) \}/.exec(jsn);
if (mRect) {
    console.log(`\n  참고 : jsn.rect = X[${mRect[1]}..${mRect[2]}] Z[${mRect[3]}..${mRect[4]}]`);
    console.log('         이 값은 벽 4장을 못 찾았을 때만 쓰이는 폴백이다.');
    console.log('         정상 상태에서는 useArenaBounds() 가 벽에서 읽은 값이 이긴다.');
}
