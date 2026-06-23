from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from courses.models import Course, ClassLevel
from accounts.models import User
from .models import Testimonial

def home_view(request):
    # For the hero carousel
    recent_courses = Course.objects.filter(is_published=True).exclude(thumbnail='').order_by('-created_at')[:8]
    
    # Grouped by class for the body
    class_levels = ClassLevel.objects.all()
    grouped_courses = []
    
    for cl in class_levels:
        cl_courses = Course.objects.filter(class_level=cl, is_published=True).order_by('-created_at')[:8]
        if cl_courses.exists():
            grouped_courses.append({
                'title': cl.name,
                'courses': cl_courses
            })
            
    # Add an "Others" category
    other_courses = Course.objects.filter(class_level__isnull=True, is_published=True).order_by('-created_at')[:8]
    if other_courses.exists():
        grouped_courses.append({
            'title': 'General Courses',
            'courses': other_courses
        })

    testimonials = Testimonial.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    # Optional stats
    stats = {
        'students': User.objects.filter(role='student').count(),
        'courses': Course.objects.filter(is_published=True).count(),
        'success_rate': "98%",
    }
    
    return render(request, 'public/home.html', {
        'recent_courses': recent_courses,
        'grouped_courses': grouped_courses,
        'testimonials': testimonials,
        'stats': stats,
    })

def all_courses_view(request):
    courses = Course.objects.filter(is_published=True).order_by('-created_at')
    
    # Filters
    class_level_id = request.GET.get('class_level')
    category = request.GET.get('category')
    
    if class_level_id:
        courses = courses.filter(class_level_id=class_level_id)
    if category:
        courses = courses.filter(category__iexact=category)
        
    class_levels = ClassLevel.objects.all()
    categories = Course.objects.values_list('category', flat=True).distinct().exclude(category='')
    
    return render(request, 'public/courses.html', {
        'courses': courses,
        'class_levels': class_levels,
        'categories': categories,
        'page_title': 'All Courses',
    })

def free_courses_view(request):
    courses = Course.objects.filter(is_published=True, is_free=True).order_by('-created_at')
    
    return render(request, 'public/courses.html', {
        'courses': courses,
        'page_title': 'Free Courses',
    })

def about_view(request):
    team = User.objects.filter(role='teacher', profile_photo__isnull=False)[:4]
    return render(request, 'public/about.html', {
        'team': team,
    })

def shop_view(request):
    return render(request, 'public/shop.html')

def course_detail_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id, is_published=True)
    subjects = course.content_nodes.filter(parent__isnull=True).order_by('order')
    
    is_enrolled = False
    if request.user.is_authenticated:
        is_enrolled = course.students.filter(id=request.user.id).exists()
        
    return render(request, 'public/course_detail.html', {
        'course': course,
        'subjects': subjects,
        'is_enrolled': is_enrolled,
    })

@login_required
def enroll_course_view(request, course_id):
    # This acts as the "Buy Now / Checkout Success" callback
    course = get_object_or_404(Course, pk=course_id, is_published=True)
    
    # In a real app, this would happen AFTER payment gateway success.
    # For now (and for free courses), we just enroll directly.
    if course.is_free or True: # Bypassing payment for now
        course.students.add(request.user)
        messages.success(request, f"You have successfully enrolled in {course.title}!")
        return redirect('/dashboard/')
    
    return redirect('public:course_detail', course_id=course.id)
