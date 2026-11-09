# KRM_Palace 를 백업본과 대조한다. + ObjectKey 중복 검사.
#
# 「셸이 또 안 보인다」가 내 작업(경기구역 벽 4장 추가) 때문인지 가리려는 것이다.
# 벽 4장 말고 달라진 게 없으면 내 작업은 무죄다.
param(
    [Parameter(Mandatory)][string] $Backup,     # 백업 .ovdrjm 경로
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm"
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

function Get-Krm {
    param([string] $Path)
    $text = Read-OvdrText -Path $Path
    $m = [regex]::Match($text, '"Name":\s*"KRM_Palace"')
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

function Get-Children {
    param([string] $Blk)
    $lc = $Blk.IndexOf('"LuaChildren"'); $arr = $Blk.IndexOf('[', $lc)
    $k = $arr + 1; $d = 0; $s = $false; $start = -1; $out = @()
    while ($k -lt $Blk.Length) {
        $c = $Blk[$k]
        if ($s) { if ($c -eq '\') { $k += 2; continue }; if ($c -eq '"') { $s = $false } }
        else {
            if ($c -eq '"') { $s = $true }
            elseif ($c -eq '{') { if ($d -eq 0) { $start = $k }; $d++ }
            elseif ($c -eq '}') {
                $d--
                if ($d -eq 0 -and $start -ge 0) {
                    $ch = $Blk.Substring($start, $k - $start + 1)
                    $nm = [regex]::Match($ch, '"InstanceType":\s*"([^"]+)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                    $ok = [regex]::Match($ch, '"ObjectKey":\s*(\d+)')
                    if ($nm.Success) {
                        $out += [pscustomobject]@{
                            Name = $nm.Groups[2].Value; Type = $nm.Groups[1].Value
                            Key = $(if ($ok.Success) { [int]$ok.Groups[1].Value } else { -1 })
                            # ObjectKey / ActorGuid 를 뺀 본문. 이것만 비교하면 내용 변화를 본다.
                            Body = ($ch -replace '"ObjectKey":\s*\d+', '' -replace '"ActorGuid":\s*"[^"]*"', '')
                        }
                    }
                    $start = -1
                }
            }
            elseif ($c -eq ']' -and $d -eq 0) { break }
        }
        $k++
    }
    return $out
}

$curBlk = Get-Krm -Path $LevelPath
$bakBlk = Get-Krm -Path $Backup
if (-not $curBlk) { throw "현재 레벨에 KRM_Palace 가 없다" }
if (-not $bakBlk) { throw "백업에 KRM_Palace 가 없다" }

$cur = Get-Children -Blk $curBlk
$bak = Get-Children -Blk $bakBlk
Write-Host ("현재 {0} 개 / 백업 {1} 개" -f $cur.Count, $bak.Count) -ForegroundColor Cyan

# ObjectKey 중복 (엔진이 인스턴스를 덮어쓸 수 있다)
foreach ($set in @(@{N='현재'; L=$cur}, @{N='백업'; L=$bak})) {
    $dup = $set.L | Group-Object Key | Where-Object { $_.Count -gt 1 -and $_.Name -ne '-1' }
    if ($dup) {
        Write-Host ("  {0} : ObjectKey 중복 {1} 건" -f $set.N, $dup.Count) -ForegroundColor Red
        $dup | Select-Object -First 5 | ForEach-Object { "      키 {0} : {1}" -f $_.Name, (($_.Group.Name) -join ', ') }
    } else {
        Write-Host ("  {0} : ObjectKey 중복 없음" -f $set.N) -ForegroundColor Green
    }
}

# 이름 기준 차집합
$curN = @{}; $cur | ForEach-Object { $curN[$_.Name] = $_ }
$bakN = @{}; $bak | ForEach-Object { $bakN[$_.Name] = $_ }
$added   = @($cur | Where-Object { -not $bakN.ContainsKey($_.Name) })
$removed = @($bak | Where-Object { -not $curN.ContainsKey($_.Name) })
Write-Host ("`n추가된 것 {0} 개 : {1}" -f $added.Count, (($added.Name) -join ', '))
Write-Host ("없어진 것 {0} 개 : {1}" -f $removed.Count, (($removed.Name) -join ', '))

# 양쪽에 다 있는 것 중 내용이 달라진 것
$changed = @()
foreach ($n in $curN.Keys) {
    if ($bakN.ContainsKey($n)) {
        if ($curN[$n].Body -cne $bakN[$n].Body) { $changed += $n }
    }
}
Write-Host ("내용이 달라진 것 {0} 개" -f $changed.Count) -ForegroundColor $(if ($changed.Count) { 'Red' } else { 'Green' })
$changed | Select-Object -First 12 | ForEach-Object { "      $_" }
