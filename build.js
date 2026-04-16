import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

/**
 * YaOG Build Script
 * 1. Clean dist and build directories
 * 2. Run Vite build (renderer)
 * 3. Run Electron-Builder (package)
 */

const log = (msg) => console.log(`\x1b[34m[BUILD]\x1b[0m ${msg}`);
const error = (msg) => console.error(`\x1b[31m[ERROR]\x1b[0m ${msg}`);

async function build() {
  const root = process.cwd();
  const distPath = path.join(root, 'dist');

  try {
    log('Starting build process...');

    // 1. Rebuild native modules first if needed
    log('Ensuring native modules are built for current environment...');
    execSync('npm run rebuild', { stdio: 'inherit' });

    // 2. Run Vite build
    log('Building renderer (Vite)...');
    execSync('npx vite build', { stdio: 'inherit' });

    // 3. Verify dist exists
    if (!fs.existsSync(distPath)) {
      throw new Error('Vite build failed to produce dist/ directory');
    }

    // 4. Package with electron-builder
    log('Packaging application (electron-builder)...');
    // On Linux, we often need to skip certain checks or use specific flags
    const platformArgs = process.platform === 'linux' ? '--linux' : '';
    execSync(`npx electron-builder ${platformArgs}`, { stdio: 'inherit' });

    log('Build successful! Check the "dist" and "release" folders.');
  } catch (err) {
    error(err.message);
    process.exit(1);
  }
}

build();
