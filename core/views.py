from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.db.models import Q
import csv
from django.http import HttpResponse
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .forms import StudentRegisterForm, StudentProfileForm, UploadedDocumentForm, StudentMessage, StudentMessageForm, AdminMessageResponseForm, AnnouncementForm
from .models import Notification, StudentProfile, Scholarship, Application, UploadedDocument, ApplicationStatusHistory, StudentMessage, Announcement

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def home(request):
    return render(request, 'core/home.html')


def register(request):
    if request.method == 'POST':
        user_form = StudentRegisterForm(request.POST)
        profile_form = StudentProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            StudentProfile.objects.create(
                user=user,
                student_number=profile_form.cleaned_data['student_number'],
                course=profile_form.cleaned_data['course'],
                year_level=profile_form.cleaned_data['year_level'],
                gpa=profile_form.cleaned_data['gpa'],
                contact_number=profile_form.cleaned_data['contact_number'],
                address=profile_form.cleaned_data['address'],
            )
            login(request, user)
            return redirect('dashboard')
    else:
        user_form = StudentRegisterForm()
        profile_form = StudentProfileForm()

    return render(request, 'core/register.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# Students Views

@login_required
def dashboard(request):
    profile = StudentProfile.objects.filter(user=request.user).first()
    return render(request, 'core/dashboard.html', {'profile': profile})

@login_required
def scholarship_list(request):
    scholarships = Scholarship.objects.all().order_by('deadline')

    keyword = request.GET.get('keyword', '').strip()
    status = request.GET.get('status', '').strip()

    if keyword:
        scholarships = scholarships.filter(title__icontains=keyword)

    if status == 'open':
        scholarships = [sch for sch in scholarships if sch.is_open()]
    elif status == 'closed':
        scholarships = [sch for sch in scholarships if sch.is_closed()]

    return render(request, 'core/scholarship_list.html', {
        'scholarships': scholarships,
        'keyword': keyword,
        'status': status,
    })


@login_required
def scholarship_detail(request, scholarship_id):
    scholarship = get_object_or_404(Scholarship, id=scholarship_id)
    return render(request, 'core/scholarship_detail.html', {
        'scholarship': scholarship
    })

@login_required
def apply_scholarship(request, scholarship_id):
    if request.method != 'POST':
        return redirect('scholarship_detail', scholarship_id=scholarship_id)

    scholarship = get_object_or_404(Scholarship, id=scholarship_id)
    profile = StudentProfile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, 'No student profile is linked to this account.')
        return redirect('scholarship_detail', scholarship_id=scholarship.id)

    if scholarship.is_closed():
        messages.error(request, 'This scholarship is already closed. You can no longer apply.')
        return redirect('scholarship_detail', scholarship_id=scholarship.id)

    existing_application = Application.objects.filter(
        student=profile,
        scholarship=scholarship
    ).first()

    if existing_application:
        messages.warning(request, 'You have already applied to this scholarship.')
        return redirect('scholarship_detail', scholarship_id=scholarship.id)

    if profile.gpa > scholarship.min_gpa:
        messages.error(request, 'You are not eligible because your GPA does not meet the scholarship requirement.')
        return redirect('scholarship_detail', scholarship_id=scholarship.id)

    Application.objects.create(
        student=profile,
        scholarship=scholarship,
        status='Pending'
    )

    messages.success(request, 'Your application has been submitted successfully.')
    return redirect('dashboard')


