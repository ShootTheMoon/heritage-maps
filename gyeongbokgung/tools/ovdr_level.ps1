# .ovdrjm 레벨 파일 조작 헬퍼
#
# 왜 텍스트 국소 삽입인가:
#   레벨 전체(14만 자)를 ConvertFrom-Json → ConvertTo-Json 으로 왕복시키면
#   숫자 표기·이스케이프·속성 순서가 미묘하게 달라져 사용자의 기존 프로젝트를
#   훼손할 수 있다. 삽입 지점만 텍스트로 건드리면 나머지는 바이트 동일하다.
#
# 인코딩: UTF-16LE + BOM (원본 그대로 유지해야 스튜디오가 읽는다)

function Get-OvdrLevelPath {
    $c = Get-Content "$env:USERPROFILE\.overdare\mcp\studios\*.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $cwd = $c.cwd -replace '/', '\'
    $f = Get-ChildItem $cwd -Filter *.ovdrjm | Select-Object -First 1
    return $f.FullName
}

function Read-OvdrText {
    param([string] $Path = (Get-OvdrLevelPath))
    return [IO.File]::ReadAllText($Path, [Text.Encoding]::Unicode)
}

function Write-OvdrText {
    param([Parameter(Mandatory)][string] $Text, [string] $Path = (Get-OvdrLevelPath))
    # UTF-16LE + BOM
    $enc = New-Object System.Text.UnicodeEncoding($false, $true)
    [IO.File]::WriteAllText($Path, $Text, $enc)
}

function New-OvdrGuid {
    return ([guid]::NewGuid().ToString('N').ToUpper())
}

function Get-OvdrKeyIndex {
    param([Parameter(Mandatory)][string] $Text)
    if ($Text -match '"MapObjectKeyIndex":\s*(\d+)') { return [int]$Matches[1] }
    throw 'MapObjectKeyIndex 를 찾지 못했다'
}

function Set-OvdrKeyIndex {
    param([Parameter(Mandatory)][string] $Text, [Parameter(Mandatory)][int] $Value)
    return [regex]::Replace($Text, '"MapObjectKeyIndex":\s*\d+', "`"MapObjectKeyIndex`": $Value", 1)
}

function Find-OvdrChildrenInsertPoint {
    <#
      지정한 InstanceType 노드의 LuaChildren 배열 여는 대괄호 바로 다음 위치를
      돌려준다. 그 노드에 LuaChildren 이 없으면 $null.
    #>
    param(
        [Parameter(Mandatory)][string] $Text,
        [Parameter(Mandatory)][string] $InstanceType,
        [string] $Name
    )
    $pat = if ($Name) {
        '"InstanceType":\s*"' + [regex]::Escape($InstanceType) + '"[\s\S]{0,4000}?"Name":\s*"' + [regex]::Escape($Name) + '"'
    } else {
        '"InstanceType":\s*"' + [regex]::Escape($InstanceType) + '"'
    }
    $m = [regex]::Match($Text, $pat)
    if (-not $m.Success) { return $null }

    $lc = $Text.IndexOf('"LuaChildren"', $m.Index)
    if ($lc -lt 0) { return $null }
    $br = $Text.IndexOf('[', $lc)
    if ($br -lt 0) { return $null }
    return $br + 1
}

function New-OvdrVector3 {
    param([double] $X, [double] $Y, [double] $Z)
    return "{ `"ObjectType`": `"Vector3`", `"X`": $X, `"Y`": $Y, `"Z`": $Z }"
}

function New-OvdrPartJson {
    <#
      원시 Part(박스) 인스턴스 JSON 텍스트를 만든다.
      좌표·크기는 전부 cm (OVERDARE 1 unit = 1 cm).
    #>
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int]    $ObjectKey,
        [Parameter(Mandatory)][double] $PX, [Parameter(Mandatory)][double] $PY, [Parameter(Mandatory)][double] $PZ,
        [double] $OX = 0, [double] $OY = 0, [double] $OZ = 0,
        [Parameter(Mandatory)][double] $SX, [Parameter(Mandatory)][double] $SY, [Parameter(Mandatory)][double] $SZ,
        [int] $R = 160, [int] $G = 160, [int] $B = 160,
        [string] $Material = 'Basic',
        [bool] $CanCollide = $true,
        [double] $Transparency = 0,
        [string] $Guid = (New-OvdrGuid)
    )
    $cc = if ($CanCollide) { 'true' } else { 'false' }
    $prof = if ($CanCollide) { 'BlockAll' } else { 'NoCollision' }
