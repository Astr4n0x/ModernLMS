from django.db import models
from django.conf import settings
from django.utils import timezone


class ClassLevel(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g. "Class 11"

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Course(models.Model):
    title = models.CharField(max_length=200)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    instructors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='taught_courses', blank=True)
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='enrolled_courses', blank=True)
    description = models.TextField()
    whats_included = models.TextField(blank=True, help_text="One item per line")
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Price in BDT")
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Discounted price in BDT")
    is_free = models.BooleanField(default=False)
    what_you_will_learn = models.TextField(blank=True, help_text="One item per line or HTML")
    category = models.CharField(max_length=100, blank=True, help_text="Subject type e.g. Science")
    batch_year = models.CharField(max_length=20, blank=True, help_text="e.g. 2026")
    is_combo = models.BooleanField(default=False, help_text="Bundle of multiple courses")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_subjects(self):
        return self.content_nodes.filter(parent__isnull=True).count()

    def total_lessons(self):
        return self.content_nodes.filter(node_type='class').count()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']


class CourseBundle(models.Model):
    """Links a combo course to the individual courses it includes."""
    combo_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='bundle_components')
    component_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='bundled_in')

    def __str__(self):
        return f"{self.combo_course.title} includes {self.component_course.title}"

    class Meta:
        unique_together = ('combo_course', 'component_course')



class CourseFAQ(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} FAQ: {self.question}"


LESSON_STATUS_CHOICES = [
    ('published', 'Published'),
    ('recorded', 'Recorded'),
    ('past_live', 'Past Live'),
    ('live', 'LiveNow'),
]


class ContentNode(models.Model):
    NODE_TYPES = [
        ('subject', 'Subject'),
        ('subsubject', 'Sub-Subject'),
        ('topic', 'Topic'),
        ('class', 'Class/Lesson'),
    ]
    title = models.CharField(max_length=300)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='content_nodes')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    node_type = models.CharField(max_length=50, choices=NODE_TYPES, default='class')
    description = models.TextField(blank=True)
    youtube_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=LESSON_STATUS_CHOICES, default='published')
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_leaf(self):
        return not self.children.exists()

    def get_ancestors(self):
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_youtube_embed_url(self):
        import re
        if not self.youtube_url:
            return ''
        if 'embed' in self.youtube_url:
            return self.youtube_url
        m = re.search(r'(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})', self.youtube_url)
        if m:
            return f'https://www.youtube.com/embed/{m.group(1)}'
        return self.youtube_url

    def is_live_now(self):
        return self.live_sessions.filter(is_live=True).exists()

    def __str__(self):
        if self.parent:
            return f"{self.parent.title} » {self.title} ({self.get_node_type_display()})"
        return f"{self.course.title} » {self.title} ({self.get_node_type_display()})"

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Content Node'


# ─────────────────────────────────────────────
# Past Exams Module
# ─────────────────────────────────────────────

class Exam(models.Model):
    title           = models.CharField(max_length=300)
    course          = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams')
    subject         = models.ForeignKey(
        ContentNode, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exams',
        limit_choices_to={'parent__isnull': True},
        help_text="Top-level subject node this exam belongs to (optional)"
    )
    topic           = models.ForeignKey(
        ContentNode, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='topic_exams',
        limit_choices_to={'node_type': 'topic'},
        help_text="Topic node this exam belongs to (optional)"
    )
    duration_minutes = models.PositiveIntegerField(default=30, help_text="Exam duration in minutes")
    is_published    = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def total_questions(self):
        return self.questions.count()

    def __str__(self):
        return f"{self.title} ({self.course.title})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Exam'


class Question(models.Model):
    exam  = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text  = models.TextField()
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"

    class Meta:
        ordering = ['order']


class Option(models.Model):
    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text       = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False, help_text="Mark the correct answer")
    order      = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{'✓ ' if self.is_correct else ''}{self.text[:60]}"

    class Meta:
        ordering = ['order']


