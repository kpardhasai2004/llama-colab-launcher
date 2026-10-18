```python
#!/usr/bin/env python3
"""
llama-colab-launcher
Run GGUF chat models on Google Colab CPU using llama.cpp's
built-in Web UI and a Cloudflare Quick Tunnel.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_FILE = BASE_DIR / "models.json"

LLAMA_DIR = Path("/content/llama.cpp")
MODEL_DIR = Path("/content/gguf-models")
CLOUDFLARED_BIN = Path("/content/cloudflared")

DEFAULT_MODEL = "qwen25-3b"
DEFAULT_PORT = 8081
DEFAULT_THREADS = 2
DEFAULT_CONTEXT = 2048


def run_command(command, **kwargs):
    """Run a command and stop if it fails."""
    print("\n>>>", " ".join(map(str, command)), flush=True)
    subprocess.run(command, check=True, **kwargs)


def install_system_packages():
    """Install required build and download utilities."""
    if shutil.which("apt-get"):
        run_command(["apt-get", "update", "-y"])
        run_command([
            "apt-get", "install", "-y",
            "git",
            "cmake",
            "build-essential",
            "curl",
            "wget",
            "ca-certificates",
            "python3",
            "psmisc",
        ])
    else:
        print("Warning: apt-get not found; assuming dependencies are installed.")


def ensure_llama_cpp():
    """Clone and compile llama.cpp if needed."""
    server_binary = LLAMA_DIR / "build" / "bin" / "llama-server"

    if server_binary.exists():
        print(f"Using existing llama-server: {server_binary}")
        return server_binary

    if not LLAMA_DIR.exists():
        run_command([
            "git", "clone",
            "--depth", "1",
            "https://github.com/ggml-org/llama.cpp",
            str(LLAMA_DIR),
        ])

    run_command([
        "cmake",
        "-S", str(LLAMA_DIR),
        "-B", str(LLAMA_DIR / "build"),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGGML_NATIVE=OFF",
    ])

    run_command([
        "cmake",
        "--build", str(LLAMA_DIR / "build"),
        "--config", "Release",
        "--target", "llama-server",
        "-j", str(max(1, min(4, os.cpu_count() or 2))),
    ])

    if not server_binary.exists():
        raise RuntimeError("Build finished, but llama-server was not found.")

    return server_binary


def load_model_config(model_name):
    """Read the selected model's settings from models.json."""
    if not MODELS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {MODELS_FILE}. Add a models.json file to the repository."
        )

    with MODELS_FILE.open("r", encoding="utf-8") as file:
        models = json.load(file)

    if model_name not in models:
        available = ", ".join(models.keys())
        raise ValueError(
            f"Unknown model '{model_name}'. Available models: {available}"
        )

    config = models[model_name]

    url = config.get("url", "").strip()
    filename = config.get("filename", "").strip()

    if not url or url.startswith("REPLACE_") or url.startswith("DIRECT_"):
        raise ValueError(
            f"Model '{model_name}' has no valid download URL. "
            "Edit models.json and provide a direct GGUF download URL."
        )

    if not filename or Path(filename).name != filename:
        raise ValueError("The model filename must be a simple filename.")

    if not filename.lower().endswith(".gguf"):
        raise ValueError("The selected model file must have a .gguf extension.")

    return config


def download_model(config):
    """Download the selected GGUF file, reusing an existing valid-sized file."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / config["filename"]

    if model_path.exists() and model_path.stat().st_size > 1024 * 1024:
        print(f"Using cached model: {model_path}")
        return model_path

    partial_path = model_path.with_suffix(model_path.suffix + ".part")
    partial_path.unlink(missing_ok=True)

    print(f"Downloading model: {config['filename']}")
    print("Large GGUF files can take several minutes to download.")

    try:
        run_command([
            "curl",
            "-fL",
            "--retry", "3",
            "--retry-delay", "2",
            "--connect-timeout", "30",
            "--output", str(partial_path),
            config["url"],
        ])

        if not partial_path.exists() or partial_path.stat().st_size < 1024 * 1024:
            raise RuntimeError(
                "The downloaded file is too small to be a valid GGUF model. "
                "Check the model URL in models.json."
            )

        partial_path.replace(model_path)

    except Exception:
        partial_path.unlink(missing_ok=True)
        raise

    print(f"Model saved to: {model_path}")
    return model_path


def ensure_cloudflared():
    """Download Cloudflare's tunnel binary if necessary."""
    if CLOUDFLARED_BIN.exists():
        return CLOUDFLARED_BIN

    machine = platform.machine().lower()

    if machine in ("x86_64", "amd64"):
        architecture = "amd64"
    elif machine in ("aarch64", "arm64"):
        architecture = "arm64"
    else:
        raise RuntimeError(f"Unsupported CPU architecture: {machine}")

    url = (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        f"cloudflared-linux-{architecture}"
    )

    print("Downloading Cloudflare Tunnel...")
    run_command([
        "curl", "-fL", "--retry", "3",
        "-o", str(CLOUDFLARED_BIN), url,
    ])
    CLOUDFLARED_BIN.chmod(0o755)

    return CLOUDFLARED_BIN


def stop_process_on_port(port):
    """Stop a previous process listening on the selected port."""
    if not shutil.which("fuser"):
        return

    result = subprocess.run(
        ["fuser", "-k", f"{port}/tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if result.returncode == 0:
        time.sleep(1)


def wait_for_server(port, process, timeout=180):
    """Wait until llama-server responds to its health endpoint."""
    health_url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout

    print("Waiting for llama-server to become ready...", flush=True)

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "llama-server exited unexpectedly. "
                "Check its logs above for the cause."
            )

        try:
            request = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                if response.status == 200:
                    print("llama-server is ready.", flush=True)
                    return
        except Exception:
            pass

        time.sleep(2)

    raise TimeoutError(
        f"llama-server did not become ready within {timeout} seconds."
    )


def start_launcher(args):
    """Set up the model and launch the Web UI and public tunnel."""
    install_system_packages()

    server_binary = ensure_llama_cpp()
    config = load_model_config(args.model)
    model_path = download_model(config)
    cloudflared = ensure_cloudflared()

    context_size = args.context or int(
        config.get("context", DEFAULT_CONTEXT)
    )

    stop_process_on_port(args.port)

    server_command = [
        str(server_binary),
        "--model", str(model_path),
        "--host", "127.0.0.1",
        "--port", str(args.port),
        "--ctx-size", str(context_size),
        "--threads", str(args.threads),
    ]

    print("\nStarting llama.cpp Web UI...", flush=True)
    server_process = subprocess.Popen(server_command)

    tunnel_process = None

    try:
        wait_for_server(args.port, server_process)

        tunnel_command = [
            str(cloudflared),
            "tunnel",
            "--url", f"http://127.0.0.1:{args.port}",
            "--no-autoupdate",
            "--protocol", "http2",
        ]

        print("\nStarting Cloudflare Quick Tunnel...", flush=True)
        print(
            "Wait for a URL ending in .trycloudflare.com below.\n",
            flush=True,
        )

        tunnel_process = subprocess.Popen(
            tunnel_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        print("=" * 60)
        print("LLAMA.CPP WEB UI IS STARTING")
        print("Keep this Colab cell running while you use the UI.")
        print("=" * 60)

        for line in tunnel_process.stdout:
            print(line, end="", flush=True)

        if tunnel_process.poll() is not None:
            raise RuntimeError("Cloudflare Tunnel exited unexpectedly.")

    except KeyboardInterrupt:
        print("\nStopping launcher...", flush=True)

    finally:
        for process in (tunnel_process, server_process):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch a GGUF model with llama.cpp Web UI on Colab."
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model key from models.json (default: qwen25-3b).",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=None,
        help="Context size; uses the model's configured default if omitted.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help="CPU threads to use (default: 2).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Local Web UI port (default: 8081).",
    )

    args = parser.parse_args()

    if args.threads < 1:
        parser.error("--threads must be at least 1.")
    if args.port < 1 or args.port > 65535:
        parser.error("--port must be between 1 and 65535.")
    if args.context is not None and args.context < 1:
        parser.error("--context must be at least 1.")

    return args


def main():
    args = parse_args()

    try:
        start_launcher(args)
    except (RuntimeError, ValueError, FileNotFoundError, TimeoutError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"\nERROR: Command failed with exit code {exc.returncode}.",
            file=sys.stderr,
        )
        sys.exit(exc.returncode or 1)


if __name__ == "__main__":
    main()
```
