from decimal import Decimal
from django.contrib import admin, messages
from django.db import transaction as dbtx
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Account, Journal, Transaction, EntryLine
from .forms import EntryLineForm, EntryLineInlineFormSet
from .services import create_and_post_transaction  # optional for actions

# ---------- Account ----------
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "normal_debit", "is_active")
    list_filter = ("type", "is_active", "normal_debit")
    search_fields = ("code", "name")
    ordering = ("code",)
    list_editable = ("is_active",)
    fieldsets = (
        (None, {"fields": ("code", "name", "type", "normal_debit", "is_active")}),
    )

# ---------- Journal ----------
@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")

# ---------- Inline: EntryLine on Transaction ----------
class EntryLineInline(admin.TabularInline):
    model = EntryLine
    form = EntryLineForm
    formset = EntryLineInlineFormSet
    extra = 2  # start with 2 rows to encourage balancing
    min_num = 2
    autocomplete_fields = ("account",)
    fields = ("account", "debit", "credit", "currency", "description")
    # Make amounts narrower
    classes = ("collapse",)
    show_change_link = False

# ---------- Transaction ----------
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    inlines = [EntryLineInline]
    date_hierarchy = "tx_date"
    list_display = ("id", "tx_date", "journal", "memo", "posted_badge", "debit_total", "credit_total")
    list_filter = ("posted", "journal")
    search_fields = ("memo", "lines__description", "journal__name")
    autocomplete_fields = ("journal",)
    readonly_fields = ("created_at", "posted")
    fields = ("journal", "tx_date", "memo", "posted", "created_at")

    def posted_badge(self, obj):
        color = "#22c55e" if obj.posted else "#ef4444"
        label = "Posted" if obj.posted else "Draft"
        return format_html('<span style="padding:2px 6px;border-radius:8px;background:{};color:white;">{}</span>', color, label)
    posted_badge.short_description = "Status"

    def debit_total(self, obj):
        q = obj.lines.all()
        return sum((l.debit for l in q), Decimal("0.00"))
    debit_total.short_description = "Σ Debit"

    def credit_total(self, obj):
        q = obj.lines.all()
        return sum((l.credit for l in q), Decimal("0.00"))
    credit_total.short_description = "Σ Credit"

    # Prevent edits on posted transactions
    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.posted:
            # make all fields read-only when posted; edits should be via reversals
            ro += ["journal", "tx_date", "memo"]
        return ro

    def has_delete_permission(self, request, obj=None):
        # For correctness: forbid delete if posted (prefer reversal entries)
        if obj and obj.posted:
            return False
        return super().has_delete_permission(request, obj)

    # Admin actions
    actions = ["action_post", "action_unpost_blocked", "action_reverse_transaction"]

    @admin.action(description="Post selected balanced transactions")
    def action_post(self, request, queryset):
        count = 0
        for tx in queryset.select_related("journal"):
            if tx.posted:
                continue
            # Validate inline formset already guarantees balance in UI,
            # but when posting from action, re-check using model clean()
            try:
                with dbtx.atomic():
                    tx.full_clean()
                    tx.post()
                count += 1
            except Exception as e:
                self.message_user(request, f"Tx {tx.pk} not posted: {e}", level=messages.ERROR)
        if count:
            self.message_user(request, f"Posted {count} transaction(s).", level=messages.SUCCESS)

    @admin.action(description="Unpost (blocked for safety) — use reversal instead")
    def action_unpost_blocked(self, request, queryset):
        self.message_user(request, "Unposting is disabled. Create reversing entries instead.", level=messages.WARNING)

    @admin.action(description="Create reversing entry for selected posted transactions")
    def action_reverse_transaction(self, request, queryset):
        """Creates same-dated reversing transactions in the same journal."""
        created = 0
        for tx in queryset:
            if not tx.posted:
                self.message_user(request, f"Tx {tx.pk} is not posted; skipping.", level=messages.WARNING)
                continue
            try:
                with dbtx.atomic():
                    lines = []
                    for l in tx.lines.all():
                        lines.append({
                            "account": l.account,
                            "debit": l.credit,   # swap
                            "credit": l.debit,
                            "description": f"Reversal of Tx {tx.pk}: {l.description or ''}",
                        })
                    rev = create_and_post_transaction(
                        journal=tx.journal,
                        tx_date=tx.tx_date,
                        memo=f"Reversal of Tx {tx.pk}",
                        lines=lines,
                    )
                    created += 1
            except Exception as e:
                self.message_user(request, f"Failed reversing Tx {tx.pk}: {e}", level=messages.ERROR)
        if created:
            self.message_user(request, f"Created {created} reversing transaction(s).", level=messages.SUCCESS)
