#!/usr/bin/env node
/**
 * Post-build script to create GitHub Pages compatible output
 * Handles Next.js 15 'output: export' with 'basePath'
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const rawOutDir = path.join(projectRoot, 'out');

// Fix for Windows Git Bash path mangling
let BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '/1proxy';
if (BASE_PATH.includes(':/')) {
    // Extract the intended path from mangled Windows path (e.g. C:/.../1proxy -> /1proxy)
    BASE_PATH = '/' + BASE_PATH.split('/').pop();
}

console.log(`🔧 Processing export for BASE_PATH: ${BASE_PATH}`);

// When basePath is set, Next.js exports to out/[basePath]
// We need to move those files to the root of out/ for GitHub Pages
const nestedDir = path.join(rawOutDir, BASE_PATH);

if (BASE_PATH && BASE_PATH !== '/' && fs.existsSync(nestedDir)) {
    console.log(`📦 Flattening nested directory: ${nestedDir}`);
    
    // Temporary move out of the way
    const tempDir = path.join(projectRoot, 'out_temp');
    if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true });
    
    fs.renameSync(nestedDir, tempDir);
    fs.rmSync(rawOutDir, { recursive: true });
    fs.renameSync(tempDir, rawOutDir);
    
    console.log('✅ Directory flattened');
}

// Post-processing cleanup for any path mangling in HTML files
// This is a safety measure for Windows builds
function cleanupPaths(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            cleanupPaths(fullPath);
        } else if (entry.name.endsWith('.html') || entry.name.endsWith('.js') || entry.name.endsWith('.css')) {
            let content = fs.readFileSync(fullPath, 'utf8');
            if (content.includes(':/')) {
                // Remove absolute Windows paths that might have leaked in
                // Regex matches C:/.../1proxy and replaces it with /1proxy
                const regex = /[A-Za-z]:\/[^\s"'>]*\/1proxy/g;
                if (regex.test(content)) {
                    content = content.replace(regex, BASE_PATH);
                    fs.writeFileSync(fullPath, content, 'utf8');
                }
            }
        }
    }
}

cleanupPaths(rawOutDir);

// Add .nojekyll to the final out directory
fs.writeFileSync(path.join(rawOutDir, '.nojekyll'), '');
console.log('✅ Added .nojekyll');

console.log(`✨ Export complete! Final files in: ${rawOutDir}`);
