// OpenCode's CLI settings accept JSONC (comments and trailing commas).
export function permissionLabel(launch, source = '{}') {
  if (launch === 'auto') return 'Auto (locked)';
  if (launch === 'ask') return 'Ask (locked)';
  if (launch !== 'interactive') return 'Unknown';
  try {
    const uncommented = source.replace(/"(?:\\.|[^"\\])*"|\/\/[^\r\n]*|\/\*[\s\S]*?\*\//g,
      token => token.startsWith('"') ? token : ' ');
    const clean = uncommented.replace(/"(?:\\.|[^"\\])*"|,\s*(?=[}\]])/g,
      token => token.startsWith('"') ? token : '');
    const mode = JSON.parse(clean).session?.permissions ?? 'prompt';
    return mode === 'autoaccept' ? 'Auto' : mode === 'prompt' ? 'Ask' : 'Unknown';
  } catch { return 'Unknown'; }
}
