import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { contextCapsule, workspaceStamp } from './context_capsule.mjs';

test('native checkpoint receives bounded current evidence and detects changed dirty files after restart', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const run = (...args) => execFileSync('git', args, { cwd: root, stdio: 'pipe' });
  fs.mkdirSync(path.join(root, 'src'));
  fs.writeFileSync(path.join(root, 'src/app.js'), 'export const mode = "old";\n');
  run('init', '-q'); run('add', '.');
  run('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
    'commit', '-qm', 'seed');
  fs.writeFileSync(path.join(root, 'src/app.js'), 'export const mode = "first";\n');
  const saved = workspaceStamp(root);
  assert.equal(saved.complete, true);
  const summary = '## Objective\n- Build UI\n## Requirements\n- Keep form state\n' +
    '## Relevant Files\n- `src/app.js:1`: current implementation\n- `../outside`: unrelated\n';
  const messages = [{ role: 'user', content: [{ type: 'text',
    text: `<conversation-checkpoint><summary>${summary}</summary><recent-context>older work</recent-context></conversation-checkpoint>` }] }];
  let capsule = contextCapsule(root, messages, saved.stamp);
  assert.match(capsule, /same bounded Git fingerprint/);
  assert.match(capsule, /export const mode = \\"first\\"/);
  assert.doesNotMatch(capsule, /"\.\.\/outside"/);
  fs.writeFileSync(path.join(root, 'src/app.js'), 'export const mode = "second";\n');
  const changed = workspaceStamp(root);
  assert.equal(changed.complete, true);
  assert.notEqual(changed.stamp, saved.stamp, 'M to M file edits must not hide behind unchanged Git status');
  capsule = contextCapsule(root, messages, saved.stamp);
  assert.match(capsule, /STALE: workspace changed since checkpoint/);
  assert.match(capsule, /export const mode = \\"second\\"/);
  assert.ok(capsule.length <= 4000);
  assert.equal(contextCapsule(root, [], null), null, 'no checkpoint means no extra context');
  const plain = [{ content: '<conversation-checkpoint><summary>## Relevant Files\n- src/app.js: current implementation\n</summary></conversation-checkpoint>' }];
  assert.match(contextCapsule(root, plain, saved.stamp), /export const mode = \\"second\\"/,
    'model-written file bullets without backticks still retrieve current source');
});

test('automatic retrieval skips symlinks and fails closed on oversized Git evidence', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-outside-'));
  t.after(() => { fs.rmSync(root, { recursive: true, force: true }); fs.rmSync(outside, { recursive: true, force: true }); });
  fs.writeFileSync(path.join(outside, 'secret.txt'), 'private marker');
  fs.symlinkSync(path.join(outside, 'secret.txt'), path.join(root, 'linked.txt'));
  const messages = [{ content: `<conversation-checkpoint><summary>## Relevant Files\n- \`linked.txt\`: reference\n</summary></conversation-checkpoint>` }];
  assert.doesNotMatch(contextCapsule(root, messages, null), /private marker|linked.txt/);
  execFileSync('git', ['init', '-q'], { cwd: root });
  fs.writeFileSync(path.join(root, 'large.bin'), Buffer.alloc(1024 * 1024 + 1, 65));
  assert.equal(workspaceStamp(root).complete, false);
  assert.match(contextCapsule(root, messages, 'a'.repeat(64)), /unverified/);
});

test('busy Git workspaces expose bounded current paths without claiming a complete fingerprint', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  execFileSync('git', ['init', '-q'], { cwd: root });
  for (let index = 0; index < 33; index++) fs.writeFileSync(path.join(root, `page-${index}.js`), 'export default 1;\n');
  const stamp = workspaceStamp(root);
  assert.equal(stamp.complete, false);
  assert.equal(stamp.changed, 33);
  assert.equal(stamp.paths.length, 6);
  const text = contextCapsule(root, [], 'a'.repeat(64));
  assert.match(text, /changed paths 33/);
  assert.match(text, /fingerprint unverified: more than 32 changed paths/);
});

