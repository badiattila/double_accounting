from .local_model import LocalCategorizer, MODEL_PATH

# Lazily create (and if needed reload) the provider so tests or runtime
# can remove/create the model file without leaving a stale instance.
_provider = None

def _get_provider():
    global _provider
    if _provider is None:
        _provider = LocalCategorizer()
        return _provider
    # if a model file appears on disk after the provider was created with no model,
    # recreate it so predictions use the newly written model.
    if getattr(_provider, "model", None) is None and MODEL_PATH.exists():
        _provider = LocalCategorizer()
    return _provider


def predict_account_code(*, payee: str, narrative: str = "", amount=None):
    provider = _get_provider()
    return provider.predict(payee=payee, narrative=narrative or "", amount=float(amount))
