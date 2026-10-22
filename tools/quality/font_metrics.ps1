# 自分で開いた校正用PPTXのテキスト幅だけを取得する。
param(
    [Parameter(Mandatory = $true)][string]$PptxPath,
    [Parameter(Mandatory = $true)][string]$Output
)
$ErrorActionPreference = "Stop"
$source = (Resolve-Path -LiteralPath $PptxPath).Path
$application = New-Object -ComObject PowerPoint.Application
try {
    $presentation = $application.Presentations.Open($source, -1, 0, 0)
    try {
        $measurements = @()
        foreach ($slide in $presentation.Slides) {
            foreach ($shape in $slide.Shapes) {
                if ($shape.Name.StartsWith("font-metric:")) {
                    $measurements += @{ id = $shape.Name; width_pt = $shape.TextFrame.TextRange.BoundWidth }
                }
            }
        }
        $measurements | ConvertTo-Json | Set-Content -LiteralPath $Output -Encoding UTF8
    }
    finally { $presentation.Close() }
}
finally {
    $application.Quit()
    [Runtime.InteropServices.Marshal]::ReleaseComObject($application) | Out-Null
}
