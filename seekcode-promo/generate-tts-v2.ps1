$outDir = "c:\Users\吴泓铮\Desktop\SeekCode\seekcode-promo"
$ffmpeg = Join-Path $outDir "ffmpeg.exe"

Add-Type -AssemblyName System.Speech

function Generate-TTS($text, $file) {
    $wavPath = Join-Path $outDir "tts-temp.wav"
    $mp3Path = Join-Path $outDir $file
    $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $speak.SelectVoice("Microsoft Huihui Desktop")
    $speak.Rate = 1
    $speak.Volume = 100
    $speak.SetOutputToWaveFile($wavPath)
    $speak.Speak($text)
    $speak.Dispose()
    & $ffmpeg -i $wavPath -ar 24000 -ac 1 -c:a libmp3lame -q:a 4 $mp3Path -y 2>$null
    Remove-Item $wavPath -Force
    Write-Output "Generated: $file"
}

Generate-TTS "你的电脑，让AI来操作！三秒钟出结果，就问你神不神奇？" "tts-scene1.mp3"
Generate-TTS "别再背命令了，说人话就行，AI替你执行。" "tts-scene2.mp3"
Generate-TTS "大白话就能用，AI秒懂你的意思，一气呵成给你搞定。" "tts-scene3.mp3"
Generate-TTS "三级权限你自己定，高危操作还自动备份，不怕你后悔。" "tts-scene4.mp3"
Generate-TTS "两个模式自动切换，简单的用Flash秒回，复杂的交给Pro深度思考。" "tts-scene5.mp3"
Generate-TTS "密码存在本地，随时能停手。GitHub点个Star就能用，快去试试吧！" "tts-scene6.mp3"

Write-Output "All TTS done!"
