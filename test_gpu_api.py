import requests

GPU_QWEN_URL = "https://brainmagictechnova--product-catalog-qwen-generate.modal.run"

response = requests.post(
    GPU_QWEN_URL,
    json={
        "prompt": "Explain what a product catalog is in one sentence."
    },
    timeout=300,
)

print("Status:", response.status_code)
print("Response:", response.json())