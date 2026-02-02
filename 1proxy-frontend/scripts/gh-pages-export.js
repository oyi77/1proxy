#!/usr/bin/env node
/**
 * Robust Post-build script for GitHub Pages (1proxy)
 * Converts paths AND reconstructs out/ if Next.js export fails
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
let outDir = path.join(projectRoot, 'out');
const nextDir = path.join(projectRoot, '.next');

// The intended deployment subdirectory
const BASE_PATH = '/1proxy';

console.log(`🔧 Processing static export for: ${BASE_PATH}`);

// FALLBACK: If Next.js export didn't create 'out', try to reconstruct it from .next
if (!fs.existsSync(outDir)) {
    console.log('⚠️ Warning: out/ directory not found. Reconstructing from .next...');
    fs.mkdirSync(outDir, { recursive: true });
    
    const serverAppDir = path.join(nextDir, 'server/app');
    const staticDir = path.join(nextDir, 'static');
    
    if (fs.existsSync(serverAppDir)) {
        copyRecursive(serverAppDir, outDir, (file) => file.endsWith('.html'));
        console.log('✅ Reconstructed HTML from .next/server/app');
    }
    
    if (fs.existsSync(staticDir)) {
        const outStaticDir = path.join(outDir, '_next/static');
        fs.mkdirSync(outStaticDir, { recursive: true });
        copyRecursive(staticDir, outStaticDir);
        console.log('✅ Reconstructed static assets from .next/static');
    }

    // Copy public files
    const publicDir = path.join(projectRoot, 'public');
    if (fs.existsSync(publicDir)) {
        copyRecursive(publicDir, outDir);
        console.log('✅ Copied public files');
    }
}

/**
 * Recursively copy files
 */
function copyRecursive(src, dest, filter = () => true) {
    const exists = fs.existsSync(src);
    const stats = exists && fs.statSync(src);
    const isDirectory = exists && stats.isDirectory();
    if (isDirectory) {
        if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
        fs.readdirSync(src).forEach((child) => {
            copyRecursive(path.join(src, child), path.join(dest, child), filter);
        });
    } else if (filter(src)) {
        fs.copyFileSync(src, dest);
    }
}

/**
 * Recursively process files to fix paths
 */
function processDirectory(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        
        if (entry.isDirectory()) {
            processDirectory(fullPath);
        } else if (
            entry.name.endsWith('.html') || 
            entry.name.endsWith('.js') || 
            entry.name.endsWith('.css') ||
            entry.name.endsWith('.json')
        ) {
            let content = fs.readFileSync(fullPath, 'utf8');
            let originalContent = content;

            // 1. Fix standard Next.js asset paths
            content = content.replace(/(["'])\/_next\//g, `$1${BASE_PATH}/_next/`);

            // 2. Fix static public assets
            content = content.replace(/(["'])\/favicon\.ico/g, `$1${BASE_PATH}/favicon.ico`);
            content = content.replace(/(["'])\/rotator\.js/g, `$1${BASE_PATH}/rotator.js`);

            if (content !== originalContent) {
                fs.writeFileSync(fullPath, content, 'utf8');
            }
        }
    }
}

// Rename the reconstructed index.html if necessary (some Next versions name it page.html)
if (fs.existsSync(path.join(outDir, 'page.html')) && !fs.existsSync(path.join(outDir, 'index.html'))) {
    fs.renameSync(path.join(outDir, 'page.html'), path.join(outDir, 'index.html'));
}

// Start processing
processDirectory(outDir);

// Add .nojekyll to the final out directory
fs.writeFileSync(path.join(outDir, '.nojekyll'), '');

console.log(`✨ Portable export complete! Final files in: ${outDir}`);
