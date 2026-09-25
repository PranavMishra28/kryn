import { openSync, writeSync, closeSync } from "node:fs";
import { createHash } from "node:crypto";

// The wire body is parsed JSON. Preserve array order; sort object keys recursively.
function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object")
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

// Metadata only: never return message text, data URLs, or remote image URLs.
export function wireMetadata(body) {
  const kwargs = body.chat_template_kwargs ?? {};
  const numeric = {};
  for (const key of ["max_tokens", "max_completion_tokens", "temperature", "top_p",
                     "top_k", "min_p", "presence_penalty", "repetition_penalty", "thinking_budget"])
    if (typeof body[key] === "number" && Number.isFinite(body[key])) numeric[key] = body[key];
  const images = [];
  let imagePartCount = 0;
  const contextBytes = { system: 0, developer: 0, user: 0, assistant: 0, toolResult: 0,
    sourceToolResult: 0, shellToolResult: 0, otherToolResult: 0,
    toolCalls: 0, toolSchemas: null, messages: 0 };
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const callNames = new Map(messages.flatMap(message => Array.isArray(message?.tool_calls)
    ? message.tool_calls.filter(call => typeof call?.id === 'string' && typeof call?.function?.name === 'string')
      .map(call => [call.id, call.function.name]) : []));
  contextBytes.messages = messages.length;
  if (Array.isArray(body.tools)) contextBytes.toolSchemas = Buffer.byteLength(JSON.stringify(body.tools));
  for (const message of messages) {
    const role = ({ system: 'system', developer: 'developer', user: 'user',
      assistant: 'assistant', tool: 'toolResult' })[message?.role];
    const parts = typeof message?.content === 'string' ? [message.content] :
      Array.isArray(message?.content) ? message.content.filter(part => part?.type === 'text')
        .map(part => part.text).filter(text => typeof text === 'string') : [];
    const bytes = parts.reduce((total, part) => total + Buffer.byteLength(part), 0);
    if (role) contextBytes[role] += bytes;
    if (role === 'toolResult') {
      const name = callNames.get(message.tool_call_id);
      const category = ['read', 'glob', 'grep'].includes(name) ? 'sourceToolResult' :
        name === 'shell' ? 'shellToolResult' : 'otherToolResult';
      contextBytes[category] += bytes;
    }
    if (Array.isArray(message?.tool_calls))
      contextBytes.toolCalls += Buffer.byteLength(JSON.stringify(message.tool_calls));
    for (const part of Array.isArray(message?.content) ? message.content : []) {
      if (part?.type !== "image_url") continue;
      imagePartCount++;
      const url = part.image_url?.url;
      if (typeof url !== "string") continue;
      const match = /^data:(image\/[a-z0-9.+-]+);base64,([A-Za-z0-9+/]*={0,2})$/i.exec(url);
      if (!match) continue;
      const bytes = Buffer.from(match[2], "base64");
      if (!bytes.length || bytes.toString("base64") !== match[2]) continue;
      images.push({ mime: match[1].toLowerCase(), bytes: bytes.length,
        sha256: createHash("sha256").update(bytes).digest("hex") });
    }
  }
  return { requestModelID: typeof body.model === "string" ? body.model : null, numeric,
    thinking: typeof kwargs.enable_thinking === "boolean" ? kwargs.enable_thinking : null,
    preserveThinking: typeof kwargs.preserve_thinking === "boolean" ? kwargs.preserve_thinking : null,
    effort: ["low", "medium", "xhigh"].includes(kwargs.reasoning_effort) ? kwargs.reasoning_effort : null,
    tools: (Array.isArray(body.tools) ? body.tools : []).map(tool => tool.function?.name).filter(Boolean),
    toolCount: body.tools == null ? 0 : Array.isArray(body.tools) ? body.tools.length : null,
    // Covers direct wire tools, not a Code Mode catalog embedded in message text.
    toolsSha256: Array.isArray(body.tools)
      ? createHash("sha256").update(canonicalJson(body.tools)).digest("hex") : null,
    imagePartCount, imageCount: images.length, images, contextBytes };
}

export default {
  id: "localai.inference-audit",
  async setup(ctx) {
    const expectedModelID = ctx.options.expectedModelID;
    if (expectedModelID !== undefined && (typeof expectedModelID !== "string" || !expectedModelID.trim()))
      throw new Error("Inference audit: expectedModelID must be a nonempty string");
    const fd = openSync(ctx.options.log, "wx", 0o600);
    const scope = e => ({
      sessionID: e.sessionID, agent: e.agent, kind: e.kind,
      model: e.model && {
        providerID: e.model.providerID, id: e.model.id,
        variant: e.model.variant
      }
    });
    const log = (event, data = {}) => writeSync(fd,
      JSON.stringify({ time: new Date().toISOString(), event, ...data }) + "\n");
    const check = (event, e, raw, extra = {}) => {
      let u;
      try { u = new URL(raw); } catch {}
      const ok = e.model?.providerID === "local" && e.model?.id === "qwen"
        && u?.origin === "http://127.0.0.1:8000"
        && (u.pathname === "/v1" || u.pathname.startsWith("/v1/"))
        && !u.username && !u.password && !u.search && !u.hash;
      log(event, { ...scope(e), ...extra, ok,
        destination: u ? u.origin + u.pathname : "invalid" });
      if (!ok) throw new Error("Inference audit: unexpected model or destination");
    };
    try {
      if (ctx.options.readyTools === true) {
        await ctx.rpc.register({ id: "localai.inference-audit", events: {}, methods: {
          tools: { input: { type: "object", properties: {}, additionalProperties: false },
            output: { type: "array", items: { type: "string" } } }
        } }, { tools: async () => (await ctx.tool.list()).map(tool => tool.id).sort() });
      }
      await ctx.session.hook("model.request", e =>
        check("model.request", e, e.baseURL));
      await ctx.session.hook("http.request", async e => {
        check("http.request", e, e.request.url, { method: e.request.method });
        const body = await e.request.clone().json();
        log("wire.options", { ...scope(e), ...wireMetadata(body),
          ...(expectedModelID === undefined ? {} : { expectedModelID }),
          captureOnly: ctx.options.captureOnly === true });
        if (expectedModelID !== undefined && body.model !== expectedModelID) {
          log("unexpected.model", { ...scope(e), expectedModelID,
            requestModelID: typeof body.model === "string" ? body.model : null, ok: false });
          throw new Error("Inference audit: unexpected request model ID");
        }
        if (ctx.options.captureOnly === true)
          throw new Error("LocalAI capture-only check: request intentionally stopped before inference");
      });
      await ctx.session.hook("http.response", e =>
        log("http.response", { ...scope(e), status: e.response.status }));
      await ctx.session.hook("retry", e => log("retry", {
        ...scope(e), attempt: e.attempt, retry: e.decision.retry,
        errorType: e.error.type ?? "unknown"
      }));
      await ctx.session.hook("experimental.ws.handshake", e => {
        log("unexpected.websocket", scope(e));
        throw new Error("Inference audit: unexpected WebSocket transport");
      });
      log("ready");
    } catch (error) { closeSync(fd); throw error; }
    return () => { try { log("closed"); } finally { closeSync(fd); } };
  }
};
