from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)

class CheckoutForm(forms.Form):
    # For simplicity only collecting name & email - extend as needed
    name = forms.CharField(max_length=100)
    email = forms.EmailField()

class SignUpForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, required=False, label="Full name")
    email = forms.EmailField(required=True, label="Email address")

    class Meta:
        model = User
        fields = ("username", "full_name", "email", "password1", "password2")
    
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get("full_name", "").strip()
        if full_name:
            # you can split into first/last name or save into first_name
            user.first_name = full_name
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user