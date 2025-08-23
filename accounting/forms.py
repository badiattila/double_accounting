from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import EntryLine, Transaction

class EntryLineForm(forms.ModelForm):
    class Meta:
        model = EntryLine
        fields = ["account", "debit", "credit", "description", "currency"]

    def clean(self):
        cleaned = super().clean()
        debit = cleaned.get("debit") or Decimal("0.00")
        credit = cleaned.get("credit") or Decimal("0.00")
        if debit == 0 and credit == 0 and not self.cleaned_data.get("DELETE", False):
            raise ValidationError("Each line must have a debit or a credit.")
        if debit > 0 and credit > 0:
            raise ValidationError("A line cannot have both debit and credit > 0.")
        return cleaned

class EntryLineInlineFormSet(BaseInlineFormSet):
    """
    Enforces the double-entry invariant at the formset level:
    - At least two non-deleted lines
    - Σ(debits) == Σ(credits)
    """
    def clean(self):
        super().clean()

        total_deb = Decimal("0.00")
        total_cred = Decimal("0.00")
        alive = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            debit = form.cleaned_data.get("debit") or Decimal("0.00")
            credit = form.cleaned_data.get("credit") or Decimal("0.00")
            total_deb += debit
            total_cred += credit
            alive += 1

        if alive < 2:
            raise ValidationError("A transaction must have at least two lines.")
        if total_deb != total_cred:
            raise ValidationError(f"Unbalanced: debits {total_deb} != credits {total_cred}.")
