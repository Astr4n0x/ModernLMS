from django.db import models
from django.conf import settings


class LiveSession(models.Model):

    content_node = models.ForeignKey('courses.ContentNode', on_delete=models.CASCADE, related_name='live_sessions_new', null=True, blank=True)
    is_live = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    viewer_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        status = "LIVE" if self.is_live else "Ended"
        return f"[{status}] {self.content_node.title if self.content_node else 'N/A'}"

    class Meta:
        ordering = ['-started_at']


class LiveComment(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.user_id}: {self.text[:40]}"

    class Meta:
        ordering = ['timestamp']
