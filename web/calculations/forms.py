from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UsernameField

class CustomUserCreationForm(forms.ModelForm):
    """
    Поля:
      username (обов’язково)
      email (обов’язково, унікальний серед непорожніх)
      first_name (необов’язково)
      last_name (необов’язково)
      password1
      password2
    """
    password1 = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Підтвердження пароля",
        widget=forms.PasswordInput,
        strip=False
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")
        field_classes = {"username": UsernameField}
        widgets = {
            "email": forms.EmailInput(attrs={"required": True}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise forms.ValidationError("Email є обов'язковим.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Користувач з таким email вже існує.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Паролі не співпадають.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user