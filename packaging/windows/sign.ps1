# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
<#
.SYNOPSIS
  Authenticode-signs every .exe/.dll under the given paths, then verifies them.

.DESCRIPTION
  Runs only in the protected release environment. The certificate is selected
  by thumbprint from the machine/user store (HSM-backed or cloud signing such as
  Azure Trusted Signing via its signtool dlib). No key material is ever stored
  in this repository.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string[]] $Path,
  [Parameter(Mandatory)] [string] $CertThumbprint,
  [string] $TimestampUrl = 'http://timestamp.digicert.com',
  [string] $SignTool = 'signtool.exe',
  [string] $Description = 'Browser-x'
)
$ErrorActionPreference = 'Stop'

$files = foreach ($p in $Path) {
  if (Test-Path $p -PathType Leaf) { Get-Item $p }
  else { Get-ChildItem -Path $p -Recurse -File -Include *.exe, *.dll }
}
if (-not $files) { throw "No PE files found under: $($Path -join ', ')" }

foreach ($f in $files) {
  & $SignTool sign /fd sha256 /sha1 $CertThumbprint /tr $TimestampUrl /td sha256 /d $Description $f.FullName
  if ($LASTEXITCODE -ne 0) { throw "signing failed: $($f.FullName)" }
}
foreach ($f in $files) {
  & $SignTool verify /pa /q $f.FullName
  if ($LASTEXITCODE -ne 0) { throw "verification failed: $($f.FullName)" }
}
Write-Host "Signed and verified $($files.Count) file(s)."
