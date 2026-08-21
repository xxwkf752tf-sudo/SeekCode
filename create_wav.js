const fs = require('fs');
const path = 'c:/Users/吴泓铮/Desktop/SeekCode/seekcode-promo/narration.wav';
const sr = 24000, dur = 58, ch = 1, bps = 16;
const byteRate = sr * ch * (bps / 8);
const blockAlign = ch * (bps / 8);
const dataSize = sr * dur * blockAlign;
const buf = Buffer.alloc(44 + dataSize);
let off = 0;
const w = (s) => { buf.write(s, off); off += s.length; };
const wb = (n, bytes) => { for (let i = bytes - 1; i >= 0; i--) buf.writeUInt8((n >> (i * 8)) & 0xff, off++); };
w('RIFF'); wb(36 + dataSize, 4); w('WAVE');
w('fmt '); wb(16, 4); wb(1, 2); wb(ch, 2); wb(sr, 4); wb(byteRate, 4); wb(blockAlign, 2); wb(bps, 2);
w('data'); wb(dataSize, 4);
// silence
for (let i = 0; i < dataSize; i++) buf[44 + i] = 0;
fs.writeFileSync(path, buf);
console.log('Created silent WAV:', buf.length, 'bytes');
