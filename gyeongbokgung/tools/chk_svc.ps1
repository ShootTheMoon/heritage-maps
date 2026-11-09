param()
$ErrorActionPreference="Stop"
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"
$t = Read-OvdrText
foreach ($s in "ServerStorage","Workspace","ReplicatedStorage") {
  $at = Find-OvdrChildrenInsertPoint -Text $t -InstanceType $s
  "{0,-20} insertPoint={1}" -f $s, $(if ($null -ne $at) { $at } else { "NOT FOUND" })
}
