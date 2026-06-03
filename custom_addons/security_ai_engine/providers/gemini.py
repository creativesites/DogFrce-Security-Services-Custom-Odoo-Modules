import requests

from .base import AIProviderBase, AIResult

_GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)
_DEFAULT_MODEL = "gemini-1.5-pro"


class GeminiProvider(AIProviderBase):

    def complete(self, system_prompt, user_message, max_tokens=None, temperature=None):
        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        model = self.model_override or _DEFAULT_MODEL
        url = _GEMINI_URL_TEMPLATE.format(model=model, key=self.api_key)
        combined = f"{system_prompt}\n\n{user_message}"

        try:
            resp = requests.post(
                url,
                json={
                    "contents": [{"role": "user", "parts": [{"text": combined}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": temperature,
                    },
                },
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return AIResult(
                text=text,
                tokens_in=usage.get("promptTokenCount", 0),
                tokens_out=usage.get("candidatesTokenCount", 0),
            )
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Gemini API error {exc.response.status_code}: {exc.response.text[:400]}"
            ) from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Gemini network error: {exc}") from exc
