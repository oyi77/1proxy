#!/usr/bin/env node
/**
 * Robust Post-build script for GitHub Pages (1proxy)
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const outDir = path.join(projectRoot, 'out');
const nextDir = path.join(projectRoot, '.next');
const publicDir = path.join(projectRoot, 'public');

const BASE_PATH = '/1proxy';

console.log(`🔧 Starting robust export processing for: ${BASE_PATH}`);

// 1. Ensure out/ exists
if (!fs.existsSync(outDir)) {
    console.log('📦 Creating out/ directory...');
    fs.mkdirSync(outDir, { recursive: true });
}

/**
 * Robust copy function
 */
function safeCopy(src, dest) {
    if (!fs.existsSync(src)) return;
    
    const stats = fs.statSync(src);
    
    if (stats.isDirectory()) {
        if (fs.existsSync(dest)) {
            const destStats = fs.statSync(dest);
            if (!destStats.isDirectory()) {
                fs.unlinkSync(dest);
                fs.mkdirSync(dest, { recursive: true });
            }
        } else {
            fs.mkdirSync(dest, { recursive: true });
        }
        
        fs.readdirSync(src).forEach(child => {
            safeCopy(path.join(src, child), path.join(dest, child));
        });
    } else {
        if (fs.existsSync(dest)) {
            const destStats = fs.statSync(dest);
            if (destStats.isDirectory()) {
                console.log(`⚠️ Removing directory at ${dest} to copy file ${src}`);
                fs.rmSync(dest, { recursive: true, force: true });
            }
        }
        fs.copyFileSync(src, dest);
    }
}

// 2. Reconstruct from .next if needed (for environments where export fails)
const serverAppDir = path.join(nextDir, 'server/app');
if (fs.existsSync(serverAppDir)) {
    console.log('📂 Copying HTML from .next/server/app...');
    safeCopy(serverAppDir, outDir);
}

const staticDir = path.join(nextDir, 'static');
if (fs.existsSync(staticDir)) {
    console.log('📂 Copying static assets from .next/static...');
    safeCopy(staticDir, path.join(outDir, '_next/static'));
}

// 3. Always sync public/ to out/ (important for favicon.ico)
if (fs.existsSync(publicDir)) {
    console.log('📂 Syncing public/ directory...');
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

            if (changed) {
                fs.writeFileSync(fullPath, content, 'utf8');
            }
        }
    }
}

// 4. Run path fixes
console.log('🛠️ Fixing asset paths...');
fixPaths(outDir);

// 5. Cleanup Next.js metadata artifacts (the favicon.ico/ directory issue)
const ghostFavicon = path.join(outDir, 'favicon.ico');
if (fs.existsSync(ghostFavicon) && fs.statSync(ghostFavicon).isDirectory()) {
    console.log('🧹 Cleaning up ghost favicon directory...');
    fs.rmSync(ghostFavicon, { recursive: true, force: true });
    // Re-copy the real one from public
    const realFavicon = path.join(publicDir, 'favicon.ico');
    if (fs.existsSync(realFavicon)) {
        fs.copyFileSync(realFavicon, ghostFavicon);
    }
}

// 6. Ensure index.html exists (fallback from page.html)
if (fs.existsSync(path.join(outDir, 'page.html')) && !fs.existsSync(path.join(outDir, 'index.html'))) {
    fs.copyFileSync(path.join(outDir, 'page.html'), path.join(outDir, 'index.html'));
}

// 7. Finalize
fs.writeFileSync(path.join(outDir, '.nojekyll'), '');
console.log(`✨ Export complete! Final files in: ${outDir}`);
