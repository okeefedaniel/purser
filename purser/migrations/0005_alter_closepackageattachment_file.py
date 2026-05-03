"""Apply FileSecurityValidator to closepackageattachment.file (keel 0.25.0+).

Auto-generated to record the AbstractAttachment.file change in keel —
keel/core/models.py now sets validators=[FileSecurityValidator()].
"""
from django.db import migrations, models

import keel.security.scanning


class Migration(migrations.Migration):

    dependencies = [
        ('purser', '0004_closepackageattachment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='closepackageattachment',
            name='file',
            field=models.FileField(
                upload_to='attachments/%Y/%m/',
                validators=[keel.security.scanning.FileSecurityValidator()],
            ),
        ),
    ]
