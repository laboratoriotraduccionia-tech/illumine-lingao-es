param(
    [string]$RootDir = "$PSScriptRoot\..\capitulos_espanol",
    [string]$Title = "El amanecer de Lingao 0.1.6",
    [string]$Lang = "es",
    [string]$OutputDir = "$PSScriptRoot\..\epub",
    [string]$OutputFile = "El_amanecer_de_Lingao.epub",
    [string]$CoverImage = "portada_3.jpg"
)

$ErrorActionPreference = "Stop"

$rootPath = Resolve-Path $RootDir

$frontDir = Join-Path $rootPath "00"
$part1Dir = Join-Path $rootPath "01"
$part2Dir = Join-Path $rootPath "02"
$part3Dir = Join-Path $rootPath "03"

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
$part3Files = Get-NormalizedFiles -Dir $part3Dir

$allFiles = @()
$allFiles += $frontMatter
$allFiles += $part1Files
$allFiles += $part2Files
$allFiles += $part3Files

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

$buildDir = Join-Path $PSScriptRoot "..\..\build_tmp"

if (-not (Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

$mergedMd = Join-Path $buildDir "illuminelingao_merged.md"

if (Test-Path $mergedMd) {
    Remove-Item $mergedMd -Force
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$writer = New-Object System.IO.StreamWriter($mergedMd, $false, $utf8NoBom)

try {
    foreach ($file in $allFiles) {
        $writer.WriteLine("")
        $writer.WriteLine("")
        $writer.WriteLine((Get-Content -Raw -Encoding UTF8 $file))
        $writer.WriteLine("")
    }
}
finally {
    $writer.Close()
}

$pandocArgs = @(
    $mergedMd,
    "-o", $outPath,
    "--metadata", "title=$Title",
    "--metadata", "lang=$Lang",
    "--toc",
    "--epub-cover-image=$coverPath"
)

& pandoc @pandocArgs

if ($LASTEXITCODE -ne 0) {
    throw "Pandoc terminó con error. Código: $LASTEXITCODE"
}

Write-Host ""
Write-Host "EPUB generado correctamente:"
Write-Host $outPath