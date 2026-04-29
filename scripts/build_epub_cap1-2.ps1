param(
    [string]$RootDir = "$PSScriptRoot\..\capitulos_espanol",
    [string]$Title = "El amanecer de Lingao 0.1.5",
    [string]$Lang = "es",
    [string]$OutputDir = "$PSScriptRoot\..\epub",
    [string]$OutputFile = "illuminelingao_parte1y2.epub",
    [string]$CoverImage = "portada_3.jpg"
)

$ErrorActionPreference = "Stop"

$rootPath = Resolve-Path $RootDir

$frontDir = Join-Path $rootPath "00"
$part1Dir = Join-Path $rootPath "01"
$part2Dir = Join-Path $rootPath "02"

$coverPath = Join-Path $frontDir $CoverImage
if (-not (Test-Path $coverPath)) {
    throw "No se encontró la portada: $coverPath"
}

$frontMatter = @(
    (Join-Path $frontDir "000-portada.md"),
    (Join-Path $frontDir "001-legal.md")
)

foreach ($file in $frontMatter) {
    if (-not (Test-Path $file)) {
        throw "No se encontró el archivo requerido: $file"
    }
}

function Get-NormalizedFiles {
    param(
        [string]$Dir
    )

    if (-not (Test-Path $Dir)) {
        throw "No existe la carpeta: $Dir"
    }

    Get-ChildItem -Path $Dir -Filter "*.md" -File |
        Sort-Object Name |
        ForEach-Object { $_.FullName }
}

$part1Files = Get-NormalizedFiles -Dir $part1Dir
$part2Files = Get-NormalizedFiles -Dir $part2Dir

$allFiles = @()
$allFiles += $frontMatter
$allFiles += $part1Files
$allFiles += $part2Files

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$outputPath = Resolve-Path $OutputDir
$outPath = Join-Path $outputPath $OutputFile

Write-Host "Generando EPUB..."
Write-Host "RootDir: $rootPath"
Write-Host "Salida:  $outPath"
Write-Host "Archivos incluidos:"
$allFiles | ForEach-Object { Write-Host " - $_" }

$pandocArgs = @()
$pandocArgs += $allFiles
$pandocArgs += @(
    "-o", $outPath,
    "--metadata", "title=$Title",
    "--metadata", "lang=$Lang",
    "--toc",
    "--epub-cover-image=$coverPath"
)

if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
    throw "No se encontró pandoc en el PATH."
}

& pandoc @pandocArgs

if ($LASTEXITCODE -ne 0) {
    throw "Pandoc terminó con error. Código: $LASTEXITCODE"
}

Write-Host ""
Write-Host "EPUB generado correctamente:"
Write-Host $outPath