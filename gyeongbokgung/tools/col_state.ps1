# 각 컨테이너의 MeshPart / Part 가 충돌을 갖고 있는지 센다.
#
# ★ 이 엔진에서 지형 메시는 CanCollide 를 켜도 뚫고 떨어진다 (convex 분해가 뭉갠다).
#   그래서 지형은 Part 슬래브로 깐다. 반대로 건물·바위처럼 convex 에 가까운 것은 켜면 먹는다.
#   어디에 무엇이 있는지 먼저 보고 결정한다.
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath

function Get-Block {
    param([string] $Name)
    $m = [regex]::Match($text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { return $null }
    $i = $m.Index; $d = 0
    while ($i -ge 0) { $c = $text[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
    $j = $i; $d = 0; $s = $false
    while ($j -lt $text.Length) {
        $c = $text[$j]
        if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
        else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { break } } }
        $j++
    }
    return $text.Substring($i, $j - $i + 1)
}

function Node-Span {
    param([string] $Txt, [int] $At)
    $i = $At; $d = 0
    while ($i -ge 0) { $c = $Txt[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
    if ($i -lt 0) { return $null }
    $j = $i; $d = 0; $s = $false
    while ($j -lt $Txt.Length) {
        $c = $Txt[$j]
        if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
        else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { return [pscustomobject]@{ Start = $i; End = $j } } } }
        $j++
    }
    return $null
}

foreach ($cn in 'Hwaseong Place', 'Hwaseong Collision', 'KRM_Palace', 'JSN_Sangok') {
    $blk = Get-Block -Name $cn
    if (-not $blk) { Write-Host "$cn 없음" -ForegroundColor Red; continue }

    $rows = @()
    foreach ($m in [regex]::Matches($blk, '"InstanceType":\s*"(MeshPart|Part|SpawnLocation)"')) {
        $ns = Node-Span -Txt $blk -At $m.Index
        if ($null -eq $ns) { continue }
        $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
        $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
        $cc = [regex]::Match($ch, '"CanCollide":\s*(true|false)')
        $cp = [regex]::Match($ch, '"CollisionProfile":\s*"([^"]*)"')
        $rows += [pscustomobject]@{
            Kind = $m.Groups[1].Value
            Name = $(if ($nm.Success) { $nm.Groups[1].Value } else { '?' })
            CC   = ($cc.Success -and $cc.Groups[1].Value -eq 'true')
            Prof = $(if ($cp.Success) { $cp.Groups[1].Value } else { '-' })
        }
    }

    Write-Host ("`n== {0} ==  잎 노드 {1}" -f $cn, $rows.Count) -ForegroundColor Cyan
    $rows | Group-Object Kind, CC, Prof | Sort-Object Name |
        ForEach-Object { "   {0,-34} {1,5}개" -f $_.Name, $_.Count }

    # 충돌이 없는 MeshPart 를 이름 앞머리별로 묶어 보여준다
    $off = @($rows | Where-Object { $_.Kind -eq 'MeshPart' -and -not $_.CC })
    if ($off.Count) {
        Write-Host ("   충돌 꺼진 MeshPart {0} 개 :" -f $off.Count) -ForegroundColor Yellow
        $off | Group-Object { ($_.Name -split '[_.]')[0..2] -join '_' } | Sort-Object Count -Descending |
            Select-Object -First 8 | ForEach-Object { "      {0,-34} {1,4}개" -f $_.Name, $_.Count }
    }
}
