const fs = require('node:fs');
const path = require('node:path');

const packagePath = path.join(__dirname, '..', 'package.json');
const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

if (pkg.publisher === 'local-dev') {
  console.error('Replace publisher "local-dev" before publishing.');
  process.exit(1);
}

if (!String(pkg.icon || '').toLowerCase().endsWith('.png')) {
  console.error('Marketplace icon must point to a PNG file.');
  process.exit(1);
}

console.log('Marketplace metadata looks ready.');
