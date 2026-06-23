from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User

class AcademicResultsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a student user
        self.student = User.objects.create_user(
            username='student_test',
            password='testpassword',
            role='student'
        )

    def test_academic_results_requires_login(self):
        """Verify that accessing academic results page requires login."""
        url = reverse('courses:academic_results')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_academic_results_welcome_state(self):
        """Verify welcome state is shown when no query has been run yet."""
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:academic_results')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Academic Results Search')
        self.assertContains(response, 'Select an exam type on the search panel')

    def test_academic_results_tutorial_success(self):
        """Verify successful query of Tutorial results for Farhan Tanvir."""
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:academic_results')
        response = self.client.get(url, {'exam_type': 'tutorial', 'uid': '86957399', 'reg': '86957399'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Farhan Tanvir')
        self.assertContains(response, 'Tutorial Examination')
        self.assertContains(response, 'Bangla')
        self.assertContains(response, 'Physics 1st')
        self.assertContains(response, 'ICT')
        # Check specific marks for Tutorial
        self.assertContains(response, '87')  # Bangla total
        self.assertContains(response, '91')  # ICT total
        self.assertContains(response, 'GPA 5.00')

    def test_academic_results_half_yearly_success(self):
        """Verify successful query of Half Yearly results for Farhan Tanvir."""
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:academic_results')
        response = self.client.get(url, {'exam_type': 'half_yearly', 'uid': '86957399', 'reg': '86957399'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Farhan Tanvir')
        self.assertContains(response, 'Half Yearly Examination')
        # Check specific marks for Half Yearly
        self.assertContains(response, '82')  # Bangla total
        self.assertContains(response, '85')  # ICT total
        self.assertContains(response, 'GPA 4.67')

    def test_academic_results_yearly_not_published(self):
        """Verify Yearly results show 'Not published yet' even for Farhan Tanvir."""
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:academic_results')
        response = self.client.get(url, {'exam_type': 'yearly', 'uid': '86957399', 'reg': '86957399'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not published yet')
        self.assertNotContains(response, 'Farhan Tanvir')

    def test_academic_results_incorrect_credentials(self):
        """Verify incorrect credentials show 'Not published yet' (or result not found)."""
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:academic_results')
        response = self.client.get(url, {'exam_type': 'tutorial', 'uid': 'invalid_uid', 'reg': 'invalid_reg'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not published yet')


from django.core.files.uploadedfile import SimpleUploadedFile
from .models import BoardQuestion

class BoardQuestionsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create student and teacher users
        self.student = User.objects.create_user(
            username='student_test',
            password='testpassword',
            role='student'
        )
        self.teacher = User.objects.create_user(
            username='teacher_test',
            password='testpassword',
            role='teacher'
        )
        # Create a mock board question
        self.pdf_file = SimpleUploadedFile(
            "physics_dhaka_2025.pdf",
            b"%PDF-1.4...",
            content_type="application/pdf"
        )
        self.bq = BoardQuestion.objects.create(
            title="Physics 1st Paper Board Question",
            board_name="Dhaka",
            year=2025,
            exam_type="Written",
            pdf_file=self.pdf_file
        )

    def test_student_board_questions_requires_login(self):
        url = reverse('courses:board_questions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_student_board_questions_list(self):
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:board_questions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Physics 1st Paper Board Question')
        self.assertContains(response, 'Dhaka')
        self.assertContains(response, '2025')
        self.assertContains(response, 'Written')

    def test_student_board_question_detail(self):
        self.client.login(username='student_test', password='testpassword')
        url = reverse('courses:board_question_detail', kwargs={'question_id': self.bq.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Physics 1st Paper Board Question')
        self.assertContains(response, 'Dhaka')
        self.assertContains(response, '2025')
        self.assertContains(response, 'Written')
        self.assertContains(response, 'iframe')

    def test_teacher_board_questions_requires_teacher_role(self):
        # Student should be redirected to courses dashboard
        self.client.login(username='student_test', password='testpassword')
        url = reverse('teacher:board_questions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response.url)

    def test_teacher_board_questions_list_and_upload(self):
        self.client.login(username='teacher_test', password='testpassword')
        url = reverse('teacher:board_questions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Physics 1st Paper Board Question')
        self.assertContains(response, 'Upload New Board Question')
        
        # Test Upload via POST
        new_pdf = SimpleUploadedFile(
            "chemistry_rajshahi_2024.pdf",
            b"%PDF-1.4...",
            content_type="application/pdf"
        )
        post_data = {
            'title': 'Chemistry 2nd Paper',
            'board_name': 'Rajshahi',
            'year': '2024',
            'exam_type': 'MCQ',
            'file': new_pdf
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BoardQuestion.objects.filter(title='Chemistry 2nd Paper').exists())

    def test_teacher_board_question_delete(self):
        self.client.login(username='teacher_test', password='testpassword')
        url = reverse('teacher:board_questions')
        post_data = {
            'action': 'delete',
            'question_id': self.bq.id
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BoardQuestion.objects.filter(id=self.bq.id).exists())


