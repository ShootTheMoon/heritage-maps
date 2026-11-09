# Workspace / ServerStorage 인스턴스 수를 레벨 파일에서 센다.
#
# fps 를 움직이는 유일한 레버가 Workspace 인스턴스 개수라(실측 4666=28fps, 3485=44fps)
# 맵 스왑 작업의 모든 단계에서 이 숫자가 검증 기준이 된다.
#
#   .\vote_count.ps1              # 요약
#   .\vote_count.ps1 -Detail      # 최상위 자식별 내역
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Detail
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath

# 서비스 블록의 범위를 잡는다. "InstanceType": "Workspace" 부터 짝이 맞는 닫는 중괄호까지.
function Get-ServiceSpan {
    param([string] $Text, [string] $Service)
    $m = [regex]::Match($Text, '"InstanceType":\s*"' + $Service + '"')
    if (-not $m.Success) { return $null }
    # 여는 중괄호까지 거슬러 올라간다
    $i = $m.Index; $d = 0
    while ($i -ge 0) {
        $c = $Text[$i]
        if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }
        $i--
    }
    if ($i -lt 0) { return $null }
    $j = $i; $d = 0; $inStr = $false
    while ($j -lt $Text.Length) {
        $c = $Text[$j]
        if ($inStr) {
            if ($c -eq '\') { $j += 2; continue }
            if ($c -eq '"') { $inStr = $false }
        } else {
            if ($c -eq '"') { $inStr = $true }
            elseif ($c -eq '{') { $d++ }
            elseif ($c -eq '}') { $d--; if ($d -eq 0) { return [pscustomobject]@{ Start = $i; End = $j } } }
        }
        $j++
    }
    return $null
}

# 파츠로 세는 InstanceType. fps 에 영향을 주는 것들.
$partTypes = 'Part|MeshPart|SpawnLocation|TrussPart|WedgePart|CornerWedgePart'

function Count-Parts { param([string] $Block) return ([regex]::Matches($Block, '"InstanceType":\s*"(' + $partTypes + ')"')).Count }
function Count-All   { param([string] $Block) return ([regex]::Matches($Block, '"InstanceType":\s*"')).Count }

foreach ($svc in 'Workspace', 'ServerStorage') {
    $sp = Get-ServiceSpan -Text $text -Service $svc
    if (-not $sp) { Write-Host "$svc : NOT FOUND" -ForegroundColor Red; continue }
    $block = $text.Substring($sp.Start, $sp.End - $sp.Start + 1)
    $p = Count-Parts $block
    $a = Count-All   $block
    Write-Host ("`n== {0} ==  파츠 {1}  /  전체 인스턴스 {2}" -f $svc, $p, ($a - 1)) -ForegroundColor Cyan

    if ($Detail) {
        # 최상위 LuaChildren 의 직속 자식만 훑는다 (중첩 깊이 1)
        $lc = $block.IndexOf('"LuaChildren"')
        if ($lc -lt 0) { continue }
        $arr = $block.IndexOf('[', $lc)
        $i = $arr + 1; $d = 0; $inStr = $false; $start = -1; $rows = @()
        while ($i -lt $block.Length) {
            $c = $block[$i]
            if ($inStr) {
                if ($c -eq '\') { $i += 2; continue }
                if ($c -eq '"') { $inStr = $false }
            } else {
                if ($c -eq '"') { $inStr = $true }
                elseif ($c -eq '{') { if ($d -eq 0) { $start = $i }; $d++ }
                elseif ($c -eq '}') {
                    $d--
                    if ($d -eq 0 -and $start -ge 0) {
                        $child = $block.Substring($start, $i - $start + 1)
                        $nm = [regex]::Match($child, '"Name":\s*"([^"]+)"')
                        $ty = [regex]::Match($child, '"InstanceType":\s*"([^"]+)"')
                        $rows += [pscustomobject]@{
                            Name  = if ($nm.Success) { $nm.Groups[1].Value } else { '?' }
                            Type  = if ($ty.Success) { $ty.Groups[1].Value } else { '?' }
                            Parts = Count-Parts $child
                            All   = Count-All   $child
                        }
                        $start = -1
                    }
                }
                elseif ($c -eq ']' -and $d -eq 0) { break }
            }
            $i++
        }
        $rows | Sort-Object -Property Parts -Descending |
            ForEach-Object { "  {0,-24} {1,-16} 파츠 {2,6}  전체 {3,6}" -f $_.Name, $_.Type, $_.Parts, $_.All }
        Write-Host ("  {0,-24} {1,-16} 자식 {2}" -f '(합계)', '', $rows.Count)
    }
}
