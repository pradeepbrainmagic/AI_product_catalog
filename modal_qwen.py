import modal

app = modal.App("product-catalog-qwen")

volume = modal.Volume.from_name("qwen-model-cache", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "zstd")
    .pip_install("fastapi")
    .run_commands(
        "curl -fsSL https://ollama.com/install.sh | sh"
    )
)


@app.function(
    image=image,
    gpu="T4",
    timeout=1800,
    volumes={"/root/.ollama": volume},
)
@modal.fastapi_endpoint(method="POST")
def generate(request: dict):
    import subprocess
    import time

    prompt = request.get("prompt", "").strip()

    if not prompt:
        return {
            "error": "prompt is required"
        }

    # Start Ollama
    server = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(5)

    # Make sure model exists
    pull = subprocess.run(
        ["ollama", "pull", "qwen2.5:7b"],
        capture_output=True,
        text=True,
    )

    if pull.returncode != 0:
        return {
            "error": "Failed to load Qwen2.5:7B",
            "details": pull.stderr,
        }

    # Generate response
    response = subprocess.run(
        [
            "ollama",
            "run",
            "qwen2.5:7b",
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    return {
        "response": response.stdout.strip()
    }