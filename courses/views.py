import json
import uuid
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from .models import (
    Course, ContentNode, Exam, ExamAttempt, StudentAnswer,
    Option, Question, SolveSheet, StudentStreak, StreakBadge,
    BADGE_MILESTONES, AIContent, BoardQuestion,
    Scholarship, ScholarshipApplication,
)


# ─────────────────────────────────────────────
# Streak Helper
# ─────────────────────────────────────────────

def _record_streak(user):
    """Get or create the student's streak record and record today's activity."""
    streak, _ = StudentStreak.objects.get_or_create(user=user)
    streak.record_activity()
    return streak


def _get_streak_context(user):
    """Return streak-related context dict for templates."""
    try:
        streak = user.streak
        current_streak = streak.current_streak
        longest_streak = streak.longest_streak
        earned_badges = list(streak.badges.all())
    except StudentStreak.DoesNotExist:
        current_streak = 0
        longest_streak = 0
        earned_badges = []

    # Determine next badge milestone
    next_badge = None
    for days, name in BADGE_MILESTONES:
        if longest_streak < days:
            next_badge = {'days': days, 'name': name, 'remaining': days - current_streak}
            break

    return {
        'streak_count': current_streak,
        'longest_streak': longest_streak,
        'earned_badges': earned_badges,
        'next_badge': next_badge,
        'all_milestones': BADGE_MILESTONES,
    }


def _user_enrolled(user, course):
    return course.students.filter(pk=user.pk).exists()

@login_required
def dashboard_view(request):
    user = request.user
    enrolled_courses = Course.objects.filter(students=user).select_related('class_level').prefetch_related('instructors')
    total_lessons = ContentNode.objects.filter(
        node_type='class',
        course__students=user
    ).distinct().count()
    past_lessons = ContentNode.objects.filter(
        node_type='class',
        status__in=['recorded', 'past_live'],
        course__students=user
    ).distinct().count()

    streak_ctx = _get_streak_context(user)

    context = {
        'user': user,
        'courses': enrolled_courses,
        'total_courses': enrolled_courses.count(),
        'total_lessons': total_lessons,
        'past_lessons': past_lessons,
        'page_title': 'Dashboard',
        **streak_ctx,
    }
    return render(request, 'dashboard.html', context)



@login_required
def catalogue_view(request):
    # Only fetch courses the student is enrolled in
    courses = Course.objects.filter(students=request.user).select_related(
        'class_level'
    ).prefetch_related('instructors', 'content_nodes').all()

    catalogue_data = []
    for course in courses:
        course_data = {
            'id': course.id,
            'title': course.title,
            'level': course.class_level.name if course.class_level else "General",
            'instructor': ", ".join([inst.get_full_name() or str(inst.user_id) for inst in course.instructors.all()]) or "Staff",
            'description': course.description,
            'total_subjects': course.total_subjects(),
            'total_lessons': course.total_lessons(),
            'subjects': []
        }
        all_nodes = list(course.content_nodes.all())
        top_nodes = [n for n in all_nodes if n.parent_id is None]
        for subject in top_nodes:
            subject_data = {
                'id': subject.id,
                'title': subject.title,
                'description': subject.description,
                'topics_count': sum(1 for n in all_nodes if n.parent_id == subject.id),
            }
            course_data['subjects'].append(subject_data)
        catalogue_data.append(course_data)

    context = {
        'courses': courses,
        'catalogue_data_json': catalogue_data,
        'page_title': 'My Courses',
    }
    return render(request, 'catalogue.html', context)


@login_required
@login_required
def node_detail_view(request, node_id):
    node = get_object_or_404(
        ContentNode.objects.select_related('course', 'parent').prefetch_related('course__instructors'),
        pk=node_id
    )
    if not _user_enrolled(request.user, node.course):
        messages.error(request, "You must be enrolled in this course to view its content.")
        return redirect('courses:course_store')

    if node.node_type == 'class':
        # Record streak for lesson view
        _record_streak(request.user)

        attachments = node.attachments_new.all()
        live_session = node.live_sessions_new.filter(is_live=True).first()
        is_live = live_session is not None
        comments_allowed = (node.status == 'published') or is_live

        context = {
            'node': node,
            'attachments': attachments,
            'live_session': live_session,
            'is_live': is_live,
            'comments_allowed': comments_allowed,
            'embed_url': node.get_youtube_embed_url(),
            'page_title': node.title,
        }
        if is_live or node.status == 'live':
            return render(request, 'live_lesson.html', context)
        return render(request, 'lesson.html', context)

    else:
        children = node.children.all().order_by('order')
        context = {
            'node': node,
            'children': children,
            'page_title': node.title,
        }
        return render(request, 'node_detail.html', context)