@login_required
def my_applications(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    applications = Application.objects.filter(student=profile).order_by('-applied_at')

    return render(request, 'core/my_applications.html', {
        'applications': applications
    })

@login_required
def upload_documents(request, application_id):
    profile = get_object_or_404(StudentProfile, user=request.user)
    application = get_object_or_404(Application, id=application_id, student=profile)

    requirements = application.scholarship.requirements.all()

    if request.method == 'POST':
        for requirement in requirements:
            file = request.FILES.get(f'requirement_{requirement.id}')

            if file:
                existing_document = UploadedDocument.objects.filter(
                    application=application,
                    requirement=requirement
                ).first()

                if existing_document:
                    existing_document.file = file
                    existing_document.save()
                else:
                    UploadedDocument.objects.create(
                        application=application,
                        requirement=requirement,
                        file=file
                    )

        messages.success(request, 'Documents uploaded successfully.')
        return redirect('my_applications')

    uploaded_documents = UploadedDocument.objects.filter(application=application)

    uploaded_map = {}
    for doc in uploaded_documents:
        uploaded_map[doc.requirement_id] = doc

    return render(request, 'core/upload_documents.html', {
        'application': application,
        'requirements': requirements,
        'uploaded_map': uploaded_map,
    })


@login_required
def application_documents(request, application_id):
    profile = get_object_or_404(StudentProfile, user=request.user)
    application = get_object_or_404(Application, id=application_id, student=profile)
    documents = UploadedDocument.objects.filter(application=application)

    return render(request, 'core/application_documents.html', {
        'application': application,
        'documents': documents,
    })


# Admin Views

@admin_required
def admin_applications(request):
    applications = Application.objects.select_related(
        'student__user',
        'scholarship'
    ).order_by('-applied_at')

    status = request.GET.get('status', '').strip()
    scholarship_id = request.GET.get('scholarship', '').strip()
    completeness = request.GET.get('completeness', '').strip()
    search = request.GET.get('search', '').strip()

    if status:
        applications = applications.filter(status=status)

    if scholarship_id:
        applications = applications.filter(scholarship_id=scholarship_id)

    if search:
        applications = applications.filter(
        Q(student__user__username__icontains=search) |
        Q(student__student_number__icontains=search)
    )


    applications = applications.order_by('-applied_at')

    if completeness == 'complete':
        applications = [app for app in applications if app.is_complete()]
    elif completeness == 'incomplete':
        applications = [app for app in applications if not app.is_complete()]

    scholarships = Scholarship.objects.all().order_by('title')

    return render(request, 'core/admin_applications.html', {
        'applications': applications,
        'scholarships': scholarships,
        'selected_status': status,
        'selected_scholarship': scholarship_id,
        'selected_completeness': completeness,
        'search': search,
    })


@admin_required
def admin_application_detail(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related('student__user', 'scholarship'),
        id=application_id
    )

    documents = UploadedDocument.objects.filter(application=application)
    history = application.status_history.select_related('changed_by').order_by('-changed_at')

    return render(request, 'core/admin_application_detail.html', {
        'application': application,
        'documents': documents,
        'history': history,
        'status_choices': Application.STATUS_CHOICES,
    })


@admin_required
def update_application_status(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = [choice[0] for choice in Application.STATUS_CHOICES]

        if new_status in valid_statuses:
            if new_status == 'Approved' and not application.is_complete():
                messages.error(request, 'This application cannot be approved because required documents are still missing.')
                return redirect('admin_application_detail', application_id=application.id)

            old_status = application.status

            if old_status != new_status:
                application.status = new_status
                application.save()

                ApplicationStatusHistory.objects.create(
                    application=application,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user
                )

                Notification.objects.create(
                    student=application.student,
                    title='Application Status Updated',
                    message=(
                        f'Your application for "{application.scholarship.title}" '
                        f'was updated from {old_status} to {new_status}.'
                    )
                )

                messages.success(request, 'Application status updated successfully.')
            else:
                messages.warning(request, 'The selected status is the same as the current status.')

    return redirect('admin_application_detail', application_id=application.id)


# CSV Report Views

@admin_required
def reports_dashboard(request):
    applications = Application.objects.select_related('student__user', 'scholarship')

    total_applications = applications.count()
    pending_count = applications.filter(status='Pending').count()
    approved_count = applications.filter(status='Approved').count()
    rejected_count = applications.filter(status='Rejected').count()
    claimed_count = applications.filter(status='Claimed').count()
    complete_count = sum(1 for application in applications if application.is_complete())
    incomplete_count = total_applications - complete_count
    scholarships = Scholarship.objects.all().order_by('title')

    return render(request, 'core/reports_dashboard.html', {
        'total_applications': total_applications,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'claimed_count': claimed_count,
        'complete_count': complete_count,
        'incomplete_count': incomplete_count,
        'scholarships': scholarships,
    })


@admin_required
def export_applications_csv(request):
    applications = Application.objects.select_related('student__user', 'scholarship').order_by('-applied_at')

    status = request.GET.get('status', '').strip()
    scholarship_id = request.GET.get('scholarship', '').strip()
    completeness = request.GET.get('completeness', '').strip()
    search = request.GET.get('search', '').strip()

    if status:
        applications = applications.filter(status=status)

    if scholarship_id:
        applications = applications.filter(scholarship_id=scholarship_id)

    if search:
        applications = applications.filter(
            Q(student__user__username__icontains=search) |
            Q(student__student_number__icontains=search)
        )

    if completeness == 'complete':
        applications = [app for app in applications if app.is_complete()]
    elif completeness == 'incomplete':
        applications = [app for app in applications if not app.is_complete()]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="applications_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Student Username',
        'Student Number',
        'Course',
        'Year Level',
        'GPA',
        'Scholarship',
        'Status',
        'Documents Complete',
        'Date Applied',
    ])

    for application in applications:
        writer.writerow([
            application.student.user.username,
            application.student.student_number,
            application.student.course,
            application.student.year_level,
            application.student.gpa,
            application.scholarship.title,
            application.status,
            'Yes' if application.is_complete() else 'No',
            application.applied_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    return response


# Message Views

@login_required
def submit_message(request):
    profile = StudentProfile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, 'No student profile is linked to this account.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = StudentMessageForm(request.POST)
        if form.is_valid():
            student_message = form.save(commit=False)
            student_message.student = profile
            student_message.save()
            messages.success(request, 'Your message has been submitted successfully.')
            return redirect('my_messages')
    else:
        form = StudentMessageForm()

    return render(request, 'core/submit_message.html', {'form': form})


@login_required
def my_messages(request):
    profile = StudentProfile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, 'No student profile is linked to this account.')
        return redirect('dashboard')

    student_messages = StudentMessage.objects.filter(student=profile).order_by('-created_at')

    return render(request, 'core/my_messages.html', {
        'student_messages': student_messages
    })


@admin_required
def admin_messages(request):
    student_messages = StudentMessage.objects.select_related('student__user').order_by('-created_at')

    message_type = request.GET.get('message_type', '').strip()
    status = request.GET.get('status', '').strip()
    search = request.GET.get('search', '').strip()

    if message_type:
        student_messages = student_messages.filter(message_type=message_type)

    if status:
        student_messages = student_messages.filter(status=status)

    if search:
        student_messages = student_messages.filter(
            Q(student__user__username__icontains=search) |
            Q(student__student_number__icontains=search) |
            Q(subject__icontains=search)
        )

    return render(request, 'core/admin_messages.html', {
        'student_messages': student_messages,
        'selected_type': message_type,
        'selected_status': status,
        'search': search,
    })


@admin_required
def admin_message_detail(request, message_id):
    student_message = get_object_or_404(
        StudentMessage.objects.select_related('student__user'),
        id=message_id
    )

    form = AdminMessageResponseForm(instance=student_message)

    return render(request, 'core/admin_message_detail.html', {
        'student_message': student_message,
        'form': form,
    })


@admin_required
def update_message_status(request, message_id):
    student_message = get_object_or_404(StudentMessage, id=message_id)

    if request.method == 'POST':
        form = AdminMessageResponseForm(request.POST, instance=student_message)

        if form.is_valid():
            updated_message = form.save(commit=False)

            response_text = form.cleaned_data.get('admin_response', '').strip()
            new_status = form.cleaned_data.get('status')

            if new_status == 'Resolved' and not response_text:
                messages.error(request, 'A response is required before marking this message as resolved.')
                return redirect('admin_message_detail', message_id=student_message.id)

            if response_text:
                updated_message.responded_by = request.user
                updated_message.responded_at = timezone.now()

            updated_message.save()

            Notification.objects.create(
                student=student_message.student,
                title='Message Response Updated',
                message=(
                    f'Your {student_message.message_type.lower()} titled '
                    f'"{student_message.subject}" has been updated. '
                    f'Current status: {updated_message.status}.'
                )
            )

            messages.success(request, 'Message response updated successfully.')

    return redirect('admin_message_detail', message_id=student_message.id)


# Scholarship Recommendation Views

@login_required
def recommended_scholarships(request):
    profile = StudentProfile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, 'No student profile is linked to this account.')
        return redirect('dashboard')

    recommendations = profile.recommended_scholarships()

    return render(request, 'core/recommended_scholarships.html', {
        'recommendations': recommendations,
        'profile': profile,
    })