@"
{
	"InstanceType": "Part",
	"ActorGuid": "$Guid",
	"ObjectKey": $ObjectKey,
	"Archivable": true,
	"Name": "$Name",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Anchored": true,
	"CanCollide": $cc,
	"CanTouch": true,
	"Transparency": $Transparency,
	"CastShadow": false,
	"Locked": false,
	"CanClimb": false,
	"IsTouchingBodyPart": false,
	"CollisionProfile": "$prof",
	"MaterialVariant": "",
	"TraceGroupNameString": "None",
	"UnitExtent": $(New-OvdrVector3 50 50 -50),
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 $PX $PY $PZ), "Orientation": $(New-OvdrVector3 $OX $OY $OZ) },
	"Size": $(New-OvdrVector3 $SX $SY $SZ),
	"AssemblyLinearVelocity": $(New-OvdrVector3 0 0 0),
	"BrickColor": { "ObjectType": "BrickColor", "Number": 194, "r": $R, "g": $G, "b": $B, "Name": "Medium stone grey" },
	"Color": { "ObjectType": "Color3", "R": $R, "G": $G, "B": $B },
	"CurrentPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Material": "$Material",
	"AssemblyRootPart": { "Value": -1, "Type": "None" },
	"Shape": "Block"
}
"@
}

function New-OvdrMeshPartJson {
    <#
      MeshPart 인스턴스 JSON. MeshId 는 "ovdrassetid://NNNN" 형식.
      UnitExtent 는 스튜디오가 메시에서 다시 계산하므로 자리표시자를 넣는다 —
      적용 후 읽어보면 임포터가 메시를 어떻게 해석했는지가 그대로 드러난다.

      MeshId 를 처음부터 함께 지정할 때 Studio 는 자리표시자 UnitExtent(±50)의
      현재 배율을 실제 메시에도 유지한다. 따라서 원본 메시 크기 그대로는
      Size 100, 전체 배율 S 는 Size 100*S 를 모든 축에 넣어야 한다.
      실제 bbox 크기를 Size 에 직접 넣으면 메시 바운드가 두 번 곱해진다.
    #>
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int]    $ObjectKey,
        [Parameter(Mandatory)][string] $MeshId,
        [string] $TextureId = '',
        [double] $PX = 0, [double] $PY = 0, [double] $PZ = 0,
        [double] $OX = 0, [double] $OY = 0, [double] $OZ = 0,
        [double] $SX = 100, [double] $SY = 100, [double] $SZ = 100,
        [int] $R = 200, [int] $G = 200, [int] $B = 200,
        [string] $Material = 'Basic',
        [bool] $CanCollide = $false,
        [bool] $DoubleSided = $false,
        [bool] $CastShadow = $true,
        [double] $Transparency = 0,
        [string] $Guid = (New-OvdrGuid)
    )
    $cc   = if ($CanCollide)   { 'true' } else { 'false' }
    $ds   = if ($DoubleSided)  { 'true' } else { 'false' }
    $cs   = if ($CastShadow)   { 'true' } else { 'false' }
    $prof = if ($CanCollide)   { 'BlockAll' } else { 'NoCollision' }
@"
{
	"InstanceType": "MeshPart",
	"ActorGuid": "$Guid",
	"ObjectKey": $ObjectKey,
	"Archivable": true,
	"Name": "$Name",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Anchored": true,
	"CanCollide": $cc,
	"CanTouch": true,
	"Transparency": $Transparency,
	"CastShadow": $cs,
	"Locked": false,
	"CanClimb": false,
	"IsTouchingBodyPart": false,
	"CollisionProfile": "$prof",
	"MaterialVariant": "",
	"TraceGroupNameString": "None",
	"UnitExtent": $(New-OvdrVector3 50 50 -50),
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 $PX $PY $PZ), "Orientation": $(New-OvdrVector3 $OX $OY $OZ) },
	"Size": $(New-OvdrVector3 $SX $SY $SZ),
	"AssemblyLinearVelocity": $(New-OvdrVector3 0 0 0),
	"BrickColor": { "ObjectType": "BrickColor", "Number": 194, "r": $R, "g": $G, "b": $B, "Name": "Medium stone grey" },
	"Color": { "ObjectType": "Color3", "R": $R, "G": $G, "B": $B },
	"CurrentPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Material": "$Material",
	"AssemblyRootPart": { "Value": -1, "Type": "None" },
	"DoubleSided": $ds,
	"MeshId": "$MeshId",
	"TextureId": "$TextureId",
	"EnableMeshShadowDetails": false,
	"MeshShadowDetailLevel": "Low"
}
"@
}