@login_required
def past_classes_view(request):
    # Only show lessons from courses the student is enrolled in
    lessons = ContentNode.objects.filter(
        node_type='class',
        status__in=['recorded', 'past_live', 'published'],
        course__students=request.user
    ).distinct().select_related(
        'course'
    ).prefetch_related('course__instructors').order_by('-created_at')

    context = {
        'lessons': lessons,
        'page_title': 'Past Classes',
    }
    return render(request, 'past_classes.html', context)


@login_required
def live_classes_view(request):
    # Only show lessons from courses the student is enrolled in that are LIVE
    lessons = ContentNode.objects.filter(
        node_type='class',
        status='live',
        course__students=request.user
    ).distinct().select_related(
        'course', 'parent'
    ).prefetch_related('course__instructors').order_by('-created_at')

    context = {
        'lessons': lessons,
        'page_title': 'Live Classes',
    }
    return render(request, 'live_classes.html', context)


# ─────────────────────────────────────────────
# Past Exams Module Views
# ─────────────────────────────────────────────

def _finalize_attempt(attempt):
    """Score and finalize a submitted attempt. Idempotent."""
    if attempt.is_submitted:
        return
    exam = attempt.exam
    total_q = exam.total_questions()
    answers = attempt.answers.select_related('selected_option')
    correct = 0
    for ans in answers:
        is_correct = ans.selected_option.is_correct
        if ans.is_correct != is_correct:
            ans.is_correct = is_correct
            ans.save(update_fields=['is_correct'])
        if is_correct:
            correct += 1
    wrong = answers.count() - correct
    attempt.is_submitted = True
    attempt.end_time = timezone.now()
    attempt.total_questions = total_q
    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.score = correct
    attempt.save(update_fields=[
        'is_submitted', 'end_time',
        'total_questions', 'correct_answers', 'wrong_answers', 'score',
    ])


@login_required
def past_exams_view(request):
    """Listing page: all published exams from courses the student is enrolled in."""
    enrolled_courses = Course.objects.filter(students=request.user).prefetch_related('exams')

    exam_data = []
    for course in enrolled_courses:
        for exam in course.exams.filter(is_published=True):
            exam_data.append({
                'id': exam.id,
                'title': exam.title,
                'course_id': course.id,
                'course_title': course.title,
                'subject_id': exam.subject_id,
                'subject_title': exam.subject.title if exam.subject else '',
                'duration_minutes': exam.duration_minutes,
                'total_questions': exam.total_questions(),
            })

    # Build course → subjects map for filter dropdowns
    courses_for_filter = []
    for course in enrolled_courses:
        exam_subjects = set()
        subjects = []
        for exam in course.exams.filter(is_published=True):
            if exam.subject and exam.subject_id not in exam_subjects:
                exam_subjects.add(exam.subject_id)
                subjects.append({'id': exam.subject_id, 'title': exam.subject.title})
        courses_for_filter.append({
            'id': course.id,
            'title': course.title,
            'subjects': subjects,
        })

    # Attempt history
    past_attempts = ExamAttempt.objects.filter(
        user=request.user, is_submitted=True
    ).select_related('exam', 'exam__course').order_by('-end_time')
    attempts_data = []
    for att in past_attempts:
        attempts_data.append({
            'id': att.id,
            'exam_id': att.exam_id,
            'exam_title': att.exam.title,
            'course_title': att.exam.course.title,
            'score': att.score,
            'total_questions': att.total_questions,
            'correct_answers': att.correct_answers,
            'wrong_answers': att.wrong_answers,
            'submitted_at': att.end_time.strftime('%d %b %Y, %H:%M') if att.end_time else '',
            'review_url': f'/exam/{att.exam_id}/review/{att.id}/',
        })

    context = {
        'exam_data_json': exam_data,
        'courses_filter_json': courses_for_filter,
        'attempts_data_json': attempts_data,
        'page_title': 'Past Exams',
    }
    return render(request, 'past_exams.html', context)


