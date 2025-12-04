"""
Simple test script to verify the LLM model is working.
Sends a "Hello" prompt and prints the response.
"""

from mlx_lm import load, generate

# Use the same model as in flag-malformed.py
MODEL_PATH = "mlx-community/Qwen2.5-7B-Instruct-4bit"

def main():
    print(f"Loading model: {MODEL_PATH}")

    # Load model and tokenizer with mlx_lm
    model, tokenizer = load(MODEL_PATH)

    prompt = "Hi"
    # Format as chat message for instruct model
    messages = [{"role": "user", "content": prompt}]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    print(f"\nPrompt: {messages[0]['content']}")
    print("\nGenerating response...")

    response = generate(model, tokenizer, prompt=prompt, max_tokens=50)

    print(f"\nResponse:\n{response}")


if __name__ == "__main__":
    main()
