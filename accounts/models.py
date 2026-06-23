import random
from django.contrib.auth.models import AbstractUser
from django.db import models


def generate_user_id():
    return str(random.randint(10000000, 99999999))


class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    user_id = models.CharField(max_length=8, unique=True, null=True, blank=True)

    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=20, blank=True)
    class_level = models.CharField(max_length=20, blank=True, help_text="e.g. Class 11")
    is_super_teacher = models.BooleanField(default=False, help_text="Grants admin privileges in the Teacher Panel")
    
    # Teacher Profile Extensions
    bio = models.TextField(blank=True, help_text="Teacher's biography")
    experience = models.CharField(max_length=200, blank=True, help_text="e.g. 5 Years of Experience")
    profile_photo = models.ImageField(upload_to='teacher_profiles/', blank=True, null=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.user_id:
            while True:
                new_id = generate_user_id()
                # Check for uniqueness before assigning
                if not type(self).objects.filter(user_id=new_id).exists():
                    self.user_id = new_id
                    break
        if not self.username:
            self.username = self.user_id
        super().save(*args, **kwargs)

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return f"{self.get_full_name() or self.user_id} ({self.role})"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    GROUP_CHOICES = [
        ('science', 'Science'),
        ('commerce', 'Commerce'),
        ('arts', 'Arts'),
    ]
    group = models.CharField(max_length=20, choices=GROUP_CHOICES, blank=True)
    college_name = models.CharField(max_length=200, blank=True)
    
    mother_name = models.CharField(max_length=100, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    mother_number = models.CharField(max_length=20, blank=True)
    father_number = models.CharField(max_length=20, blank=True)
    
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_number = models.CharField(max_length=20, blank=True)
    guardian_relation = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
