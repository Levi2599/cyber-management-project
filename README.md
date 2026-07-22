# Dual Code Auditor

An n8n multi-agent workflow that scans code changes for security vulnerabilities and proposes fixes.
A **Red Team** agent analyses the code, produces a proof-of-concept and a CVSS 3.1 vector string;
a **Blue Team** agent receives the original code plus that report and returns a hardened version.

Built as a capstone project for the course *Introduction to Cyber Management*.

---

## How it works

```
GitHub PR  ─→  Webhook  ─→  Signature / allow-list check  ─→  Fetch diff  ─→  Extract added lines
                                                                                      │
                                                                                      ▼
   PR comment  ←─  Markdown report  ←─  Blue Team agent  ←─  Red Team agent (CVSS 3.1 + PoC)
        │
        └─→  optional auto-fix commit (only when a real code block was returned)
```

A second entry point, `POST /webhook/scan-code`, accepts a raw snippet and returns the same report —
used by the demo page and by the evaluation harness.

**Stack:** n8n (23 nodes) · Groq / Llama 3.3 70B · GitHub API · Google Drive · static HTML front end

---

## Things worth looking at

**`Verify Request` node** — the webhook is public, so before any expensive work the request must
prove itself. Requests from GitHub are checked against an HMAC-SHA256 signature using a
timing-safe comparison; manual requests carry no signature and are therefore restricted to an
allow-list of repositories. Anything else gets a `403` with a reason and never reaches an LLM call.
Without this, anyone could point the system at an arbitrary repository and spend the owner's tokens.

**`Build Report` node** — the Blue Team agent returns prose *and* code. Committing its raw output
would overwrite a source file with Hebrew explanation text, so the node extracts the fenced code
block only, and refuses to commit when no vulnerability was reported, no code block came back, or
no file path is known.

**Tests** — `scripts/eval/test_code_nodes.js` loads the node code straight out of the workflow JSON
and runs it in a mocked n8n environment, so the tests exercise the code that actually ships rather
than a copy that can drift.

```bash
node scripts/eval/test_code_nodes.js     # 18 tests
```

---

## Evaluation

`scripts/eval/dataset.json` holds 20 labelled snippets — 12 vulnerable across 7 OWASP Top 10
categories, and 8 safe. Most safe cases are the fixed counterpart of a vulnerable one
(parameterised query vs. string concatenation), which makes them harder to tell apart than
arbitrary clean code. The safe half exists so that false positives can be measured at all.

```bash
python scripts/eval/run_eval.py          # measures recall, false-positive rate, precision, runtime
python scripts/generate_report.py        # builds the report from measured results
```

The report generator reads `results.json` if it exists and states plainly that the evaluation has
not been run if it does not. It does not contain a number that was not measured.

**Current status:** the pipeline, security layer and error handling are verified end-to-end against
a live server. The quantitative evaluation has not been run yet, because it needs an active LLM
provider credential — so no accuracy figures are claimed here.

---

## Repository layout

| Path | Contents |
|---|---|
| `dual_code_auditor_wf_updated.json` | The workflow, importable into n8n |
| `index.html` | Demo page |
| `scripts/eval/` | Labelled dataset, evaluation harness, unit tests |
| `scripts/n8n/` | Helper scripts for the n8n public API |
| `scripts/` | Chart and report generators, server setup scripts |
| `docs/DEPLOYMENT.md` | Deployment guide and configuration notes |

---

## Running it

Full setup — server, environment variables, credentials and the GitHub webhook — is documented in
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

Configuration comes from environment variables; copy `.env.example` to `.env` and fill it in.
No keys are committed to this repository.
