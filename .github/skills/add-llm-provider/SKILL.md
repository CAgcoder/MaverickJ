---
name: add-llm-provider
description: "Add a new LLM provider to the debate engine. Use when integrating a new AI model provider (e.g., Mistral, Llama, Deepseek, Cohere, local Ollama), configuring API keys, or extending model routing."
argument-hint: "Name the provider and model to add (e.g., Mistral, Ollama)"
---
# Add a New LLM Provider

## When to Use

- Integrating a new cloud LLM provider (Mistral, Cohere, Deepseek, etc.)
- Adding local model support (Ollama, vLLM, etc.)
- Extending the ModelRouter with a new backend

## Procedure

### Step 1: Install LangChain Integration

Find the appropriate LangChain community package:

```bash
pip install langchain-{provider}
```

Add it to `pyproject.toml` dependencies:

```toml
dependencies = [
    # ... existing deps
    "langchain-{provider}>=X.Y.Z",
]
```

### Step 2: Extend the Factory

In `src/llm/factory.py`, add a new case in `create_model()`:

```python
def create_model(assignment: ModelAssignment) -> BaseChatModel:
    if assignment.provider == "{provider}":
        from langchain_{provider} import Chat{Provider}
        return Chat{Provider}(
            model=assignment.model,
            temperature=assignment.temperature,
            max_tokens=assignment.max_tokens,
        )
    # ... existing providers
```

### Step 3: Add Provider to Config Schema

In `src/schemas/config.py`, extend the `provider` field in `ModelAssignment`:

```python
provider: Literal["claude", "openai", "gemini", "{provider}"]
```

### Step 4: Add Pricing

In `src/llm/cost.py`, add entries to `MODEL_PRICING`:

```python
MODEL_PRICING = {
    # ... existing entries
    "{model-name}": {"input": X.XX, "output": X.XX},  # per 1M tokens
}
```

### Step 5: Document Environment Variable

The API key should follow the LangChain convention (auto-loaded from env):
- Add to `.env.example`: `{PROVIDER}_API_KEY=xxxxx`
- Document in `config.yaml` comments

### Step 6: Test

```bash
# Verify the model loads
python -c "from src.llm.factory import create_model; ..."

# Run with the new provider
# Update config.yaml:
# default_provider: {provider}
# default_model: {model-name}

debate-interactive
```

## Checklist

- [ ] LangChain integration package installed and in `pyproject.toml`
- [ ] Factory case added in `create_model()`
- [ ] Provider literal added to `ModelAssignment.provider`
- [ ] Pricing added to `MODEL_PRICING`
- [ ] API key documented in `.env.example`
- [ ] Smoke test passes with new provider
