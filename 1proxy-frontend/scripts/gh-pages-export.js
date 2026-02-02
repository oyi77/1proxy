#!/usr/bin/env node
/**
 * Robust Post-build script for GitHub Pages (1proxy)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const projectRoot = path.join(__dirname, '..');
let outDir = path.join(projectRoot, 'out');
const nextDir = path.join(projectRoot, '.next');
const publicDir = path.join(projectRoot, 'public');

const BASE_PATH = '/1proxy';

console.log(`🔧 Starting robust export processing for: ${BASE_PATH}`);

// DIAGNOSTIC: List directories to see where Next.js put the files
if (!fs.existsSync(outDir)) {
    console.log('❌ out/ directory not found in root.');
    try {
        console.log('🔍 Searching for files...');
        // Standard Linux/Mac find
        const findOut = execSync('find . -maxdepth 3 -name "out" -type d').toString();
        console.log('Found "out" directories:\n', findOut);
    } catch (e) {
        // ignore find errors
    }
}

// 1. Ensure out/ exists (Reconstruct if missing)
if (!fs.existsSync(outDir)) {
    console.log('⚠️ out/ missing. Attempting to reconstruct from .next/server/app and .next/static...');
    fs.mkdirSync(outDir, { recursive: true });
}

// Reconstruct HTML if missing
const serverAppDir = path.join(nextDir, 'server/app');
if (fs.existsSync(serverAppDir)) {
    console.log('📂 Found .next/server/app, copying HTML...');
    copyRecursive(serverAppDir, outDir, (file) => file.endsWith('.html'));
}

// Reconstruct static assets if missing
const nextStaticTarget = path.join(outDir, '_next/static');
if (!fs.existsSync(nextStaticTarget)) {
    console.log('📂 Static assets missing from out/_next/static. Copying from .next/static...');
    const sourceStaticDir = path.join(nextDir, 'static');
    if (fs.existsSync(sourceStaticDir)) {
        if (!fs.existsSync(path.join(outDir, '_next'))) fs.mkdirSync(path.join(outDir, '_next'));
        fs.mkdirSync(nextStaticTarget, { recursive: true });
        copyRecursive(sourceStaticDir, nextStaticTarget);
    }
}

// 2. Handle nested basePath if Next.js exported it that way
const nestedDir = path.join(outDir, BASE_PATH);
if (BASE_PATH && BASE_PATH !== '/' && fs.existsSync(nestedDir)) {
    console.log(`📦 Flattening nested directory: ${nestedDir}`);
    const tempDir = path.join(projectRoot, `out_temp_${Date.now()}`);
    fs.renameSync(nestedDir, tempDir);
    fs.rmSync(outDir, { recursive: true, force: true });
    fs.renameSync(tempDir, outDir);
}

// 3. Always sync public/ to out/ (important for favicon.ico)
if (fs.existsSync(publicDir)) {
    console.log('📂 Syncing public/ directory...');
    copyRecursive(publicDir, outDir);
}

/**
 * Robust copy function
 */
function copyRecursive(src, dest, filter = () => true) {
    if (!fs.existsSync(src)) return;
    const stats = fs.statSync(src);
    if (stats.isDirectory()) {
        if (fs.existsSync(dest) && !fs.statSync(dest).isDirectory()) fs.unlinkSync(dest);
        if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
        fs.readdirSync(src).forEach(child => copyRecursive(path.join(src, child), path.join(dest, child), filter));
    } else if (filter(src)) {
        if (fs.existsSync(dest) && fs.statSync(dest).isDirectory()) {
            console.log(`🧹 Removing directory at ${dest} to copy file ${src}`);
            fs.rmSync(dest, { recursive: true, force: true });
        }
        fs.copyFileSync(src, dest);
    }
}

/**
 * Path rewriting logic
 */
function fixPaths(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            fixPaths(fullPath);
        } else if (/\.(html|js|css|json)$/.test(entry.name)) {
            let content = fs.readFileSync(fullPath, 'utf8');
            let changed = false;

            // Fix /_next/ paths
            if (content.includes('/_next/')) {
                content = content.replace(/(["'])\/_next\//g, `$1${BASE_PATH}/_next/`);
                changed = true;
            }

            // Fix public asset paths
            ['favicon.ico', 'rotator.js'].forEach(asset => {
                const regex = new RegExp(`(["'])\/${asset.replace('.', '\\.')}`, 'g');
                if (regex.test(content)) {
                    content = content.replace(regex, `$1${BASE_PATH}/${asset}`);
                    changed = true;
                }
            });

            if (changed) fs.writeFileSync(fullPath, content, 'utf8');
        }
    }
}

console.log('🛠️ Fixing asset paths...');
fixPaths(outDir);

// 4. Ensure index.html exists
if (fs.existsSync(path.join(outDir, 'page.html')) && !fs.existsSync(path.join(outDir, 'index.html'))) {
    fs.copyFileSync(path.join(outDir, 'page.html'), path.join(outDir, 'index.html'));
}

// 5. Cleanup ghost directories
['favicon.ico', 'rotator.js'].forEach(file => {
    const p = path.join(outDir, file);
    if (fs.existsSync(p) && fs.statSync(p).isDirectory()) fs.rmSync(p, { recursive: true, force: true });
});

fs.writeFileSync(path.join(outDir, '.nojekyll'), '');
console.log(`✨ Export complete! Final files in: ${outDir}`);
