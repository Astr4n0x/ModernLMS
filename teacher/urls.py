from django.urls import path
from . import views

app_name = 'teacher'

urlpatterns = [
    path('teacher/', views.panel_view, name='panel'),
    path('teacher/create-subject/', views.create_subject_view, name='create_subject'),
    path('teacher/create-topic/', views.create_topic_view, name='create_topic'),
    path('teacher/create-exam/', views.create_exam_view, name='create_exam'),
    path('teacher/exam/<int:exam_id>/edit/', views.edit_exam_view, name='edit_exam'),
    path('teacher/exam/<int:exam_id>/delete/', views.delete_exam_view, name='delete_exam'),
    path('teacher/upload-lesson/', views.upload_lesson_view, name='upload_lesson'),    
    path('teacher/solve-sheets/', views.solve_sheets_view, name='solve_sheets'),
    path('teacher/board-questions/', views.board_questions_view, name='board_questions'),
    
    path('teacher/lesson/<int:lesson_id>/edit/', views.edit_lesson_view, name='edit_lesson'),
    path('teacher/lesson/<int:lesson_id>/delete/', views.delete_lesson_view, name='delete_lesson'),
    path('teacher/lesson/<int:lesson_id>/toggle-status/', views.toggle_lesson_status_view, name='toggle_status'),
    
    path('teacher/lesson/<int:lesson_id>/add-attachment/', views.add_attachment_view, name='add_attachment'),
    path('teacher/attachment/<int:attachment_id>/delete/', views.delete_attachment_view, name='delete_attachment'),
    
    path('teacher/assign-course/', views.assign_course_view, name='assign_course'),
    path('teacher/add-teacher/', views.add_teacher_view, name='add_teacher'),
    path('teacher/publish-course/', views.publish_course_view, name='publish_course'),
    path('teacher/create-combo/', views.create_combo_view, name='create_combo'),

    # Live
    path('live-monitor/', views.live_monitor_view, name='live_monitor'),
    path('live/<int:lesson_id>/start/', views.start_live_view, name='start_live'),
    path('live/<int:session_id>/end/', views.end_live_view, name='end_live'),

    # APIs for cascade selects
    path('api/subjects/<int:course_id>/', views.get_subjects_api, name='api_subjects'),
    path('api/topics/<int:subject_id>/', views.get_topics_api, name='api_topics'),
    
    # Content Builder APIs
    path('api/builder/tree/<int:course_id>/', views.get_course_tree_api, name='api_builder_tree'),
    path('api/builder/node/save/', views.save_node_api, name='api_builder_save'),
    path('api/builder/node/<int:node_id>/delete/', views.delete_node_api, name='api_builder_delete'),

    # Content Import APIs
    path('api/builder/import/courses/', views.get_import_courses_api, name='api_import_courses'),
    path('api/builder/import/node/', views.import_node_api, name='api_import_node'),
]
