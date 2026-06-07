from django.urls import path
from . import views

app_name = 'results'

urlpatterns = [
    # --- Student Result Patterns ---
    path('check/', views.check_result_view, name='check_results'),
    
    # --- Teacher/Admin Result Entry Patterns ---
    path('teacher/entry/search-student/', views.teacher_search_student_view, name='teacher_search_student'),
    path('teacher/entry/select-session-term/<int:student_id>/', views.teacher_select_session_term_view, name='teacher_select_session_term'),
    path('teacher/score-sheet/<int:student_id>/<int:session_id>/<int:term_id>/', 
         views.teacher_score_sheet_view, name='teacher_score_sheet'),

    # --- Paystack Fee Payment Patterns ---
    path('pay-fees/', views.initialize_payment, name='pay_fees'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('paystack-webhook/', views.paystack_webhook, name='paystack_webhook'),

    # --- NEW: Testimonial Submission ---
    path('submit-review/', views.submit_review, name='submit_review'),
]