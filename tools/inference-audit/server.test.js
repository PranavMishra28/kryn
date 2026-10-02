import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import plugin, { wireMetadata } from "./server.js";

const tool = { type: "function", function: { name: "lookup", description: "private-description",
  parameters: { type: "object", properties: { query: { type: "string", description: "private-schema" } }, required: ["query"] } } };
const hash = tools => wireMetadata({ tools }).toolsSha256;

test("direct tools hash ignores recursive object key order", () => {
  const reordered = { function: { parameters: { required: ["query"], properties: {
    query: { description: "private-schema", type: "string" } }, type: "object" },
    description: "private-description", name: "lookup" }, type: "function" };
  assert.equal(hash([tool]), hash([reordered]));
  assert.match(hash([tool]), /^[a-f0-9]{64}$/);
});

test("description and schema changes alter the hash without changing names", () => {
  for (const change of [x => { x.function.description += " changed"; },
    x => { x.function.parameters.properties.query.type = "number"; }]) {
    const changed = structuredClone(tool); change(changed);
    assert.deepEqual(wireMetadata({ tools: [changed] }).tools, ["lookup"]);
    assert.notEqual(hash([tool]), hash([changed]));
  }
});

test("array order stays significant at every depth", () => {
  const other = structuredClone(tool); other.function.name = "other";
  assert.notEqual(hash([tool, other]), hash([other, tool]));
  const first = structuredClone(tool), second = structuredClone(tool);
  first.function.parameters.required = ["query", "limit"];
  second.function.parameters.required = ["limit", "query"];
  assert.notEqual(hash([first]), hash([second]));
});

test("omitted tools retain defaults; explicit empty tools hash separately", () => {
  assert.deepEqual(wireMetadata({}), { requestModelID: null, numeric: {}, thinking: null, preserveThinking: null,
    effort: null, messageCount: 0, systemMessageFingerprints: [], tools: [], toolCount: 0, toolsSha256: null,
    workspaceNormalizedToolsSha256: null, toolFingerprints: [],
    imagePartCount: 0, imageCount: 0, images: [] });
  assert.equal(hash(null), null);
  assert.equal(hash({}), null);
  assert.equal(wireMetadata({ tools: {} }).toolCount, null);
  assert.equal(hash([]), createHash("sha256").update("[]").digest("hex"));
});

test("existing sampling and image evidence stays intact; schema text is not logged", () => {
  const bytes = Buffer.from("image-fixture"), data = bytes.toString("base64");
  const metadata = wireMetadata({ tools: [tool], thinking_budget: 0, max_tokens: 128,
    chat_template_kwargs: { enable_thinking: true, preserve_thinking: true, reasoning_effort: "low" },
    messages: [{ content: [{ type: "text", text: "private-message" },
      { type: "image_url", image_url: { url: `data:image/png;base64,${data}` } },
      { type: "image_url", image_url: { url: "https://private.invalid/image" } }] }] });
  assert.deepEqual(metadata.numeric, { max_tokens: 128, thinking_budget: 0 });
  assert.equal(metadata.thinking, true); assert.equal(metadata.preserveThinking, true);
  assert.equal(metadata.effort, "low"); assert.equal(metadata.toolCount, 1);
  assert.deepEqual(metadata.toolFingerprints.map(x => x.name), ["lookup"]);
  assert.match(metadata.toolFingerprints[0].argumentsSha256, /^[a-f0-9]{64}$/);
  assert.match(metadata.toolFingerprints[0].descriptionSha256, /^[a-f0-9]{64}$/);
  assert.match(metadata.toolFingerprints[0].workspaceNormalizedDescriptionSha256, /^[a-f0-9]{64}$/);
  assert.equal(metadata.imagePartCount, 2); assert.equal(metadata.imageCount, 1);
  assert.deepEqual(metadata.images, [{ mime: "image/png", bytes: bytes.length,
    sha256: createHash("sha256").update(bytes).digest("hex") }]);
  const logged = JSON.stringify(metadata);
  for (const secret of ["private-description", "private-schema", "private-message", "private.invalid", data])
    assert(!logged.includes(secret));
});

