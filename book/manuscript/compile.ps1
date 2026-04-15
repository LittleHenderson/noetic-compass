# Requires pandoc to be installed: https://pandoc.org/installing.html
# Run this script in PowerShell to compile the manuscript into DOCX and PDF

Write-Host "Compiling DOCX via pandoc..."
pandoc book\manuscript\COMPLETE.md -o book\manuscript\COMPLETE.docx

Write-Host "Compiling PDF via pandoc..."
# Note: PDF generation usually requires a LaTeX engine (like pdflatex) or wkhtmltopdf.
pandoc book\manuscript\COMPLETE.md -o book\manuscript\COMPLETE.pdf -V geometry:margin=1in

Write-Host "Compilation finished."