test('a false native checkpoint is contradicted by durable user requirements', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const messages = [{ content: '<conversation-checkpoint><summary>## Objective\n- No user conversation or task objective was provided.\n## Requirements\n- (none)\n</summary></conversation-checkpoint>' }];
  const recorded = { total: 1, clipped: false, requests: ['Build a form with atomic import and keep existing seed data.'] };
  const text = contextCapsule(root, messages, null, recorded);
  assert.match(text, /CHECKPOINT CONTRADICTION/);
  assert.match(text, /atomic import and keep existing seed data/);
  assert.ok(text.length <= 8000);
  assert.match(contextCapsule(root, messages, null), /No private user-request baseline/);
});

test('checkpoint decisions require a verbatim anchor in retained user requests', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const recorded = { total: 1, clipped: false, requests: ['Keep the 64K context tier for now.'] };
  const summary = '## Decisions\n- User: "Keep the 64K context tier for now."\n' +
    '- Wrote Store-only tests to avoid HTTP setup\n## Work State\n- Filter edited\n';
  const messages = [{ content: `<conversation-checkpoint><summary>${summary}</summary></conversation-checkpoint>` }];
  assert.match(contextCapsule(root, messages, null, recorded), /CHECKPOINT DECISIONS UNVERIFIED: 1 item/);
  const supported = summary.replace('- Wrote Store-only tests to avoid HTTP setup\n', '');
  const clean = [{ content: `<conversation-checkpoint><summary>${supported}</summary></conversation-checkpoint>` }];
  assert.doesNotMatch(contextCapsule(root, clean, null, recorded), /CHECKPOINT DECISIONS UNVERIFIED/);
});

test('a later handoff remains visible when the checkpoint work state contradicts it', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const messages = [{ content: '<conversation-checkpoint><summary>## Work State\n### Active\n- Implement UI controls</summary>' +
    '<recent-context>[Assistant]: UI controls were edited; browser checks remain unrun. Next: verify in browser.' +
    '</recent-context></conversation-checkpoint>' }];
  const capsule = contextCapsule(root, messages, null);
  assert.match(capsule, /Recent pre-checkpoint transcript tail \(historical, unverified/);
  assert.match(capsule, /UI controls were edited; browser checks remain unrun/);
  assert.match(capsule, /Next: verify in browser/);
});

test('long recorded requests cannot crowd out current Git and file evidence', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'src'));
  fs.writeFileSync(path.join(root, 'src', 'app.js'), 'export const current = true;\n');
  const messages = [{ content: '<conversation-checkpoint><summary>## Relevant Files\n- src/app.js: implementation\n</summary></conversation-checkpoint>' }];
  const recorded = { total: 7, clipped: true, requests: ['A'.repeat(6000), 'B'.repeat(2000), 'C'.repeat(2000), 'D'.repeat(2000)] };
  const capsule = contextCapsule(root, messages, null, recorded);
  assert.match(capsule, /export const current = true/);
  assert.match(capsule, /coverage is partial/);
  assert.ok(capsule.length <= 8000);
});

test('overflow keeps the latest request and an explicit truncation notice', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kryn-context-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  execFileSync('git', ['init', '-q'], { cwd: root });
  const names = Array.from({ length: 6 }, (_, index) => `changed-${index}-` + 'p'.repeat(130) + '.js');
  for (const name of names) fs.writeFileSync(path.join(root, name), 'z'.repeat(500));
  const summary = '## Relevant Files\n' + names.slice(0, 4).map(name => '- `' + name + '`: current').join('\n');
  const messages = [{ content: '<conversation-checkpoint><summary>' + summary + '</summary>' +
    '<recent-context>' + 'r'.repeat(2000) + '</recent-context></conversation-checkpoint>' }];
  const requests = ['A'.repeat(6000), 'B'.repeat(2000), 'C'.repeat(2000),
    'D'.repeat(1900) + ' Latest criterion: retry after 503.'];
  const capsule = contextCapsule(root, messages, null, { total: 4, clipped: true, requests });
  assert.ok(capsule.length <= 8000);
  assert.match(capsule, /Latest criterion: retry after 503/);
  assert.match(capsule, /Further current evidence omitted/);
  assert.match(capsule, /Native transcript remains available outside this prompt/);
});
