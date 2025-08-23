from .local_model import LocalCategorizer
_provider = LocalCategorizer()

def predict_account_code(*, payee: str, narrative: str = "", amount):
    return _provider.predict(payee=payee, narrative=narrative or "", amount=float(amount))
