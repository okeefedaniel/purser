from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _lazy
from keel.accounts.forms import LoginForm  # noqa: F401  (shared across DockLabs suite)


# LoginForm is now shared in Keel for suite-wide consistency.
# See keel/accounts/forms.py for the canonical definition.
