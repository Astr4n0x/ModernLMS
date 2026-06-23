import json
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Max

from courses.models import Course, CourseBundle, ContentNode, ClassLevel, Exam, Question, Option, SolveSheet, BoardQuestion
from live.models import LiveSession, LiveComment
from .models import Attachment

User = get_user_model()


# ─── Decorators ──────────────────────────────────────────────────────────────
def teacher_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher():
            return redirect('courses:dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def super_teacher_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_teacher() or not request.user.is_super_teacher:
            messages.error(request, "You do not have permission to access that feature.")
            return redirect('/teacher/')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─── Main Panel ──────────────────────────────────────────────────────────────
@teacher_required
def panel_view(request):
    # Which sidebar section should be active (persists across refresh)
    active_section = request.GET.get('section', 'content-builder-module')

    courses = Course.objects.prefetch_related('content_nodes').all()
    lessons = ContentNode.objects.filter(node_type='class').select_related('course').order_by('-created_at')
    live_sessions = LiveSession.objects.filter(is_live=True).select_related('content_node__course')
    class_levels = ClassLevel.objects.all()

    context = {
        'courses': courses,
        'lessons': lessons,
        'live_sessions': live_sessions,
        'class_levels': class_levels,
        'all_exams': Exam.objects.select_related('course', 'subject', 'topic').order_by('-created_at'),
        'page_title': 'Teacher Admin Panel',
        'active_section': active_section,
    }

    if request.user.is_super_teacher:
        context['all_students'] = User.objects.filter(role='student').order_by('first_name')
        context['all_teachers'] = User.objects.filter(role='teacher').order_by('first_name')
        context['all_courses'] = Course.objects.annotate(student_count=Count('students')).order_by('title')
        context['all_teachers_for_course'] = User.objects.filter(role='teacher')

    return render(request, 'teacher/panel.html', context)


# ─── Subject & Topic Creation (all teachers) ─────────────────────────────────
@teacher_required
@require_POST
def create_subject_view(request):
    course_id = request.POST.get('course_id')
    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    if not course_id or not title:
        messages.error(request, 'Course and subject title are required.')
        return redirect('/teacher/?section=content-builder-module')
    course = get_object_or_404(Course, pk=course_id)
    ContentNode.objects.get_or_create(
        title=title, 
        course=course, 
        parent=None, 
        node_type='subject',
        defaults={'description': description}
    )
    messages.success(request, f'Subject "{title}" created under {course.title}.')
    return redirect('/teacher/?section=content-builder-module')


@teacher_required
@require_POST
def create_topic_view(request):
    parent_id = request.POST.get('subject_id')
    title = request.POST.get('title', '').strip()
    order = request.POST.get('order', 1)
    if not parent_id or not title:
        messages.error(request, 'Parent Subject and topic title are required.')
        return redirect('/teacher/?section=content-builder-module')
    parent = get_object_or_404(ContentNode, pk=parent_id)
    ContentNode.objects.get_or_create(
        title=title, 
        parent=parent, 
        course=parent.course,
        node_type='topic',
        defaults={'order': order}
    )
    messages.success(request, f'Topic "{title}" added under {parent.title}.')
    return redirect('/teacher/?section=content-builder-module')


# ─── Exam Creation (all teachers) ───────────────────────────────────────────
@teacher_required
def create_exam_view(request):
    """GET: render exam creation page.  POST: save exam + questions via JSON."""
    if request.method == 'GET':
        courses = Course.objects.all()
        return render(request, 'teacher/exam_create.html', {
            'courses': courses,
            'page_title': 'Create Exam',
            'active_section': 'exams-module',
        })

    # POST - expect JSON body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)

    title = data.get('title', '').strip()
    course_id = data.get('course_id')
    subject_id = data.get('subject_id') or None
    topic_id = data.get('topic_id') or None
    duration = data.get('duration_minutes', 30)
    questions_data = data.get('questions', [])

    if not title or not course_id:
        return JsonResponse({'success': False, 'message': 'Exam title and course are required.'}, status=400)

    if not questions_data:
        return JsonResponse({'success': False, 'message': 'At least one question is required.'}, status=400)

    course = get_object_or_404(Course, pk=course_id)
    subject = get_object_or_404(ContentNode, pk=subject_id, course=course) if subject_id else None
    topic = get_object_or_404(ContentNode, pk=topic_id, course=course) if topic_id else None

    with transaction.atomic():
        exam = Exam.objects.create(
            title=title,
            course=course,
            subject=subject,
            topic=topic,
            duration_minutes=int(duration),
            is_published=True
        )

        for idx, q in enumerate(questions_data, start=1):
            q_text = q.get('text', '').strip()
            if not q_text:
                continue
            question = Question.objects.create(exam=exam, text=q_text, order=idx)
            options = q.get('options', [])
            correct_index = q.get('correct_index', 0)
            for o_idx, opt_text in enumerate(options):
                opt_text = opt_text.strip()
                if not opt_text:
                    continue
                Option.objects.create(
                    question=question,
                    text=opt_text,
                    is_correct=(o_idx == correct_index),
                    order=o_idx + 1
                )

    return JsonResponse({'success': True, 'message': f'Exam "{title}" created with {len(questions_data)} question(s).'})


@teacher_required
def edit_exam_view(request, exam_id):
    """GET: render edit page with existing data.  POST: save changes via JSON."""
    exam = get_object_or_404(Exam, pk=exam_id)

    if request.method == 'GET':
        courses = Course.objects.all()
        questions = []
        for q in exam.questions.prefetch_related('options').all():
            correct_idx = 0
            opts = []
            for i, o in enumerate(q.options.all()):
                opts.append(o.text)
                if o.is_correct:
                    correct_idx = i
            questions.append({
                'id': q.id,
                'text': q.text,
                'options': opts,
                'correct_index': correct_idx,
            })

        return render(request, 'teacher/exam_edit.html', {
            'exam': exam,
            'courses': courses,
            'questions_json': json.dumps(questions),
            'page_title': f'Edit: {exam.title}',
            'active_section': 'exams-module',
        })

    # POST - JSON body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON.'}, status=400)

    title = data.get('title', '').strip()
    course_id = data.get('course_id')
    subject_id = data.get('subject_id') or None
    topic_id = data.get('topic_id') or None
    duration = data.get('duration_minutes', 30)
    questions_data = data.get('questions', [])

    if not title or not course_id:
        return JsonResponse({'success': False, 'message': 'Exam title and course are required.'}, status=400)

    course = get_object_or_404(Course, pk=course_id)
    subject = get_object_or_404(ContentNode, pk=subject_id, course=course) if subject_id else None
    topic = get_object_or_404(ContentNode, pk=topic_id, course=course) if topic_id else None

    with transaction.atomic():
        exam.title = title
        exam.course = course
        exam.subject = subject
        exam.topic = topic
        exam.duration_minutes = int(duration)
        exam.save()

        # Delete old questions & options, re-create from scratch
        exam.questions.all().delete()

        for idx, q in enumerate(questions_data, start=1):
            q_text = q.get('text', '').strip()
            if not q_text:
                continue
            question = Question.objects.create(exam=exam, text=q_text, order=idx)
            options = q.get('options', [])
            correct_index = q.get('correct_index', 0)
            for o_idx, opt_text in enumerate(options):
                opt_text = opt_text.strip()
                if not opt_text:
                    continue
                Option.objects.create(
                    question=question,
                    text=opt_text,
                    is_correct=(o_idx == correct_index),
                    order=o_idx + 1
                )

    return JsonResponse({'success': True, 'message': f'Exam "{title}" updated successfully.'})


@teacher_required
@require_POST
def delete_exam_view(request, exam_id):
    exam = get_object_or_404(Exam, pk=exam_id)
    exam_title = exam.title
    exam.delete()
    messages.success(request, f'Exam "{exam_title}" deleted.')
    return redirect('/teacher/?section=exams-module')


# ─── Lesson Upload ────────────────────────────────────────────────────────────
@teacher_required
@require_POST
def upload_lesson_view(request):
    parent_id = request.POST.get('topic_id') or request.POST.get('subject_id')
    title = request.POST.get('title', '').strip()
    youtube_url = request.POST.get('youtube_url', '').strip()
    description = request.POST.get('description', '').strip()

    if not all([parent_id, title]):
        messages.error(request, 'Parent (Subject/Topic) and lesson title are required.')
        return redirect('/teacher/?section=content-builder-module')

    parent = get_object_or_404(ContentNode, pk=parent_id)
    lesson_count = parent.children.count()

    node = ContentNode.objects.create(
        title=title,
        order=lesson_count + 1,
        description=description,
        youtube_url=youtube_url,
        parent=parent,
        course=parent.course,
        node_type='class',
        status='published',
    )

    # Handle multiple attachments
    names = request.POST.getlist('attachment_name')
    types = request.POST.getlist('attachment_type')
    ext_urls = request.POST.getlist('attachment_url')
    files = request.FILES.getlist('attachment_file')

    for i, name in enumerate(names):
        if not name.strip():
            continue
        att = Attachment(
            content_node=node, name=name.strip(),
            file_type=types[i] if i < len(types) else 'other',
        )
        if i < len(files) and files[i]:
            att.file = files[i]
        elif i < len(ext_urls) and ext_urls[i]:
            att.external_url = ext_urls[i]
        att.save()

    messages.success(request, f'Lesson "{node.title}" published successfully!')
    return redirect('/teacher/?section=content-builder-module')


# ─── Live Session Management ──────────────────────────────────────────────────
@teacher_required
@require_POST
def start_live_view(request, lesson_id):
    node = get_object_or_404(ContentNode, pk=lesson_id)
    # End any other live sessions for this node first
    LiveSession.objects.filter(content_node=node, is_live=True).update(is_live=False)
    session = LiveSession.objects.create(content_node=node, is_live=True)
    node.status = 'live'
    node.save()
    return JsonResponse({'session_id': session.id, 'message': 'Live session started.'})


@teacher_required
@require_POST
def end_live_view(request, session_id):
    session = get_object_or_404(LiveSession, pk=session_id)
    session.is_live = False
    session.ended_at = timezone.now()
    session.save()
    node = session.content_node
    if node:
        node.status = 'past_live'
        node.save()
    return JsonResponse({'message': 'Live session ended. Lesson marked as Past Live.'})


@teacher_required
@require_POST
def toggle_lesson_status_view(request, lesson_id):
    node = get_object_or_404(ContentNode, pk=lesson_id)
    new_status = request.POST.get('status', 'past_live')
    if new_status in ['published', 'recorded', 'past_live']:
        node.status = new_status
        node.save()
        return JsonResponse({'message': f'Status changed to {new_status}.', 'new_status': new_status})
    return JsonResponse({'message': 'Invalid status.'}, status=400)


@teacher_required
def live_monitor_view(request):
    live_sessions = LiveSession.objects.filter(is_live=True).select_related('content_node__course')
    return render(request, 'teacher/live_monitor.html', {
        'live_sessions': live_sessions,
        'page_title': 'Live Classes',
    })


# ─── Lesson & Attachment Management ──────────────────────────────────────────
@teacher_required
@require_POST
def delete_lesson_view(request, lesson_id):
    node = get_object_or_404(ContentNode, pk=lesson_id)
    node.delete()
    messages.success(request, 'Lesson deleted.')
    return redirect('/teacher/?section=manage-module')


@teacher_required
@require_POST
def add_attachment_view(request, lesson_id):
    node = get_object_or_404(ContentNode, pk=lesson_id)
    name = request.POST.get('name', '').strip()
    file_type = request.POST.get('file_type', 'other')
    ext_url = request.POST.get('external_url', '').strip()
    uploaded_file = request.FILES.get('file')
    if not name:
        messages.error(request, 'Attachment name is required.')
        return redirect('/teacher/?section=attachment-module')
    att = Attachment(content_node=node, name=name, file_type=file_type)
    if uploaded_file:
        att.file = uploaded_file
    elif ext_url:
        att.external_url = ext_url
    att.save()
    messages.success(request, f'Attachment "{name}" added.')
    return redirect('/teacher/?section=attachment-module')


@teacher_required
def edit_lesson_view(request, lesson_id):
    node = get_object_or_404(ContentNode, pk=lesson_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        youtube_url = request.POST.get('youtube_url', '').strip()
        description = request.POST.get('description', '').strip()
        if title:
            node.title = title
            node.youtube_url = youtube_url
            node.description = description
            node.save()
            messages.success(request, f'Lesson "{node.title}" updated.')
            return redirect('/teacher/?section=manage-module')
        else:
            messages.error(request, 'Title is required.')
    return render(request, 'teacher/edit_lesson.html', {
        'lesson': node, 'page_title': f'Edit: {node.title}'
    })


@teacher_required
@require_POST
def delete_attachment_view(request, attachment_id):
    attachment = get_object_or_404(Attachment, pk=attachment_id)
    lesson_id = attachment.content_node.id
    attachment.delete()
    messages.success(request, 'Attachment removed.')
    return redirect('teacher:edit_lesson', lesson_id=lesson_id)


# ─── Super Teacher: Student & Course Management ───────────────────────────────
@super_teacher_required
@require_POST
def assign_course_view(request):
    student_id = request.POST.get('student_id')
    course_id = request.POST.get('course_id')
    if not student_id or not course_id:
        messages.error(request, "Please select both a student and a course.")
        return redirect('/teacher/?section=students-module')
    student = get_object_or_404(User, pk=student_id, role='student')
    course = get_object_or_404(Course, pk=course_id)
    course.students.add(student)
    messages.success(request, f"{student.get_full_name() or student.user_id} enrolled in {course.title}.")
    return redirect('/teacher/?section=students-module')


@super_teacher_required
@require_POST
def add_teacher_view(request):
    first_name = request.POST.get('first_name', '').strip()
    last_name  = request.POST.get('last_name', '').strip()
    email      = request.POST.get('email', '').strip()
    username   = request.POST.get('user_id', '').strip()
    password   = request.POST.get('password', '')
    is_super   = request.POST.get('is_super_teacher') == 'on'

    if not all([first_name, last_name, email, username, password]):
        messages.error(request, "All fields are required.")
        return redirect('/teacher/?section=teachers-module')
    if User.objects.filter(user_id=username).exists():
        messages.error(request, f"User ID '{username}' is already taken.")
        return redirect('/teacher/?section=teachers-module')

    User.objects.create_user(
        username=username, user_id=username, email=email, password=password,
        first_name=first_name, last_name=last_name,
        role='teacher', is_super_teacher=is_super
    )
    messages.success(request, f"Teacher {first_name} {last_name} created.")
    return redirect('/teacher/?section=teachers-module')


# ─── Super Teacher: Publish Course ────────────────────────────────────────────
@super_teacher_required
@require_POST
def publish_course_view(request):
    title       = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    whats_included = request.POST.get('whats_included', '').strip()
    price       = request.POST.get('price', '0')
    class_level_id = request.POST.get('class_level_id') or None
    instructor_ids = request.POST.getlist('instructor_ids')
    thumbnail   = request.FILES.get('thumbnail')

    if not title or not description:
        messages.error(request, "Title and description are required.")
        return redirect('/teacher/?section=publish-course-module')

    class_level = ClassLevel.objects.filter(pk=class_level_id).first() if class_level_id else None

    course = Course.objects.create(
        title=title, description=description, whats_included=whats_included,
        price=price, class_level=class_level,
        is_published=True,
    )
    
    if instructor_ids:
        instructors = User.objects.filter(pk__in=instructor_ids, role='teacher')
        course.instructors.set(instructors)

    if thumbnail:
        course.thumbnail = thumbnail
        course.save()

    messages.success(request, f'Course "{course.title}" published successfully!')
    return redirect('/teacher/?section=publish-course-module')


# ─── Super Teacher: Combo Course ──────────────────────────────────────────────
@super_teacher_required
@require_POST
def create_combo_view(request):
    title       = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    price       = request.POST.get('price', '0')
    component_ids = request.POST.getlist('component_courses')
    thumbnail   = request.FILES.get('thumbnail')

    if not title or not component_ids:
        messages.error(request, "Combo title and at least one component course are required.")
        return redirect('/teacher/?section=combo-course-module')

    combo = Course.objects.create(
        title=title, description=description,
        price=price, is_combo=True, is_published=True,
    )
    if thumbnail:
        combo.thumbnail = thumbnail
        combo.save()

    for cid in component_ids:
        try:
            comp = Course.objects.get(pk=cid)
            CourseBundle.objects.get_or_create(combo_course=combo, component_course=comp)
        except Course.DoesNotExist:
            pass

    messages.success(request, f'Combo course "{combo.title}" created with {len(component_ids)} courses.')
    return redirect('/teacher/?section=combo-course-module')


# ─── API for Selects ──────────────────────────────────────────────────────────
@login_required
def get_subjects_api(request, course_id):
    # Only allow fetching for valid courses
    nodes = ContentNode.objects.filter(course_id=course_id, parent__isnull=True).order_by('title')
    data = [{'id': s.id, 'title': s.title} for s in nodes]
    return JsonResponse({'subjects': data})


@login_required
def get_topics_api(request, subject_id):
    # Check if there's a specific "Live Class" folder
    live_folder = ContentNode.objects.filter(
        parent_id=subject_id,
        title__icontains='Live Class'
    ).first()

    if live_folder:
        # Fetch topics from inside the Live Class folder
        nodes = ContentNode.objects.filter(parent_id=live_folder.id).order_by('order', 'title')
    else:
        # Fallback to direct children
        nodes = ContentNode.objects.filter(parent_id=subject_id).order_by('order', 'title')

    data = [{'id': t.id, 'title': t.title} for t in nodes]
    return JsonResponse({'topics': data})


# ─── Content Builder APIs ───────────────────────────────────────────────────────
@teacher_required
def get_course_tree_api(request, course_id):
    nodes = ContentNode.objects.filter(course_id=course_id).order_by('order', 'created_at')
    nodes_dict = {}
    for n in nodes:
        nodes_dict[n.id] = {
            'id': n.id,
            'title': n.title,
            'description': n.description,
            'node_type': n.node_type,
            'youtube_url': n.youtube_url,
            'order': n.order,
            'parent_id': n.parent_id,
            'children': []
        }
    
    tree = []
    for n in nodes:
        node_data = nodes_dict[n.id]
        if n.parent_id and n.parent_id in nodes_dict:
            nodes_dict[n.parent_id]['children'].append(node_data)
        elif not n.parent_id:
            tree.append(node_data)
            
    return JsonResponse({'tree': tree})

@teacher_required
@require_POST
def save_node_api(request):
    try:
        node_id = request.POST.get('id')
        course_id = request.POST.get('course_id')
        parent_id = request.POST.get('parent_id')
        title = request.POST.get('title', '').strip()
        node_type = request.POST.get('node_type', 'class')
        description = request.POST.get('description', '').strip()
        youtube_url = request.POST.get('youtube_url', '').strip() if node_type == 'class' else ''
        order = int(request.POST.get('order', 1))
        class_mode = request.POST.get('class_mode', 'recorded')

        if not title or not course_id:
            return JsonResponse({'success': False, 'message': 'Title and Course are required.'}, status=400)
            
        course = get_object_or_404(Course, pk=course_id)
        parent = None
        if parent_id:
            parent = get_object_or_404(ContentNode, pk=parent_id)
            if parent.course != course:
                return JsonResponse({'success': False, 'message': 'Parent must belong to the same course.'}, status=400)

        status_val = 'published'
        if node_type == 'class':
            status_val = class_mode

        if node_id:
            node = get_object_or_404(ContentNode, pk=node_id, course=course)
            node.title = title
            node.node_type = node_type
            node.description = description
            node.youtube_url = youtube_url
            node.order = order
            node.status = status_val
            if parent_id and str(parent_id) != str(node.id):
                node.parent = parent
            node.save()
            msg = f"Node '{title}' updated successfully."
        else:
            node = ContentNode.objects.create(
                title=title, node_type=node_type, description=description,
                youtube_url=youtube_url, order=order, parent=parent, course=course,
                status=status_val
            )
            msg = f"Node '{title}' created successfully."

        # Handle LiveSession
        if node_type == 'class':
            if class_mode == 'live':
                session, created = LiveSession.objects.get_or_create(content_node=node, is_live=True)
            else:
                LiveSession.objects.filter(content_node=node, is_live=True).update(is_live=False)

        # Handle Attachments
        if node_type == 'class':
            attachment_names = request.POST.getlist('attachment_name')
            attachment_types = request.POST.getlist('attachment_type')
            attachment_urls = request.POST.getlist('attachment_url')
            # Using getlist for files can vary, but usually request.FILES.getlist('attachment_file') gets all files attached (if same name)
            # It's better to fetch them individually or use a single name approach. Our JS sends them as 'attachment_file' iteratively?
            # Actually, `FormData` appends multiple files to the same key 'attachment_file' if the HTML name is 'attachment_file'
            attachment_files = request.FILES.getlist('attachment_file')
            
            # Since some rows might not have a file, getting 'attachment_file' list might skip rows
            # Let's iterate based on the name len
            # File list only contains items where a file was selected. So indices won't match. 
            # A correct approach is iterating request.FILES explicitly or grabbing by unique names. 
            # Given we'll fix JS, let's fix JS to append correctly or send them uniquely.
            # Easiest way in JS: use `attachment_file_0`, `attachment_file_1` etc.
            for i in range(len(attachment_names)):
                name = attachment_names[i].strip()
                if not name:
                    continue
                a_type = attachment_types[i] if i < len(attachment_types) else 'other'
                att = Attachment(content_node=node, name=name, file_type=a_type)
                
                a_file = request.FILES.get(f'attachment_file_{i}')
                a_url = attachment_urls[i] if i < len(attachment_urls) else ''
                
                if a_file:
                    att.file = a_file
                elif a_url:
                    att.external_url = a_url
                att.save()

        return JsonResponse({'success': True, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@teacher_required
@require_POST
def delete_node_api(request, node_id):
    node = get_object_or_404(ContentNode, pk=node_id)
    node.delete()
    return JsonResponse({'success': True, 'message': 'Node deleted successfully.'})


# ─── Import Node API ────────────────────────────────────────────────────────────
@teacher_required
def get_import_courses_api(request):
    """Return all courses for the import modal dropdown."""
    courses = Course.objects.values('id', 'title').order_by('title')
    return JsonResponse({'courses': list(courses)})


@teacher_required
@require_POST
def import_node_api(request):
    """
    Clone a source ContentNode and its full subtree into a target location.

    POST params:
        source_node_id  – ID of the node to clone (with all children)
        target_parent_id – ID of the node to nest the clone under (empty = root)
        target_course_id – Course the clone belongs to
    """
    try:
        source_node_id  = request.POST.get('source_node_id')
        target_parent_id = request.POST.get('target_parent_id') or None
        target_course_id = request.POST.get('target_course_id')

        if not source_node_id or not target_course_id:
            return JsonResponse({'success': False, 'message': 'source_node_id and target_course_id are required.'}, status=400)

        source_node   = get_object_or_404(ContentNode, pk=source_node_id)
        target_course = get_object_or_404(Course, pk=target_course_id)
        target_parent = None
        if target_parent_id:
            target_parent = get_object_or_404(ContentNode, pk=target_parent_id, course=target_course)

        # ── Anti-circular check ─────────────────────────────────────────────
        # Ensure source node is not equal to, or an ancestor of, target_parent
        if target_parent:
            cursor = target_parent
            while cursor is not None:
                if cursor.id == source_node.id:
                    return JsonResponse(
                        {'success': False, 'message': 'Cannot import a node into itself or one of its descendants.'},
                        status=400
                    )
                cursor = cursor.parent

        # ── Fetch full subtree of the source with ONE query ─────────────────
        source_course_id = source_node.course_id
        all_source_nodes = ContentNode.objects.filter(
            course_id=source_course_id
        ).order_by('order', 'created_at')

        # Build an id → node lookup
        node_map = {n.id: n for n in all_source_nodes}

        # ── Determine the order offset for the cloned root ──────────────────
        if target_parent:
            existing_max = target_parent.children.aggregate(m=Max('order'))['m'] or 0
        else:
            existing_max = ContentNode.objects.filter(
                course=target_course, parent__isnull=True
            ).aggregate(m=Max('order'))['m'] or 0

        # ── Two-pass approach: collect flat list, then bulk_create, then map parents ──
        cloned_instances = []

        # Pass 1: collect all clones with their orig_id and orig_parent_id
        def collect_flat(orig_node, new_parent_clone=None):
            order_val = orig_node.order
            if new_parent_clone is None and orig_node.id == source_node.id:
                order_val = existing_max + 1

            clone = ContentNode(
                title=orig_node.title,
                description=orig_node.description,
                node_type=orig_node.node_type,
                youtube_url=orig_node.youtube_url,
                status=orig_node.status,
                order=order_val,
                course=target_course,
                parent=None,  # set in pass 2
            )
            clone._orig_id        = orig_node.id
            clone._orig_parent_id = orig_node.parent_id  # original DB parent
            cloned_instances.append(clone)

            children = sorted(
                [n for n in node_map.values() if n.parent_id == orig_node.id],
                key=lambda n: (n.order, n.id)
            )
            for child in children:
                collect_flat(child)

        collect_flat(source_node)


        # Pass 2: bulk_create inside a transaction, then wire up parents
        with transaction.atomic():
            # Create without parents first (parent=None for all)
            created = ContentNode.objects.bulk_create(cloned_instances)

            # Build orig_id → new instance map
            orig_to_new = {inst._orig_id: inst for inst in created}

            # Set parents correctly
            to_update = []
            for inst in created:
                if inst._orig_id == source_node.id:
                    # Root of the subtree → attach to target_parent
                    inst.parent = target_parent
                else:
                    # Map old parent_id to new clone
                    new_parent_inst = orig_to_new.get(inst._orig_parent_id)
                    inst.parent = new_parent_inst
                to_update.append(inst)

            ContentNode.objects.bulk_update(to_update, ['parent'])

        return JsonResponse({
            'success': True,
            'message': f'Successfully imported "{source_node.title}" with {len(created)} node(s).',
            'imported_count': len(created),
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ─── Solve Sheets Module ──────────────────────────────────────────────────
@teacher_required
def solve_sheets_view(request):
    """GET: Render solve sheets page with catalogue data. POST: Upload solve sheet."""
    if request.method == 'GET':
        courses = Course.objects.prefetch_related('content_nodes').all()
        
        # Build catalogue data matching catalogue.html logic
        catalogue_data = []
        for course in courses:
            subjects_data = []
            subjects = course.content_nodes.filter(parent__isnull=True).order_by('order', 'title')
            for subject in subjects:
                # Find Live Class folder topics or direct child topics
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
            
            # Fetch solve sheets for this course
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
            'courses': courses,
            'catalogue_data_json': json.dumps(catalogue_data),
            'page_title': 'Solve Sheets',
            'active_section': 'solve-sheets-module'
        }
        return render(request, 'teacher/solve_sheets.html', context)
    
    # POST
    title = request.POST.get('title', '').strip()
    course_id = request.POST.get('course_id')
    subject_id = request.POST.get('subject_id')
    topic_id = request.POST.get('topic_id') or None
    file = request.FILES.get('file')
    
    if not title or not course_id or not subject_id or not file:
        messages.error(request, 'Title, Course, Subject, and File are required.')
        return redirect('teacher:solve_sheets')
        
    course = get_object_or_404(Course, pk=course_id)
    subject = get_object_or_404(ContentNode, pk=subject_id, course=course)
    topic = get_object_or_404(ContentNode, pk=topic_id, course=course) if topic_id else None
    
    SolveSheet.objects.create(
        title=title,
        course=course,
        subject=subject,
        topic=topic,
        file=file
    )
    
    messages.success(request, f'Solve Sheet "{title}" uploaded successfully.')
    return redirect('teacher:solve_sheets')


@teacher_required
def board_questions_view(request):
    """GET: Render board questions list and upload form. POST: Upload new board question or delete existing one."""
    if request.method == 'GET':
        questions = BoardQuestion.objects.all().order_by('-year', 'board_name', 'title')
        
        boards = ['Dhaka', 'Rajshahi', 'Cumilla', 'Jashore', 'Chattogram', 'Barishal', 'Sylhet', 'Dinajpur', 'Mymensingh']
        years = list(range(2027, 2014, -1))
        types = ['Written', 'MCQ']
        
        context = {
            'questions': questions,
            'boards': boards,
            'years': years,
            'types': types,
            'page_title': 'Board Questions Manager',
            'active_section': 'board-questions-module'
        }
        return render(request, 'teacher/board_questions.html', context)
        
    elif request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete':
            question_id = request.POST.get('question_id')
            question = get_object_or_404(BoardQuestion, pk=question_id)
            title = question.title
            question.delete()
            messages.success(request, f'Board Question "{title}" deleted successfully.')
            return redirect('teacher:board_questions')
            
        # Standard Upload
        title = request.POST.get('title', '').strip()
        board_name = request.POST.get('board_name')
        year = request.POST.get('year')
        exam_type = request.POST.get('exam_type')
        pdf_file = request.FILES.get('file')
        
        if not title or not board_name or not year or not exam_type or not pdf_file:
            messages.error(request, 'Title, Board, Year, Type, and PDF file are required.')
            return redirect('teacher:board_questions')
            
        try:
            year = int(year)
        except ValueError:
            messages.error(request, 'Invalid year provided.')
            return redirect('teacher:board_questions')
            
        BoardQuestion.objects.create(
            title=title,
            board_name=board_name,
            year=year,
            exam_type=exam_type,
            pdf_file=pdf_file
        )
        
        messages.success(request, f'Board Question "{title}" uploaded successfully.')
        return redirect('teacher:board_questions')

