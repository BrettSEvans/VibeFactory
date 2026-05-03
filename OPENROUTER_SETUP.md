# 🚀 OpenRouter Setup Guide for VibeFactory

## Overview
VibeFactory is now configured to use **OpenRouter** with **Llama 3.3-70B** model. OpenRouter provides access to multiple LLMs through a single API, with generous free tiers.

## Quick Setup

### 1. Get Your OpenRouter API Key

1. Go to **https://openrouter.ai/keys**
2. Sign up or log in
3. Click "New API Key"
4. Give it a name (e.g., "VibeFactory")
5. Copy the key (starts with `sk-or-`)

### 2. Set the API Key

**Option A: Temporary (current session only)**
```bash
export OPENROUTER_API_KEY='sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
```

**Option B: Permanent (save to .env file)**
```bash
cd /Users/brettevanssf/Code/Saasless/VibeFactory
python setup_openrouter.py
```
This interactive script will:
- Ask for your API key
- Save it to `.env` file
- Test the connection

### 3. Install Dependencies

```bash
cd /Users/brettevanssf/Code/Saasless/VibeFactory
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Test the Connection

```bash
python openrouter_config.py
```

You should see:
```
✅ OpenRouter configured successfully!
   Model: meta-llama/llama-3.3-70b-instruct:free
   API Key: Set

🧪 Testing connection...
✅ OpenRouter connection test successful!
```

### 5. Run VibeFactory

```bash
streamlit run app.py
```

## Available Models on OpenRouter

### Free Tier Models (No Credit Card Required)

| Model | Size | Use Case |
|-------|------|----------|
| `meta-llama/llama-3.3-70b-instruct:free` | 70B | **Recommended** - Best balance |
| `meta-llama/llama-3.1-8b-instruct:free` | 8B | Fast, lightweight tasks |
| `mistralai/mistral-nemo:free` | 12B | Good alternative |
| `google/gemma-7b-it:free` | 7B | Quick tasks |

### Paid Models (Require Credits)

| Model | Size | Price | Use Case |
|-------|------|-------|----------|
| `meta-llama/llama-3.1-405b-instruct:free` | 405B | Free tier available | Most capable |
| `anthropic/claude-3.5-sonnet` | - | Paid | Best for code |
| `openai/gpt-4o` | - | Paid | General purpose |

## Configuration

### Default Model
The system is configured to use:
```
meta-llama/llama-3.3-70b-instruct:free
```

### Changing the Model

**In the code** (`orchestrator.py` and `engineer.py`):
```python
# Change this line:
llm_model: str = Field(
    default="meta-llama/llama-3.3-70b-instruct:free",
    ...
)

# To:
llm_model: str = Field(
    default="meta-llama/llama-3.1-405b-instruct:free",
    ...
)
```

**Via environment variable**:
```bash
export VIBEFACTORY_LLM_MODEL="meta-llama/llama-3.1-405b-instruct:free"
```

## Rate Limits & Quotas

### Free Tier Limits
- **Requests per minute**: Varies by model
- **Daily quota**: Available for most free models
- **Concurrent requests**: Limited

### Tips for Best Performance
1. **Start with 70B model** - Good balance of quality and speed
2. **Use 8B for quick tasks** - Faster for simple critiques
3. **Monitor usage** - Check OpenRouter dashboard
4. **Cache responses** - Avoid redundant API calls

## Troubleshooting

### "API Key Invalid"
```
❌ OpenRouter connection test failed: Invalid API Key
```
**Solution**: 
- Double-check you copied the entire key
- Keys start with `sk-or-v1-`
- Regenerate key if unsure

### "Rate Limit Exceeded"
```
❌ Error: Rate limit exceeded for model
```
**Solution**:
- Wait a few minutes
- Switch to a smaller model (8B or 12B)
- Add credits to your account

### "Model Not Found"
```
❌ Error: Model not found
```
**Solution**:
- Check model name is correct
- Visit https://openrouter.ai/models to verify
- Try a different model

### "Insufficient Credits"
```
❌ Error: Insufficient credits
```
**Solution**:
- Add credits at https://openrouter.ai/credits
- Free tier models don't require credits
- Switch to a free model

## Cost Estimation

### Free Tier Models
- **Completely free** for most use cases
- No credit card required
- Generous daily limits

### Paid Models (if you choose)
- **Per 1M tokens**: ~$0.20 - $3.00
- **Average project**: ~50,000 - 200,000 tokens
- **Estimated cost**: $0.01 - $0.10 per project

## Security Best Practices

### 1. Never Commit API Keys
```bash
# ✅ Good - .env is in .gitignore
echo "OPENROUTER_API_KEY=sk-or-..." > .env

# ❌ Bad - Don't hardcode in source
api_key = "sk-or-..."  # Never do this!
```

### 2. Use .env File
```bash
# Create .env file
cat > .env << EOF
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF

# Load in Python
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
```

### 3. Rotate Keys Periodically
- Create new key every 3-6 months
- Revoke old keys
- Update .env file

## Advanced Configuration

### Custom Temperature
```python
# In orchestrator.py or engineer.py
response = self.client.chat.completions.create(
    model=self.config.llm_model,
    messages=messages,
    temperature=0.8,  # Higher = more creative
    max_tokens=8000
)
```

### Custom Max Tokens
```python
max_tokens=16000  # For longer responses
```

### Multiple Models
```python
# Use different models for different tasks
orchestrator_config = OrchestratorConfig(llm_model="meta-llama/llama-3.3-70b-instruct:free")
engineer_config = EngineerConfig(llm_model="meta-llama/llama-3.1-8b-instruct:free")
```

## Next Steps

1. ✅ Get API key from OpenRouter
2. ✅ Run `python setup_openrouter.py`
3. ✅ Test connection
4. ✅ Run `streamlit run app.py`
5. 🎉 Start building with AI!

## Resources

- **OpenRouter**: https://openrouter.ai
- **Models**: https://openrouter.ai/models
- **Documentation**: https://openrouter.ai/docs
- **Dashboard**: https://openrouter.ai/keys
- **Pricing**: https://openrouter.ai/pricing

## Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Visit OpenRouter Discord: https://discord.gg/openrouter
3. Check OpenRouter status: https://openrouter.ai/status

---

**Ready to build amazing software with AI! 🚀**
