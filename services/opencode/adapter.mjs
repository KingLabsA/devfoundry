import express from "express";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const exec = promisify(execFile);
const app = express();
app.use(express.json({ limit: "10mb" }));

app.get("/health", (_req, res) => res.json({ ok: true }));

app.post("/api/run", async (req, res) => {
  const { project_dir, instruction } = req.body;
  try {
    const { stdout } = await exec("opencode", ["run", instruction], {
      cwd: project_dir, timeout: 540_000, maxBuffer: 32 * 1024 * 1024,
    });
    const { stdout: diff } = await exec("git", ["diff", "--name-only"], { cwd: project_dir }).catch(() => ({ stdout: "" }));
    res.json({ summary: stdout.slice(-4000), changed_files: diff.split("\n").filter(Boolean) });
  } catch (err) {
    console.error("opencode run failed:", err);
    res.status(500).json({ error: String(err) });
  }
});

app.post("/api/test", async (req, res) => {
  try {
    const { stdout } = await exec("opencode", ["run", "Run the project's test suite and report results as JSON: {passed, failed, failures}"], {
      cwd: req.body.project_dir, timeout: 540_000, maxBuffer: 32 * 1024 * 1024,
    });
    const match = stdout.match(/\{[\s\S]*\}/);
    res.json(match ? JSON.parse(match[0]) : { passed: 0, failed: 0, failures: "" });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.listen(9103, () => console.log("opencode adapter on :9103"));
