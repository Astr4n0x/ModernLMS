import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from courses.models import ContentNode
from .models import LiveSession, LiveComment


@login_required
def get_comments(request, node_id):
    """Return existing comments for a live class node (most recent active session)."""
    try:
        node = get_object_or_404(ContentNode, pk=node_id, node_type='class')
        # Prefer the live session; fall back to the most recent ended one
        session = node.live_sessions_new.filter(is_live=True).first()
        if not session:
            session = node.live_sessions_new.first()

        if not session:
            return JsonResponse({'comments': []})

        comments = session.comments.select_related('author').all()
        data = [
            {
                'id': c.id,
                'author': c.author.get_full_name() or c.author.user_id,
                'text': c.text,
                'timestamp': c.timestamp.isoformat(),
                'time_display': c.timestamp.strftime('%H:%M'),
            }
            for c in comments
        ]
        return JsonResponse({'comments': data})
    except Exception as e:
        return JsonResponse({'comments': [], 'error': str(e)})

