# Studio 창의 지정 좌표를 클릭한다. (창 기준 좌표. 화면 좌표가 아니다)
#
# 출력(Output) 패널을 열어 Lua print 를 읽으려고 만들었다.
# 이 PC 엔 런타임 상태를 읽는 RPC 가 없고 Lua print 는 엔진 로그에도 안 남는다.
#
#   .\vote_click.ps1 -X 588 -Y 41           # View 메뉴
#   .\vote_click.ps1 -X 588 -Y 41 -Shot     # 클릭하고 바로 캡처
param(
    [Parameter(Mandatory)][int] $X,
    [Parameter(Mandatory)][int] $Y,
    [double] $Wait = 0.6,
    [switch] $Shot,
    [string] $Name = ''
)
$ErrorActionPreference = 'Stop'

$sig = @'
using System;
using System.Runtime.InteropServices;
public class Clk {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, IntPtr e);
    public delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    public const uint DOWN = 0x0002, UP = 0x0004;
}
'@
if (-not ('Clk' -as [type])) { Add-Type -TypeDefinition $sig }

$procIds = @(Get-Process -Name 'Sandbox-Win64-Shipping' -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
if (-not $procIds) { throw "Studio 프로세스를 못 찾았다" }

$best = $null
$cb = [Clk+EnumProc] {
    param($h, $p)
    $pid2 = 0
    [void][Clk]::GetWindowThreadProcessId($h, [ref]$pid2)
    if ($procIds -notcontains $pid2) { return $true }
    if (-not [Clk]::IsWindowVisible($h)) { return $true }
    $r = New-Object Clk+RECT
    if (-not [Clk]::GetWindowRect($h, [ref]$r)) { return $true }
    $w = $r.R - $r.L; $ht = $r.B - $r.T
    if ($w -lt 400 -or $ht -lt 300) { return $true }
    $area = $w * $ht
    if ($null -eq $script:best -or $area -gt $script:best.Area) {
        $script:best = [pscustomobject]@{ H = $h; L = $r.L; T = $r.T; Area = $area }
    }
    return $true
}
[void][Clk]::EnumWindows($cb, [IntPtr]::Zero)
if (-not $best) { throw "Studio 창을 못 찾았다" }

$saved = New-Object Clk+POINT
[void][Clk]::GetCursorPos([ref]$saved)

[void][Clk]::SetForegroundWindow($best.H)
Start-Sleep -Milliseconds 200
$sx = $best.L + $X
$sy = $best.T + $Y
Write-Host ("클릭 : 창({0},{1}) -> 화면({2},{3})" -f $X, $Y, $sx, $sy)
[void][Clk]::SetCursorPos($sx, $sy)
Start-Sleep -Milliseconds 150
[Clk]::mouse_event([Clk]::DOWN, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds 60
[Clk]::mouse_event([Clk]::UP, 0, 0, 0, [IntPtr]::Zero)
Start-Sleep -Milliseconds ([int]($Wait * 1000))

if ($Shot) {
    $stem = if ($Name) { $Name } else { 'click_' + (Get-Date -Format 'HHmmss') }
    & "$PSScriptRoot\vote_shot.ps1" -Name $stem | Out-Null
    Write-Host "캡처 : $stem.png"
}

# 커서를 원래 자리로. 사람이 쓰는 세션이다.
[void][Clk]::SetCursorPos($saved.X, $saved.Y)
