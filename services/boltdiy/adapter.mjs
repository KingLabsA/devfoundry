import express from "express";

const app = express();
app.use(express.json({ limit: "10mb" }));

app.get("/health", (_req, res) => res.json({ ok: true }));

app.post("/api/generate", async (req, res) => {
  try {
    const { runHeadless } = await import("./build/headless.js");
    const result = await runHeadless({ prompt: req.body.prompt, context: req.body.context });
    res.json({ files: result.files, project_dir: result.projectDir ?? "" });
  } catch (err) {
    console.error("bolt.diy generate failed:", err);
    res.status(500).json({ error: String(err) });
  }
});

app.listen(9102, () => console.log("bolt.diy adapter on :9102"));
