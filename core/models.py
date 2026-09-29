from django.conf import settings
from django.db import models
from django.db.models import Q

from .providers.types import is_truncated

MICROS = 1_000_000  # 1 credit = $1.00 = 1,000,000 micro-credits

MAX_PROMPT_CHARS = 4000  # global system prompt; it is sent (and billed as input) with every message
MAX_MEMORY_CHARS = 500
MAX_MEMORY_ITEMS = 50

NO_ANSWER_TRUNCATED = (
    "The model used its whole token budget thinking and gave no answer, so you weren't charged. "
    "Try again, or ask a shorter or simpler question."
)
NO_ANSWER = "The model returned no answer, so you weren't charged. Try again."
CUT_OFF = "The reply was cut off at the length limit. Ask it to continue."


class LLMModel(models.Model):
    PROVIDERS = [("openai", "OpenAI"), ("anthropic", "Anthropic"), ("google", "Google")]

    provider = models.CharField(max_length=20, choices=PROVIDERS)
    model_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    # Prices are micro-credits per one million tokens (250_000 = $0.25 / Mtok).
    input_price_micros_per_mtok = models.PositiveIntegerField()
    output_price_micros_per_mtok = models.PositiveIntegerField()
    max_output_tokens = models.PositiveIntegerField(default=8192)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["provider", "display_name"]

    def __str__(self):
        return f"{self.display_name} ({self.get_provider_display()})"


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance_micros = models.BigIntegerField(default=0)  # cache; the ledger is the truth

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(balance_micros__gte=0), name="wallet_balance_non_negative")]

    def __str__(self):
        return f"{self.user} ${self.balance_micros / MICROS:.4f}"


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=200, default="New chat")
    model = models.ForeignKey(LLMModel, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Message(models.Model):
    ROLES = [("user", "User"), ("assistant", "Assistant")]
    STATUSES = [("pending", "Pending"), ("complete", "Complete"), ("failed", "Failed"), ("cancelled", "Cancelled")]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLES)
    content = models.TextField(blank=True)
    reasoning = models.TextField(blank=True)
    model = models.ForeignKey(LLMModel, on_delete=models.PROTECT, null=True, blank=True)  # which model answered
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_micros = models.BigIntegerField(default=0)  # snapshot; price edits never rewrite history
    status = models.CharField(max_length=10, choices=STATUSES, default="complete")
    error = models.TextField(blank=True)
    finish_reason = models.CharField(max_length=40, blank=True)  # provider's stop reason, e.g. stop / length
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"

    @property
    def truncated(self):
        return is_truncated(self.finish_reason)

    @property
    def notice(self):
        """What to tell the user about this reply (empty when nothing is wrong). Also covers old rows with no finish_reason."""
        if self.error:
            return self.error
        if self.role != "assistant" or self.status == "pending":
            return ""
        if not self.content.strip():
            return NO_ANSWER
        return CUT_OFF if self.truncated else ""


class LedgerEntry(models.Model):
    """Append-only. Corrections are new rows, never edits."""

    KINDS = [("grant", "Grant"), ("topup", "Top-up"), ("charge", "Charge"), ("adjustment", "Adjustment")]

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="entries")
    kind = models.CharField(max_length=12, choices=KINDS)
    amount_micros = models.BigIntegerField()  # signed: credits positive, charges negative
    balance_after_micros = models.BigIntegerField()
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries")
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.kind} {self.amount_micros}"


class UserProfile(models.Model):
    """Per-user settings. One row per user, created with the account (see signals.py)."""

    APPS = [("simgen", "SimGen"), ("ask", "Ask"), ("chat", "Chat")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    system_prompt = models.TextField(blank=True)
    auto_memory = models.BooleanField(default=False)  # stored only; generation is a separate future feature
    default_app = models.CharField(max_length=10, choices=APPS, default="chat")

    def __str__(self):
        return f"profile of {self.user}"


def profile_for(user):
    """The user's profile, created on demand (covers accounts made before profiles existed)."""
    return UserProfile.objects.get_or_create(user=user)[0]


class MemoryItem(models.Model):
    KINDS = [("preference", "Preference"), ("fact", "Fact"), ("goal", "Goal"), ("context", "Context")]
    SOURCES = [("user", "You"), ("ai", "AI")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memories")
    kind = models.CharField(max_length=12, choices=KINDS, default="preference")
    content = models.CharField(max_length=MAX_MEMORY_CHARS)
    source = models.CharField(max_length=4, choices=SOURCES, default="user")  # "ai" reserved for generated memories
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.content[:40]}"
