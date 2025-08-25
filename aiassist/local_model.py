import joblib, os, re
from pathlib import Path
from typing import Tuple
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import numpy as np
from .providers import Categorizer

MODEL_PATH = Path(os.environ.get("AI_MODEL_PATH", ".model/category.joblib"))


class LocalCategorizer(Categorizer):
    def __init__(self):
        if MODEL_PATH.exists():
            self.model = joblib.load(MODEL_PATH)
        else:
            self.model = None

    def predict(
        self, *, payee: str, narrative: str, amount: float
    ) -> Tuple[str, float]:
        if not self.model:
            return ("5000", 0.10)  # fallback default to Office Supplies
        X = [[f"{payee} {narrative or ''}", float(amount)]]
        probs = self.model.predict_proba(X)[0]
        idx = probs.argmax()
        return (self.model.classes_[idx], float(probs[idx]))


def train_from_ledger(lines_qs):
    """
    lines_qs: queryset of EntryLine joined with Transaction and Account
    using: payee/narrative from a linked BankTransaction or line.description
    """
    rows = []
    for l in lines_qs.select_related("account", "transaction"):
        text = getattr(l, "description", "") or ""
        amt = float(abs(l.debit or l.credit))
        rows.append((f"{text}", amt, l.account.code))
    if not rows:
        return
    texts = [r[0] for r in rows]
    amounts = [[r[1]] for r in rows]
    y = [r[2] for r in rows]

    text_vec = HashingVectorizer(n_features=2**15, lowercase=True, ngram_range=(1, 2))
    amt_bins = KBinsDiscretizer(n_bins=8, encode="onehot-dense", strategy="quantile")
    ct = ColumnTransformer(
        [
            ("text", text_vec, 0),
            ("amt", amt_bins, [1]),
        ]
    )
    clf = LogisticRegression(max_iter=200)
    pipe = Pipeline(steps=[("ct", ct), ("clf", clf)])
    X = list(zip(texts, amounts))
    X_arr = [[t, a[0]] for t, a in X]
    pipe.fit(X_arr, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
