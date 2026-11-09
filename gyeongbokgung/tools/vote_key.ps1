# 플레이 중인 Studio 뷰포트에 키/클릭을 보낸다.
#
# 왜 필요한가 :
#   이 PC 엔 런타임 상태를 읽는 RPC 가 없고 Lua print 도 엔진 로그에 안 남는다.
#   그래서 "실제로 맵에 서 있는가" 를 확인하려면 로비에서 DEPLOY 를 눌러 봐야 한다.
#   LobbyUI 는 SPACE 를 DEPLOY 로 받는다 (LobbyUI.lua 의 키 처리).
#
# ★ PostMessage 는 UE 입력에 안 먹는다. SendInput 으로 실제 입력을 만들어야 한다.
#   그래서 커서를 잠깐 뺏는다. 사람이 쓰는 세션이라 꼭 필요할 때만 쓴다.
#
#   .\vote_key.ps1 -Click            # 뷰포트를 한 번 클릭해 포커스를 준다
#   .\vote_key.ps1 -Key Space
#   .\vote_key.ps1 -Click -Key Space -Then 2
param(
    [switch] $Click,
    [ValidateSet('Space','Escape','Tab','W','A','S','D','F9')][string] $Key,
    [double] $Then = 0,
    [int]    $Hold = 60          # 키를 누르고 있는 시간 (ms)
)
$ErrorActionPreference = 'Stop'

$sig = @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Inp {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, IntPtr e);
    [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint f, IntPtr e);
    public delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    public const uint MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004;
    public const uint KEYEVENTF_KEYUP = 0x0002;
}
'@
if (-not ('Inp' -as [type])) { Add-Type -TypeDefinition $sig }

$procIds = @(Get-Process -Name 'Sandbox-Win64-Shipping' -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
if (-not $procIds) { throw "Studio 프로세스를 못 찾았다" }

$best = $null
$cb = [Inp+EnumProc] {
    param($h, $p)
    $pid2 = 0
    [void][Inp]::GetWindowThreadProcessId($h, [ref]$pid2)
    if ($procIds -notcontains $pid2) { return $true }
    if (-not [Inp]::IsWindowVisible($h)) { return $true }
    $r = New-Object Inp+RECT
    if (-not [Inp]::GetWindowRect($h, [ref]$r)) { return $true }
    $w = $r.R - $r.L; $ht = $r.B - $r.T
    if ($w -lt 400 -or $ht -lt 300) { return $true }
    $area = $w * $ht
    if ($null -eq $script:best -or $area -gt $script:best.Area) {
        $script:best = [pscustomobject]@{ H = $h; L = $r.L; T = $r.T; W = $w; Ht = $ht; Area = $area }
    }
    return $true
}
[void][Inp]::EnumWindows($cb, [IntPtr]::Zero)
if (-not $best) { throw "Studio 창을 못 찾았다" }

# 뷰포트 중앙. 좌측 패널(약 640px)과 상단 툴바(약 260px)를 피해서 잡는다.
$vx = $best.L + [int](($best.W + 640) / 2)
$vy = $best.T + [int](($best.Ht + 260) / 2)

$saved = New-Object Inp+POINT
[void][Inp]::GetCursorPos([ref]$saved)

[void][Inp]::SetForegroundWindow($best.H)
Start-Sleep -Milliseconds 150

if ($Click) {
    Write-Host ("클릭 : ({0}, {1})" -f $vx, $vy)
    [void][Inp]::SetCursorPos($vx, $vy)
    Start-Sleep -Milliseconds 120
    [Inp]::mouse_event([Inp]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 60
    [Inp]::mouse_event([Inp]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 250
}

if ($Key) {
    $vk = switch ($Key) {
        'Space'  { 0x20 } 'Escape' { 0x1B } 'Tab' { 0x09 }
        'W' { 0x57 } 'A' { 0x41 } 'S' { 0x53 } 'D' { 0x44 } 'F9' { 0x78 }
    }
    Write-Host ("키 : {0} (0x{1:X2})" -f $Key, $vk)
    [Inp]::keybd_event([byte]$vk, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds $Hold
    [Inp]::keybd_event([byte]$vk, 0, [Inp]::KEYEVENTF_KEYUP, [IntPtr]::Zero)
}

if ($Then -gt 0) { Start-Sleep -Milliseconds ([int]($Then * 1000)) }

# 커서를 원래 자리로 돌려 놓는다. 사람이 쓰는 세션이다.
[void][Inp]::SetCursorPos($saved.X, $saved.Y)
Write-Host "완료" -ForegroundColor Green
