#!/usr/bin/env node
/**
 * Post-build script to create GitHub Pages compatible output
 * Handles Next.js 15 'output: export' with 'basePath'
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const rawOutDir = path.join(projectRoot, 'out');

// Get BASE_PATH (ensure it starts with /)
let BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '/1proxy';
if (BASE_PATH && !BASE_PATH.startsWith('/')) BASE_PATH = '/' + BASE_PATH;

// Fix for Windows Git Bash path mangling (e.g. C:/.../1proxy -> /1proxy)
if (BASE_PATH.includes(':/')) {
    BASE_PATH = '/' + BASE_PATH.split('/').pop();
}

console.log(`🔧 Processing export for BASE_PATH: ${BASE_PATH}`);

// When basePath is set, Next.js exports to out/[basePath]
// e.g. out/1proxy/index.html
const nestedPath = BASE_PATH.startsWith('/') ? BASE_PATH.substring(1) : BASE_PATH;
const nestedDir = path.join(rawOutDir, nestedPath);

if (BASE_PATH && BASE_PATH !== '/' && fs.existsSync(nestedDir)) {
    console.log(`📦 Flattening nested directory: ${nestedDir}`);
    
    // Create a unique temporary directory name
    const tempDirName = `out_temp_${Date.now()}`;
    const tempDir = path.join(projectRoot, tempDirName);
    
    // Move nested contents to temp
    fs.renameSync(nestedDir, tempDir);
    
    // Delete the old out directory structure
    fs.rmSync(rawOutDir, { recursive: true, force: true });
    
    // Move temp to out
    fs.renameSync(tempDir, rawOutDir);
    
    console.log('✅ Directory flattened successfully');
} else {
    console.log('ℹ️ No nested directory to flatten or already flat.');
}

// Add .nojekyll to the final out directory
fs.writeFileSync(path.join(rawOutDir, '.nojekyll'), '');
console.log('✅ Added .nojekyll');

console.log(`✨ Export complete! Final files in: ${rawOutDir}`);
