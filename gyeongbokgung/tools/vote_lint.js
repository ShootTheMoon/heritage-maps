// Lua 블록 구조 검사기.
//
// 이 PC 에 Lua 인터프리터가 없다. 스크립트를 여러 개 고치는 동안
// `end` 하나가 어긋나면 발행 뒤 런타임에야 알게 되는데, 그땐 이미 늦다.
// 문법 전체를 보는 게 아니라 "블록 여닫이가 맞는가" 만 본다 -- 실제로 이게 거의 전부다.
//
//   node vote_lint.js <file.lua> [more.lua ...]
//
// 문자열 / 긴 문자열([[ ]]) / 주석 / 긴 주석(--[[ ]]) 안은 건너뛴다.
// `then`, `do` 없는 한 줄 if 같은 건 Lua 문법상 불가능하므로 신경 쓰지 않는다.

const fs = require('fs');

function scan(src) {
    const opens = [];          // { kw, line }
    const problems = [];
    let i = 0, line = 1;
    const n = src.length;

    const isWord = (c) => /[A-Za-z0-9_]/.test(c);

    while (i < n) {
        const c = src[i];

        if (c === '\n') { line++; i++; continue; }

        // 긴 주석 / 긴 문자열 : --[[ ... ]]  또는  [[ ... ]]  (= 표시 포함)
        const longOpen = /^(--)?\[(=*)\[/.exec(src.slice(i, i + 12));
        if (longOpen) {
            const eq = longOpen[2];
            const close = ']' + eq + ']';
            const at = src.indexOf(close, i + longOpen[0].length);
            const stop = at < 0 ? n : at + close.length;
            for (let k = i; k < stop; k++) if (src[k] === '\n') line++;
            i = stop;
            continue;
        }

        // 한 줄 주석
        if (c === '-' && src[i + 1] === '-') {
            while (i < n && src[i] !== '\n') i++;
            continue;
        }

        // 문자열
        if (c === '"' || c === "'") {
            const q = c; i++;
            while (i < n) {
                if (src[i] === '\\') { i += 2; continue; }
                if (src[i] === '\n') { line++; break; }   // 닫히지 않은 문자열
                if (src[i] === q) { i++; break; }
                i++;
            }
            continue;
        }

        // 낱말
        if (isWord(c)) {
            let j = i;
            while (j < n && isWord(src[j])) j++;
            const w = src.slice(i, j);
            const prev = src.slice(Math.max(0, i - 1), i);

            // `a.function` 같은 필드 접근은 키워드가 아니다
            const isField = prev === '.' || prev === ':';

            if (!isField) {
                if (w === 'function' || w === 'if' || w === 'for' || w === 'while' || w === 'do') {
                    // `end` 로 닫히는 do 만 센다. for/while 뒤의 do 는 이미 for/while 이 세었다.
                    if (w === 'do') {
                        const top = opens[opens.length - 1];
                        if (top && (top.kw === 'for' || top.kw === 'while')) {
                            // for/while 의 do. 새로 열지 않는다.
                        } else {
                            opens.push({ kw: 'do', line });
                        }
                    } else {
                        opens.push({ kw: w, line });
                    }
                } else if (w === 'repeat') {
                    opens.push({ kw: 'repeat', line });
                } else if (w === 'until') {
                    const top = opens.pop();
                    if (!top || top.kw !== 'repeat') {
                        problems.push(`${line}행: until 인데 짝이 되는 repeat 가 없다`);
                    }
                } else if (w === 'end') {
                    const top = opens.pop();
                    if (!top) {
                        problems.push(`${line}행: end 가 남는다 (여는 블록이 없다)`);
                    } else if (top.kw === 'repeat') {
                        problems.push(`${line}행: repeat(${top.line}행)는 until 로 닫아야 한다`);
                    }
                }
            }
            i = j;
            continue;
        }

        i++;
    }

    for (const o of opens) problems.push(`${o.line}행: ${o.kw} 가 안 닫혔다`);
    return problems;
}

let bad = 0;
for (const f of process.argv.slice(2)) {
    const src = fs.readFileSync(f, 'utf8');
    const p = scan(src);
    const name = f.split(/[\\/]/).pop();
    if (p.length === 0) {
        console.log(`  OK    ${name}  (${src.split('\n').length}행)`);
    } else {
        bad++;
        console.log(`  FAIL  ${name}`);
        for (const m of p.slice(0, 12)) console.log(`          ${m}`);
        if (p.length > 12) console.log(`          ... +${p.length - 12}건`);
    }
}
process.exit(bad ? 1 : 0);
