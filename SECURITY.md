# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

Only the latest minor release receives security patches.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by emailing the maintainers via the contact listed in `pyproject.toml`, or by opening a [GitHub Private Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability).

Include:
- A clear description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept code if applicable)
- Affected version(s)

You can expect an acknowledgement within **72 hours** and a resolution timeline within **14 days** for critical issues.

---

## Security Architecture

Auto-Gangjing is a multi-agent LLM debate engine. The following threat surfaces are inherent to its design and must be understood by operators and contributors.

### 1. API Key Management

The engine integrates with three LLM providers: **Anthropic Claude**, **OpenAI**, and **Google Gemini**.

**Requirements:**
- Store API keys exclusively in environment variables or a `.env` file — never in `config.yaml`, source files, or committed history.
- Add `.env` to `.gitignore` before your first commit.
- Rotate keys immediately if they are accidentally exposed.
- Apply the principle of least privilege: use provider-specific key scopes where available (e.g., project-scoped OpenAI keys).

```bash
# Correct: load from environment
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# Or use a .env file (never commit this)
cp .env.example .env
```

### 2. Prompt Injection

Because debate topics are user-supplied and forwarded verbatim into LLM prompts, this engine is susceptible to **prompt injection** — where a malicious topic string attempts to override agent roles, extract system prompts, or produce harmful output.

**Mitigations in place:**
- Each agent uses a strongly-typed `with_structured_output(PydanticSchema)` call; free-form jailbreak text cannot satisfy the schema and will trigger a `ValidationError` retry or outright failure.
- System prompts and user messages are assembled by dedicated builder functions (`build_*_system_prompt` / `build_*_user_message`) — topic content is always injected into a bounded `user_message` context, never merged with system instructions via string concatenation.

**Operator responsibilities:**
- Validate and sanitize debate topics at system boundaries (e.g., your API layer or CLI wrapper) before passing to `run_debate()`.
- Do not expose a raw `run_debate()` endpoint to untrusted users without input filtering.
- Monitor agent outputs for unexpected role-switching language (e.g., "Ignore previous instructions…").

### 3. LLM Structured Output Validation

All agent responses are parsed and validated by **Pydantic v2** schemas (`maverickj/schemas/`). This provides a critical second layer of defence against malformed or injected LLM output:

- `AgentResponse`, `FactCheckResponse`, `ModeratorResponse`, and `DecisionReport` all enforce strict field types and enum constraints.
- `ArgumentStatus` and `FactCheckVerdict` are closed enums — arbitrary string values are rejected.
- Retry logic (`MAX_RETRIES = 2`) appends a correction instruction on `ValidationError`; it does not silently swallow bad output.

**Do not** relax Pydantic validators or add `model_config = ConfigDict(extra="allow")` to schema classes without careful review.

### 4. Configuration Security (`config.yaml`)

`config.yaml` controls model selection, temperature, and debate parameters. An attacker with write access to this file can:

- Route all traffic to an exfiltration proxy by changing provider endpoints (if custom provider support is added).
- Increase `max_rounds` to inflate API costs (denial-of-wallet).
- Adjust `temperature` to produce less reliable structured output.

**Requirements:**
- Treat `config.yaml` with the same access controls as application code.
- In containerised deployments, mount `config.yaml` as a read-only volume.
- Validate `config.yaml` contents against `maverickj/schemas/config.py` (`DebateConfig`) on startup — do not trust arbitrary YAML.

### 5. Dependency Security

The project depends on `langchain-*`, `langgraph`, `pydantic`, `pyyaml`, and related packages. Supply-chain vulnerabilities in these packages could affect the engine.

**Practices:**
- Pin transitive dependencies via `pip-compile` or `uv lock` and commit the lock file.
- Regularly audit dependencies with `pip-audit` or GitHub Dependabot.
- Do not add new dependencies without reviewing their maintenance status and CVE history.

```bash
pip-audit                      # Scan installed packages for known CVEs
pip list --outdated            # Identify stale packages
```

### 6. Docker / Container Security

The provided `Dockerfile` uses `python:3.12-slim`. Follow these practices when building and deploying:

- **Never** bake API keys into the image with `ENV` or `ARG` instructions. Pass them at runtime via `--env-file`.
- Run the container as a non-root user (add `USER nobody` or a dedicated app user to the Dockerfile).
- Mount `config.yaml` as a read-only volume: `-v ./config.yaml:/app/config.yaml:ro`.
- Scan images for CVEs before deployment: `docker scout cves` or `trivy image maverickj`.

### 7. MCP Server (`maverickj-mcp`)

The optional MCP server (`maverickj/mcp_server.py`) exposes debate functionality as a tool callable by external agents (e.g., Claude Desktop). This increases the attack surface significantly:

- **Authentication**: The MCP protocol does not provide built-in authentication. If the server is exposed beyond localhost, place it behind an authenticated reverse proxy.
- **Input validation**: All `topic` strings received over MCP must be treated as untrusted input — apply the same prompt-injection mitigations described in §2.
- **Rate limiting**: Apply rate limits at the transport layer to prevent cost exploitation.
- **Scope restriction**: Only expose the MCP server on `127.0.0.1` unless network exposure is explicitly required.

### 8. Data Privacy

Debate topics and intermediate agent outputs may contain sensitive business or personal information.

- Agent responses are accumulated in `DebateState` and passed to every subsequent agent. Do not include PII, trade secrets, or regulated data in debate topics unless your deployment environment satisfies applicable data-handling requirements.
- LLM providers (Anthropic, OpenAI, Google) may log API requests. Review their data retention and opt-out policies before submitting sensitive topics.
- Disable provider training opt-ins via their respective API console settings for production deployments.

---

## Security Checklist for Contributors

Before submitting a pull request:

- [ ] No API keys, tokens, or credentials committed to source.
- [ ] User-supplied strings handled through schema-validated boundaries, not raw string interpolation into prompts.
- [ ] New Pydantic models use closed enums and strict validators — no `extra="allow"`.
- [ ] New dependencies reviewed for known CVEs and added to lock file.
- [ ] `config.yaml` schema changes validated against `DebateConfig` on load.
- [ ] MCP endpoint changes reviewed for unauthenticated access risks.

---

## Known Limitations

- **Prompt injection** cannot be fully prevented at the engine level when topics come from untrusted sources. Operators deploying this engine as a service must add input filtering upstream.
- **Structured output** validation depends on LLM providers correctly following the schema. Model regressions may cause increased validation errors; monitor `ValidationError` rates in production.
- **Cost-based DoS**: There is no built-in per-session token budget enforcement. Operator-level rate limiting is required for multi-tenant deployments.
