from django.contrib import admin, messages

from . import ledger
from .models import Conversation, LedgerEntry, LLMModel, Message, Wallet


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = ("display_name", "provider", "model_id", "input_price_micros_per_mtok", "output_price_micros_per_mtok", "is_active")
    list_editable = ("is_active",)


MICROS_PER_DOLLAR = 1_000_000


def _grant(amount_dollars):
    def action(modeladmin, request, queryset):
        for wallet in queryset:
            ledger.credit(wallet.pk, amount_dollars * MICROS_PER_DOLLAR, "topup", note=f"Granted by {request.user.username}")
        modeladmin.message_user(request, f"Granted ${amount_dollars} to {queryset.count()} wallet(s).", messages.SUCCESS)

    action.__name__ = f"grant_{amount_dollars}"
    action.short_description = f"Grant ${amount_dollars} credit"
    return action



@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance_micros")
    readonly_fields = ("balance_micros",)  # balances change only through the ledger (see the grant actions)
    actions = [_grant(1), _grant(5), _grant(10)]

    def has_add_permission(self, request):
        return False


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "wallet", "kind", "amount_micros", "balance_after_micros", "note")
    list_filter = ("kind",)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("role", "content", "status", "cost_micros")
    readonly_fields = fields
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "model", "updated_at")
    inlines = [MessageInline]
