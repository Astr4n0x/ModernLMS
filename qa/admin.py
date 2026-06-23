from django.contrib import admin
from .models import QAQuestion, QAAnswer


class QAAnswerInline(admin.TabularInline):
    model = QAAnswer
    extra = 0
    readonly_fields = ('is_ai', 'responder', 'created_at')


@admin.register(QAQuestion)
class QAQuestionAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'course', 'subject', 'answer_type', 'status', 'created_at')
    list_filter   = ('status', 'answer_type', 'course')
    search_fields = ('content', 'user__user_id', 'course__title')
    inlines       = [QAAnswerInline]
    readonly_fields = ('created_at',)


@admin.register(QAAnswer)
class QAAnswerAdmin(admin.ModelAdmin):
    list_display  = ('id', 'question', 'responder', 'is_ai', 'created_at')
    list_filter   = ('is_ai',)
    readonly_fields = ('created_at',)