test("workspace path normalization identifies equivalent tool descriptions", () => {
  const a = structuredClone(tool), b = structuredClone(tool);
  a.function.description = "Read /private/tmp/a/workspace/file";
  b.function.description = "Read /private/tmp/b/workspace/file";
  const left = wireMetadata({ tools: [a] }, "/private/tmp/a/workspace");
  const right = wireMetadata({ tools: [b] }, "/private/tmp/b/workspace");
  assert.notEqual(left.toolsSha256, right.toolsSha256);
  assert.equal(left.workspaceNormalizedToolsSha256, right.workspaceNormalizedToolsSha256);
});

test("system prompt fingerprints expose change without logging prompt text", () => {
  const system = text => ({ messages: [{ role: "system", content: text },
    { role: "user", content: "private-user-message" }] });
  const left = wireMetadata(system("Read /private/tmp/a/workspace/file"), "/private/tmp/a/workspace");
  const right = wireMetadata(system("Read /private/tmp/b/workspace/file"), "/private/tmp/b/workspace");
  const changed = wireMetadata(system("Different guidance"));
  assert.equal(left.messageCount, 2);
  assert.deepEqual(left.systemMessageFingerprints, right.systemMessageFingerprints);
  assert.notDeepEqual(left.systemMessageFingerprints, changed.systemMessageFingerprints);
  assert(!JSON.stringify(left).includes("private-user-message"));
  assert(!JSON.stringify(left).includes("/private/tmp/a/workspace"));
});

async function auditHook(t, expectedModelID) {
  const folder = mkdtempSync(join(tmpdir(), "localai-audit-test-")), log = join(folder, "audit.jsonl");
  const hooks = new Map();
  const close = await plugin.setup({ options: { log, ...(expectedModelID === undefined ? {} : { expectedModelID }) },
    session: { hook: async (name, handler) => { hooks.set(name, handler); } } });
  t.after(() => { close(); rmSync(folder, { recursive: true }); });
  return { records: () => readFileSync(log, "utf8").trim().split("\n").map(JSON.parse),
    invoke: async body => {
      const request = new Request("http://127.0.0.1:8000/v1/chat/completions",
        { method: "POST", body: JSON.stringify(body) });
      await hooks.get("http.request")({ model: { providerID: "local", id: "qwen" }, request });
      return request.json(); // Transport continuation is reached only if the hook accepts; no fetch occurs.
    } };
}

test("expected wire model passes unchanged and is recorded", async t => {
  const audit = await auditHook(t, "candidate-model"), body = { model: "candidate-model", max_tokens: 32 };
  assert.deepEqual(await audit.invoke(body), body);
  const record = audit.records().find(r => r.event === "wire.options");
  assert.equal(record.requestModelID, "candidate-model");
  assert.equal(record.expectedModelID, "candidate-model");
  assert(!audit.records().some(r => r.ok === false));
});

test("mismatched, omitted or non-string wire model fails before transport continuation", async t => {
  const audit = await auditHook(t, "candidate-model");
  for (const body of [{ model: "different-model" }, {}, { model: null }, { model: 42 }])
    await assert.rejects(audit.invoke(body), /unexpected request model ID/);
  const rejected = audit.records().filter(r => r.event === "unexpected.model");
  assert.equal(rejected.length, 4);
  assert(rejected.every(r => r.ok === false && r.expectedModelID === "candidate-model"));
  assert.deepEqual(rejected.map(r => r.requestModelID), ["different-model", null, null, null]);
});

test("absent expectation preserves historical acceptance while recording actual model", async t => {
  const audit = await auditHook(t);
  for (const body of [{ model: "unconstrained-model" }, {}]) assert.deepEqual(await audit.invoke(body), body);
  const records = audit.records().filter(r => r.event === "wire.options");
  assert.deepEqual(records.map(r => r.requestModelID), ["unconstrained-model", null]);
  assert(records.every(r => !Object.hasOwn(r, "expectedModelID")));
});

test("malformed expected-model option fails instead of silently disabling the check", async () => {
  for (const expectedModelID of [null, "", " ", 42])
    await assert.rejects(plugin.setup({ options: { expectedModelID } }), /expectedModelID must be a nonempty string/);
});
