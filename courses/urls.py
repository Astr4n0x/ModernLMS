from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('dashboard/', views.dashboard_view,       name='dashboard'),
    path('my-courses/',   views.catalogue_view,        name='catalogue'),
    path('node/<int:node_id>/', views.node_detail_view, name='node_detail'),
    path('past-classes/', views.past_classes_view,  name='past_classes'),
    path('live-classes/', views.live_classes_view,  name='live_classes'),
    path('solve-sheets/', views.student_solve_sheets_view, name='solve_sheets'),

    # Past Exams
    path('past-exams/',                                           views.past_exams_view,    name='past_exams'),
    path('exam/<int:exam_id>/',                                   views.exam_detail_view,   name='exam_detail'),
    path('exam/<int:exam_id>/submit/',                            views.submit_exam_view,   name='exam_submit'),
    path('attempt/<int:attempt_id>/delete/',                      views.delete_attempt_view,name='delete_attempt'),
    path('exam/<int:exam_id>/answer/',                            views.save_answer_view,   name='save_answer'),
    path('exam/<int:exam_id>/submitted/<int:attempt_id>/',        views.exam_submitted_view, name='exam_submitted'),
    path('exam/<int:exam_id>/review/<int:attempt_id>/',           views.exam_review_view,   name='exam_review'),

    # Course Store
    path('all-courses/', views.course_store_view,   name='course_store'),
    path('store/course/<int:course_id>/', views.course_detail_view, name='course_detail'),

    # Payment
    path('course/<int:course_id>/pay/', views.initiate_payment_view, name='initiate_payment'),
    path('payment/success/', views.payment_success_view, name='payment_success'),
    path('payment/fail/',    views.payment_fail_view,    name='payment_fail'),
    path('payment/cancel/',  views.payment_cancel_view,  name='payment_cancel'),

    # Streak Profile
    path('streak/', views.streak_profile_view, name='streak_profile'),

    # Academic Results
    path('academic-results/', views.academic_results_view, name='academic_results'),

    # Board Questions
    path('board-questions/', views.board_questions_view, name='board_questions'),
    path('board-questions/<int:question_id>/', views.board_question_detail_view, name='board_question_detail'),

    # Scholarships & Admissions
    path('scholarships/', views.scholarships_view, name='scholarships'),
    path('scholarships/<int:scholarship_id>/apply/', views.scholarship_apply_view, name='scholarship_apply'),

    # AI Study Assistant
    path('node/<int:node_id>/ai/status/',                       views.ai_status_view,      name='ai_status'),
    path('node/<int:node_id>/ai/<str:content_type>/',           views.ai_get_content_view, name='ai_get_content'),
    path('node/<int:node_id>/ai/<str:content_type>/generate/',  views.ai_generate_view,    name='ai_generate'),
]
