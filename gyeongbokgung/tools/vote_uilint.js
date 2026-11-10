// LobbyUI 타이포그래피 린터.
//
// 이 엔진에는 TextBounds 가 없다. 그래서 relayout() 이 바이트 수로 글자 폭을 어림해서
// 박스보다 넓으면 그 요소만 조용히 줄인다. 줄어든 걸 알 방법이 화면밖에 없다.
// 여기서 relayout() 과 **같은 식**을 돌려 미리 잡는다.
//
//   node vote_uilint.js <LobbyUI.lua>
//
// 두 가지를 본다 :
//   1) 바닥 충돌 — TEXT_MIN(8) 에 걸리는 요소. 위계가 뭉개진다
//   2) 자동 축소 — 어림 폭이 박스를 넘는 요소. 그 요소만 혼자 작아진다
//
// 뷰포트 세 가지에서 전부 확인한다. 에디터 창이 가장 가혹하다(배율이 제일 작다).

const fs = require('fs');

const TEXT_MIN = 8;
const TEXT_SCALE = 0.85;
const REF_W = 1386, REF_H = 640;

const VIEWPORTS = [
    { name: '에디터 1132x633', w: 1132, h: 633 },
    { name: '기준   1386x640', w: 1386, h: 640 },
    { name: '풀HD   1920x1080', w: 1920, h: 1080 },
];

// relayout() 의 어림식 그대로 : ASCII 0.55, UTF-8 선두바이트(>=0xC0) 1.0
function units(str) {
    const b = Buffer.from(str, 'utf8');
    let u = 0;
    for (const byte of b) {
        if (byte < 128) u += 0.55;
        else if (byte >= 192) u += 1.0;
    }
    return u;
}

const src = fs.readFileSync(process.argv[2] || 'LobbyUI.lua', 'utf8');

// L 테이블 상수를 읽어 이름 -> 숫자 로 만든다 (x/w 에 L.XXX 를 쓰는 호출이 많다)
const L = {};
{
    const m = /local L = \{([\s\S]*?)\n\}/.exec(src);
    if (m) {
        for (const mm of m[1].matchAll(/([A-Z_][A-Z0-9_]*)\s*=\s*(-?[\d.]+)/g)) {
            L[mm[1]] = parseFloat(mm[2]);
        }
    }
}

// 아주 단순한 산술 평가 : 숫자, L.XXX, + - * / 와 괄호만.
function evalExpr(e) {
    if (e == null) return null;
    let s = e.trim();
    if (!s) return null;
    s = s.replace(/L\.([A-Z_][A-Z0-9_]*)/g, (_, k) => (k in L ? L[k] : 'NaN'));
    if (!/^[-+*/(). 0-9]+$/.test(s)) return null;      // 변수가 섞이면 포기
    try {
        const v = Function('"use strict";return (' + s + ')')();
        return Number.isFinite(v) ? v : null;
    } catch { return null; }
}

// U.txt(parent, str, x, y, w, h, size, color, bold, align, z, rule)
// 인자를 콤마로 쪼갠다. 괄호/따옴표 깊이를 세어 안전하게.
function splitArgs(s) {
    const out = []; let d = 0, q = null, cur = '';
    for (let i = 0; i < s.length; i++) {
        const c = s[i];
        if (q) { cur += c; if (c === q && s[i - 1] !== '\\') q = null; continue; }
        if (c === '"' || c === "'") { q = c; cur += c; continue; }
        if (c === '(' || c === '{') d++;
        if (c === ')' || c === '}') d--;
        if (c === ',' && d === 0) { out.push(cur); cur = ''; continue; }
        cur += c;
    }
    if (cur.trim()) out.push(cur);
    return out.map(x => x.trim());
}