@login_required
def exam_detail_view(request, exam_id):
    """Exam page: resumes an in-progress attempt or creates a new one.
    Timer is always computed from DB start_time - survives page refresh."""
    exam = get_object_or_404(
        Exam.objects.select_related('course', 'subject').prefetch_related(
            'questions__options'
        ),
        pk=exam_id,
        is_published=True,
    )

    # Enrolment check
    if not _user_enrolled(request.user, exam.course):
        messages.error(request, "You must be enrolled in this course to take this exam.")
        return redirect('courses:past_exams')

    # Resume an active (non-submitted, non-expired) attempt, or create new
    attempt = ExamAttempt.objects.filter(
        user=request.user, exam=exam, is_submitted=False
    ).order_by('-start_time').first()

    if attempt:
        if attempt.remaining_seconds() <= 0:
            # Expired but never submitted - auto-finalize
            _finalize_attempt(attempt)
            attempt = None  # will create a fresh one below

    if not attempt:
        attempt = ExamAttempt.objects.create(user=request.user, exam=exam)

    remaining = attempt.remaining_seconds()

    # Build question data, restoring previously saved answers
    saved_answers = {
        sa.question_id: sa.selected_option_id
        for sa in attempt.answers.all()
    }
    questions_data = []
    for q in exam.questions.prefetch_related('options'):
        questions_data.append({
            'id': q.id,
            'text': q.text,
            'order': q.order,
            'options': [{'id': o.id, 'text': o.text} for o in q.options.all()],
            'selected_option_id': saved_answers.get(q.id),
        })

    context = {
        'exam': exam,
        'attempt': attempt,
        'remaining_seconds': remaining,
        'questions': questions_data,
        'page_title': exam.title,
    }
    return render(request, 'exam_page.html', context)


@login_required
@require_POST
def save_answer_view(request, exam_id):
    """AJAX endpoint: save a single answer immediately on option click.
    Enforces: attempt belongs to user, not submitted, question not already answered."""
    try:
        data        = json.loads(request.body)
        attempt_id  = data.get('attempt_id')
        question_id = data.get('question_id')
        option_id   = data.get('option_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)

    attempt  = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user, exam_id=exam_id)
    question = get_object_or_404(Question, pk=question_id, exam_id=exam_id)
    option   = get_object_or_404(Option, pk=option_id, question=question)

    if attempt.is_submitted:
        return JsonResponse({'ok': False, 'error': 'Exam already submitted'}, status=403)

    # Reject if timer has expired (30-second grace)
    deadline = attempt.start_time + datetime.timedelta(minutes=attempt.exam.duration_minutes, seconds=30)
    if timezone.now() > deadline:
        return JsonResponse({'ok': False, 'error': 'Time expired'}, status=403)

    # One answer per question - if already answered, reject
    if StudentAnswer.objects.filter(attempt=attempt, question=question).exists():
        return JsonResponse({'ok': False, 'error': 'Already answered'}, status=409)

    StudentAnswer.objects.create(
        attempt=attempt,
        question=question,
        selected_option=option,
        is_correct=option.is_correct,
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def submit_exam_view(request, exam_id):
    """AJAX endpoint: submit the exam, compute score, return JSON with answer key."""
    # Support both JSON body and form-encoded
    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body)
            attempt_id = body.get('attempt_id')
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)
    else:
        attempt_id = request.POST.get('attempt_id')

    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user, exam_id=exam_id)

    if attempt.is_submitted:
        return JsonResponse({'ok': False, 'error': 'Already submitted'}, status=409)

    # Finalize
    _finalize_attempt(attempt)

    # Record streak for exam completion
    _record_streak(request.user)

    # Build answer key for reveal UI
    exam = attempt.exam
    questions_result = []
    saved_answers = {
        sa.question_id: sa
        for sa in attempt.answers.select_related('selected_option')
    }
    for q in exam.questions.prefetch_related('options'):
        correct_opt = q.options.filter(is_correct=True).first()
        sa = saved_answers.get(q.id)
        questions_result.append({
            'question_id': q.id,
            'selected_option_id': sa.selected_option_id if sa else None,
            'correct_option_id': correct_opt.id if correct_opt else None,
            'is_correct': sa.is_correct if sa else False,
        })

    return JsonResponse({
        'ok': True,
        'score': attempt.score,
        'total_questions': attempt.total_questions,
        'correct_answers': attempt.correct_answers,
        'wrong_answers': attempt.wrong_answers,
        'attempt_id': attempt.id,
        'questions': questions_result,
    })


@login_required
def exam_submitted_view(request, exam_id, attempt_id):
    """Simple confirmation page after exam submission - kept for legacy compatibility."""
    exam    = get_object_or_404(Exam, pk=exam_id)
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user, exam=exam)
    context = {
        'exam': exam,
        'attempt': attempt,
        'total_answered': attempt.answers.count(),
        'total_questions': attempt.total_questions or exam.total_questions(),
        'score': attempt.score,
        'correct_answers': attempt.correct_answers,
        'wrong_answers': attempt.wrong_answers,
        'page_title': 'Exam Submitted',
    }
    return render(request, 'exam_submitted.html', context)


