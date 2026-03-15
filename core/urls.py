from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Main 
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Scholarship Info
    path('scholarships/', views.scholarship_list, name='scholarship_list'),
    path('scholarships/<int:scholarship_id>/', views.scholarship_detail, name='scholarship_detail'),

    # Scholarship Application
    path('scholarships/<int:scholarship_id>/apply/', views.apply_scholarship, name='apply_scholarship'),
    path('my-applications/', views.my_applications, name='my_applications'),

    # Document Upload
    path('applications/<int:application_id>/upload-documents/', views.upload_documents, name='upload_documents'),
    path('applications/<int:application_id>/documents/', views.application_documents, name='application_documents'),

    # Admin 
    path('admin-applications/', views.admin_applications, name='admin_applications'),
    path('admin-applications/<int:application_id>/', views.admin_application_detail, name='admin_application_detail'),
    path('admin-applications/<int:application_id>/update-status/', views.update_application_status, name='update_application_status'),

    # CSV Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/export/csv/', views.export_applications_csv, name='export_applications_csv'),

    # Messages
    path('messages/submit/', views.submit_message, name='submit_message'),
    path('my-messages/', views.my_messages, name='my_messages'),

    path('admin-messages/', views.admin_messages, name='admin_messages'),
    path('admin-messages/<int:message_id>/', views.admin_message_detail, name='admin_message_detail'),
    path('admin-messages/<int:message_id>/update-status/', views.update_message_status, name='update_message_status'),

    # Scholarship Recommendations
    path('recommended-scholarships/', views.recommended_scholarships, name='recommended_scholarships'),

    # Notifications
    path('my-notifications/', views.my_notifications, name='my_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_as_read'),

    # Announcements
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('admin-announcements/', views.admin_announcements, name='admin_announcements'),
    path('admin-announcements/create/', views.create_announcement, name='create_announcement'),
    path('admin-announcements/<int:announcement_id>/edit/', views.edit_announcement, name='edit_announcement'),
]