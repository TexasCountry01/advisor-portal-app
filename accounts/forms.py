from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class UserCreationForm(forms.Form):
    """Form for creating new users with role and technician level assignment"""
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    
    password = forms.CharField(
        max_length=128,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'roleSelect'
        })
    )
    
    user_level = forms.ChoiceField(
        choices=[('', '-- Select Level (Technician Only) --')] + list(User.USER_LEVEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'userLevelSelect'
        }),
        help_text='Only required if role is Technician'
    )
    
    workshop_code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Workshop Code (for members)',
            'id': 'workshopCodeInput'
        }),
        help_text='Only for Members: Pre-assigned workshop code'
    )
    
    def clean_username(self):
        """Check if username already exists"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists')
        return username
    
    def clean_email(self):
        """Check if email already exists"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already exists')
        return email
    
    def clean(self):
        """Validate that technician role has a user level"""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        user_level = cleaned_data.get('user_level')
        
        if role == 'technician' and not user_level:
            raise ValidationError('Technician role requires a user level')
        
        return cleaned_data
    
    def save(self):
        """Create the user with the provided data"""
        username = self.cleaned_data['username']
        email = self.cleaned_data['email']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        password = self.cleaned_data['password']
        role = self.cleaned_data['role']
        user_level = self.cleaned_data.get('user_level')
        workshop_code = self.cleaned_data.get('workshop_code')
        
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            user_level=user_level if user_level else None,
            workshop_code=workshop_code if workshop_code else ''
        )
        user.set_password(password)
        user.save()
        
        return user