@login_required
@require_POST
def delete_attempt_view(request, attempt_id):
    """AJAX endpoint: Deletes an unsubmitted attempt to reset the timer on exit."""
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user)
    if not attempt.is_submitted:
        attempt.delete()
    return JsonResponse({'ok': True})


@login_required
def exam_review_view(request, exam_id, attempt_id):
    """Read-only review of a submitted attempt with answer reveal."""
    exam = get_object_or_404(
        Exam.objects.select_related('course', 'subject').prefetch_related(
            'questions__options'
        ),
        pk=exam_id,
    )
    attempt = get_object_or_404(
        ExamAttempt, pk=attempt_id, user=request.user, exam=exam, is_submitted=True
    )

    if not _user_enrolled(request.user, exam.course):
        messages.error(request, "You must be enrolled in this course.")
        return redirect('courses:past_exams')

    # Build question data with answer reveal info
    saved_answers = {
        sa.question_id: sa
        for sa in attempt.answers.select_related('selected_option')
    }
    questions_data = []
    for q in exam.questions.prefetch_related('options'):
        correct_opt = q.options.filter(is_correct=True).first()
        sa = saved_answers.get(q.id)
        options_data = []
        for o in q.options.all():
            css_class = ''
            icon = ''
            if sa and o.id == sa.selected_option_id:
                if sa.is_correct:
                    css_class = 'correct'
                    icon = '✓'
                else:
                    css_class = 'wrong'
                    icon = '✗'
            elif correct_opt and o.id == correct_opt.id and sa and not sa.is_correct:
                # Show the correct answer when student got it wrong
                css_class = 'correct'
                icon = '✓'
            options_data.append({
                'id': o.id,
                'text': o.text,
                'css_class': css_class,
                'icon': icon,
            })
        questions_data.append({
            'id': q.id,
            'text': q.text,
            'order': q.order,
            'options': options_data,
            'was_answered': sa is not None,
            'was_correct': sa.is_correct if sa else False,
        })

    context = {
        'exam': exam,
        'attempt': attempt,
        'questions': questions_data,
        'page_title': f'Review: {exam.title}',
    }
    return render(request, 'exam_review.html', context)


# ─────────────────────────────────────────────
# Course Store
# ─────────────────────────────────────────────
@login_required
def course_store_view(request):
    all_courses = Course.objects.select_related(
        'class_level'
    ).prefetch_related('instructors', 'content_nodes').all()
    enrolled_ids = set(
        Course.objects.filter(students=request.user).values_list('id', flat=True)
    )
    context = {
        'all_courses': all_courses,
        'enrolled_ids': enrolled_ids,
        'page_title': 'All Courses',
    }
    return render(request, 'course_store.html', context)


@login_required
def course_detail_view(request, course_id):
    course = get_object_or_404(
        Course.objects.select_related('class_level').prefetch_related('instructors', 'content_nodes'),
        pk=course_id
    )
    is_enrolled = _user_enrolled(request.user, course)
    inclusions = [line.strip() for line in course.whats_included.splitlines() if line.strip()]

    context = {
        'course': course,
        'is_enrolled': is_enrolled,
        'inclusions': inclusions,
        'page_title': course.title,
    }
    return render(request, 'course_detail.html', context)


