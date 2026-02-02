#!/usr/bin/env node
/**
 * Bulletproof Post-build script for GitHub Pages (1proxy)
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

/**
 * Robust copy function with collision detection
 */
function safeCopy(src, dest) {
    if (!fs.existsSync(src)) return;
    
    const stats = fs.statSync(src);
    
    if (stats.isDirectory()) {
        // Destination exists and is a file? Remove it.
        if (fs.existsSync(dest) && !fs.statSync(dest).isDirectory()) {
            console.log(`🧹 Removing file at ${dest} to create directory`);
            fs.unlinkSync(dest);
        }
        
        if (!fs.existsSync(dest)) {
            fs.mkdirSync(dest, { recursive: true });
        }
        
        fs.readdirSync(src).forEach(child => {
            safeCopy(path.join(src, child), path.join(dest, child));
        });
    } else {
        // Destination exists and is a directory? Remove it.
        if (fs.existsSync(dest)) {
            if (fs.statSync(dest).isDirectory()) {
                console.log(`🧹 Removing directory at ${dest} to copy file ${src}`);
                fs.rmSync(dest, { recursive: true, force: true });
            }
        }
        
        try {
            fs.copyFileSync(src, dest);
        } catch (e) {
            console.error(`❌ Failed to copy ${src} to ${dest}: ${e.message}`);
        }
    }
}

// 1. Ensure out/ exists
if (!fs.existsSync(outDir)) {
    console.log('📦 Creating out/ directory...');
    fs.mkdirSync(outDir, { recursive: true });
}

// 2. Try to find where Next.js put the files
// In some environments, Next.js 15 might put them in .next/out even if we don't ask
const nextOut = path.join(nextDir, 'out');
if (fs.existsSync(nextOut)) {
    console.log('📂 Found files in .next/out, copying to root out/...');
    safeCopy(nextOut, outDir);
}

// 3. Reconstruct from .next server/app if out/ is still empty
const serverAppDir = path.join(nextDir, 'server/app');
if (fs.existsSync(serverAppDir)) {
    console.log('📂 Reconstructing HTML from .next/server/app...');
    safeCopy(serverAppDir, outDir);
}

const staticDir = path.join(nextDir, 'static');
if (fs.existsSync(staticDir)) {
    console.log('📂 Reconstructing static assets from .next/static...');
    const outStaticDir = path.join(outDir, '_next/static');
    if (!fs.existsSync(path.join(outDir, '_next'))) fs.mkdirSync(path.join(outDir, '_next'));
    safeCopy(staticDir, outStaticDir);
}

// 4. Handle nested basePath (out/1proxy/...)
const nestedDir = path.join(outDir, '1proxy');
if (fs.existsSync(nestedDir) && nestedDir !== outDir) {
    console.log(`📦 Flattening nested directory: ${nestedDir}`);
    const tempDir = path.join(projectRoot, `out_temp_${Date.now()}`);
    fs.renameSync(nestedDir, tempDir);
    // Don't delete everything, might have just merged other files
    safeCopy(tempDir, outDir);
    fs.rmSync(tempDir, { recursive: true, force: true });
}

// 5. Always sync public/ to out/ (critical for favicon.ico)
if (fs.existsSync(publicDir)) {
    console.log('📂 Final sync of public/ directory...');
    safeCopy(publicDir, outDir);
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

// 6. Ensure index.html (fallback from page.html)
const indexPath = path.join(outDir, 'index.html');
const pagePath = path.join(outDir, 'page.html');
if (fs.existsSync(pagePath) && !fs.existsSync(indexPath)) {
    fs.copyFileSync(pagePath, indexPath);
}

// 7. Cleanup ghost favicon.ico/ directory if it still exists
const ghostFav = path.join(outDir, 'favicon.ico');
if (fs.existsSync(ghostFav) && fs.statSync(ghostFav).isDirectory()) {
    console.log('🧹 Removing stubborn ghost favicon directory');
    fs.rmSync(ghostFav, { recursive: true, force: true });
    // Restore from public
    const realFav = path.join(publicDir, 'favicon.ico');
    if (fs.existsSync(realFav)) fs.copyFileSync(realFav, ghostFav);
}

fs.writeFileSync(path.join(outDir, '.nojekyll'), '');
console.log(`✨ Export complete! Final files in: ${outDir}`);
