from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UploadedDocument, StudentMessage, Announcement, Scholarship, StudentProfile, Requirement



class StudentRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'student_number',
            'course',
            'year_level',
            'gpa',
            'contact_number',
            'address',
        ]


class UploadedDocumentForm(forms.ModelForm):
    class Meta:
        model = UploadedDocument
        fields = ['file']


class StudentMessageForm(forms.ModelForm):
    class Meta:
        model = StudentMessage
        fields = ['message_type', 'subject', 'body']


class AdminMessageResponseForm(forms.ModelForm):
    class Meta:
        model = StudentMessage
        fields = ['status', 'admin_response']


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'body', 'is_active']


class ScholarshipForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['title', 'description', 'min_gpa', 'deadline']


class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ['name']