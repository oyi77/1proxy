#!/usr/bin/env node
/**
 * Post-build script for GitHub Pages (1proxy)
 * Converts all root-absolute paths to subdirectory-safe paths
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const outDir = path.join(projectRoot, 'out');

// The intended deployment subdirectory
const BASE_PATH = '/1proxy';

console.log(`🔧 Processing static export for: ${BASE_PATH}`);

if (!fs.existsSync(outDir)) {
    console.error('❌ Error: out/ directory not found. Run npm run build first.');
    process.exit(1);
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
            // Replace /_next/ with /1proxy/_next/
            content = content.replace(/(["'])\/_next\//g, `$1${BASE_PATH}/_next/`);

            // 2. Fix static public assets
            // Replace /favicon.ico with /1proxy/favicon.ico
            content = content.replace(/(["'])\/favicon\.ico/g, `$1${BASE_PATH}/favicon.ico`);
            // Replace /rotator.js with /1proxy/rotator.js
            content = content.replace(/(["'])\/rotator\.js/g, `$1${BASE_PATH}/rotator.js`);

            // 3. Fix internal API references if they are absolute
            // (Standard API calls use the full paijo77 URL, but safety first)
            
            if (content !== originalContent) {
                fs.writeFileSync(fullPath, content, 'utf8');
                console.log(`✅ Fixed paths in: ${path.relative(outDir, fullPath)}`);
            }
        }
    }
}

// Start processing
processDirectory(outDir);

// Add .nojekyll to the final out directory
fs.writeFileSync(path.join(outDir, '.nojekyll'), '');
console.log('✅ Added .nojekyll');

console.log(`✨ Portable export complete! Deployment ready for: ${BASE_PATH}`);