# ─────────────────────────────────────────────
# SSLCommerz Payment
# ─────────────────────────────────────────────
@login_required
@require_POST
def initiate_payment_view(request, course_id):
    import requests
    course = get_object_or_404(Course, pk=course_id)

    if _user_enrolled(request.user, course):
        messages.info(request, "You are already enrolled in this course.")
        return redirect('courses:catalogue')

    amount = course.discount_price if course.discount_price is not None else course.price

    if getattr(course, 'is_free', False) or amount == 0:
        course.students.add(request.user)
        messages.success(request, f"You have successfully enrolled in {course.title}!")
        return redirect('courses:catalogue')

    tran_id = str(uuid.uuid4()).replace('-', '')[:20].upper()
    # Store transaction info in session so we can use it in the callback
    request.session['pending_payment'] = {
        'tran_id': tran_id,
        'course_id': course.id,
        'user_id': request.user.id,
    }

    host = request.get_host()
    scheme = 'https' if request.is_secure() else 'http'
    base_url = f"{scheme}://{host}"

    store_id   = settings.SSLCOMMERZ_STORE_ID
    store_pass = settings.SSLCOMMERZ_STORE_PASS
    is_sandbox = getattr(settings, 'SSLCOMMERZ_SANDBOX', True)
    api_url    = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php" if is_sandbox else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"

    post_data = {
        'store_id':        store_id,
        'store_passwd':    store_pass,
        'total_amount':    str(amount),
        'currency':        'BDT',
        'tran_id':         tran_id,
        'success_url':     f"{base_url}/payment/success/",
        'fail_url':        f"{base_url}/payment/fail/",
        'cancel_url':      f"{base_url}/payment/cancel/",
        'product_name':    course.title,
        'product_category':'Education',
        'product_profile': 'general',
        'cus_name':        request.user.get_full_name() or request.user.user_id,
        'cus_email':       request.user.email or 'noreply@lms.com',
        'cus_phone':       request.user.phone or '01700000000',
        'cus_add1':        'Bangladesh',
        'cus_city':        'Dhaka',
        'cus_country':     'Bangladesh',
        'shipping_method': 'NO',
        'num_of_item':     1,
        'value_a':         str(course.id),
        'value_b':         str(request.user.id),
    }

    try:
        response = requests.post(api_url, data=post_data, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'SUCCESS':
            return redirect(data['GatewayPageURL'])
        else:
            messages.error(request, f"Payment gateway error: {data.get('failedreason', 'Unknown error')}")
    except Exception as e:
        messages.error(request, f"Could not connect to payment gateway. Please try again. ({e})")

    return redirect('courses:course_detail', course_id=course_id)


@csrf_exempt
def payment_success_view(request):
    # Try session first
    pending = request.session.pop('pending_payment', None)

    course_id = None
    user_id = None

    if pending:
        course_id = pending.get('course_id')
        user_id = pending.get('user_id')
    else:
        # Fallback to POST data (IPN)
        course_id = request.POST.get('value_a')
        user_id = request.POST.get('value_b')

    if course_id and user_id:
        try:
            course = Course.objects.get(pk=course_id)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student = User.objects.get(pk=user_id)
            course.students.add(student)
        except Exception as e:
            # Handle possible exception optionally, but pass is kept for safety
            pass

    return render(request, 'payment_result.html', {
        'status': 'success',
        'page_title': 'Payment Successful',
        'message': f"You are now enrolled! Head to your courses.",
    })


@csrf_exempt
def payment_fail_view(request):
    request.session.pop('pending_payment', None)
    return render(request, 'payment_result.html', {
        'status': 'fail',
        'page_title': 'Payment Failed',
        'message': 'Your payment was not completed. Please try again.',
    })


@csrf_exempt
def payment_cancel_view(request):
    request.session.pop('pending_payment', None)
    return render(request, 'payment_result.html', {
        'status': 'cancel',
        'page_title': 'Payment Cancelled',
        'message': 'You cancelled the payment. You can try again anytime.',
    })


@login_required
def student_solve_sheets_view(request):
    """Student view for solve sheets."""
    courses = Course.objects.filter(students=request.user).prefetch_related('content_nodes').all()
    
    catalogue_data = []
    for course in courses:
        subjects_data = []
        subjects = course.content_nodes.filter(parent__isnull=True).order_by('order', 'title')
        for subject in subjects:
            live_folder = subject.children.filter(title__icontains='Live Class').first()
            if live_folder:
                topics = live_folder.children.order_by('order', 'title')
            else:
                topics = subject.children.order_by('order', 'title')
            
            topics_data = [{'id': t.id, 'title': t.title} for t in topics]
            subjects_data.append({
                'id': subject.id,
                'title': subject.title,
                'topics': topics_data
            })
        
        sheets = SolveSheet.objects.filter(course=course).select_related('subject', 'topic').order_by('-uploaded_at')
        sheets_data = [{
            'id': s.id,
            'title': s.title,
            'subject_id': s.subject_id,
            'topic_id': s.topic_id,
            'url': s.file.url if s.file else '',
            'uploaded_at': s.uploaded_at.strftime('%b %d, %Y')
        } for s in sheets]

        catalogue_data.append({
            'id': course.id,
            'title': course.title,
            'subjects': subjects_data,
            'solve_sheets': sheets_data
        })
        
    context = {
        'catalogue_data_json': catalogue_data,
        'page_title': 'Solve Sheets',
    }
    return render(request, 'solve_sheets_student.html', context)


# ─────────────────────────────────────────────
# Streak Profile View
# ─────────────────────────────────────────────

@login_required
def streak_profile_view(request):
    """Dedicated page showing full streak stats and all badges."""
    streak_ctx = _get_streak_context(request.user)

    # Build milestones with earned status for the full progress grid
    try:
        streak = request.user.streak
        earned_days = set(b.days_required for b in streak.badges.all())
        current_streak = streak.current_streak
        longest_streak = streak.longest_streak
    except StudentStreak.DoesNotExist:
        earned_days = set()
        current_streak = 0
        longest_streak = 0

    milestones = []
    for days, name in BADGE_MILESTONES:
        milestones.append({
            'days': days,
            'name': name,
            'earned': days in earned_days,
            'progress_pct': min(100, int((longest_streak / days) * 100)) if days > 0 else 0,
        })

    context = {
        'page_title': 'My Streak & Badges',
        'milestones': milestones,
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        **streak_ctx,
    }
    return render(request, 'streak_profile.html', context)


@login_required
def academic_results_view(request):
    """View to search and display academic results for Tutorial, Half Yearly, and Yearly exams."""
    exam_type = request.GET.get('exam_type')
    uid = request.GET.get('uid', '').strip()
    reg = request.GET.get('reg', '').strip()

    context = {
        'page_title': 'Academic Results',
        'exam_type': exam_type,
        'uid': uid,
        'reg': reg,
        'searched': False,
        'not_published': False,
        'result_data': None,
    }

    if exam_type:
        context['searched'] = True
        
        # Yearly is not published yet, as per requirement
        if exam_type.lower() == 'yearly':
            context['not_published'] = True
        elif exam_type.lower() in ('tutorial', 'half_yearly'):
            # Only match the specified dummy credentials
            if uid == '86957399' and reg == '86957399':
                if exam_type.lower() == 'tutorial':
                    context['result_data'] = {
                        'student_name': 'Farhan Tanvir',
                        'uid': '86957399',
                        'reg': '86957399',
                        'exam_title': 'Tutorial Examination',
                        'class_level': 'Class XII (Science)',
                        'gpa': '5.00',
                        'grade': 'A+',
                        'total_marks': 776,
                        'max_marks': 900,
                        'status': 'Passed',
                        'subjects': [
                            {'name': 'Bangla', 'mcq': 26, 'cq': 61, 'practical': None, 'total': 87, 'grade': 'A+'},
                            {'name': 'English', 'mcq': None, 'cq': 84, 'practical': None, 'total': 84, 'grade': 'A+'},
                            {'name': 'Physics 1st', 'mcq': 22, 'cq': 41, 'practical': 23, 'total': 86, 'grade': 'A+'},
                            {'name': 'Physics 2nd', 'mcq': 20, 'cq': 43, 'practical': 22, 'total': 85, 'grade': 'A+'},
                            {'name': 'Chem 1st', 'mcq': 23, 'cq': 39, 'practical': 24, 'total': 86, 'grade': 'A+'},
                            {'name': 'Chem 2nd', 'mcq': 21, 'cq': 40, 'practical': 23, 'total': 84, 'grade': 'A+'},
                            {'name': 'Biology 1st', 'mcq': 22, 'cq': 42, 'practical': 24, 'total': 88, 'grade': 'A+'},
                            {'name': 'Biology 2nd', 'mcq': 24, 'cq': 38, 'practical': 23, 'total': 85, 'grade': 'A+'},
                            {'name': 'ICT', 'mcq': 23, 'cq': 44, 'practical': 24, 'total': 91, 'grade': 'A+'},
                        ]
                    }
                else:  # half_yearly
                    context['result_data'] = {
                        'student_name': 'Farhan Tanvir',
                        'uid': '86957399',
                        'reg': '86957399',
                        'exam_title': 'Half Yearly Examination',
                        'class_level': 'Class XII (Science)',
                        'gpa': '4.67',
                        'grade': 'A',
                        'total_marks': 728,
                        'max_marks': 900,
                        'status': 'Passed',
                        'subjects': [
                            {'name': 'Bangla', 'mcq': 24, 'cq': 58, 'practical': None, 'total': 82, 'grade': 'A+'},
                            {'name': 'English', 'mcq': None, 'cq': 76, 'practical': None, 'total': 76, 'grade': 'A'},
                            {'name': 'Physics 1st', 'mcq': 21, 'cq': 39, 'practical': 22, 'total': 82, 'grade': 'A+'},
                            {'name': 'Physics 2nd', 'mcq': 19, 'cq': 40, 'practical': 21, 'total': 80, 'grade': 'A+'},
                            {'name': 'Chem 1st', 'mcq': 20, 'cq': 38, 'practical': 23, 'total': 81, 'grade': 'A+'},
                            {'name': 'Chem 2nd', 'mcq': 18, 'cq': 39, 'practical': 22, 'total': 79, 'grade': 'A'},
                            {'name': 'Biology 1st', 'mcq': 22, 'cq': 39, 'practical': 23, 'total': 84, 'grade': 'A+'},
                            {'name': 'Biology 2nd', 'mcq': 20, 'cq': 37, 'practical': 22, 'total': 79, 'grade': 'A'},
                            {'name': 'ICT', 'mcq': 22, 'cq': 41, 'practical': 22, 'total': 85, 'grade': 'A+'},
                        ]
                    }
            else:
                context['not_published'] = True

    return render(request, 'academic_results.html', context)


# ─────────────────────────────────────────────
# AI Study Assistant
# ─────────────────────────────────────────────

def _build_class_context(node):
    """Build a text context from the node title, description, and PDF attachments."""
    parts = [f"Class Title: {node.title}"]
    if node.description:
        parts.append(f"Description: {node.description}")

    attachments = node.attachments_new.all()
    for att in attachments:
        parts.append(f"\n--- Attachment: {att.name} ({att.get_file_type_display()}) ---")
        if att.file and att.file_type == 'pdf':
            try:
                import PyPDF2
                with att.file.open('rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages[:12]:  # cap at 12 pages
                        extracted = page.extract_text()
                        if extracted:
                            parts.append(extracted)
            except ImportError:
                parts.append("[PDF content not extractable – PyPDF2 not installed]")
            except Exception:
                pass
        elif att.file and att.file_type in ('note', 'other'):
            try:
                with att.file.open('r', encoding='utf-8', errors='ignore') as f:
                    parts.append(f.read(6000))
            except Exception:
                pass
        elif att.external_url:
            parts.append(f"External URL: {att.external_url}")

    return "\n".join(parts)


_AI_PROMPTS = {
    'notes': (
        "You are an expert teacher. Based on the class material below, write comprehensive, "
        "well-structured study notes in plain text. Use headings (##), bullet points, bold (**term**), "
        "and numbered lists where appropriate. Cover every key concept thoroughly.\n\nMaterial:\n{ctx}"
    ),
    'flashcards': (
        "You are an expert teacher. Based on the class material below, create exactly 10 flashcards. "
        "Return ONLY a valid JSON array. Each element: {{\"question\": \"...\", \"answer\": \"...\"}}.\n\nMaterial:\n{ctx}"
    ),
    'mcqs': (
        "You are an expert teacher preparing board-competitive MCQs. Based on the class material below, "
        "create exactly 10 multiple-choice questions. Return ONLY a valid JSON array. "
        "Each element: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], "
        "\"correct\": 0, \"explanation\": \"...\"}}.  'correct' is the 0-indexed position of the right answer.\n\nMaterial:\n{ctx}"
    ),
    'summary': (
        "You are an expert teacher. Based on the class material below, write a concise summary "
        "in 2-3 paragraphs covering the most important concepts and takeaways.\n\nMaterial:\n{ctx}"
    ),
    'next_topics': (
        "You are an expert curriculum designer. Based on the class material below, suggest the next "
        "8 topics the student should study. Return ONLY a valid JSON array. "
        "Each element: {{\"title\": \"...\", \"reason\": \"...\"}}.\n\nMaterial:\n{ctx}"
    ),
}


@login_required
def ai_status_view(request, node_id):
    """Return which AI content types have already been generated for this node."""
    node = get_object_or_404(ContentNode, pk=node_id)
    if not _user_enrolled(request.user, node.course):
        return JsonResponse({'ok': False, 'error': 'Not enrolled'}, status=403)

    existing = AIContent.objects.filter(node=node)
    status = {}
    for ac in existing:
        status[ac.content_type] = {
            'exists': True,
            'generated_at': ac.updated_at.strftime('%b %d, %Y • %H:%M'),
        }
    return JsonResponse({'ok': True, 'status': status})


@login_required
def ai_get_content_view(request, node_id, content_type):
    """Return saved AI content for a specific type."""
    node = get_object_or_404(ContentNode, pk=node_id)
    if not _user_enrolled(request.user, node.course):
        return JsonResponse({'ok': False, 'error': 'Not enrolled'}, status=403)

    try:
        ac = AIContent.objects.get(node=node, content_type=content_type)
        return JsonResponse({
            'ok': True,
            'content': ac.content,
            'content_type': content_type,
            'generated_at': ac.updated_at.strftime('%b %d, %Y • %H:%M'),
        })
    except AIContent.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Not generated yet'})


@login_required
@require_POST
def ai_generate_view(request, node_id, content_type):
    """Generate AI content, save it, and return the result."""
    if content_type not in dict(AIContent.CONTENT_TYPES):
        return JsonResponse({'ok': False, 'error': 'Invalid content type'}, status=400)

    node = get_object_or_404(ContentNode, pk=node_id)
    if not _user_enrolled(request.user, node.course):
        return JsonResponse({'ok': False, 'error': 'Not enrolled'}, status=403)

    ctx = _build_class_context(node)
    prompt = _AI_PROMPTS[content_type].format(ctx=ctx[:12000])  # guard token limit

    try:
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are an expert educational content creator for an online LMS. '
                        'Always follow the exact output format requested by the user.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            max_tokens=3000,
            temperature=0.6,
        )
        raw = response.choices[0].message.content.strip()
    except ImportError:
        return JsonResponse({'ok': False, 'error': 'openai package not installed. Run: pip install openai'}, status=500)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)

    # Parse structured types
    if content_type in ('flashcards', 'mcqs', 'next_topics'):
        import re
        m = re.search(r'(\[.*\]|\{.*\})', raw, re.DOTALL)
        try:
            content_data = json.loads(m.group(1) if m else raw)
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'ok': False, 'error': 'AI returned malformed JSON. Please try again.'}, status=500)
    else:
        content_data = {'text': raw}

    # Upsert
    AIContent.objects.update_or_create(
        node=node, content_type=content_type,
        defaults={'content': content_data},
    )

    return JsonResponse({'ok': True, 'content': content_data, 'content_type': content_type})