const rows = [];
const lines = src.split(/\r?\n/);
for (let i = 0; i < lines.length; i++) {
    const idx = lines[i].indexOf('U.txt(');
    if (idx < 0) continue;
    // 호출이 여러 줄에 걸칠 수 있다. 괄호가 닫힐 때까지 이어 붙인다.
    let buf = lines[i].slice(idx + 6), d = 1, j = i;
    while (j < lines.length) {
        let done = false, cut = -1;
        for (let k = 0; k < buf.length; k++) {
            if (buf[k] === '(') d++;
            else if (buf[k] === ')') { d--; if (d === 0) { cut = k; done = true; break; } }
        }
        if (done) { buf = buf.slice(0, cut); break; }
        j++;
        if (j >= lines.length) break;
        buf += ' ' + lines[j];
    }
    const a = splitArgs(buf);
    if (a.length < 7) continue;

    const strRaw = a[1];
    const strM = /^"((?:[^"\\]|\\.)*)"$/.exec(strRaw);
    const text = strM ? strM[1].replace(/\\"/g, '"') : null;   // 변수면 null
    const w = evalExpr(a[4]);
    const size = evalExpr(a[6]);
    const rule = a[11] || '';
    if (size == null) continue;

    rows.push({ line: i + 1, text, w, size, rule, raw: buf.slice(0, 60) });
}

console.log(`U.txt 호출 ${rows.length} 개  (문자열이 리터럴인 것 ${rows.filter(r => r.text !== null).length})`);

// 쓰이는 크기 분포
const sizes = [...new Set(rows.map(r => r.size))].sort((x, y) => x - y);
console.log(`\n쓰이는 기준 크기 ${sizes.length} 가지 : ${sizes.join(' · ')}`);

let bad = 0;
for (const vp of VIEWPORTS) {
    const s = Math.min(vp.w / REF_W, vp.h / REF_H);
    const dW = vp.w / s - REF_W;

    console.log(`\n=== ${vp.name}   s=${s.toFixed(4)}  dW=${dW.toFixed(0)} ===`);

    // 크기별 실제 px
    const px = {};
    for (const sz of sizes) px[sz] = Math.max(TEXT_MIN, Math.floor(sz * s * TEXT_SCALE + 0.5));
    const collide = [];
    for (let i = 1; i < sizes.length; i++) {
        if (px[sizes[i]] === px[sizes[i - 1]]) collide.push(`${sizes[i - 1]}=${sizes[i]}→${px[sizes[i]]}px`);
    }
    console.log('  크기→px : ' + sizes.map(z => `${z}→${px[z]}`).join('  '));
    if (collide.length) {
        console.log(`  ⚠ 구별 안 되는 짝 ${collide.length} : ${collide.join(', ')}`);
        bad++;
    }
    const floored = sizes.filter(z => px[z] === TEXT_MIN);
    if (floored.length) {
        console.log(`  ⚠ 바닥(${TEXT_MIN}px)에 걸린 크기 : ${floored.join(', ')}`);
        bad++;
    }

    // 자동 축소가 걸리는 요소
    const shrunk = [];
    for (const r of rows) {
        if (r.text === null || r.w == null) continue;
        const gw = /RULE_W|RULE_H|\{\s*0\s*,\s*0\s*,\s*1/.test(r.rule) ? 1 : 0;
        const lim = (r.w + gw * dW) * s;
        const u = units(r.text);
        if (u <= 0 || lim <= 1) continue;
        const base = Math.max(TEXT_MIN, Math.floor(r.size * s * TEXT_SCALE + 0.5));
        const fit = Math.floor(lim / u);
        if (fit < base) shrunk.push({ ...r, base, fit: Math.max(TEXT_MIN, fit) });
    }
    if (shrunk.length) {
        console.log(`  ⚠ 자동 축소가 걸리는 요소 ${shrunk.length} 개 :`);
        for (const x of shrunk.slice(0, 12)) {
            console.log(`      ${String(x.line).padStart(4)}행  "${x.text}"  기준${x.size} → ${x.base}px 인데 박스가 ${x.fit}px 로 깎는다`);
        }
        if (shrunk.length > 12) console.log(`      ... +${shrunk.length - 12}개`);
        bad++;
    } else {
        console.log('  자동 축소 걸리는 요소 없음');
    }
}

console.log('');
process.exit(bad ? 1 : 0);
