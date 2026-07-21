$ErrorActionPreference = 'Continue'

function Write-StampedHeading {
    param([Parameter(Mandatory = $true)][string]$Label)
    Write-Output ("### {0} @ {1}" -f $Label, (Get-Date).ToUniversalTime().ToString('o'))
}

Write-StampedHeading 'Python'
python --version 2>&1

Write-StampedHeading 'Docker version and daemon status'
docker version 2>&1
docker info 2>&1

Write-StampedHeading 'Docker Compose'
docker compose version 2>&1

Write-StampedHeading 'Git'
git --version 2>&1

Write-StampedHeading 'Disk'
$drive = [System.IO.DriveInfo]::new((Get-Location).Path.Substring(0, 1))
[pscustomobject]@{
    Name       = $drive.Name
    IsReady    = $drive.IsReady
    TotalBytes = $drive.TotalSize
    FreeBytes  = $drive.AvailableFreeSpace
    FreeGiB    = [math]::Round($drive.AvailableFreeSpace / 1GB, 2)
} | Format-List

Write-StampedHeading 'GitHub CLI'
gh --version 2>&1
gh auth status 2>&1
