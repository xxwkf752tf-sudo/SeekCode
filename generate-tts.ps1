Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $engine.GetInstalledVoices()
foreach ($v in $voices) { Write-Host "  - $($v.VoiceInfo.Name) ($($v.VoiceInfo.Culture))" }
$zhVoice = $voices | Where-Object { $_.VoiceInfo.Culture.ToString() -match '^zh' } | Select-Object -First 1
if ($zhVoice) {
    $engine.SelectVoice($zhVoice.VoiceInfo.Name)
    Write-Host "Using voice: $($zhVoice.VoiceInfo.Name)"
}
$engine.Rate = 1
$engine.Volume = 100
$outPath = 'c:\Users\吴泓铮\Desktop\SeekCode\seekcode-promo\narration.wav'
$engine.SetOutputToWaveFile($outPath)
$text = 'SeekCode 一个让 AI 通过自然语言帮你操作电脑的 Windows 桌面助手。你不需要记住命令。把任务说给 AI 听，它自己拆解步骤、调用终端、完成操作。用大白话描述需求，AI 理解意图，自主规划并执行。三级权限控制：对话模式、标准模式、完全访问模式。高危操作自动备份，随时可中断。双模型自动切换：Flash 处理简单任务，Pro 应对复杂工程。智能判断，快人一步。API Key 本地加密存储，所有命令执行都有超时保护。你的数据，始终在你手中。SeekCode 打开 GitHub，星标这个仓库，开始你的 AI 桌面助手之旅。'
$engine.Speak($text)
$engine.SetOutputToNull()
Write-Host "Done"
$size = (Get-Item $outPath).Length
Write-Host ("Size: " + [math]::Round($size/1MB, 2) + " MB")
