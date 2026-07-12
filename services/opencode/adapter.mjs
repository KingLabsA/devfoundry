import express from "express";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const exec = promisify(execFile);
const app = express();
app.use(express.json({ limit: "20mb" }));

let hasCli = false;
try {
  await exec("opencode", ["--version"], { timeout: 15000 });
  hasCli = true;
  console.log("opencode CLI available");
} catch {
  console.log("opencode CLI not available — using direct LLM refinement fallback");
}

app.get("/health", (_req, res) => res.json({ ok: true, engine: hasCli ? "opencode-cli" : "llm-fallback" }));

/* ---------- LLM fallback (Anthropic or OpenAI-compatible gateway) ---------- */

async function llm(prompt, system) {
  const baseUrl = (process.env.LLM_BASE_URL || "").replace(/\/$/, "");
  const openaiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY || "";
  const anthropicKey = process.env.ANTHROPIC_API_KEY || "";
  if (baseUrl || (openaiKey && !anthropicKey)) {
    const resp = await fetch(`${baseUrl || "https://api.openai.com/v1"}/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(openaiKey && { Authorization: `Bearer ${openaiKey}` }) },
      body: JSON.stringify({
        model: process.env.LLM_MODEL || "gpt-4o-mini",
        max_tokens: 8000,
        messages: [...(system ? [{ role: "system", content: system }] : []), { role: "user", content: prompt }],
      }),
    });
    if (!resp.ok) throw new Error(`gateway ${resp.status}: ${await resp.text()}`);
    return (await resp.json()).choices[0].message.content;
  }
  if (anthropicKey) {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": anthropicKey, "anthropic-version": "2023-06-01" },
      body: JSON.stringify({
        model: process.env.LLM_MODEL || "claude-sonnet-5",
        max_tokens: 8000,
        ...(system && { system }),
        messages: [{ role: "user", content: prompt }],
      }),
    });
    if (!resp.ok) throw new Error(`anthropic ${resp.status}: ${await resp.text()}`);
    return (await resp.json()).content[0].text;
  }
  throw new Error("No LLM provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or LLM_BASE_URL in Settings.");
}

function snapshotProject(dir, maxBytes = 60000) {
  const files = {};
  let used = 0;
  const walk = (d) => {
    for (const name of readdirSync(d)) {
      if (name.startsWith(".") || name === "node_modules" || name === "__pycache__") continue;
      const p = join(d, name);
      if (statSync(p).isDirectory()) walk(p);
      else if (used < maxBytes) {
        const content = readFileSync(p, "utf8").slice(0, 6000);
        files[relative(dir, p)] = content;
        used += content.length;
      }
    }
  };
  walk(dir);
  return files;
}

async function llmRefine(projectDir, instruction) {
  const files = snapshotProject(projectDir);
  const text = await llm(
    `Project files:\n${JSON.stringify(files)}\n\nTask: ${instruction}\n\n` +
      `Respond with ONLY JSON: {"files": {"path": "new full content"}, "summary": "what changed"} ` +
      `containing every file you modified or created.`,
    "You are an expert software engineer performing a focused code change.",
  );
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("model returned no JSON");
  const result = JSON.parse(match[0]);
  const changed = [];
  for (const [rel, content] of Object.entries(result.files || {})) {
    if (rel.includes("..")) continue;
    writeFileSync(join(projectDir, rel), String(content));
    changed.push(rel);
  }
  return { summary: result.summary || "", changed_files: changed };
}

/* ---------- routes ---------- */

app.post("/api/run", async (req, res) => {
  const { project_dir, instruction } = req.body;
  try {
    if (hasCli) {
      const { stdout } = await exec("opencode", ["run", instruction], {
        cwd: project_dir, timeout: 540_000, maxBuffer: 32 * 1024 * 1024,
      });
      const { stdout: diff } = await exec("git", ["diff", "--name-only"], { cwd: project_dir }).catch(() => ({ stdout: "" }));
      res.json({ summary: stdout.slice(-4000), changed_files: diff.split("\n").filter(Boolean) });
    } else {
      res.json(await llmRefine(project_dir, instruction));
    }
  } catch (err) {
    console.error("refine failed:", err);
    res.status(500).json({ error: String(err) });
  }
});

app.post("/api/test", async (req, res) => {
  const { project_dir } = req.body;
  try {
    for (const [cmd, args] of [["npm", ["test", "--silent"]], ["python3", ["-m", "pytest", "-q"]]]) {
      try {
        const { stdout } = await exec(cmd, args, { cwd: project_dir, timeout: 300_000, maxBuffer: 8 * 1024 * 1024 });
        return res.json({ passed: 1, failed: 0, failures: "", output: stdout.slice(-2000) });
      } catch (err) {
        if (err.stdout || err.stderr) {
          return res.json({ passed: 0, failed: 1, failures: String(err.stdout || err.stderr).slice(-3000) });
        }
      }
    }
    res.json({ passed: 0, failed: 0, failures: "", note: "no test runner found in project" });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.listen(9103, () => console.log("refinement service on :9103"));
