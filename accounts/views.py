from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Max
from .models import User, StudentProfile

def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        identifier = request.POST.get('userid', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=identifier, password=password)
        if user:
            login(request, user)
            return _redirect_by_role(user)
        else:
            messages.error(request, 'Invalid credentials. Please try again.')

    return render(request, 'login.html')

def signup_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        class_level = request.POST.get('class_level', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
    
        if password != confirm_password:
            messages.error(request, "Passwords don't match.")
            return render(request, 'signup.html')
        
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "This phone number is already registered.")
            return render(request, 'signup.html')

        # Create new user, user_id is automatically assigned randomly by User.save()
        # username is generated dynamically if left blank, but we must provide it to create_user to satisfy its signature.
        user = User.objects.create_user(
            username="temp_" + phone, # Provide a temporary one, then we fix it. Actually wait, User.save will do it later, but if we provide temp_, it will stay temp_.
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            class_level=class_level,
            role='student'
        )
        user.username = user.user_id
        user.save()
        
        # [Future] OTP implementation goes here
        # generate_and_send_otp(phone)
        # request.session['pending_registration'] = user.id
        # return redirect('accounts:otp_verify')

        # Instant login for now
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('courses:dashboard')

    return render(request, 'signup.html')

def _redirect_by_role(user):
    if user.is_teacher():
        return redirect('teacher:panel')
    return redirect('courses:dashboard')

@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')

@login_required
def edit_profile_view(request):
    user = request.user
    # Get or create the profile for the logged in user
    profile, created = StudentProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # Update User model fields
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.class_level = request.POST.get('class_level', '').strip()
        user.save()

        # Update StudentProfile fields
        profile.group = request.POST.get('group', '').strip()
        profile.college_name = request.POST.get('college_name', '').strip()
        profile.mother_name = request.POST.get('mother_name', '').strip()
        profile.father_name = request.POST.get('father_name', '').strip()
        profile.mother_number = request.POST.get('mother_number', '').strip()
        profile.father_number = request.POST.get('father_number', '').strip()
        profile.guardian_name = request.POST.get('guardian_name', '').strip()
        profile.guardian_number = request.POST.get('guardian_number', '').strip()
        profile.guardian_relation = request.POST.get('guardian_relation', '').strip()
        profile.save()

        messages.success(request, 'Your profile has been updated successfully.')
        return redirect('accounts:edit_profile')

    context = {
        'profile': profile,
    }
    return render(request, 'accounts/edit_profile.html', context)
