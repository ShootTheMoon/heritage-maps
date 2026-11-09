# OVERDARE 레벨 스크립트 배포 헬퍼
#
# 왜 필요한가:
#   .ovdrjm 안 스크립트 노드의 "Source" 문자열이 실제로 실행되는 정본이다.
#   Lua\*.lua 파일은 Studio 가 뽑아 둔 사본이라, 파일만 고치면 반영이 보장되지 않는다.
#   그래서 파일 -> 레벨 Source 로 밀어 넣고 level.apply 하는 경로를 여기 고정한다.
#
# 한글 주의: 명령문에 한글을 직접 타이핑하면 콘솔 코드페이지에서 깨진다.
#           소스는 반드시 UTF-8 파일에서 읽어 온다 (여기서 그렇게 한다).
#
#   . .\ovdr_rpc.ps1 ; . .\ovdr_level.ps1 ; . .\ovdr_script.ps1
#   Set-OvdrScriptSource -Name 'PerfProbe' -File 'C:\...\probe.lua'
#   Publish-OvdrLevel

function ConvertTo-OvdrJsonString {
    <# Lua 소스를 .ovdrjm 의 "Source" 값에 넣을 수 있는 JSON 문자열 리터럴 본문으로 만든다.
       (양옆 따옴표는 붙이지 않는다) #>
    param([Parameter(Mandatory)][string] $Text)

    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $Text.ToCharArray()) {
        $c = [int]$ch
        switch ($ch) {
            '"'  { [void]$sb.Append('\"');  continue }
            '\'  { [void]$sb.Append('\\');  continue }
            "`n" { [void]$sb.Append('\n');  continue }
            "`r" { [void]$sb.Append('\r');  continue }
            "`t" { [void]$sb.Append('\t');  continue }
            default {
                if ($c -lt 32) { [void]$sb.Append(('\u{0:x4}' -f $c)) }
                else           { [void]$sb.Append($ch) }
            }
        }
    }
    return $sb.ToString()
}

function Get-OvdrScriptSourceSpan {
    <# 이름으로 스크립트 노드를 찾아 "Source" 값 문자열의 시작/끝 인덱스를 돌려준다.
       (따옴표 안쪽 본문 범위. 이스케이프된 따옴표를 건너뛰며 끝을 찾는다.) #>
    param(
        [Parameter(Mandatory)][string] $Text,
        [Parameter(Mandatory)][string] $Name
    )

    # "Name": "<Name>" 이 나오고 그 뒤 가까운 곳의 "Source": " 를 잡는다.
    $pat = '"Name":\s*"' + [regex]::Escape($Name) + '"'
    foreach ($m in [regex]::Matches($Text, $pat)) {
        $after = $m.Index + $m.Length
        $s = $Text.IndexOf('"Source"', $after)
        if ($s -lt 0) { continue }
        # 같은 노드인지 확인 : 이름 뒤부터 Source 사이에 다른 "Name": 이 끼면 안 된다
        # ★ $m.Index 부터 자르면 자기 자신의 "Name": 이 걸려 늘 실패한다. 반드시 이름 뒤부터.
        $between = $Text.Substring($after, $s - $after)
        if ($between -match '"Name":') { continue }

        $q = $Text.IndexOf('"', $Text.IndexOf(':', $s) + 1)
        if ($q -lt 0) { continue }
        $start = $q + 1

        $i = $start
        while ($i -lt $Text.Length) {
            $ch = $Text[$i]
            if ($ch -eq '\') { $i += 2; continue }
            if ($ch -eq '"') { return [pscustomobject]@{ Start = $start; End = $i } }
            $i++
        }
    }
    return $null
}

function Get-OvdrScriptSource {
    <# 레벨에서 스크립트 원본(이스케이프 해제된 Lua)을 꺼낸다. 백업용. #>
    param(
        [Parameter(Mandatory)][string] $Name,
        [string] $Path = (Get-OvdrLevelPath)
    )
    $text = Read-OvdrText -Path $Path
    $span = Get-OvdrScriptSourceSpan -Text $text -Name $Name
    if ($null -eq $span) { throw "script node not found: $Name" }
    $raw = $text.Substring($span.Start, $span.End - $span.Start)
    return ('"' + $raw + '"' | ConvertFrom-Json)
}

function Set-OvdrScriptSource {
    <# UTF-8 .lua 파일 내용을 지정한 스크립트 노드의 Source 로 밀어 넣는다.
       파일에 쓰기만 한다. 반영은 Publish-OvdrLevel 이 한다. #>
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][string] $File,
        [string] $Path = (Get-OvdrLevelPath)
    )
    if (-not (Test-Path $File)) { throw "lua file not found: $File" }

    $lua  = [IO.File]::ReadAllText($File, [Text.UTF8Encoding]::new($false))
    $text = Read-OvdrText -Path $Path
    $span = Get-OvdrScriptSourceSpan -Text $text -Name $Name
    if ($null -eq $span) { throw "script node not found: $Name" }

    $enc = ConvertTo-OvdrJsonString -Text $lua
    $new = $text.Substring(0, $span.Start) + $enc + $text.Substring($span.End)

    try { $null = $new | ConvertFrom-Json } catch { throw "JSON broken after edit: $($_.Exception.Message)" }

    Write-OvdrText -Text $new -Path $Path
    Write-Host ("Source replaced: {0}  ({1} chars lua -> {2} chars json)" -f $Name, $lua.Length, $enc.Length)
}

