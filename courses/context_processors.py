from .models import StudentStreak


def streak_context(request):
    """Inject streak_count into every template for authenticated students."""
    if request.user.is_authenticated and request.user.role == 'student':
        try:
            streak_count = request.user.streak.current_streak
        except StudentStreak.DoesNotExist:
            streak_count = 0
    else:
        streak_count = 0
    return {'streak_count': streak_count}
