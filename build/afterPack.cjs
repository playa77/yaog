// build/afterPack.cjs
// Electron-builder afterPack hook: swap the real binary for a
// shell wrapper that passes --no-sandbox on Linux.
//
// Why: The SUID sandbox check runs before Node/Chromium flags are
// parsed, so app.commandLine.appendSwitch('no-sandbox') in main.cjs
// is too late. The only reliable fix is to pass the flag on the
// actual command line before the binary starts.

const fs = require('fs');
const path = require('path');

module.exports = async function afterPack(context) {
  if (process.platform !== 'linux') return;

  const appDir = context.appOutDir;

  // electron-builder may use productFilename, executableName, or name
  // depending on config. Check all candidates.
  const candidates = [
    context.packager.appInfo.productFilename,
    context.packager.executableName,
    context.packager.appInfo.name,
  ].filter(Boolean);

  let found = false;
  for (const execName of candidates) {
    const realBin = path.join(appDir, execName);
    if (fs.existsSync(realBin) && !fs.lstatSync(realBin).isDirectory()) {
      doSwap(realBin, path.join(appDir, execName + '.bin'), execName);
      found = true;
      break;
    }
  }

  if (!found) {
    // Last resort: look for any ELF binary in appDir root
    const files = fs.readdirSync(appDir);
    for (const f of files) {
      const fp = path.join(appDir, f);
      if (fs.lstatSync(fp).isDirectory()) continue;
      try {
        const head = Buffer.alloc(4);
        const fd = fs.openSync(fp, 'r');
        fs.readSync(fd, head, 0, 4, 0);
        fs.closeSync(fd);
        if (head[0] === 0x7f && head[1] === 0x45 && head[2] === 0x4c && head[3] === 0x46) {
          // ELF binary found
          console.log(`[afterPack] Found ELF binary by scan: ${f}`);
          doSwap(fp, fp + '.bin', f);
          found = true;
          break;
        }
      } catch {}
    }
  }

  if (!found) {
    console.error('[afterPack] Could not find Electron binary to wrap!');
  }
};

function doSwap(realBin, backupBin, execName) {
  console.log(`[afterPack] Wrapping ${execName} with --no-sandbox launcher`);

  // 1. Rename real binary → *.bin
  fs.renameSync(realBin, backupBin);

  // 2. Write shell wrapper in its place
  const wrapper = `#!/bin/bash
# YaOG launcher — passes --no-sandbox to avoid SUID sandbox issues on Linux
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/${execName}.bin" --no-sandbox "$@"
`;

  fs.writeFileSync(realBin, wrapper, { mode: 0o755 });
  console.log(`[afterPack] Created wrapper: ${realBin}`);
  console.log(`[afterPack] Real binary: ${backupBin}`);
}
