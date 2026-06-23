from django.db import models
from django.conf import settings
from courses.models import Course

class Message(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='discussion_messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discussion_messages')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='discussions/attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.user_id} - {self.course.title} - {self.created_at}"
