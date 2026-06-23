from django.db import models
from django.conf import settings
from courses.models import Course, ContentNode


class QAQuestion(models.Model):
    ANSWER_TYPE_CHOICES = [
        ('ai',    'AI Teacher'),
        ('human', 'Human Teacher'),
    ]
    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('ai_answered', 'AI Answered'),
        ('answered',    'Answered'),
    ]

    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qa_questions',
    )
    course      = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='qa_questions',
    )
    subject     = models.ForeignKey(
        ContentNode,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qa_questions',
        limit_choices_to={'parent__isnull': True},
        help_text='Top-level subject node (optional)',
    )
    content     = models.TextField(help_text='The question text')
    image       = models.ImageField(upload_to='qa/question_images/', null=True, blank=True)
    pdf         = models.FileField(upload_to='qa/question_pdfs/',   null=True, blank=True)
    audio       = models.FileField(upload_to='qa/question_audio/',  null=True, blank=True)
    answer_type = models.CharField(
        max_length=10, choices=ANSWER_TYPE_CHOICES,
        null=True, blank=True,
        help_text='Set after modal choice',
    )
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Q#{self.pk} by {self.user} - {self.content[:60]}'

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Question'


class QAAnswer(models.Model):
    question  = models.ForeignKey(
        QAQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qa_answers',
        help_text='Null for AI answers',
    )
    is_ai     = models.BooleanField(default=False)
    content   = models.TextField()
    image     = models.ImageField(upload_to='qa/answer_images/', null=True, blank=True)
    audio     = models.FileField(upload_to='qa/answer_audio/',   null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = 'AI' if self.is_ai else str(self.responder)
        return f'Answer by {who} → Q#{self.question_id}'

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Answer'
