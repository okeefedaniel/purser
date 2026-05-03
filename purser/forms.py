from django import forms

from .models import Program, SubmissionAttachment, SubmissionLineValue


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

    # 25 MB ceiling — close packages are PDFs, not video. Prevents
    # arbitrary-size uploads from chewing through Railway disk before
    # the FOIA pipeline ever sees them.
    MAX_BYTES = 25 * 1024 * 1024

    signed_pdf = forms.FileField(
        label='Signed close package PDF',
        help_text='Upload the signed close package.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
    )

    def clean_signed_pdf(self):
        f = self.cleaned_data['signed_pdf']
        if not f.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Only PDF files are accepted.')
        if f.size > self.MAX_BYTES:
            raise forms.ValidationError(
                f'File is too large ({f.size // (1024 * 1024)} MB). '
                f'Limit is {self.MAX_BYTES // (1024 * 1024)} MB.'
            )
        # Magic-byte sniff — extension is user-controlled, content is
        # what actually matters. Read a small head and rewind.
        head = f.read(5)
        f.seek(0)
        if not head.startswith(b'%PDF-'):
            raise forms.ValidationError(
                'Uploaded file is not a valid PDF (missing %PDF- header).'
            )
        return f
