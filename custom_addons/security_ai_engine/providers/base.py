from collections import namedtuple

# Structured return value from every provider call
AIResult = namedtuple("AIResult", ["text", "tokens_in", "tokens_out"])


class AIProviderBase:
    """
    Abstract base for all AI provider implementations.

    Subclasses must implement complete(), which now returns an AIResult
    namedtuple carrying the response text AND token usage counters.
    """

    DEFAULT_MAX_TOKENS = 1500
    DEFAULT_TEMPERATURE = 0.3

    def __init__(self, api_key, model_override=None):
        if not api_key:
            raise ValueError(f"{self.__class__.__name__}: API key is required.")
        self.api_key = api_key
        self.model_override = model_override

    def complete(self, system_prompt, user_message, max_tokens=None, temperature=None):
        """
        Send a prompt to the AI provider and return an AIResult.

        :param system_prompt: Role / instruction context for the model.
        :param user_message:  The actual data/question to analyse.
        :param max_tokens:    Override token limit for this call.
        :param temperature:   Override temperature for this call.
        :returns:             AIResult(text, tokens_in, tokens_out)
        :raises:              RuntimeError on API or network error.
        """
        raise NotImplementedError
