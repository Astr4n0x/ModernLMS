from django.contrib import admin
from .models import (
    ClassLevel, Course, CourseBundle, ContentNode,
    Exam, Question, Option, ExamAttempt, StudentAnswer,
    StudentStreak, StreakBadge, BoardQuestion,
    Scholarship, ScholarshipApplication,
)


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'class_level', 'price', 'is_combo', 'is_published', 'created_at']
    list_filter = ['class_level', 'is_combo', 'is_published']
    list_editable = ['is_published', 'price']
    filter_horizontal = ['students']


@admin.register(CourseBundle)
class CourseBundleAdmin(admin.ModelAdmin):
    list_display = ['combo_course', 'component_course']


@admin.register(ContentNode)
class ContentNodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'node_type', 'course', 'parent', 'order', 'status']
    list_filter = ['node_type', 'status', 'course']
    list_editable = ['status', 'order']


# ─────────────────────────────────────────────
# Past Exams Admin
# ─────────────────────────────────────────────

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    fields = ['text', 'is_correct', 'order']


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = ['text', 'order']
    show_change_link = True


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'subject', 'topic', 'duration_minutes', 'total_questions', 'is_published', 'created_at']
    list_filter = ['course', 'is_published']
    list_editable = ['is_published', 'duration_minutes']
    inlines = [QuestionInline]
    search_fields = ['title', 'course__title']

    def total_questions(self, obj):
        return obj.total_questions()
    total_questions.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'order', 'text']
    list_filter = ['exam']
    inlines = [OptionInline]
    search_fields = ['text', 'exam__title']


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ['question', 'selected_option', 'is_correct', 'timestamp']
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'start_time', 'end_time', 'is_submitted', 'score', 'correct_answers', 'wrong_answers']
    list_filter = ['is_submitted', 'exam']
    readonly_fields = ['user', 'exam', 'start_time', 'end_time', 'is_submitted', 'score', 'total_questions', 'correct_answers', 'wrong_answers']
    inlines = [StudentAnswerInline]


class StreakBadgeInline(admin.TabularInline):
    model = StreakBadge
    extra = 0
    readonly_fields = ['days_required', 'name', 'earned_at']
    can_delete = False


@admin.register(StudentStreak)
class StudentStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'last_activity_date', 'total_active_days']
    list_filter = ['last_activity_date']
    readonly_fields = ['user', 'current_streak', 'longest_streak', 'last_activity_date', 'total_active_days', 'updated_at']
    inlines = [StreakBadgeInline]
    search_fields = ['user__username', 'user__first_name', 'user__last_name']


@admin.register(StreakBadge)
class StreakBadgeAdmin(admin.ModelAdmin):
    list_display = ['streak', 'name', 'days_required', 'earned_at']
    list_filter = ['days_required']
    readonly_fields = ['streak', 'name', 'days_required', 'earned_at']
    search_fields = ['streak__user__username', 'name']


@admin.register(BoardQuestion)
class BoardQuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'board_name', 'year', 'exam_type', 'uploaded_at']
    list_filter = ['board_name', 'year', 'exam_type']
    search_fields = ['title']


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'country', 'category', 'level', 'status', 'is_featured', 'deadline']
    list_filter = ['status', 'category', 'level', 'is_featured']
    list_editable = ['status', 'is_featured']
    search_fields = ['title', 'provider', 'country']


@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display = ['scholarship', 'user', 'full_name', 'email', 'status', 'applied_at']
    list_filter = ['status', 'scholarship']
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'scholarship__title']


