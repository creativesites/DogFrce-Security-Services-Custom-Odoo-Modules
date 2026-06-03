import requests

from .base import AIProviderBase, AIResult

_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_DEFAULT_MODEL = "claude-sonnet-4-6"


class ClaudeProvider(AIProviderBase):

    def complete(self, system_prompt, user_message, max_tokens=None, temperature=None):
        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        model = self.model_override or _DEFAULT_MODEL

        try:
            resp = requests.post(
                _ANTHROPIC_MESSAGES_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            usage = data.get("usage", {})
            return AIResult(
                text=text,
                tokens_in=usage.get("input_tokens", 0),
                tokens_out=usage.get("output_tokens", 0),
            )
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Claude API error {exc.response.status_code}: {exc.response.text[:400]}"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Claude network error: {exc}") from exc
