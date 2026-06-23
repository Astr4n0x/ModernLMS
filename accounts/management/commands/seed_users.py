from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds initial users after database reset'

    def handle(self, *args, **kwargs):
        # 1. Admin User
        admin, created = User.objects.get_or_create(
            user_id='00000000',
            defaults={
                'email': 'admin@lms.com',
                'is_superuser': True,
                'is_staff': True,
                'first_name': 'System',
                'last_name': 'Admin'
            }
        )
        if created:
            admin.set_password('pass1234')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created Admin (User ID: {admin.user_id})'))

        # 2. Admin Teacher
        admin_teacher, created = User.objects.get_or_create(
            user_id='11111111',
            defaults={
                'email': 'adminteacher@lms.com',
                'role': 'teacher',
                'is_staff': True,
                'is_super_teacher': True,
                'first_name': 'Admin',
                'last_name': 'Teacher',
                'phone': '11111111'
            }
        )
        if created:
            admin_teacher.set_password('pass1234')
            admin_teacher.save()
            self.stdout.write(self.style.SUCCESS(f'Created Admin Teacher (User ID: {admin_teacher.user_id})'))

        # 3. Normal Teacher
        normal_teacher, created = User.objects.get_or_create(
            email='teacher@lms.com',
            defaults={
                'role': 'teacher',
                'is_staff': True,
                'is_super_teacher': False,
                'first_name': 'Normal',
                'last_name': 'Teacher',
                'phone': '22222222'
            }
        )
        if created:
            normal_teacher.set_password('pass1234')
            normal_teacher.save()
            self.stdout.write(self.style.SUCCESS(f'Created Normal Teacher (User ID: {normal_teacher.user_id})'))
            
        # 4. Normal Student
        student, created = User.objects.get_or_create(
            email='student@lms.com',
            defaults={
                'role': 'student',
                'is_staff': False,
                'first_name': 'Normal',
                'last_name': 'Student',
                'phone': '33333333',
                'class_level': 'Class 10'
            }
        )
        if created:
            student.set_password('pass1234')
            student.save()
            self.stdout.write(self.style.SUCCESS(f'Created Normal Student (User ID: {student.user_id})'))

        self.stdout.write(self.style.SUCCESS('Successfully seeded initial users!'))
