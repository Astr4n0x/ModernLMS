"""
Management command to seed the database with demo data.
Run: python manage.py seed_demo
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from courses.models import ClassLevel, Course, ContentNode
from live.models import LiveSession

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed demo data: users, classes, courses, subjects, lessons'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')

        # --- Users ---
        teacher1, _ = User.objects.get_or_create(user_id='dr_ahmed', defaults={
            'first_name': 'Dr.', 'last_name': 'Ahmed',
            'email': 'ahmed@lms.com', 'role': 'teacher',
        })
        teacher1.set_password('teacher123')
        teacher1.save()

        teacher2, _ = User.objects.get_or_create(user_id='dr_sarah', defaults={
            'first_name': 'Dr.', 'last_name': 'Sarah',
            'email': 'sarah@lms.com', 'role': 'teacher',
        })
        teacher2.set_password('teacher123')
        teacher2.save()

        student1, _ = User.objects.get_or_create(user_id='student1', defaults={
            'first_name': 'Jane', 'last_name': 'Doe',
            'email': 'jane@lms.com', 'role': 'student', 'class_level': 'Class 11',
        })
        student1.set_password('student123')
        student1.save()

        student2, _ = User.objects.get_or_create(user_id='student2', defaults={
            'first_name': 'John', 'last_name': 'Smith',
            'email': 'john@lms.com', 'role': 'student', 'class_level': 'Class 10',
        })
        student2.set_password('student123')
        student2.save()

        # --- Class Levels ---
        cl10, _ = ClassLevel.objects.get_or_create(name='Class 10')
        cl11, _ = ClassLevel.objects.get_or_create(name='Class 11')
        cl12, _ = ClassLevel.objects.get_or_create(name='Class 12')

        # --- Courses ---
        physics, _ = Course.objects.get_or_create(title='Physics', defaults={
            'class_level': cl11, 'instructor': teacher1,
            'description': 'Learn mechanics, thermodynamics, and electromagnetism.'
        })
        chemistry, _ = Course.objects.get_or_create(title='Chemistry', defaults={
            'class_level': cl11, 'instructor': teacher2,
            'description': 'Atomic structures, chemical bonds, and stoichiometry.'
        })
        math, _ = Course.objects.get_or_create(title='Mathematics', defaults={
            'class_level': cl10, 'instructor': teacher1,
            'description': 'Algebra, geometry, and introductory calculus.'
        })
        biology, _ = Course.objects.get_or_create(title='Biology', defaults={
            'class_level': cl12, 'instructor': teacher2,
            'description': 'Living organisms, genetics, and human physiology.'
        })

        # --- Subjects & Lessons (ContentNodes) ---
        dynamics, _ = ContentNode.objects.get_or_create(title='Dynamics', course=physics, node_type='subject', defaults={
            'description': 'Motion, forces, and Newton\'s laws of motion.', 'order': 1
        })
        thermo, _ = ContentNode.objects.get_or_create(title='Thermodynamics', course=physics, node_type='subject', defaults={
            'description': 'Heat transfer, thermal energy, and thermodynamic laws.', 'order': 2
        })
        atomic, _ = ContentNode.objects.get_or_create(title='Atomic Structure', course=chemistry, node_type='subject', defaults={
            'description': 'Protons, neutrons, electrons, and atomic theories.', 'order': 1
        })
        algebra, _ = ContentNode.objects.get_or_create(title='Algebra', course=math, node_type='subject', defaults={
            'description': 'Polynomials, linear equations, and quadratic formulas.', 'order': 1
        })
        cell_bio, _ = ContentNode.objects.get_or_create(title='Cellular Biology', course=biology, node_type='subject', defaults={
            'description': 'Structure and function of plant and animal cells.', 'order': 1
        })

        DEMO_YT = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        lessons_data = [
            (dynamics, 1, 'Introduction to Dynamics', 'Learn the basics of motion and force.', 'published'),
            (dynamics, 2, "Newton's Laws", 'An in-depth look into the three laws of motion.', 'recorded'),
            (dynamics, 3, 'Friction and Drag', 'Understanding resistive forces.', 'past_live'),
            (dynamics, 4, 'Practice Exercises: Dynamics', 'Solving real-world dynamics problems.', 'published'),
            (thermo, 1, 'Basic Concepts of Heat', 'Temperature and heat capacity.', 'published'),
            (thermo, 2, 'Heat Transfer Mechanisms', 'Conduction, convection, radiation.', 'recorded'),
            (atomic, 1, 'The Atom', 'History and discovery of atomic particles.', 'published'),
            (atomic, 2, 'Electron Configuration', 'How electrons are arranged in orbitals.', 'past_live'),
            (algebra, 1, 'Linear Equations', 'Solving single and multi-variable equations.', 'published'),
            (cell_bio, 1, 'Cell Structure', 'Organelles and their specific functions.', 'published'),
        ]

        for subject, number, title, desc, status in lessons_data:
            ContentNode.objects.get_or_create(title=title, parent=subject, node_type='class', course=subject.course, defaults={
                'order': number,
                'description': desc,
                'youtube_url': DEMO_YT,
                'status': status,
            })

        self.stdout.write(self.style.SUCCESS('✅ Demo data seeded successfully!'))
        self.stdout.write('')
        self.stdout.write('  Teacher accounts:')
        self.stdout.write('    User ID: dr_ahmed       Password: teacher123')
        self.stdout.write('    User ID: dr_sarah       Password: teacher123')
        self.stdout.write('  Student accounts:')
        self.stdout.write('    User ID: student1       Password: student123')
        self.stdout.write('    User ID: student2       Password: student123')
        self.stdout.write('')
        self.stdout.write('  Run: python manage.py runserver')
        self.stdout.write('  Then visit: http://127.0.0.1:8000/')
