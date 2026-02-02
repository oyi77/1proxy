#!/usr/bin/env node
/**
 * Post-build script to create GitHub Pages compatible output
 * Copies static files from .next/server/app to out/ directory
 * AND fixes asset paths for subdirectory deployment
 */

const fs = require('fs');
const path = require('path');

// Get the project root (parent of scripts/)
const projectRoot = path.join(__dirname, '..');

const sourceDir = path.join(projectRoot, '.next/server/app');
const outDir = path.join(projectRoot, 'out');
const staticDir = path.join(projectRoot, '.next/static');

// GitHub Pages subdirectory (change this if deploying to root)
const BASE_PATH = '/1proxy';

// Create out directory
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

// Copy static assets
if (fs.existsSync(staticDir)) {
  const outStaticDir = path.join(outDir, '_next/static');
  fs.mkdirSync(outStaticDir, { recursive: true });
  copyDir(staticDir, outStaticDir);
  console.log('✅ Copied static assets');
}

// Copy HTML files and restructure
function copyHTMLFiles(source, dest) {
  const entries = fs.readdirSync(source, { withFileTypes: true });
  
  for (const entry of entries) {
    const sourcePath = path.join(source, entry.name);
    
    if (entry.isDirectory()) {
      const destPath = path.join(dest, entry.name);
      fs.mkdirSync(destPath, { recursive: true });
      copyHTMLFiles(sourcePath, destPath);
    } else if (entry.name.endsWith('.html')) {
      let content = fs.readFileSync(sourcePath, 'utf8');
      
      // Fix asset paths by adding BASE_PATH prefix
      content = content
        .replace(/href="\/_next\//g, `href="${BASE_PATH}/_next/`)
        .replace(/src="\/_next\//g, `src="${BASE_PATH}/_next/`)
        .replace(/href="\/favicon\.ico"/g, `href="${BASE_PATH}/favicon.ico"`)
        .replace(/"\/rotator\.js"/g, `"${BASE_PATH}/rotator.js"`);
      
      const destPath = path.join(dest, entry.name);
      fs.writeFileSync(destPath, content, 'utf8');
    }
  }
}

function copyDir(source, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }
  
  const entries = fs.readdirSync(source, { withFileTypes: true });
  
  for (const entry of entries) {
    const sourcePath = path.join(source, entry.name);
    const destPath = path.join(dest, entry.name);
    
    if (entry.isDirectory()) {
      copyDir(sourcePath, destPath);
    } else {
      fs.copyFileSync(sourcePath, destPath);
    }
  }
}

copyHTMLFiles(sourceDir, outDir);

// Copy public files (including .nojekyll)
const publicDir = path.join(projectRoot, 'public');
if (fs.existsSync(publicDir)) {
  copyDir(publicDir, outDir);
  console.log('✅ Copied public files');
}

// Rename index.html if needed
const indexPath = path.join(outDir, 'index.html');
if (!fs.existsSync(indexPath)) {
  // Find and rename the first HTML file to index.html
  const files = fs.readdirSync(outDir);
  const firstHTML = files.find(f => f.endsWith('.html'));
  if (firstHTML) {
    fs.renameSync(path.join(outDir, firstHTML), indexPath);
  }
}

console.log('✅ GitHub Pages export complete!');
console.log(`📁 Output directory: ${outDir}`);
console.log(`🔧 Base path: ${BASE_PATH}`);
