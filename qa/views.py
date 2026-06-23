import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from courses.models import ContentNode, Course
from .models import QAAnswer, QAQuestion

logger = logging.getLogger(__name__)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _enrolled_courses(user):
    return user.enrolled_courses.all()


def _teacher_courses(user):
    """All courses where this teacher is the instructor OR all courses for super_teachers."""
    if user.is_super_teacher:
        return Course.objects.all()
    return Course.objects.filter(instructors=user)


# ─── Student: Q&A list ───────────────────────────────────────────────────────

@login_required
def qa_list_view(request):
    enrolled = _enrolled_courses(request.user)
    questions = (
        QAQuestion.objects
        .filter(course__in=enrolled)
        .select_related('user', 'course', 'subject')
        .prefetch_related('answers')
        .order_by('-created_at')
    )
    return render(request, 'qa_list.html', {
        'questions': questions,
        'page_title': 'Q&A Service',
        'enrolled_courses': enrolled,
    })


# ─── Student: Ask a question ─────────────────────────────────────────────────

@login_required
def qa_ask_view(request):
    enrolled = _enrolled_courses(request.user)
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        subject_id = request.POST.get('subject_id') or None
        content = request.POST.get('content', '').strip()

        if not course_id or not content:
            return render(request, 'qa_ask.html', {
                'error': 'Course and question text are required.',
                'enrolled_courses': enrolled,
                'page_title': 'Ask a Question',
            })

        course = get_object_or_404(Course, pk=course_id)
        # Verify the student is actually enrolled
        if course not in enrolled:
            return redirect('qa:qa_list')

        subject = None
        if subject_id:
            subject = ContentNode.objects.filter(pk=subject_id, course=course, parent__isnull=True).first()

        q = QAQuestion(
            user=request.user,
            course=course,
            subject=subject,
            content=content,
        )
        if request.FILES.get('image'):
            q.image = request.FILES['image']
        if request.FILES.get('pdf'):
            q.pdf = request.FILES['pdf']
        if request.FILES.get('audio'):
            q.audio = request.FILES['audio']
        q.save()

        return redirect('qa:qa_choice', q_id=q.pk)

    return render(request, 'qa_ask.html', {
        'enrolled_courses': enrolled,
        'page_title': 'Ask a Question',
    })


# ─── Student: Choose AI or Human ─────────────────────────────────────────────

@login_required
def qa_choice_view(request, q_id):
    question = get_object_or_404(QAQuestion, pk=q_id, user=request.user)
    return render(request, 'qa_choice.html', {
        'question': question,
        'page_title': 'Choose Responder',
    })


# ─── Student: Submit (AJAX) - sets answer_type, optionally calls AI ──────────

@login_required
@require_POST
def qa_submit_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    q_id       = data.get('question_id')
    answer_type = data.get('answer_type', 'human')

    question = get_object_or_404(QAQuestion, pk=q_id, user=request.user)
    question.answer_type = answer_type

    if answer_type == 'ai':
        ai_text = _call_openai(question)
        if ai_text:
            QAAnswer.objects.create(
                question=question,
                is_ai=True,
                responder=None,
                content=ai_text,
            )
            question.status = 'ai_answered'
        else:
            question.status = 'pending'
    else:
        question.status = 'pending'

    question.save()
    return JsonResponse({'success': True, 'question_id': question.pk})


