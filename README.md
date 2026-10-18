# 🚀 Llama Colab Launcher

<p align="center">
  <strong>Run GGUF chat models on Google Colab CPU with llama.cpp's native Web UI.</strong>
</p>


**Llama Colab Launcher** is a simple launcher for running GGUF language models on Google Colab using CPU inference and the built-in Web UI provided by `llama.cpp`.

It automates dependency installation, builds `llama.cpp`, downloads your selected model, starts the chat interface, and creates a public Cloudflare Quick Tunnel URL.

No Gradio required. No separate frontend to build.

## 🚀 Quick Start

### 1. Open Google Colab

Open [Google Colab](https://colab.research.google.com/) and create a new notebook.

Select a **CPU runtime** from the runtime settings.

### 2. Run the Launcher

Paste the following command into a Colab code cell:

```python
!git clone https://github.com/kpardhasai2004/llama-colab-launcher.git /content/llama-colab-launcher && python /content/llama-colab-launcher/setup.py --model qwen25-3b
```

The launcher will:

1. Install required system packages.
2. Download and build `llama.cpp` if needed.
3. Download the selected GGUF model if it is not already cached.
4. Start the `llama-server` process.
5. Start the Cloudflare Quick Tunnel.
6. Print the tunnel logs, including the public URL when Cloudflare provides it.

### 3. Open the Chat Interface

Wait for a URL similar to:

```text
https://example-name.trycloudflare.com
```

Open the actual URL printed in your Colab output to access the chat interface.

**Keep the Colab cell running** while using the interface. Stopping the cell or disconnecting the runtime will stop the server and tunnel.

## 🧠 Available Models

The launcher reads model configurations from `models.json`.

The default configuration uses:

| Setting | Value |
|---|---|
| Model | Qwen2.5 3B Instruct |
| Quantization | Q4_K_M |
| Format | GGUF |
| Default context | 2048 tokens |
| Default CPU threads | 2 |
| Web UI port | 8081 |

Model download links can change, so verify that the configured URL exists before launching.

## 🔄 Switching Models

Open `models.json` and add or modify a model entry.

Example:

```json
{
  "qwen25-3b": {
    "description": "Qwen2.5 3B Instruct - Q4_K_M",
    "url": "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf",
    "filename": "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
    "context": 2048
  },
  "custom": {
    "description": "Custom GGUF model",
    "url": "REPLACE_WITH_DIRECT_GGUF_DOWNLOAD_URL",
    "filename": "my-model.gguf",
    "context": 2048
  }
}
```

Replace the custom URL with a direct download link to a compatible GGUF file before using that entry.

Launch the default model:

```python
!python /content/llama-colab-launcher/setup.py --model qwen25-3b
```

Launch your custom model:

```python
!python /content/llama-colab-launcher/setup.py --model custom
```

**Important:** Stop the currently running Colab cell before switching models. The `custom` entry will not work until its placeholder URL is replaced.

## ⚙️ Command-Line Options

The launcher supports the following options:

| Option | Default | Description |
|---|---|---|
| `--model` | `qwen25-3b` | Model key from `models.json` |
| `--context` | Model configuration | Context window size |
| `--threads` | `2` | CPU inference threads |
| `--port` | `8081` | Local Web UI port |

### Examples

Use four CPU threads:

```python
!python /content/llama-colab-launcher/setup.py --model qwen25-3b --threads 4
```

Change the context size:

```python
!python /content/llama-colab-launcher/setup.py --model qwen25-3b --context 4096
```

Use a different local port:

```python
!python /content/llama-colab-launcher/setup.py --model qwen25-3b --port 8082
```

These settings depend on available RAM and CPU resources. Larger contexts and models require more memory and may run slowly on CPU.

## 📁 Project Structure

```text
llama-colab-launcher/
├── setup.py       # Automated setup and launch script
├── models.json    # Model URLs and configurations
└── README.md      # Project documentation
```

## ✨ Features

- 🚀 **One-command launch** — start your model directly from a Colab cell.
- 🧠 **GGUF model support** — run compatible GGUF models supported by `llama.cpp`.
- 💬 **Native chat interface** — use the built-in `llama.cpp` Web UI.
- 🔗 **Public access** — access the interface through a Cloudflare Quick Tunnel.
- 📦 **Automatic setup** — install required system packages and build `llama.cpp`.
- 📥 **Automatic model download** — download the configured GGUF model.
- ⚡ **Model caching** — reuse downloaded models in the same Colab runtime.
- 🔄 **Easy model switching** — configure multiple models in `models.json`.
- ⚙️ **Configurable inference** — adjust context size, CPU threads, and port.
- 🖥️ **CPU-focused** — designed for Colab CPU runtimes without requiring a GPU.

## 🛠️ How It Works

```text
Google Colab Notebook
        |
        v
   setup.py Launcher
        |
        +---- Install Dependencies
        |
        +---- Build llama.cpp
        |
        +---- Download GGUF Model
        |
        v
   llama-server
        |
        v
  Built-in Web UI
        |
        v
 Cloudflare Quick Tunnel
        |
        v
  Open Chat in Browser
```



## 🧰 Troubleshooting

<details>
<summary><strong>Cloudflare URL does not appear</strong></summary>

- Wait for the tunnel process to start.
- Check the Colab output for Cloudflare errors.
- Confirm that `llama-server` successfully started and passed its health check.
- Restart the launcher cell if necessary.

</details>

<details>
<summary><strong>Model download fails</strong></summary>

- Verify the URL in `models.json`.
- Ensure the URL points to the intended GGUF file.
- Check whether the model repository requires authentication or accepts direct downloads.
- Confirm that enough disk space is available in the Colab runtime.

</details>

<details>
<summary><strong>Out-of-memory errors</strong></summary>

- Try a smaller GGUF model.
- Use a lower context size, such as `--context 1024`.
- Close other processes consuming RAM.
- Prefer smaller quantizations when available.

</details>

<details>
<summary><strong>Chat responses are slow</strong></summary>

CPU inference speed depends on the model size, quantization, CPU allocation, and context length.

- Try a smaller instruct model.
- Adjust `--threads` to suit the available CPU resources.
- Reduce the context size if memory usage is high.
- Allow the first model load to finish before sending prompts.

</details>

<details>
<summary><strong>Port is already in use</strong></summary>

Stop the existing launcher cell before starting another instance, or choose another port:

```python
!python /content/llama-colab-launcher/setup.py --model qwen25-3b --port 8082
```

</details>

## 🔐 Security Notes

- Cloudflare Quick Tunnels provide a publicly reachable URL. Anyone who obtains that URL may be able to access your interface.
- Do not enter passwords, API keys, private documents, or other sensitive information.
- Do not assume the public interface has authentication enabled.
- Stop the Colab cell when you finish using the launcher.
- Review the licenses and usage restrictions of the GGUF model you download.

## 🙌 Credits

This project builds on the work of:

- [llama.cpp](https://github.com/ggml-org/llama.cpp) — local LLM inference and the built-in Web UI.
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — public tunnel connectivity.
- [Google Colab](https://colab.research.google.com/) — hosted notebook environment.
- Model authors and publishers — for the GGUF-compatible model files and their respective licenses.

## ⭐ Support

If this project helps you, consider giving the repository a ⭐ on GitHub!

**Repository:** https://github.com/kpardhasai2004/llama-colab-launcher