@login_required
def board_questions_view(request):
    """View to list and filter board questions."""
    questions = BoardQuestion.objects.all().order_by('-year', 'board_name', 'title')
    
    boards = ['Dhaka', 'Rajshahi', 'Cumilla', 'Jashore', 'Chattogram', 'Barishal', 'Sylhet', 'Dinajpur', 'Mymensingh']
    
    # Extract distinct years from the database
    years = sorted(list(BoardQuestion.objects.values_list('year', flat=True).distinct()), reverse=True)
    types = ['Written', 'MCQ']
    
    questions_data = []
    for q in questions:
        questions_data.append({
            'id': q.id,
            'title': q.title,
            'board_name': q.board_name,
            'year': q.year,
            'exam_type': q.exam_type,
            'pdf_url': q.pdf_file.url if q.pdf_file else '',
        })
        
    context = {
        'board_questions_json': questions_data,
        'boards': boards,
        'years': years,
        'types': types,
        'page_title': 'Board Questions',
    }
    return render(request, 'board_questions.html', context)


@login_required
def board_question_detail_view(request, question_id):
    """View to read a specific board question with an integrated PDF viewer."""
    question = get_object_or_404(BoardQuestion, pk=question_id)
    
    # Record streak for reading a board question
    _record_streak(request.user)
    
    context = {
        'question': question,
        'page_title': question.title,
    }
    return render(request, 'board_question_detail.html', context)


