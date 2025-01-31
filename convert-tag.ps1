# ========== CONFIGURABLE SETTINGS ==========
$ToolText = "HandBrake 1.9.0 2024120100"  # Text to be written to the Tool tag
$mp4tagPath = "C:\Tools\mp4tag\mp4tag.exe" # Path to the mp4tag executable
# ===========================================

$script:terminateScript = $false

function ConvertAndTagMP4 {
    param (
        [string]$sourceFolder,
        [string]$destinationFolder
    )

    # Ensure the source folder exists
    if (-not (Test-Path -Path $sourceFolder)) {
        Write-Error "Source folder does not exist: $sourceFolder"
        return
    }

    # Ensure the destination folder exists or create it
    if (-not (Test-Path -Path $destinationFolder)) {
        New-Item -ItemType Directory -Path $destinationFolder | Out-Null
        Write-Host "Destination folder created: $destinationFolder"
    }

    # Initialize lists to track unprocessed files
    $unsupportedFiles = @()
    $failedTaggingFiles = @()
    $failedConversions = @()

    while ($true) {
        # Get a list of all files in the source folder
        $allFiles = Get-ChildItem -Path $sourceFolder -Recurse
        $sourceFiles = $allFiles | Where-Object { $_.Extension -in '.mkv', '.webm', '.avi' }
        $unsupportedFiles += $allFiles | Where-Object { $_.Extension -notin '.mkv', '.webm', '.avi', '.mp4' }

        # Convert non-MP4 files to MP4
        $conversionMade = $false
        foreach ($file in $sourceFiles) {
            if ($script:terminateScript) { break }

            $outputFilePath = Join-Path -Path $sourceFolder -ChildPath ($file.BaseName + ".mp4")
            if (Test-Path -Path $outputFilePath) {
                Write-Host "Skipping existing file: $outputFilePath"
                continue
            }

            $ffmpegCommand = "ffmpeg -fflags +genpts -i `"$($file.FullName)`" -c copy `"$outputFilePath`""
            try {
                Invoke-Expression $ffmpegCommand
                if ($LASTEXITCODE -ne 0) {
                    throw "FFmpeg encountered an error converting: $($file.FullName)"
                }

                # Verify the output file using ffprobe
                $ffprobeCommand = "ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 `"$outputFilePath`""
                $ffprobeResult = Invoke-Expression $ffprobeCommand 2>&1

                if (-not $ffprobeResult) {
                    Write-Host "Error: Verification failed for '$outputFilePath'. Keeping original file." -ForegroundColor Red
                    $failedConversions += $file
                    Remove-Item -LiteralPath $outputFilePath -Force
                    continue
                }

                # If ffprobe is successful, delete the original file
                Remove-Item -LiteralPath $file.FullName -Force
                Write-Host "Converted and removed original file: $($file.Name)"
                $conversionMade = $true
            } catch {
                Write-Error "Failed to convert file: $($file.FullName)"
                $failedConversions += $file
            }
        }

        # Restart the loop if any files were converted
        if ($conversionMade) {
            Write-Host "Rescanning the folder for newly converted files..."
            continue
        } else {
            break
        }
    }

    # Tag all MP4 files (excluding failed conversions)
    $allMP4Files = Get-ChildItem -Path $sourceFolder -Filter "*.mp4" -File
    foreach ($file in $allMP4Files) {
        $outputFile = Join-Path -Path $destinationFolder -ChildPath $file.Name
        $escapedToolText = "`"$ToolText`"" # Escape quotes for the Tool text
        $command = "$mp4tagPath --set Tool:S:$escapedToolText `"$($file.FullName)`" `"$outputFile`""

        Write-Host "Tagging file: $($file.FullName)"
        try {
            Invoke-Expression $command
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Error: Failed to write the Tool tag for '$($file.Name)'." -ForegroundColor Red
                $failedTaggingFiles += $file
            } else {
                Write-Host "Success: Tagged file saved to '$outputFile'." -ForegroundColor Green
            }
        } catch {
            Write-Error "Failed to tag file: $($file.FullName)"
            $failedTaggingFiles += $file
        }
    }

    # Organize files into subfolders of 99 files each
    $allTaggedFiles = Get-ChildItem -Path $destinationFolder -Filter "*.mp4" -File
    if ($allTaggedFiles.Count -gt 99) {
        Write-Host "Organizing files into folders of 99..."

        $folderIndex = 1
        $currentFolder = Join-Path -Path $destinationFolder -ChildPath $folderIndex
        New-Item -ItemType Directory -Path $currentFolder | Out-Null

        $fileCount = 0
        foreach ($file in $allTaggedFiles) {
            if ($script:terminateScript) { break }

            if ($fileCount -ge 99) {
                $folderIndex++
                $currentFolder = Join-Path -Path $destinationFolder -ChildPath $folderIndex
                New-Item -ItemType Directory -Path $currentFolder | Out-Null
                $fileCount = 0
            }

            Move-Item -LiteralPath $file.FullName -Destination $currentFolder
            Write-Host "Moved file: $($file.Name) to folder: $folderIndex"
            $fileCount++
        }
    } else {
        Write-Host "Less than 100 files; skipping folder organization."
    }

    # Print summary of unprocessed files
    if ($unsupportedFiles.Count -gt 0) {
        Write-Host "The following unsupported files were not processed:" -ForegroundColor Yellow
        $unsupportedFiles | ForEach-Object { Write-Host $_.FullName }
    }

    if ($failedConversions.Count -gt 0) {
        Write-Host "The following files failed verification and were not deleted:" -ForegroundColor Yellow
        $failedConversions | ForEach-Object { Write-Host $_.FullName }
    }

    if ($failedTaggingFiles.Count -gt 0) {
        Write-Host "The following files failed tagging:" -ForegroundColor Yellow
        $failedTaggingFiles | ForEach-Object { Write-Host $_.FullName }
    }

    Write-Host "Script completed successfully."
}

# Example usage
$sourceFolder = Read-Host "Enter the source folder path"
$destinationFolder = Read-Host "Enter the destination folder path"
ConvertAndTagMP4 -sourceFolder $sourceFolder -destinationFolder $destinationFolder
