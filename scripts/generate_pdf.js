const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const mdPath = path.join(__dirname, '..', 'VARVE_MASTER_DOCUMENTATION.md');
const htmlPath = path.join(__dirname, '..', 'VARVE_MASTER_DOCUMENTATION.html');
const pdfPath = path.join(__dirname, '..', 'VARVE_MASTER_DOCUMENTATION.pdf');

const mdContent = fs.readFileSync(mdPath, 'utf8');

// Basic Markdown to HTML converter
function simpleMarkdownToHtml(md) {
  let html = md
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^#### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/\n\n/g, '<p></p>');

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Varve Master System Documentation</title>
  <style>
    @page { margin: 20mm; size: A4; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #18181b;
      line-height: 1.6;
      font-size: 13px;
      padding: 0;
      margin: 0;
    }
    h1 { font-size: 24px; color: #09090b; border-bottom: 2px solid #71717a; padding-bottom: 8px; margin-top: 24px; }
    h2 { font-size: 18px; color: #18181b; border-bottom: 1px solid #e4e4e7; padding-bottom: 6px; margin-top: 20px; }
    h3 { font-size: 15px; color: #27272a; margin-top: 16px; }
    h4 { font-size: 13px; color: #3f3f46; margin-top: 14px; }
    blockquote { background: #f4f4f5; border-left: 4px solid #9B7FF6; margin: 16px 0; padding: 10px 16px; font-style: italic; color: #3f3f46; }
    code { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; background: #f4f4f5; color: #6b21a8; padding: 2px 5px; border-radius: 4px; font-size: 12px; }
    pre { background: #18181b; color: #f4f4f5; padding: 14px; border-radius: 8px; overflow-x: auto; font-size: 11px; line-height: 1.5; }
    pre code { background: none; color: #f4f4f5; padding: 0; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 12px; }
    th, td { border: 1px solid #e4e4e7; padding: 8px 12px; text-align: left; }
    th { background: #f4f4f5; font-weight: 600; color: #18181b; }
    tr:nth-child(even) { background: #fafafa; }
    ul, ol { padding-left: 20px; }
    li { margin-bottom: 4px; }
  </style>
</head>
<body>
  ${html}
</body>
</html>`;
}

const htmlContent = simpleMarkdownToHtml(mdContent);
fs.writeFileSync(htmlPath, htmlContent);

console.log('HTML written to', htmlPath);

// Chrome Headless PDF generation
const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
try {
  if (fs.existsSync(chromePath)) {
    execSync(`"${chromePath}" --headless --disable-gpu --print-to-pdf="${pdfPath}" "${htmlPath}"`);
    console.log('PDF successfully generated at:', pdfPath);
  } else {
    console.log('Chrome executable not found at default path');
  }
} catch (err) {
  console.error('Error generating PDF with Chrome:', err.message);
}
