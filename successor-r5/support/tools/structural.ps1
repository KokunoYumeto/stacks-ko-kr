param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Target,
    [int]$SourceEndLine = 0
)

$ErrorActionPreference = 'Stop'
$sourceText = [IO.File]::ReadAllText($Source)
if ($SourceEndLine -gt 0) {
    $sourceLines = Get-Content -LiteralPath $Source
    if ($SourceEndLine -gt $sourceLines.Count) {
        throw "SourceEndLine $SourceEndLine exceeds $($sourceLines.Count)"
    }
    $sourceText = (($sourceLines[0..($SourceEndLine - 1)] -join [Environment]::NewLine) + [Environment]::NewLine)
}
$targetText = [IO.File]::ReadAllText($Target)
$options = [Text.RegularExpressions.RegexOptions]::Singleline -bor
    [Text.RegularExpressions.RegexOptions]::CultureInvariant

function Captures([string]$Text, [string]$Pattern) {
    $values = [Collections.Generic.List[string]]::new()
    foreach ($match in [regex]::Matches($Text, $Pattern, $options)) {
        for ($i = 1; $i -lt $match.Groups.Count; $i++) {
            if ($match.Groups[$i].Success) {
                $values.Add($match.Groups[$i].Value)
                break
            }
        }
    }
    return @($values)
}

function Ordered-Exact($Left, $Right) {
    if ($Left.Count -ne $Right.Count) { return $false }
    for ($i = 0; $i -lt $Left.Count; $i++) {
        if ($Left[$i] -cne $Right[$i]) { return $false }
    }
    return $true
}

function First-Difference($Left, $Right) {
    $limit = [Math]::Min($Left.Count, $Right.Count)
    for ($i = 0; $i -lt $limit; $i++) {
        if ($Left[$i] -cne $Right[$i]) {
            return [ordered]@{index = $i; source = $Left[$i]; target = $Right[$i]}
        }
    }
    if ($Left.Count -ne $Right.Count) {
        return [ordered]@{index = $limit; source = $null; target = $null}
    }
    return $null
}

function Normalize-Math([string]$Text) {
    $builder = [Text.StringBuilder]::new()
    $i = 0
    while ($i -lt $Text.Length) {
        if ($i + 6 -le $Text.Length -and $Text.Substring($i, 6) -ceq '\text{') {
            $cursor = $i + 6
            $depth = 1
            while ($cursor -lt $Text.Length -and $depth -gt 0) {
                $char = $Text[$cursor]
                $escaped = $cursor -gt 0 -and $Text[$cursor - 1] -eq '\'
                if (-not $escaped) {
                    if ($char -eq '{') { $depth++ }
                    elseif ($char -eq '}') { $depth-- }
                }
                $cursor++
            }
            if ($depth -ne 0) { throw 'Unbalanced \text group' }
            [void]$builder.Append('\text{<localized>}')
            $i = $cursor
        } else {
            [void]$builder.Append($Text[$i])
            $i++
        }
    }
    return [regex]::Replace($builder.ToString(), '\s+', '')
}