class ExamAttempt(models.Model):
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    exam            = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    start_time      = models.DateTimeField(auto_now_add=True)
    end_time        = models.DateTimeField(null=True, blank=True)
    is_submitted    = models.BooleanField(default=False)
    score           = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers   = models.PositiveIntegerField(default=0)

    def remaining_seconds(self):
        """Compute how many seconds remain for this attempt."""
        from django.utils import timezone
        import datetime
        deadline = self.start_time + datetime.timedelta(minutes=self.exam.duration_minutes)
        remaining = (deadline - timezone.now()).total_seconds()
        return max(int(remaining), 0)

    def __str__(self):
        return f"{self.user} - {self.exam.title} ({'submitted' if self.is_submitted else 'in progress'})"

    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Exam Attempt'


class StudentAnswer(models.Model):
    attempt         = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question        = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_answers')
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name='selected_by')
    is_correct      = models.BooleanField(default=False)
    timestamp       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attempt.user} → Q{self.question.order}: {self.selected_option.text[:40]}"

    class Meta:
        unique_together = ('attempt', 'question')
        ordering = ['question__order']
        verbose_name = 'Student Answer'


# ─────────────────────────────────────────────
# Solve Sheets Module
# ─────────────────────────────────────────────

class SolveSheet(models.Model):
    title = models.CharField(max_length=300)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='solve_sheets')
    subject = models.ForeignKey(
        ContentNode, on_delete=models.CASCADE,
        related_name='subject_solve_sheets',
        limit_choices_to={'parent__isnull': True},
        help_text="Top-level subject node this solve sheet belongs to"
    )
    topic = models.ForeignKey(
        ContentNode, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='topic_solve_sheets',
        limit_choices_to={'node_type': 'topic'},
        help_text="Topic node this solve sheet belongs to (optional)"
    )
    file = models.FileField(upload_to='solve_sheets/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.course.title})"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Solve Sheet'


# ─────────────────────────────────────────────
# Streak System
# ─────────────────────────────────────────────

BADGE_MILESTONES = [
    (3,   '🌱 First Spark'),
    (7,   '🔥 Rising Flame'),
    (12,  '⚡ Consistent Learner'),
    (15,  '🏹 Knowledge Hunter'),
    (21,  '🛡️ Discipline Guardian'),
    (30,  '👑 Learning Warrior'),
    (45,  '🚀 Momentum Master'),
    (60,  '💎 Diamond Dedication'),
    (75,  '🌟 Academic Champion'),
    (90,  '🏆 Study Legend'),
    (120, '⚔️ Grand Scholar'),
    (150, '🌌 Master of Consistency'),
    (180, '🥇 Elite Achiever'),
    (240, '🔮 Wisdom Seeker'),
    (300, '👑 Learning Emperor'),
    (365, '🌠 Immortal Scholar'),
]


class StudentStreak(models.Model):
    """Tracks a student's daily learning streak."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='streak'
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    total_active_days = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def record_activity(self):
        """Call this whenever a student completes a lesson or exam.
        Updates the streak safely - idempotent within the same day."""
        today = timezone.localdate()

        if self.last_activity_date == today:
            # Already recorded today, nothing to do
            return False

        if self.last_activity_date is None:
            # First ever activity
            self.current_streak = 1
            self.total_active_days = 1
        elif (today - self.last_activity_date).days == 1:
            # Consecutive day - extend streak
            self.current_streak += 1
            self.total_active_days += 1
        else:
            # Streak broken - reset
            self.current_streak = 1
            self.total_active_days += 1

        self.last_activity_date = today
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.save()
        self._award_badges()
        return True

    def _award_badges(self):
        """Award any newly earned milestone badges based on longest streak."""
        for days, name in BADGE_MILESTONES:
            if self.longest_streak >= days:
                StreakBadge.objects.get_or_create(
                    streak=self,
                    days_required=days,
                    defaults={'name': name}
                )

    def __str__(self):
        return f"{self.user} - {self.current_streak} day streak"

    class Meta:
        verbose_name = 'Student Streak'


class StreakBadge(models.Model):
    """A badge earned by a student at a streak milestone. Permanent - never lost."""
    streak = models.ForeignKey(
        StudentStreak,
        on_delete=models.CASCADE,
        related_name='badges'
    )
    days_required = models.PositiveIntegerField()  # e.g. 7
    name = models.CharField(max_length=100)        # e.g. '🔥 Rising Flame'
    earned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.streak.user} - {self.name}"

    class Meta:
        unique_together = ('streak', 'days_required')
        ordering = ['days_required']
        verbose_name = 'Streak Badge'


# ─────────────────────────────────────────────
# AI Study Assistant Content
# ─────────────────────────────────────────────

class AIContent(models.Model):
    """Stores AI-generated study content for a class node."""
    CONTENT_TYPES = [
        ('notes', 'Notes'),
        ('flashcards', 'Flashcards'),
        ('mcqs', 'MCQs'),
        ('summary', 'Summary'),
        ('next_topics', 'Next Topics'),
    ]
    node = models.ForeignKey(
        ContentNode, on_delete=models.CASCADE, related_name='ai_contents'
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content = models.JSONField()
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('node', 'content_type')
        verbose_name = 'AI Content'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.node.title} [{self.content_type}]"


class BoardQuestion(models.Model):
    BOARD_CHOICES = [
        ('Dhaka', 'Dhaka'),
        ('Rajshahi', 'Rajshahi'),
        ('Cumilla', 'Cumilla'),
        ('Jashore', 'Jashore'),
        ('Chattogram', 'Chattogram'),
        ('Barishal', 'Barishal'),
        ('Sylhet', 'Sylhet'),
        ('Dinajpur', 'Dinajpur'),
        ('Mymensingh', 'Mymensingh'),
    ]

    TYPE_CHOICES = [
        ('Written', 'Written'),
        ('MCQ', 'MCQ'),
    ]

    title = models.CharField(max_length=300)
    board_name = models.CharField(max_length=50, choices=BOARD_CHOICES)
    year = models.IntegerField(help_text="Exam Year")
    exam_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    pdf_file = models.FileField(upload_to='board_questions/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.board_name} Board ({self.year}) [{self.exam_type}]"

    class Meta:
        ordering = ['-year', 'board_name', 'title']
        verbose_name = 'Board Question'


# ─────────────────────────────────────────────
# Scholarships & Admissions
# ─────────────────────────────────────────────

class Scholarship(models.Model):
    CATEGORY_CHOICES = [
        ('local', 'Local'),
        ('international', 'International'),
    ]
    LEVEL_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('any', 'Any Level'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('upcoming', 'Upcoming'),
    ]

    title = models.CharField(max_length=300)
    provider = models.CharField(max_length=200, help_text="Organisation or government offering the scholarship")
    country = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='local')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='any')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    benefits = models.TextField(help_text="What students receive (stipend, tuition, airfare, etc.)")
    description = models.TextField(help_text="Full details about the scholarship")
    eligibility = models.TextField(help_text="Who can apply", blank=True)
    apply_url = models.URLField(blank=True, help_text="External application link")
    deadline = models.DateField(null=True, blank=True)
    icon = models.CharField(max_length=100, default='fas fa-graduation-cap', help_text="FontAwesome icon class")
    color_class = models.CharField(max_length=30, default='blue', help_text="Colour theme: blue, green, purple, orange, red, teal")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = 'Scholarship'

    def __str__(self):
        return f"{self.title} ({self.country})"

    def is_open(self):
        return self.status == 'open'


class ScholarshipApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scholarship_applications')
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True, help_text="Why do you want to apply for this scholarship?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('scholarship', 'user')
        verbose_name = 'Scholarship Application'

    def __str__(self):
        return f"{self.user} → {self.scholarship.title}"

