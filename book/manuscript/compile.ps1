# Requires pandoc to be installed: https://pandoc.org/installing.html
# Run this script in PowerShell to compile the canonical manuscript into review formats.
# Canonical source for exports: book/manuscript/FULL_MANUSCRIPT.md

$ErrorActionPreference = "Stop"

$manuscriptDir = $PSScriptRoot
$bookDir = Split-Path -Parent $manuscriptDir
$manuscript = Join-Path $manuscriptDir "FULL_MANUSCRIPT.md"
$docxOutput = Join-Path $bookDir "Thinking_in_Cognitive_Architecture_FINAL.docx"
$draftPdfOutput = Join-Path $manuscriptDir "Thinking_in_Cognitive_Architecture_DRAFT.pdf"

if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    throw "pandoc is not installed or not on PATH."
}

if (-not (Test-Path $manuscript)) {
    throw "Canonical manuscript not found: $manuscript"
}

Write-Host "Compiling canonical DOCX via pandoc..."
pandoc $manuscript -o $docxOutput

Write-Host "Compiling draft PDF via pandoc..."
# Note: print-ready PDF and EPUB are built with book-formatting/build.bat.
pandoc $manuscript -o $draftPdfOutput -V geometry:margin=1in

Write-Host "Compilation finished."
Write-Host "DOCX: $docxOutput"
Write-Host "Draft PDF: $draftPdfOutput"
Write-Host "Print-ready PDF/EPUB: book-formatting\\build.bat"
