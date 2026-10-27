#!/usr/bin/env node
// Erzeugt tokens/tokens.css aus tokens/tokens.json.
// Aufruf im Repo-Wurzelverzeichnis:  node scripts/build-tokens.mjs
// Keine Abhängigkeiten, Node 18 oder neuer.

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const T = JSON.parse(readFileSync(join(root, 'tokens/tokens.json'), 'utf8'));

const themes = T.color.themes.map((t) => t.id);
const first = themes[0];
const isAlias = (v) => /^\{[A-Za-z0-9_.-]+\}$/.test(v);
const toCss = (v) => (isAlias(v) ? `var(--${v.slice(1, -1)})` : v);

// Wert eines Tokens für ein Theme. Fehlt ein Theme, gilt der Wert des ersten Themes.
// Aliase werden in jedem Theme neu deklariert, damit sie auch in verschachtelten Themes stimmen.
function valueFor(tok, theme) {
  if (typeof tok.value === 'string') {
    if (theme === first || isAlias(tok.value)) return tok.value;
    return null;
  }
  if (tok.value[theme] != null) return tok.value[theme];
  if (theme === first) return Object.values(tok.value)[0];
  return null;
}

const out = [];
out.push(`/* ${T.name} — generated from tokens.json */`);
out.push('/* Nicht von Hand bearbeiten: tokens/tokens.json ändern und `node scripts/build-tokens.mjs` ausführen. */');
out.push('');

// Schriften (Pfade in tokens.json sind relativ zum Repo, diese Datei liegt in tokens/)
for (const f of T.type.fonts) {
  out.push(`@font-face { font-family: "${f.family}"; src: url("../${f.file}") format("woff2"); font-weight: ${f.weight}; font-style: ${f.style || 'normal'}; font-display: swap; }`);
}
out.push('');

// Farben und Schatten je Theme
themes.forEach((theme, i) => {
  const selector = i === 0 ? `:root, [data-theme="${theme}"]` : `[data-theme="${theme}"]`;
  const decls = [];
  for (const tok of T.color.tokens) {
    const v = valueFor(tok, theme);
    if (v != null) decls.push(`  --${tok.name}: ${toCss(v)};`);
  }
  for (const tok of T.shadow?.tokens ?? []) {
    const v = valueFor(tok, theme);
    if (v != null) decls.push(`  --${tok.name}: ${v};`);
  }
  out.push(`${selector} {`, ...decls, '}', '');
});

// Abstände, Radien, Schriftfamilien
const rootDecls = [];
for (const fam of ['spacing', 'radius']) {
  for (const tok of T[fam]?.tokens ?? []) rootDecls.push(`  --${tok.name}: ${tok.value};`);
}
for (const [key, stack] of Object.entries(T.type.families)) rootDecls.push(`  --font-${key}: ${stack};`);
out.push(':root {', ...rootDecls, '}', '');

// Typstile als Klassen
for (const group of T.type.groups) {
  for (const s of group.styles) {
    const fam = s.family || group.family;
    const props = [
      `font-family: var(--font-${fam})`,
      `font-size: ${s.fontSize}`,
      `line-height: ${s.lineHeight}`,
      `font-weight: ${s.fontWeight}`,
    ];
    if (s.letterSpacing) props.push(`letter-spacing: ${s.letterSpacing}`);
    out.push(`.${s.name} { ${props.join('; ')}; }`);
  }
}
out.push('');

writeFileSync(join(root, 'tokens/tokens.css'), out.join('\n'));
console.log('tokens/tokens.css geschrieben');
