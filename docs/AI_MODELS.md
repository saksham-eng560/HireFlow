# AI models

Which AI HireFlow uses and how to run a free one yourself. See also [How the LLM providers fall back](ARCHITECTURE.md#how-the-llm-provider-fallback-works).

## Free AI with Ollama

[Ollama](https://ollama.com) runs open AI models on your own computer or server, for free and with no
API key. HireFlow talks to it through Ollama's own API with JSON-schema constrained answers, so job
scoring, resume tailoring, cover letters and form answers all work without Claude. Claude is still the
better writer: with `LLM_PROVIDER` left empty (auto), a Claude key goes first and Ollama becomes the
fallback; `LLM_PROVIDER=ollama` puts Ollama first.

**Which model.** Pick one that fits in memory. Download sizes are approximate, and the speeds are rough
estimates for a CPU-only server such as Oracle's free 4-core ARM machine. An Apple Silicon Mac answers
in seconds rather than minutes.

| `OLLAMA_MODEL` | Download | Quality | Rough time per answer, 4 ARM cores, no GPU |
|---|---|---|---|
| `qwen3.5:4b` (default) | ~3.4 GB | Good scores and answers, plain writing | 1–2 min |
| `qwen3.5:9b` | ~6.6 GB | Better writing and reasoning | 2–4 min |
| `qwen3:4b` / `qwen3:8b` | ~2.5 / ~5.2 GB | Proven alternatives | similar to the above |
| `llama3.2:3b` | ~2 GB | Fastest, weakest on long resumes | under 1 min |

### On your Mac

1. Install the Ollama app from https://ollama.com/download (or `brew install ollama`) and open it
   once. It serves on `http://localhost:11434`.
2. Run `./start.sh --ollama`. It checks that Ollama is running, downloads `qwen3.5:4b` once (showing
   progress), and adds `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=qwen3.5:4b` to `.env` only if those are
   missing or empty. It never overwrites a value you set or touches any other line.
3. Open **Settings › Integrations › AI model** and press **Test AI**.

The Docker stack (`./start.sh --docker --ollama`) uses the same Ollama app: inside a container,
`localhost` in `OLLAMA_BASE_URL` automatically means your Mac (`host.docker.internal`).

### On your Oracle server

Re-run the setup script with `WITH_OLLAMA=1`:

```bash
curl -fsSL https://raw.githubusercontent.com/saksham-eng560/HireFlow/main/scripts/server-setup.sh | WITH_OLLAMA=1 bash
# another model:  ... | WITH_OLLAMA=1 OLLAMA_MODEL=qwen3.5:9b bash
```

The script keeps your `.env` and only fills in what's missing:

- `COMPOSE_PROFILES=ollama` starts the `ollama` container (it's off by default);
- `LLM_PROVIDER=ollama`;
- `OLLAMA_BASE_URL=http://ollama:11434`;
- `OLLAMA_MODEL`.

It then downloads the model inside the container and prints the disk space it uses. Models live in the
`ollama-models` volume, so updates don't download them again. Ollama's API has no password, so its
port (11434) is never published: only the app's own containers can reach it. With 24 GB of RAM, the
4B and 9B models fit next to the app comfortably.

To do it by hand, add those four lines to `~/hireflow/.env` and run
`docker compose -f docker-compose.prod.yml up -d`. Then press **Download model** in Settings, or run
`docker compose -f docker-compose.prod.yml exec ollama ollama pull qwen3.5:4b`.

### Ollama Cloud

Ollama also runs much bigger models on its own servers. Create an API key at
https://ollama.com/settings/keys, then open `.env` in an editor and add:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gpt-oss:120b
OLLAMA_API_KEY=            # paste the key here, in .env only
```

Restart the app. `OLLAMA_API_KEY` is only for Ollama Cloud; a local Ollama needs no key. Keep it in
`.env`, never on the command line or in the dashboard. Cloud models don't support JSON-schema output,
so the app asks for JSON in the prompt and checks every answer, retrying once. The free plan runs one
request at a time, which is what `OLLAMA_CONCURRENCY=1` does. You can also use cloud models through a
local Ollama after `ollama signin`, with model names ending in `-cloud`.

### Test it

**Settings › Integrations › AI model** shows:

- the active provider and model, and the fallbacks;
- whether Ollama is reachable, its version, and whether the model is downloaded. If it isn't, a
  **Download model** button downloads it with a progress bar;
- a **Test AI** button that sends one small request and shows the answer and how long it took;
- copyable `.env` lines for each setup above.

The page never asks for keys or shows them. Edit `.env` and restart instead.

### What to expect

- **Slower.** Without a GPU an answer takes one to a few minutes. A scan gives the best
  `OLLAMA_MAX_EVALUATIONS_PER_SCAN` (15) jobs to the model one at a time (`OLLAMA_CONCURRENCY=1`) and
  scores the rest instantly with the built-in heuristic. Cards reach Swipe Review as they're scored.
  Preparing a kept job (resume, cover letter, answers) takes several minutes.
- **Plainer writing.** Small models score jobs well, but their cover letters and written answers are
  less polished than Claude's. Now and then a reply misses the requested format: the app asks once
  more, then falls back to heuristics. Every application goes through review, so you can fix anything
  before it's submitted.
- **Context.** `OLLAMA_NUM_CTX` (8192 tokens) is how much the model reads at once; Ollama's own
  default is only 4096. Long job descriptions and resumes are shortened to fit. Raise it (for example
  to 16384) if you have RAM to spare.
- **Embeddings (optional).** `EMBEDDING_PROVIDER=ollama` uses `nomic-embed-text`
  (`ollama pull nomic-embed-text`) instead of the built-in keyword matcher. After switching providers,
  re-compute the stored vectors with `python scripts/migrate.py --reembed` (in Docker:
  `docker compose exec api python scripts/migrate.py --reembed`).

Every setting is described in the "Free AI with Ollama" block of [`.env.example`](../.env.example).
