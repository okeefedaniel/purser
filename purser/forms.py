from django import forms

from .models import Program, Submission, SubmissionLineValue, SubmissionAttachment


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['name', 'code', 'program_type', 'report_schema',
                  'is_active', 'pulls_from_harbor', 'harbor_api_endpoint']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class SubmissionLineValueForm(forms.ModelForm):
    class Meta:
        model = SubmissionLineValue
        fields = ['numeric_value', 'text_value', 'note']
        widgets = {
            'numeric_value': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm text-end',
                'step': '0.01',
            }),
            'text_value': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control form-control-sm',
                'rows': 2,
            }),
        }


class SubmissionAttachmentForm(forms.ModelForm):
    class Meta:
        model = SubmissionAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }


class CloseLocalSignForm(forms.Form):
    """Upload a locally-signed close package when Manifest isn't deployed."""

    signed_pdf = forms.FileField(
        label='Signed close package PDF',
        help_text='Upload the signed close package.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
    )

    def clean_signed_pdf(self):
        f = self.cleaned_data['signed_pdf']
        if not f.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Only PDF files are accepted.')
        return f
