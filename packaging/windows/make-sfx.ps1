# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
<#
.SYNOPSIS
  Builds the one-file portable download: a 7-Zip GUI self-extractor that asks
  the user where to extract the BrowserX folder. It does not run anything after
  extracting and never extracts to a temporary or hidden location.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)] [string] $Zip,        # dist\BrowserX-<ver>-win-x64-portable.zip
  [Parameter(Mandatory)] [string] $SevenZip,   # path to 7z.exe
  [Parameter(Mandatory)] [string] $SfxModule   # path to 7-Zip's GUI module 7z.sfx
)
$ErrorActionPreference = 'Stop'

if ((Split-Path $SfxModule -Leaf) -ne '7z.sfx') {
  throw 'Use the GUI SFX module 7z.sfx (asks for a destination), not an installer/temp SFX.'
}
$zipItem = Get-Item $Zip
$work = Join-Path $zipItem.DirectoryName 'sfx-work'
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory $work | Out-Null

Expand-Archive -Path $zipItem.FullName -DestinationPath $work
$archive = Join-Path $work 'payload.7z'
& $SevenZip a -t7z -mx=9 $archive (Join-Path $work 'BrowserX')
if ($LASTEXITCODE -ne 0) { throw '7z failed' }

$out = Join-Path $zipItem.DirectoryName ($zipItem.BaseName + '.exe')
$sfx = [IO.File]::ReadAllBytes((Resolve-Path $SfxModule))
$payload = [IO.File]::ReadAllBytes($archive)
$stream = [IO.File]::Create($out)
try { $stream.Write($sfx, 0, $sfx.Length); $stream.Write($payload, 0, $payload.Length) }
finally { $stream.Dispose() }
Remove-Item $work -Recurse -Force
Write-Host "Created $out (sign it next with sign.ps1)"
