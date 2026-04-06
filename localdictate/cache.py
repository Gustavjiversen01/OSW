"""Model cache check — lightweight, no audio dependencies."""

from . import settings


def is_model_cached(model_id: str) -> bool:
    """Check if a model is already downloaded in the HuggingFace cache."""
    repo_id = settings.MODEL_REPOS.get(model_id, model_id)
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        return any(r.repo_id == repo_id for r in cache.repos)
    except Exception:
        return False