function New-OvdrModelJson {
    <# 빈 Model 컨테이너. 자식은 나중에 LuaChildren 에 삽입한다. #>
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int]    $ObjectKey,
        [string] $Guid = (New-OvdrGuid)
    )
@"
{
	"InstanceType": "Model",
	"ActorGuid": "$Guid",
	"ObjectKey": $ObjectKey,
	"Archivable": true,
	"Name": "$Name",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"LuaChildren": [
	]
}
"@
}

function Add-OvdrInstances {
    <#
      완성된 인스턴스 JSON 텍스트들을 지정 부모의 LuaChildren 맨 앞에 삽입하고
      MapObjectKeyIndex 를 올린다. 파일을 쓰지는 않고 새 텍스트를 돌려준다.
    #>
    param(
        [Parameter(Mandatory)][string]   $Text,
        [Parameter(Mandatory)][string[]] $InstanceJson,
        [string] $ParentType = 'Workspace',
        [string] $ParentName,
        [Parameter(Mandatory)][int] $NewKeyIndex
    )
    $at = Find-OvdrChildrenInsertPoint -Text $Text -InstanceType $ParentType -Name $ParentName
    if ($null -eq $at) { throw "$ParentType $ParentName 의 LuaChildren 을 찾지 못했다" }

    # 배열이 비어 있으면(다음 비공백이 ']') 후행 쉼표를 붙이면 안 된다.
    $k = $at
    while ($k -lt $Text.Length -and $Text[$k] -match '[\s\r\n]') { $k++ }
    $isEmpty = ($k -lt $Text.Length -and $Text[$k] -eq ']')

    $blob = ($InstanceJson -join ",`r`n")
    if (-not $isEmpty) { $blob += ',' }
    $out = $Text.Substring(0, $at) + "`r`n" + $blob + $Text.Substring($at)
    return (Set-OvdrKeyIndex -Text $out -Value $NewKeyIndex)
}

function Remove-OvdrInstancesByName {
    <#
      이름 접두사로 인스턴스를 제거한다. 구조 파싱 없이 중괄호 균형만 세어
      해당 객체 블록을 잘라낸다 (삽입의 역연산).
    #>
    param(
        [Parameter(Mandatory)][string] $Text,
        [Parameter(Mandatory)][string] $NamePrefix
    )
    $out = $Text
    while ($true) {
        $m = [regex]::Match($out, '"Name":\s*"' + [regex]::Escape($NamePrefix) + '[^"]*"')
        if (-not $m.Success) { break }

        # 이 Name 을 품은 객체의 여는 중괄호를 뒤로 훑어 찾는다
        $start = $out.LastIndexOf('{', $m.Index)
        $depth = 0
        $end = -1
        for ($i = $start; $i -lt $out.Length; $i++) {
            if ($out[$i] -eq '{') { $depth++ }
            elseif ($out[$i] -eq '}') { $depth--; if ($depth -eq 0) { $end = $i; break } }
        }
        if ($end -lt 0) { throw '객체 블록의 끝을 찾지 못했다' }

        # 뒤따르는 쉼표까지 삼킨다 (없으면 앞의 쉼표를)
        $tail = $end + 1
        while ($tail -lt $out.Length -and $out[$tail] -match '[\s\r\n]') { $tail++ }
        if ($tail -lt $out.Length -and $out[$tail] -eq ',') { $tail++ }
        else {
            $head = $start - 1
            while ($head -ge 0 -and $out[$head] -match '[\s\r\n]') { $head-- }
            if ($head -ge 0 -and $out[$head] -eq ',') { $start = $head }
        }
        $out = $out.Substring(0, $start) + $out.Substring($tail)
    }
    return $out
}
