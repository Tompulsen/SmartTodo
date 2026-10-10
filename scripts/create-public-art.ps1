# Original geometric illustrations for the public distribution.
# Run on Windows; generated assets are checked in and require no runtime tooling.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path $PSScriptRoot -Parent
$audioRoot = Join-Path $root 'web\public\focus-audio'
$plannerRoot = Join-Path $root 'web\public\planner'
[void][System.IO.Directory]::CreateDirectory($audioRoot)
[void][System.IO.Directory]::CreateDirectory($plannerRoot)
$names = @('quiet', 'music-box', 'forest-rain', 'rain', 'stream', 'ocean', 'wind', 'clock', 'focus', 'rest')
$colors = @('#e5edf6', '#f7e8e5', '#e1eee6', '#e1edf4', '#e5f2ef', '#deedf6', '#f5edce', '#eae8f2', '#edf3ed', '#e5eff1')
$inks = @('#627f9e', '#bc7e75', '#6b9575', '#6392ab', '#5e9b8b', '#528ca9', '#a9954a', '#8e80a9', '#729677', '#6f9d9f')
for ($index = 0; $index -lt $names.Count; $index++) {
    $bitmap = [System.Drawing.Bitmap]::new(240, 288)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $pen = [System.Drawing.Pen]::new([System.Drawing.ColorTranslator]::FromHtml($inks[$index]), 4)
    $brush = [System.Drawing.SolidBrush]::new($pen.Color)
    $white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
    try {
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
        $graphics.Clear([System.Drawing.ColorTranslator]::FromHtml($colors[$index]))
        if ($index -in @(7, 8)) {
            $graphics.FillEllipse($white, 45, 56, 150, 150)
            $graphics.DrawEllipse($pen, 45, 56, 150, 150)
            $graphics.DrawLine($pen, 120, 131, 120, 83)
            $graphics.DrawLine($pen, 120, 131, 157, 153)
            $graphics.FillEllipse($brush, 114, 125, 12, 12)
        } elseif ($index -eq 9) {
            $graphics.DrawArc($pen, 136, 109, 50, 47, 260, 205)
            $graphics.FillRectangle($white, 63, 108, 91, 67)
            $graphics.DrawRectangle($pen, 63, 108, 91, 67)
            $graphics.DrawLine($pen, 52, 190, 175, 190)
            for ($x = 81; $x -lt 150; $x += 29) {
                $graphics.DrawArc($pen, $x, 58, 13, 35, 90, 180)
            }
        } elseif ($index -eq 1) {
            $graphics.FillEllipse($white, 51, 55, 140, 140)
            $graphics.DrawLine($pen, 105, 104, 105, 167)
            $graphics.DrawLine($pen, 154, 90, 154, 150)
            $graphics.DrawLine($pen, 105, 104, 154, 90)
            $graphics.FillEllipse($brush, 79, 155, 27, 18)
            $graphics.FillEllipse($brush, 128, 139, 27, 18)
        } elseif ($index -in @(2, 3)) {
            $graphics.FillEllipse($white, 42, 70, 92, 60)
            $graphics.FillEllipse($white, 87, 45, 91, 91)
            $graphics.FillEllipse($white, 142, 81, 59, 48)
            for ($x = 69; $x -lt 190; $x += 32) {
                $graphics.DrawLine($pen, $x, 153, ($x - 10), 176)
                $graphics.DrawLine($pen, ($x + 5), 194, ($x - 5), 217)
            }
        } else {
            for ($row = 0; $row -lt 5; $row++) {
                $points = [System.Drawing.PointF[]]::new(61)
                for ($point = 0; $point -le 60; $point++) {
                    $x = 30 + $point * 3
                    $amplitude = 10 + 2 * $index
                    $y = 88 + $row * 27 + $amplitude * [Math]::Sin(($point / 60.0 * [Math]::PI * 2) + $row * .7 + $index)
                    $points[$point] = [System.Drawing.PointF]::new($x, $y)
                }
                $graphics.DrawLines($pen, $points)
            }
        }
        $pen.Width = 2
        $graphics.DrawLine($pen, 88, 252, 152, 252)
        $folder = if ($index -lt 8) { $audioRoot } else { $plannerRoot }
        $bitmap.Save((Join-Path $folder ($names[$index] + '.png')), [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $pen.Dispose()
        $brush.Dispose()
        $white.Dispose()
        $bitmap.Dispose()
    }
}
$iconBitmap = [System.Drawing.Bitmap]::new(32, 32)
$iconGraphics = [System.Drawing.Graphics]::FromImage($iconBitmap)
$iconPen = [System.Drawing.Pen]::new([System.Drawing.Color]::White, 3)
try {
    $iconGraphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $iconGraphics.Clear([System.Drawing.ColorTranslator]::FromHtml('#527c61'))
    $iconGraphics.DrawLine($iconPen, 7, 16, 13, 22)
    $iconGraphics.DrawLine($iconPen, 13, 22, 25, 9)
    $icon = [System.Drawing.Icon]::FromHandle($iconBitmap.GetHicon())
    $stream = [System.IO.File]::Create((Join-Path $root 'web\public\favicon.ico'))
    try { $icon.Save($stream) } finally { $stream.Dispose(); $icon.Dispose() }
} finally {
    $iconPen.Dispose()
    $iconGraphics.Dispose()
    $iconBitmap.Dispose()
}
Write-Output 'Created 8 audio covers, 2 focus illustrations, and favicon.'