# Notification Views

@login_required
def my_notifications(request):
    profile = StudentProfile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, 'No student profile is linked to this account.')
        return redirect('dashboard')

    notifications = Notification.objects.filter(student=profile).order_by('-created_at')

    return render(request, 'core/my_notifications.html', {
        'notifications': notifications
    })


@login_required
def mark_notification_as_read(request, notification_id):
    profile = StudentProfile.objects.filter(user=request.user).first()

    if not profile:
        messages.error(request, 'No student profile is linked to this account.')
        return redirect('dashboard')

    notification = get_object_or_404(Notification, id=notification_id, student=profile)
    notification.is_read = True
    notification.save()

    return redirect('my_notifications')



# Announcement Views

@login_required
def announcements_list(request):
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')

    return render(request, 'core/announcements_list.html', {
        'announcements': announcements
    })


@admin_required
def admin_announcements(request):
    announcements = Announcement.objects.select_related('created_by').order_by('-created_at')

    return render(request, 'core/admin_announcements.html', {
        'announcements': announcements
    })


@admin_required
def create_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            messages.success(request, 'Announcement created successfully.')
            return redirect('admin_announcements')
    else:
        form = AnnouncementForm()

    return render(request, 'core/create_announcement.html', {
        'form': form
    })


@admin_required
def edit_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement updated successfully.')
            return redirect('admin_announcements')
    else:
        form = AnnouncementForm(instance=announcement)

    return render(request, 'core/edit_announcement.html', {
        'form': form,
        'announcement': announcement,
    })