# ─────────────────────────────────────────────
# Scholarships & Admissions
# ─────────────────────────────────────────────

@login_required
def scholarships_view(request):
    """Main scholarships listing page with filtering."""
    category_filter = request.GET.get('category', 'all')
    level_filter = request.GET.get('level', 'all')
    status_filter = request.GET.get('status', 'all')

    scholarships = Scholarship.objects.all()
    if category_filter != 'all':
        scholarships = scholarships.filter(category=category_filter)
    if level_filter != 'all':
        scholarships = scholarships.filter(level=level_filter)
    if status_filter != 'all':
        scholarships = scholarships.filter(status=status_filter)

    # Which scholarships has this user already applied to?
    applied_ids = set(
        ScholarshipApplication.objects.filter(user=request.user)
        .values_list('scholarship_id', flat=True)
    )

    context = {
        'scholarships': scholarships,
        'applied_ids': applied_ids,
        'category_filter': category_filter,
        'level_filter': level_filter,
        'status_filter': status_filter,
        'page_title': 'Scholarships & Admissions',
    }
    return render(request, 'scholarships.html', context)


@login_required
@require_POST
def scholarship_apply_view(request, scholarship_id):
    """Handle scholarship application submission."""
    scholarship = get_object_or_404(Scholarship, pk=scholarship_id, status='open')

    # Prevent duplicate application
    if ScholarshipApplication.objects.filter(scholarship=scholarship, user=request.user).exists():
        messages.warning(request, f'You have already applied for "{scholarship.title}".')
        return redirect('courses:scholarships')

    full_name = request.POST.get('full_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    message = request.POST.get('message', '').strip()

    if not full_name or not email:
        messages.error(request, 'Full name and email are required.')
        return redirect('courses:scholarships')

    ScholarshipApplication.objects.create(
        scholarship=scholarship,
        user=request.user,
        full_name=full_name,
        email=email,
        phone=phone,
        message=message,
    )

    messages.success(request, f'Your application for "{scholarship.title}" has been submitted successfully!')
    return redirect('courses:scholarships')