def _call_openai(question: QAQuestion) -> str:
    """Call OpenAI chat completion and return response text, or '' on failure."""
    try:
        from django.conf import settings as djsettings
        api_key = getattr(djsettings, 'OPENAI_API_KEY', '')
        if not api_key:
            return 'AI response unavailable: OpenAI API key not configured.'

        from openai import OpenAI
        import base64
        import PyPDF2
        import os

        client = OpenAI(api_key=api_key)

        course_name  = question.course.title
        subject_name = question.subject.title if question.subject else 'General'
        
        system_prompt = (
            f"You are a helpful academic tutor for the course '{course_name}' "
            f"(subject: {subject_name}). "
            f"Explain precisely in simple words. No unnecessary yapping."
        )

        messages_content = []
        if question.content:
            messages_content.append({"type": "text", "text": question.content})

        if question.pdf and question.pdf.name and os.path.exists(question.pdf.path):
            try:
                pdf_text = ""
                with open(question.pdf.path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        if page.extract_text():
                            pdf_text += page.extract_text() + "\n"
                if pdf_text:
                    messages_content.append({
                        "type": "text", 
                        "text": f"Context from attached PDF:\n{pdf_text[:15000]}"
                    })
            except Exception as e:
                logger.warning(f"Failed to read PDF: {e}")

        if question.audio and question.audio.name and os.path.exists(question.audio.path):
            try:
                with open(question.audio.path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                if transcription.text:
                    messages_content.append({
                        "type": "text",
                        "text": f"Transcript of attached audio message:\n{transcription.text}"
                    })
            except Exception as e:
                logger.warning(f"Failed to transcribe audio: {e}")

        if question.image and question.image.name and os.path.exists(question.image.path):
            try:
                with open(question.image.path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    ext = os.path.splitext(question.image.path)[1].lower()
                    mime_type = "image/jpeg"
                    if ext == ".png": mime_type = "image/png"
                    elif ext == ".webp": mime_type = "image/webp"
                    elif ext == ".gif": mime_type = "image/gif"
                    
                    messages_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    })
            except Exception as e:
                logger.warning(f"Failed to process image: {e}")

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': messages_content}
            ],
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception('OpenAI call failed: %s', exc)
        return f'AI response error: {exc}'


# ─── Student: Thread detail ───────────────────────────────────────────────────

@login_required
def qa_thread_view(request, q_id):
    question = get_object_or_404(
        QAQuestion.objects.select_related('user', 'course', 'subject').prefetch_related('answers__responder'),
        pk=q_id,
    )
    # Students can view threads for courses they are enrolled in
    if request.user.is_student() and question.course not in _enrolled_courses(request.user):
        return redirect('qa:qa_list')

    return render(request, 'qa_thread.html', {
        'question': question,
        'page_title': f'Q&A Thread #{question.pk}',
    })


# ─── Teacher: Q&A list ───────────────────────────────────────────────────────

@login_required
def teacher_qa_list_view(request):
    if not request.user.is_teacher():
        return redirect('courses:dashboard')

    teacher_courses = _teacher_courses(request.user)

    # Filters
    course_id  = request.GET.get('course_id')
    subject_id = request.GET.get('subject_id')
    status     = request.GET.get('status')

    qs = (
        QAQuestion.objects
        .filter(course__in=teacher_courses)
        .select_related('user', 'course', 'subject')
        .prefetch_related('answers')
        .order_by('-created_at')
    )
    if course_id:
        qs = qs.filter(course_id=course_id)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if status:
        qs = qs.filter(status=status)

    return render(request, 'teacher/qa_panel.html', {
        'questions': qs,
        'teacher_courses': teacher_courses,
        'selected_course_id': int(course_id) if course_id else None,
        'selected_status': status or '',
        'page_title': 'Q&A Service',
        'active_section': 'qa-module',
    })


# ─── Teacher: Reply ──────────────────────────────────────────────────────────

@login_required
@require_POST
def teacher_qa_reply_view(request, q_id):
    if not request.user.is_teacher():
        return redirect('courses:dashboard')

    question = get_object_or_404(QAQuestion, pk=q_id)
    content  = request.POST.get('content', '').strip()

    if content:
        ans = QAAnswer(
            question=question,
            responder=request.user,
            is_ai=False,
            content=content,
        )
        if request.FILES.get('image'):
            ans.image = request.FILES['image']
        if request.FILES.get('audio'):
            ans.audio = request.FILES['audio']
        ans.save()

        question.status = 'answered'
        question.save()

    return redirect('qa:qa_thread', q_id=q_id)
