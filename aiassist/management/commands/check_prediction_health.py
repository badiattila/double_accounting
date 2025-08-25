from django.core.management.base import BaseCommand
from pathlib import Path
import joblib
import json

DEFAULT_MODEL_PATH = Path(".model/category.joblib")


class Command(BaseCommand):
    help = "Inspect the trained categorizer model and print a small health report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            default=str(DEFAULT_MODEL_PATH),
            help="Path to the joblib model file (default: .model/category.joblib)",
        )
        parser.add_argument(
            "--sample",
            default="STAPLES DUBLIN pens|23.45",
            help='Sample text and amount, format: "text|amount"',
        )

    def handle(self, *args, **opts):
        path = Path(opts["model"])
        sample_raw = opts["sample"]

        # 1) Load
        if not path.exists():
            self.stdout.write(self.style.WARNING(f"Model not found: {path}"))
            self.stdout.write("Train first: python manage.py train_categorizer")
            return

        try:
            model = joblib.load(path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load model: {e!r}"))
            self.stdout.write("Delete the corrupt file and retrain:")
            self.stdout.write(f"  rm -f {path}")
            self.stdout.write("  python manage.py train_categorizer")
            return

        # 2) Basic structure
        steps = [
            (name, type(step).__name__) for name, step in getattr(model, "steps", [])
        ]
        clf = getattr(model, "named_steps", {}).get("clf", None)

        self.stdout.write("\n--- Pipeline steps ---")
        if steps:
            for name, clsname in steps:
                self.stdout.write(f"{name}: {clsname}")
        else:
            self.stdout.write("Unknown pipeline structure")

        # 3) Classes
        classes = getattr(clf, "classes_", None) if clf is not None else None
        self.stdout.write("\n--- Classes (account codes) ---")
        self.stdout.write(str(classes) if classes is not None else "N/A")

        # 4) Coefficients shape
        coef = getattr(clf, "coef_", None) if clf is not None else None
        shape = getattr(coef, "shape", None) if coef is not None else None
        self.stdout.write("\n--- Coefficients shape ---")
        self.stdout.write(str(shape) if shape is not None else "N/A")

        # 5) Example prediction
        try:
            text_part, amt_part = sample_raw.split("|", 1)
            amt = float(amt_part)
        except Exception:
            text_part, amt = sample_raw, 0.0

        try:
            pred = model.predict([[text_part, amt]])
            proba = model.predict_proba([[text_part, amt]])
            self.stdout.write("\n--- Example prediction ---")
            self.stdout.write(str(pred))
            self.stdout.write(str(proba))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Prediction failed on sample: {e!r}"))

        # 6) JSON summary for tooling
        summary = {
            "model_path": str(path),
            "steps": steps,
            "classes": list(map(str, classes)) if classes is not None else None,
            "coef_shape": list(shape) if shape is not None else None,
        }
        self.stdout.write("\n--- Summary (JSON) ---")
        self.stdout.write(json.dumps(summary, indent=2))
