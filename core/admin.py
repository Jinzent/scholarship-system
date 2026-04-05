from django.contrib import admin
from .models import (
    StudentProfile,
    Scholarship,
    Requirement,
    Application,
    UploadedDocument,
    ApplicationStatusHistory,
    StudentMessage,
    Notification,
    Announcement,
    ApplicationRequirementSnapshot,
)

admin.site.register(StudentProfile)
admin.site.register(Scholarship)
admin.site.register(Requirement)
admin.site.register(Application)
admin.site.register(UploadedDocument)
admin.site.register(ApplicationStatusHistory)
admin.site.register(StudentMessage)
admin.site.register(Notification)
admin.site.register(Announcement)
admin.site.register(ApplicationRequirementSnapshot)