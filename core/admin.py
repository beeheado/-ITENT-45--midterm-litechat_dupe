from django.contrib import admin

from .models import Conversation, LedgerEntry, LLMModel, Message, Wallet


@admin.register(LLMModel)
class LLMModelAdmin(admin.ModelAdmin):
    list_display = ("display_name", "provider", "model_id", "input_price_micros_per_mtok", "output_price_micros_per_mtok", "is_active")
    list_editable = ("is_active",)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance_micros")
    readonly_fields = ("balance_micros",)  # change balances by adding ledger entries, not by editing


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
