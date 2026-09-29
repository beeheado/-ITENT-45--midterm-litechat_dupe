from .models import Wallet


def balance(request):
    if request.user.is_authenticated:
        w = Wallet.objects.filter(user=request.user).first()
        return {"balance_micros": w.balance_micros if w else 0}
    return {}
