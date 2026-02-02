#!/usr/bin/env node
/**
 * Post-build script for GitHub Pages (1proxy)
 * Re-aligned for Next.js 15 'output: export' with 'basePath'
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const rawOutDir = path.join(projectRoot, 'out');
const BASE_PATH = '/1proxy';

console.log(`🔧 Processing export for: ${BASE_PATH}`);

if (!fs.existsSync(rawOutDir)) {
    console.error('❌ Error: out/ directory not found.');
    process.exit(1);
}

// When basePath is set, Next.js exports to out/1proxy/index.html
const nestedDir = path.join(rawOutDir, BASE_PATH);

if (fs.existsSync(nestedDir)) {
    console.log(`📦 Flattening nested directory: ${nestedDir}`);
    
    // Create unique temp directory
    const tempDir = path.join(projectRoot, `out_temp_${Date.now()}`);
    
    // 1. Move out/1proxy to out_temp
    fs.renameSync(nestedDir, tempDir);
    
    // 2. Clear out/ (which now contains only an empty '1proxy' folder)
    fs.rmSync(rawOutDir, { recursive: true, force: true });
    
    // 3. Move out_temp to out/
    fs.renameSync(tempDir, rawOutDir);
    
    console.log('✅ Directory flattened. Contents of /1proxy are now at root of out/');
} else {
    console.log('ℹ️ No nested directory found. out/ might already be flat.');
}

// Add .nojekyll to the final out directory
fs.writeFileSync(path.join(rawOutDir, '.nojekyll'), '');
console.log('✅ Added .nojekyll');

console.log(`✨ Export complete! Final files in: ${rawOutDir}`);
