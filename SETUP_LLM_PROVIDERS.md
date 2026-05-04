# VibeFactory LLM Provider Configuration

VibeFactory supports three different LLM providers. You can use any combination of them, and the UI will automatically detect which ones are available.

## Configuration

### 1. Create a `.env` file

Copy `.env.example` to `.env` in the VibeFactory directory:

```bash
cp .env.example .env
```

Then fill in the API keys for the providers you want to use.

---

## Provider Options

### Option 1: Inception Mercury-2 (Recommended for Reasoning)

**What it is:** Inception Labs' Mercury-2 is a reasoning-focused LLM with strong performance on complex tasks.

**Cost:** 10 million free tokens for new users; competitive pricing for additional tokens.

**Setup:**

1. Sign up at https://app.inceptionlabs.ai
2. Get your API key from the API Keys section of your dashboard
3. Add to your `.env` file:
   ```
   INCEPTION_API_KEY=your-api-key-here
   ```

**Documentation:** https://docs.inceptionlabs.ai/get-started/get-started

**Model identifier:** `mercury-2` (automatically selected in UI)

---

### Option 2: OpenRouter (Free & Diverse Models)

**What it is:** OpenRouter provides access to dozens of LLMs including free models.

**Cost:** Free tier with Llama 3.3 70B, paid tier for additional models.

**Setup:**

1. Sign up at https://openrouter.ai
2. Get your API key from https://openrouter.ai/keys
3. Add to your `.env` file:
   ```
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
   ```

**Documentation:** https://openrouter.ai/docs

**Default model:** `meta-llama/llama-3.3-70b-instruct:free` (can change in UI)

---

### Option 3: Ollama (Local, Free, Private)

**What it is:** Run open-source LLMs locally on your machine. No API key needed, completely private.

**Cost:** Free (you provide the compute)

**Setup:**

1. Download Ollama from https://ollama.ai
2. Start the Ollama service:
   ```bash
   ollama serve
   ```
3. Pull a model (e.g., Qwen):
   ```bash
   ollama pull qwen2.5:7b
   # or larger variants:
   ollama pull qwen3.5:7b
   ollama pull qwen3.5:14b
   ```
4. VibeFactory automatically detects Ollama at `http://localhost:11434` — no `.env` configuration needed

**Available models:** Qwen, Llama, Mistral, and hundreds of others from https://ollama.ai/library

---

## Environment Variables Reference

| Variable | Provider | Required | Example |
|----------|----------|----------|---------|
| `INCEPTION_API_KEY` | Inception Mercury-2 | No | `incp_...` (your API key) |
| `OPENROUTER_API_KEY` | OpenRouter | No | `sk-or-v1-...` |
| (none) | Ollama | No | (automatic localhost detection) |

**Note:** You must configure at least one provider for the app to work.

---

## GitHub & Secrets Management

### For GitHub Actions or Deployment

If deploying to GitHub (CI/CD, Actions, or cloud), store your API keys as **GitHub Secrets**:

1. Go to your repository: Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret:
   - Name: `INCEPTION_API_KEY`, Value: your Inception API key
   - Name: `OPENROUTER_API_KEY`, Value: your OpenRouter API key
4. In your GitHub Actions workflow (`.github/workflows/*.yml`), reference them:
   ```yaml
   env:
     INCEPTION_API_KEY: ${{ secrets.INCEPTION_API_KEY }}
     OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
   ```

**Important:** Never commit your `.env` file to GitHub. Add it to `.gitignore`:
```
# .gitignore
.env
.env.local
*.pyc
__pycache__/
```

---

## Which Provider Should I Use?

### For Development (Local)
- **Best:** Ollama (private, free, no API key)
- **Good:** OpenRouter (free tier)
- **Premium:** Inception (10M free tokens)

### For Complex Reasoning
- **Best:** Inception Mercury-2 (built for reasoning)
- **Good:** OpenRouter (access to Llama, Claude variants)

### For Cost-Conscious Production
- **Best:** Ollama (free compute if you own hardware)
- **Good:** OpenRouter (pay per token, transparent pricing)

### For Simplicity
- **Best:** OpenRouter (large variety, one endpoint)
- **Good:** Inception (focused selection, high quality)

---

## Troubleshooting

### "LLM Provider not available"
- Ensure you have at least one API key in `.env` or Ollama running
- Check file permissions: `.env` should be readable by the app
- Reload the page; providers are detected on startup

### "Ollama not running"
- Start Ollama: `ollama serve`
- Check it's accessible: `curl http://localhost:11434/api/tags`

### "API key invalid"
- Double-check the key is correct in your `.env` file
- No extra spaces or quotes
- File should use `KEY=value` format, not `KEY: value`

### Inception API fails
- Verify your API key is enabled in https://app.inceptionlabs.ai/dashboard
- Check you haven't exceeded your token quota
- Ensure you're using the correct key (not from another Inception product)

---

## Advanced: Custom Model Selection

In the VibeFactory UI, you can select different models within each provider:

- **Inception:** Only Mercury-2 available currently
- **OpenRouter:** Change the model dropdown to use different models (Llama, Claude, etc.)
- **Ollama:** Models automatically listed from your local Ollama instance

The selected model persists in your browser's localStorage across sessions.
