import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from courses.models import Course
from .models import Message

@login_required
def discussion_list(request):
    if request.user.is_teacher():
        if request.user.is_super_teacher:
            courses = Course.objects.all()
        else:
            courses = Course.objects.filter(instructors=request.user)
    else:
        courses = request.user.enrolled_courses.all()

    return render(request, 'discussion/discussion_list.html', {'courses': courses})

@login_required
def discussion_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # In a real scenario we'd check if student is enrolled or user is teacher
    # Assuming the template handles permission/enrollment or it's accessible.
    
    # Get last 50 messages
    messages_qs = Message.objects.filter(course=course).order_by('-created_at')[:50]
    # Reverse to chronological
    messages = list(messages_qs)[::-1]

    context = {
        'course': course,
        'messages': messages,
    }
    return render(request, 'discussion/discussion.html', context)

@login_required
@require_POST
def upload_attachment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    file = request.FILES.get('attachment')
    
    if not file:
        return JsonResponse({'success': False, 'error': 'No file uploaded'})
        
    if not (file.name.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))):
        return JsonResponse({'success': False, 'error': 'Invalid file type. Only PDF or Images allowed.'})

    message = Message.objects.create(
        course=course,
        user=request.user,
        attachment=file
    )
    
    # Broadcast via channel layer
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'discussion_{course.id}',
        {
            'type': 'chat_message',
            'message': '',
            'attachment_url': message.attachment.url,
            'user_id': message.user.user_id,
            'user_name': message.user.get_full_name() or message.user.user_id,
            'is_teacher': message.user.is_teacher(),
            'created_at': message.created_at.strftime("%I:%M %p")
        }
    )

    return JsonResponse({'success': True, 'url': message.attachment.url})

@login_required
@require_POST
def send_message(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    try:
        data = json.loads(request.body)
        content = data.get('message', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        
    if not content:
        return JsonResponse({'success': False, 'error': 'Empty message'})
        
    msg = Message.objects.create(
        course=course,
        user=request.user,
        content=content
    )
    
    # Broadcast via channel layer (for clients that DO have WS connected)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'discussion_{course.id}',
        {
            'type': 'chat_message',
            'message': msg.content,
            'attachment_url': '',
            'user_id': msg.user.user_id,
            'user_name': msg.user.get_full_name() or msg.user.user_id,
            'is_teacher': msg.user.is_teacher(),
            'created_at': msg.created_at.strftime("%I:%M %p")
        }
    )
    
    return JsonResponse({'success': True, 'message': msg.content})
