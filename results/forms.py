# results/forms.py
from django import forms

class ScoreEntryForm(forms.Form):
    subject_id = forms.IntegerField(widget=forms.HiddenInput())
    
    test_score_1 = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="CA 1", # Shorter label for table header
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm score-input', 'step': '0.01', 'style': 'width: 70px;'})
    )
    test_score_2 = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="CA 2",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm score-input', 'step': '0.01', 'style': 'width: 70px;'})
    )
    exam_score = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label="Exam",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm score-input', 'step': '0.01', 'style': 'width: 70px;'})
    )
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 1, 'style': 'min-width: 150px;'}), 
        required=False
    )

    def __init__(self, *args, **kwargs):
        # subject_name_display is passed in initial data by the view for display in the template
        # It's not a true form field here.
        self.subject_name_display = kwargs.get('initial', {}).get('subject_name_display', '')
        super().__init__(*args, **kwargs)

    # Example custom validation (adjust max scores as needed)
    def clean_test_score_1(self):
        score = self.cleaned_data.get('test_score_1')
        if score is not None and (score < 0 or score > 20): # Assuming CA1 is out of 20
            raise forms.ValidationError("Score must be between 0 and 20.")
        return score

    def clean_test_score_2(self):
        score = self.cleaned_data.get('test_score_2')
        if score is not None and (score < 0 or score > 20): # Assuming CA2 is out of 20
            raise forms.ValidationError("Score must be between 0 and 20.")
        return score

    def clean_exam_score(self):
        score = self.cleaned_data.get('exam_score')
        if score is not None and (score < 0 or score > 60): # Assuming Exam is out of 60
            raise forms.ValidationError("Score must be between 0 and 60.")
        return score