function Remove-OvdrNodeByName {
    <# 이름으로 노드 하나를 통째로 지운다.
       중괄호를 세어 노드 경계를 찾고, 앞뒤 쉼표까지 정리한다.
       (문자열 안의 중괄호에 속지 않도록 따옴표 구간을 건너뛴다.) #>
    param(
        [Parameter(Mandatory)][string] $Text,
        [Parameter(Mandatory)][string] $Name
    )

    $m = [regex]::Match($Text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { return $Text }

    # 노드 여는 중괄호까지 뒤로 간다
    $open = $Text.LastIndexOf('{', $m.Index)
    if ($open -lt 0) { throw "opening brace not found for $Name" }

    # 짝 맞는 닫는 중괄호를 찾는다
    $i = $open; $depth = 0; $inStr = $false
    while ($i -lt $Text.Length) {
        $ch = $Text[$i]
        if ($inStr) {
            if ($ch -eq '\') { $i += 2; continue }
            if ($ch -eq '"') { $inStr = $false }
        } else {
            if ($ch -eq '"') { $inStr = $true }
            elseif ($ch -eq '{') { $depth++ }
            elseif ($ch -eq '}') { $depth--; if ($depth -eq 0) { break } }
        }
        $i++
    }
    if ($depth -ne 0) { throw "unbalanced braces for $Name" }
    $close = $i

    # 뒤에 쉼표가 있으면 같이, 없으면 앞 쉼표를 같이 지운다
    $endCut = $close + 1
    $j = $endCut
    while ($j -lt $Text.Length -and [char]::IsWhiteSpace($Text[$j])) { $j++ }
    if ($j -lt $Text.Length -and $Text[$j] -eq ',') {
        $endCut = $j + 1
    } else {
        $k = $open - 1
        while ($k -ge 0 -and [char]::IsWhiteSpace($Text[$k])) { $k-- }
        if ($k -ge 0 -and $Text[$k] -eq ',') { $open = $k }
    }

    return $Text.Substring(0, $open) + $Text.Substring($endCut)
}

function New-OvdrScriptNodeJson {
    <# Script / LocalScript / ModuleScript 노드 텍스트를 만든다.
       ★ level.apply 는 속성이 빠지면 경고를 내고 기본값을 넣는다. 빠뜨리지 마라.
         (ModuleScript 에는 Enabled 가 없다 — 레벨 파일 실물에서 확인했다.) #>
    param(
        [Parameter(Mandatory)][ValidateSet('Script', 'LocalScript', 'ModuleScript')][string] $Kind,
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int]    $ObjectKey,
        [Parameter(Mandatory)][string] $File
    )
    $lua = [IO.File]::ReadAllText($File, [Text.UTF8Encoding]::new($false))
    $src = ConvertTo-OvdrJsonString -Text $lua
    $g   = New-OvdrGuid
    $tail = if ($Kind -eq 'ModuleScript') { '' } else { ",`n`t`t`t`t`t`t`"Enabled`": true" }

    return @"

					{
						"InstanceType": "$Kind",
						"ActorGuid": "$g",
						"ObjectKey": $ObjectKey,
						"Archivable": true,
						"Name": "$Name",
						"bDisableAdaptiveNetUpdateFrequency": false,
						"Mobility": "Movable",
						"Source": "$src"$tail
					},
"@
}

function New-OvdrSimpleNodeJson {
    <# RemoteEvent / SoundGroup 처럼 속성이 거의 없는 노드. #>
    param(
        [Parameter(Mandatory)][string] $Kind,
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int]    $ObjectKey,
        [string] $Extra = ''
    )
    $g = New-OvdrGuid
    if ($Extra) { $Extra = ",`n`t`t`t`t`t`t$Extra" }
    return @"

					{
						"InstanceType": "$Kind",
						"ActorGuid": "$g",
						"ObjectKey": $ObjectKey,
						"Archivable": true,
						"Name": "$Name",
						"bDisableAdaptiveNetUpdateFrequency": false,
						"Mobility": "Movable"$Extra
					},
"@
}

function Backup-OvdrLevel {
    param([string] $Path = (Get-OvdrLevelPath), [string] $Tag = '')
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    if ($Tag) { $stamp = "${stamp}_$Tag" }
    $dir = Join-Path $env:USERPROFILE "Desktop\ovdr_backup\$stamp"
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Copy-Item $Path (Join-Path $dir (Split-Path $Path -Leaf))
    Write-Host "backup: $dir"
    return $dir
}

function Publish-OvdrLevel {
    <# 디스크의 레벨을 Studio 에 반영하고 저장한다.
       level.apply 는 속성이 빠지면 success:false + 경고를 돌려준다.
       경고를 삼키지 말고 그대로 보여 준다. #>
    param([switch] $NoSave)

    $r = Invoke-OvdrRpc -Method 'level.apply' -TimeoutSec 240
    if ($r.PSObject.Properties.Name -contains 'success' -and -not $r.success) {
        Write-Host "level.apply reported problems:" -ForegroundColor Yellow
        $r.messages | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        if (@($r.messages).Count -gt 20) { Write-Host ("  ... +{0} more" -f (@($r.messages).Count - 20)) -ForegroundColor Yellow }
    } else {
        Write-Host "applied" -ForegroundColor Green
    }
    if (-not $NoSave) {
        $null = Invoke-OvdrRpc -Method 'level.save.file' -TimeoutSec 300
        Write-Host "saved" -ForegroundColor Green
    }
    return $r
}
