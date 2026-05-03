# 🚀 Local Model Setup Guide for VibeFactory

## Overview
VibeFactory is now configured to use **local Qwen3.5** model via **Ollama**. This means:
- ✅ **100% Free** - No API costs
- ✅ **100% Private** - Your data never leaves your machine
- ✅ **Unlimited** - No rate limits or quotas
- ✅ **Offline** - Works without internet

## Quick Setup

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
- Download from: https://ollama.ai
- Run the installer

### 2. Pull Qwen3.5 Model

```bash
# For most systems (8GB+ RAM)
ollama pull qwen3.5:7b

# For better quality (32GB+ RAM)
ollama pull qwen3.5:32b

# For best quality (64GB+ RAM)
ollama pull qwen3.5:72b
```

### 3. Start Ollama

**macOS/Windows:**
- Ollama starts automatically when you install
- Check the menu bar/system tray for the Ollama icon

**Linux:**
```bash
ollama serve
```

### 4. Run Interactive Setup

```bash
cd /Users/brettevanssf/Code/Saasless/VibeFactory
source venv/bin/activate
python setup_local.py
```

This will:
- Check if Ollama is installed and running
- Pull the Qwen3.5 model if needed
- Update configuration files
- Test the connection

### 5. Run VibeFactory

```bash
streamlit run app.py
```

## System Requirements

| Model | RAM Required | Speed | Quality |
|-------|-------------|-------|---------|
| **qwen3.5:7b** | 8GB min, 16GB rec | Fast | Good |
| **qwen3.5:14b** | 16GB min, 32GB rec | Medium | Very Good |
| **qwen3.5:32b** | 32GB min, 64GB rec | Slower | Excellent |
| **qwen3.5:72b** | 64GB min, 128GB rec | Slow | Best |

## Available Models

### Qwen3.5 Series (Recommended)
```bash
ollama pull qwen3.5:7b   # Best for most systems
ollama pull qwen3.5:14b  # Better quality
ollama pull qwen3.5:32b  # Excellent quality
ollama pull qwen3.5:72b  # Best quality (requires powerful hardware)
```

### Alternative Models
```bash
ollama pull llama3.2:3b   # Very fast, less capable
ollama pull llama3.2:1b   # Ultra fast, basic tasks
ollama pull mistral:7b    # Good alternative
ollama pull codellama:7b  # Code-focused
```

## Configuration

### Changing the Model

**Via Setup Script:**
```bash
python setup_local.py
```

**Manually in Code:**

In `orchestrator.py` and `engineer.py`:
```python
llm_model: str = Field(
    default="qwen3.5:7b",  # Change this
    ...
)
```

**Via Environment Variable:**
```bash
export LOCAL_MODEL="qwen3.5:32b"
```

### Ollama Host Configuration

If Ollama is running on a different host:
```bash
export OLLAMA_HOST="http://your-server:11434"
```

## Troubleshooting

### "Ollama not found"
```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai
```

### "Ollama not running"
```bash
# Start Ollama
ollama serve

# On macOS/Windows, check if the app is running
# Look for Ollama icon in menu bar/system tray
```

### "Model not found"
```bash
# Pull the model
ollama pull qwen3.5:7b

# List available models
ollama list
```

### "Out of memory"
```bash
# Use a smaller model
ollama pull qwen3.5:7b

# Close other applications
# Increase swap space (Linux)
```

### "Slow generation"
```bash
# Use a smaller model
ollama pull qwen3.5:7b

# Use GPU acceleration (if available)
# Ollama automatically uses GPU when available
```

## Performance Tips

### 1. Use GPU Acceleration
- Ollama automatically uses GPU when available
- NVIDIA GPUs work best
- Apple Silicon (M1/M2/M3) has excellent support

### 2. Model Quantization
- Smaller quantizations = faster, less RAM
- `qwen3.5:7b-q4_K_M` = 4-bit quantization
- Default models are already optimized

### 3. Parallel Processing
```bash
# Set number of threads
export OLLAMA_NUM_THREADS=8

# Set GPU layers
export OLLAMA_NUM_GPU=35
```

### 4. Keep Model Loaded
```bash
# Keep model in memory
ollama run qwen3.5:7b " "

# Or use keep-alive
export OLLAMA_KEEP_ALIVE=5m
```

## Advanced Usage

### Running Multiple Models
```bash
# Pull multiple models
ollama pull qwen3.5:7b
ollama pull qwen3.5:32b

# Run specific model
ollama run qwen3.5:7b
ollama run qwen3.5:32b
```

### API Access
```bash
# Ollama provides REST API at http://localhost:11434

# Test API
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:7b",
  "prompt": "Hello"
}'
```

### Docker Support
```bash
# Run Ollama in Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull model in container
docker exec ollama ollama pull qwen3.5:7b
```

## Monitoring

### Check Model Status
```bash
ollama list
ollama ps
```

### Check Resource Usage
```bash
# macOS
top | grep ollama

# Linux
htop | grep ollama

# Windows
Task Manager → Performance
```

### View Logs
```bash
# macOS
tail -f ~/Library/Logs/ollama/server.log

# Linux
journalctl -u ollama -f
```

## Benefits of Local Models

### ✅ Advantages
- **Free**: No API costs, unlimited usage
- **Private**: Data never leaves your machine
- **Unlimited**: No rate limits or quotas
- **Offline**: Works without internet
- **Customizable**: Fine-tune models yourself

### ⚠️ Considerations
- **Hardware**: Requires good RAM and CPU/GPU
- **Speed**: Slower than cloud APIs
- **Quality**: May be less capable than largest cloud models
- **Setup**: Requires local installation

## Comparison: Local vs Cloud

| Feature | Local (Ollama) | Cloud (OpenRouter) |
|---------|---------------|-------------------|
| Cost | Free | Free tier + paid |
| Privacy | 100% private | Data sent to provider |
| Speed | Depends on hardware | Usually faster |
| Limits | None | Rate limits apply |
| Setup | Install Ollama | Get API key |
| Offline | ✅ Yes | ❌ No |
| RAM Required | 8-128GB | None |

## Next Steps

1. ✅ Install Ollama
2. ✅ Pull Qwen3.5 model
3. ✅ Run `python setup_local.py`
4. ✅ Test the connection
5. 🎉 Run VibeFactory with local AI!

## Resources

- **Ollama**: https://ollama.ai
- **Models**: https://ollama.ai/library
- **Documentation**: https://github.com/ollama/ollama
- **Qwen3.5**: https://ollama.ai/library/qwen3.5

## Support

If you encounter issues:
1. Check if Ollama is running: `ollama ps`
2. Verify model is pulled: `ollama list`
3. Check system resources: `top` or `htop`
4. Review Ollama logs

---

**Enjoy building with your local AI! 🚀**

No costs. No limits. 100% private.
