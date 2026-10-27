// Compare R64texHD's Rice port with RT64's original C++ (ref.txt) on the same inputs.
const fs = require('fs');
const rice = require(require('path').join(__dirname, '..', '..', 'app', 'core', 'rice.js'));
const internals = require(require('path').join(__dirname, '..', '..', 'app', 'core', 'rice.js'))._test;
const lines = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n');
let crcOk = 0, crcBad = 0, maxOk = 0, maxBad = 0, dxtOk = 0, dxtBad = 0;
for (let i = 0; i < lines.length; i++) {
  const l = lines[i];
  if (l.startsWith('crc ')) {
    const [, size, width, height, stride, want] = l.split(' ').map(Number);
    const [, m4, , m8] = lines[i + 1].split(' ').map(Number);
    const buf = Buffer.from(lines[i + 2], 'hex');
    rice.riceCRC32(buf, width, height, size, stride) === want ? crcOk++ : crcBad++;
    (internals.maxCI(buf, width, height, stride, true) === m4 && internals.maxCI(buf, width, height, stride, false) === m8) ? maxOk++ : maxBad++;
    i += 2;
  } else if (l.startsWith('rdxt ')) {
    const [, v, w, s, want] = l.split(' ').map(Number);
    internals.reverseDXT(v, w, s) === want ? dxtOk++ : dxtBad++;
  }
}
console.log(`RiceCRC32 ${crcOk} match, ${crcBad} differ | CalculateMaxCI ${maxOk} match, ${maxBad} differ | ReverseDXT ${dxtOk} match, ${dxtBad} differ`);
process.exit(crcBad + maxBad + dxtBad ? 1 : 0);
