from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone



class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_number = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100)
    year_level = models.PositiveIntegerField()
    gpa = models.DecimalField(max_digits=4, decimal_places=2)
    contact_number = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username

    def applied_scholarship_ids(self):
        return self.applications.values_list('scholarship_id', flat=True)

    def recommended_scholarships(self):
        scholarships = Scholarship.objects.all().order_by('deadline')
        applied_ids = set(self.applied_scholarship_ids())

        recommended = []
        for scholarship in scholarships:
            if scholarship.id in applied_ids:
                continue
            if scholarship.is_closed():
                continue
            if self.gpa > scholarship.min_gpa:
                continue

            recommended.append({
                'scholarship': scholarship,
                'reasons': [
                    'You meet the GPA requirement',
                    'The scholarship deadline is still open',
                    'You have not applied yet',
                ]
            })

        return recommended



class Scholarship(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    min_gpa = models.DecimalField(max_digits=4, decimal_places=2)
    deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def is_open(self):
        return timezone.localdate() <= self.deadline

    def is_closed(self):
        return timezone.localdate() > self.deadline


class Requirement(models.Model):
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='requirements')
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.scholarship.title} - {self.name}"


class Application(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Claimed', 'Claimed'),
        ('Withdrawn', 'Withdrawn'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='applications')
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.scholarship.title}"

    def can_withdraw(self):
        return self.status == 'Pending'

    def is_withdrawn(self):
        return self.status == 'Withdrawn'

    def can_upload_documents(self):
        return self.status == 'Pending'

    def can_reapply(self):
        return self.status == 'Withdrawn'

    def active_requirements(self):
        if self.status == 'Pending':
            return list(self.scholarship.requirements.all())
        return list(self.requirement_snapshots.all())

    def total_requirements(self):
        return len(self.active_requirements())

    def uploaded_requirements_count(self):
        active_names = {req.name if hasattr(req, 'name') else req.requirement_name for req in self.active_requirements()}
        uploaded_names = set(
            self.documents.values_list('requirement__name', flat=True)
        )
        return len(active_names.intersection(uploaded_names))

    def is_complete(self):
        active_names = {req.name if hasattr(req, 'name') else req.requirement_name for req in self.active_requirements()}
        uploaded_names = set(
            self.documents.values_list('requirement__name', flat=True)
        )
        return active_names.issubset(uploaded_names)

    def missing_requirements(self):
        uploaded_names = set(
            self.documents.values_list('requirement__name', flat=True)
        )

        missing = []
        for req in self.active_requirements():
            req_name = req.name if hasattr(req, 'name') else req.requirement_name
            if req_name not in uploaded_names:
                missing.append(req_name)
        return missing

    def has_snapshot(self):
        return self.requirement_snapshots.exists()

    def create_requirement_snapshot(self):
        if self.has_snapshot():
            return

        for requirement in self.scholarship.requirements.all():
            ApplicationRequirementSnapshot.objects.create(
                application=self,
                requirement_name=requirement.name
            )


class UploadedDocument(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application} - {self.requirement.name}"
    

class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application} | {self.old_status} -> {self.new_status}"

    
class StudentMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('Inquiry', 'Inquiry'),
        ('Complaint', 'Complaint'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Resolved', 'Resolved'),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_response = models.TextField(blank=True, null=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_messages'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.message_type} - {self.subject}"


# Notification model

class Notification(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.title}"


# Announcement model

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# Application Snapshot
class ApplicationRequirementSnapshot(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='requirement_snapshots'
    )
    requirement_name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.application} - {self.requirement_name}"