function Multiset-Differences($Left, $Right) {
    $leftCounts = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
    $rightCounts = [Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
    foreach ($value in $Left) {
        if ($leftCounts.ContainsKey($value)) { $leftCounts[$value]++ }
        else { $leftCounts[$value] = 1 }
    }
    foreach ($value in $Right) {
        if ($rightCounts.ContainsKey($value)) { $rightCounts[$value]++ }
        else { $rightCounts[$value] = 1 }
    }
    $keys = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($key in $leftCounts.Keys) { [void]$keys.Add($key) }
    foreach ($key in $rightCounts.Keys) { [void]$keys.Add($key) }
    $differences = [Collections.Generic.List[object]]::new()
    foreach ($key in $keys) {
        $left = if ($leftCounts.ContainsKey($key)) { $leftCounts[$key] } else { 0 }
        $right = if ($rightCounts.ContainsKey($key)) { $rightCounts[$key] } else { 0 }
        if ($left -ne $right) {
            $differences.Add([ordered]@{formula = $key; source = $left; target = $right})
        }
    }
    return @($differences | Sort-Object { $_.formula })
}

$results = [Collections.Generic.List[object]]::new()
foreach ($check in @(
    @('labels', '\\label\{([^}]+)\}'),
    @('references', '\\(?:ref|pageref|eqref|autoref)\{([^}]+)\}|\\hyperref\[([^\]]+)\]'),
    @('citations', '\\cite(?:\[[^\]]*\])?\{([^}]+)\}'),
    @('begin', '\\begin\{([^}]+)\}'),
    @('end', '\\end\{([^}]+)\}')
)) {
    $sourceValues = Captures $sourceText $check[1]
    $targetValues = Captures $targetText $check[1]
    $results.Add([ordered]@{
        check = $check[0]
        source = $sourceValues.Count
        target = $targetValues.Count
        exact = Ordered-Exact $sourceValues $targetValues
        first_difference = First-Difference $sourceValues $targetValues
    })
}

$inlinePattern = '(?<!\\)(?<!\$)\$(?!\$)(.*?)(?<!\\)(?<!\$)\$(?!\$)'
$sourceInline = @(Captures $sourceText $inlinePattern | ForEach-Object { Normalize-Math $_ })
$targetInline = @(Captures $targetText $inlinePattern | ForEach-Object { Normalize-Math $_ })
$inlineDiff = @(Multiset-Differences $sourceInline $targetInline)
$results.Add([ordered]@{
    check = 'inline_math'
    source = $sourceInline.Count
    target = $targetInline.Count
    difference_count = $inlineDiff.Count
    first_differences = @($inlineDiff | Select-Object -First 10)
})

foreach ($check in @(
    @('display', '(?<!\$)\$\$(.*?)(?<!\$)\$\$(?!\$)'),
    @('align_star', '\\begin\{align\*\}(.*?)\\end\{align\*\}'),
    @('equation', '\\begin\{equation\}(.*?)\\end\{equation\}')
)) {
    $sourceValues = @(Captures $sourceText $check[1] | ForEach-Object { Normalize-Math $_ })
    $targetValues = @(Captures $targetText $check[1] | ForEach-Object { Normalize-Math $_ })
    $results.Add([ordered]@{
        check = $check[0]
        source = $sourceValues.Count
        target = $targetValues.Count
        exact = Ordered-Exact $sourceValues $targetValues
        first_difference = First-Difference $sourceValues $targetValues
    })
}

$targetItem = Get-Item -LiteralPath $Target
$results.Add([ordered]@{
    check = 'topology_and_hazards'
    source_items = ([regex]::Matches($sourceText, '\\item(?:\[[^\]]*\])?', $options)).Count
    target_items = ([regex]::Matches($targetText, '\\item(?:\[[^\]]*\])?', $options)).Count
    source_xymatrix = ([regex]::Matches($sourceText, '\\xymatrix\b', $options)).Count
    target_xymatrix = ([regex]::Matches($targetText, '\\xymatrix\b', $options)).Count
    target_bytes = $targetItem.Length
    target_lines = (Get-Content -LiteralPath $Target).Count
    target_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Target).Hash
    left_braces = ($targetText.ToCharArray() | Where-Object { $_ -eq '{' }).Count
    right_braces = ($targetText.ToCharArray() | Where-Object { $_ -eq '}' }).Count
    double_escaped_ref_or_cite = ([regex]::Matches($targetText, '\\\\(?:ref|cite)\{', $options)).Count
    unicode_replacement_characters = ([regex]::Matches($targetText, [char]0xFFFD, $options)).Count
    vertical_tabs = ([regex]::Matches($targetText, [char]0x0B, $options)).Count
})

$results | ConvertTo-Json -Depth 8
