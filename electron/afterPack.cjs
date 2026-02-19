const fs = require('fs');
const path = require('path');

exports.default = async function(context) {
  if (process.platform !== 'linux') return;

  const appOutDir = context.appOutDir;
  const execName = context.packager.executableName;
  const execPath = path.join(appOutDir, execName);
  const realExec = execPath + '.bin';

  console.log(`afterPack: wrapping ${execPath}`);
  console.log(`afterPack: directory contents:`, fs.readdirSync(appOutDir));

  fs.renameSync(execPath, realExec);
  fs.writeFileSync(execPath,
    `#!/bin/bash\nexec "$(dirname "$(readlink -f "$0")")/${execName}.bin" --no-sandbox "$@"\n`
  );
  fs.chmodSync(execPath, '755');

  console.log('afterPack: wrapper created successfully');
};
