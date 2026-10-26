from .collaboration import summary
from .models import Notification


def collaboration(request):
    """Badge counts and latest notifications for the app shell; empty for anonymous pages."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    data = summary(user)
    data["latest"] = list(Notification.objects.filter(user=user)[:5])
    return {"collab": data}
