"""Model name validators for each provider."""

import logging
from .model_catalog import get_known_models

logger = logging.getLogger(__name__)

VALID_MODELS = {
    provider: models
    for provider, models in get_known_models().items()
    if provider not in ("ollama", "lmstudio", "openrouter", "aihubmix", "custom_openai")
}


def validate_model(provider: str, model: str) -> bool:
    provider_lower = provider.lower()

    if provider_lower in ("ollama", "lmstudio", "openrouter", "aihubmix", "custom_openai"):
        return True

    if provider_lower not in VALID_MODELS:
        logger.warning(f"Unknown provider '%s', allowing model '%s' without validation", provider, model)
        return True

    if model not in VALID_MODELS[provider_lower]:
        logger.warning(f"Model '%s' not found in provider '%s' valid models: %s", model, provider, VALID_MODELS[provider_lower])
        return False

    return True
