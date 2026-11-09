# OVERDARE Studio RPC 헬퍼
#
# 포트 13377 은 HTTP 가 아니라 raw TCP 위의 줄바꿈 구분 JSON-RPC 다.
# (HTTP 로 붙으면 "protocol violation. Section=ResponseStatusLine" 이 난다.)
# 인증은 없다 — 로컬 스튜디오 프로세스가 직접 듣는다.
#
#   . .\ovdr_rpc.ps1
#   Invoke-OvdrRpc level.browse @{ depth = 1 }

$script:OvdrHost = '127.0.0.1'
$script:OvdrPort = 13377

function Invoke-OvdrRpc {
    param(
        [Parameter(Mandatory = $true)][string] $Method,
        $Params = @{},
        [int] $TimeoutSec = 60,
        [switch] $Raw
    )

    $req = @{ jsonrpc = '2.0'; id = 1; method = $Method; params = $Params } |
           ConvertTo-Json -Depth 40 -Compress

    $cli = New-Object System.Net.Sockets.TcpClient
    try {
        $cli.Connect($script:OvdrHost, $script:OvdrPort)
        $stream = $cli.GetStream()
        $stream.ReadTimeout = $TimeoutSec * 1000

        $out = [Text.Encoding]::UTF8.GetBytes($req + "`n")
        $stream.Write($out, 0, $out.Length)
        $stream.Flush()

        # 응답은 한 줄(개행 종료). UTF-8 멀티바이트가 읽기 경계에서 쪼개질 수
        # 있으므로 바이트로 모은 뒤 한 번에 디코딩한다.
        $ms  = New-Object System.IO.MemoryStream
        $buf = New-Object byte[] 65536
        while ($true) {
            $n = $stream.Read($buf, 0, $buf.Length)
            if ($n -le 0) { break }
            $ms.Write($buf, 0, $n)
            if ($buf[0..($n - 1)] -contains 0x0A) { break }
        }
        $txt = [Text.Encoding]::UTF8.GetString($ms.ToArray()).Trim()
    }
    finally {
        $cli.Close()
    }

    if ($Raw) { return $txt }
    if (-not $txt) { throw "RPC $Method : 빈 응답" }

    $obj = $txt | ConvertFrom-Json
    if ($obj.PSObject.Properties.Name -contains 'error' -and $null -ne $obj.error) {
        throw "RPC $Method 실패 [$($obj.error.code)] $($obj.error.message)"
    }
    return $obj.result
}

function Test-OvdrMethod {
    <#
      메서드가 존재하는지만 본다. 존재하지 않으면 -32601(method not found)
      계열로 떨어지고, 존재하면 파라미터 오류이거나 성공한다.
    #>
    param([Parameter(Mandatory = $true)][string] $Method)
    try {
        $null = Invoke-OvdrRpc -Method $Method -TimeoutSec 10
        return [pscustomobject]@{ method = $Method; exists = $true; note = 'OK' }
    } catch {
        $m = $_.Exception.Message
        if ($m -match '-32601' -or $m -match 'not found' -or $m -match 'Unknown method') {
            return [pscustomobject]@{ method = $Method; exists = $false; note = 'no such method' }
        }
        return [pscustomobject]@{ method = $Method; exists = $true; note = $m }
    }
}

function Get-OvdrProject {
    $c = Get-Content "$env:USERPROFILE\.overdare\mcp\studios\*.json" -Raw -Encoding UTF8 |
         ConvertFrom-Json
    [pscustomobject]@{
        cwd       = $c.cwd -replace '/', '\'
        projectId = $c.projectId
        port      = $c.studioPort
    }
}
