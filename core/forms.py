# royal_bees_project/core/forms.py
from django import forms

class AdmissionForm(forms.Form):
    applicant_name = forms.CharField(max_length=255, label="Full Name of Applicant")
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Date of Birth")

    APPLYING_GRADE_CHOICES = [
        ('', 'Select Grade'),
        ('JSS 1', 'JSS 1'),
        ('JSS 2', 'JSS 2'),
        ('JSS 3', 'JSS 3'),
        ('KG 1', 'KG 1'),
        ('KG 2', 'KG 2'),
        ('NURSERY 1', 'NURSERY 1'),
        ('NURSERY 2', 'NURSERY 2'),
        ('PRIMARY 1', 'PRIMARY 1'),
        ('PRIMARY 2', 'PRIMARY 2'),
        ('PRIMARY 3', 'PRIMARY 3'),
        ('PRIMARY 4', 'PRIMARY 4'),
        ('PRIMARY 5', 'PRIMARY 5'),
        ('PRIMARY 6', 'PRIMARY 6'),
        ('SSS 1', 'SSS 1'),
        ('SSS 2', 'SSS 2'),
        ('SSS 3', 'SSS 3'),
    ]
    applying_grade = forms.ChoiceField(choices=APPLYING_GRADE_CHOICES, label="Applying for Grade/Class")

    parent_name = forms.CharField(max_length=255, label="Parent/Guardian Full Name")
    parent_email = forms.EmailField(label="Parent/Guardian Email")
    parent_phone = forms.CharField(max_length=20, label="Parent/Guardian Phone Number", help_text="e.g., +23480XXXXXXXX")
    address = forms.CharField(widget=forms.Textarea, label="Residential Address")
    terms_agreed = forms.BooleanField(label="I agree to the terms and conditions of admission.", required=True)