# OVERDARE Studio 창을 그대로 캡처한다.
#
# ★ 왜 화면 캡처가 아니라 PrintWindow 인가 (2026-08-26 실측, memory 에 기록됨)
#   - Studio 창은 화면 밖(-1931, 552)에 있다. 전체화면을 찍으면 엉뚱한 앱이 찍힌다.
#   - SetForegroundWindow 가 안 먹는다.
#   - game.screenshot 에는 UI 가 안 찍힌다 (3D 뷰포트만 나온다).
#   -> PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2) 만이 창 내용을 온전히 준다.
#
#   .\vote_shot.ps1                       # 창 전체
#   .\vote_shot.ps1 -Crop 0,700,1000,400  # 잘라내기 (x,y,w,h) - 출력 패널만 볼 때
#   .\vote_shot.ps1 -Zoom 3               # 확대 (NearestNeighbor)
param(
    [string] $Out  = "$env:USERPROFILE\Desktop\onlyoneshot\Screenshots\Agent",
    [int[]]  $Crop,
    [int]    $Zoom = 1,
    [string] $Name = ''
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$sig = @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class Win {
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    public delegate bool EnumProc(IntPtr h, IntPtr p);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
'@
if (-not ('Win' -as [type])) { Add-Type -TypeDefinition $sig -ReferencedAssemblies System.Drawing }

# Studio 프로세스의 창 중 가장 큰 것을 고른다. (툴팁/보조 창이 여럿 있다)
#
# ★ 프로세스 이름은 'Sandbox' 가 아니라 'Sandbox-Win64-Shipping' 이다.
#   'Sandbox' 라는 이름의 별도 프로세스도 같이 떠 있는데 그쪽엔 창이 없다.
$procIds = @(
    Get-Process -Name 'Sandbox-Win64-Shipping' -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }
)
if (-not $procIds) {
    # 이름이 또 바뀌면 창 제목으로 찾는다
    $procIds = @(Get-Process | Where-Object { $_.MainWindowTitle -like '*Unreal Editor*' } | ForEach-Object { $_.Id })
}
if (-not $procIds) { throw "Studio 프로세스를 못 찾았다 (Sandbox-Win64-Shipping)" }

$best = $null
$cb = [Win+EnumProc] {
    param($h, $p)
    $pid2 = 0
    [void][Win]::GetWindowThreadProcessId($h, [ref]$pid2)
    if ($procIds -notcontains $pid2) { return $true }
    if (-not [Win]::IsWindowVisible($h)) { return $true }
    $r = New-Object Win+RECT
    if (-not [Win]::GetWindowRect($h, [ref]$r)) { return $true }
    $w = $r.R - $r.L; $ht = $r.B - $r.T
    if ($w -lt 400 -or $ht -lt 300) { return $true }
    $len = [Win]::GetWindowTextLength($h)
    $sb = New-Object System.Text.StringBuilder ($len + 2)
    [void][Win]::GetWindowText($h, $sb, $sb.Capacity)
    $area = $w * $ht
    if ($null -eq $script:best -or $area -gt $script:best.Area) {
        $script:best = [pscustomobject]@{ H = $h; W = $w; Ht = $ht; L = $r.L; T = $r.T; Area = $area; Title = $sb.ToString() }
    }
    return $true
}
[void][Win]::EnumWindows($cb, [IntPtr]::Zero)
if (-not $best) { throw "Studio 창을 못 찾았다 (보이는 큰 창이 없다)" }
Write-Host ("창 : {0}x{1} @({2},{3})  '{4}'" -f $best.W, $best.Ht, $best.L, $best.T, $best.Title)

$bmp = New-Object System.Drawing.Bitmap $best.W, $best.Ht
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $gfx.GetHdc()
$ok = [Win]::PrintWindow($best.H, $hdc, 2)      # 2 = PW_RENDERFULLCONTENT
$gfx.ReleaseHdc($hdc); $gfx.Dispose()
if (-not $ok) { Write-Host "PrintWindow 가 false 를 돌려줬다 (그래도 이미지는 확인해 봐라)" -ForegroundColor Yellow }

$img = $bmp
if ($Crop -and $Crop.Count -eq 4) {
    $x = [Math]::Max(0, $Crop[0]); $y = [Math]::Max(0, $Crop[1])
    $w = [Math]::Min($Crop[2], $bmp.Width - $x); $h = [Math]::Min($Crop[3], $bmp.Height - $y)
    $rect = New-Object System.Drawing.Rectangle $x, $y, $w, $h
    $img = $bmp.Clone($rect, $bmp.PixelFormat)
}
if ($Zoom -gt 1) {
    $z = New-Object System.Drawing.Bitmap ($img.Width * $Zoom), ($img.Height * $Zoom)
    $g2 = [System.Drawing.Graphics]::FromImage($z)
    $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $g2.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
    $g2.DrawImage($img, 0, 0, $z.Width, $z.Height)
    $g2.Dispose()
    $img = $z
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
$stem = if ($Name) { $Name } else { 'win_' + (Get-Date -Format 'yyyyMMdd_HHmmss') }
$path = Join-Path $Out ($stem + '.png')
$img.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Host ("저장 : {0}  ({1}x{2})" -f $path, $img.Width, $img.Height) -ForegroundColor Green
$path
