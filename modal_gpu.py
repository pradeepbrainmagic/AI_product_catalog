import modal

app = modal.App("product-catalog-gpu-test")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch")
)


@app.function(
    image=image,
    gpu="T4",
)
def gpu_test():
    import torch

    return {
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else None,
    }


@app.local_entrypoint()
def main():
    result = gpu_test.remote()
    print(result)