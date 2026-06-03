import requests

from .base import AIProviderBase, AIResult

_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(AIProviderBase):

    def complete(self, system_prompt, user_message, max_tokens=None, temperature=None):
        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        model = self.model_override or _DEFAULT_MODEL

        try:
            resp = requests.post(
                _OPENAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=90,
            )
            resp.raise_for_status()
            body = resp.json()
            text = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            return AIResult(
                text=text,
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"OpenAI API error {exc.response.status_code}: {exc.response.text[:400]}"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenAI network error: {exc}") from exc
