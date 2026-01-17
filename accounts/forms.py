from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import DelegateAccess, MemberCreditAllowance, WorkshopDelegate

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
    
    def __init__(self, *args, current_user=None, **kwargs):
        """Initialize form with role filtering based on current user"""
        super().__init__(*args, **kwargs)
        
        # Filter role choices based on current user's role
        if current_user:
            if current_user.role == 'administrator':
                # Admin can create techs and managers
                self.fields['role'].choices = [
                    ('technician', 'Technician'),
                    ('manager', 'Manager'),
                ]
            elif current_user.role == 'technician':
                # Tech can only create members
                self.fields['role'].choices = [
                    ('member', 'Member'),
                ]
            else:
                # Others can't create users
                self.fields['role'].choices = []
    
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


# ============================================================================
# MEMBER PROFILE MANAGEMENT FORMS
# ============================================================================
# These forms support editing member (advisor) profiles post-creation.
# Only Benefits Technicians (role='technician', level_1+) can access these.
#
# Key design considerations:
# - No password editing here (separate password change form)
# - Can toggle active/inactive status (WP Fusion placeholder)
# - Can edit workshop code (for workshop-based grouping)
# - Can manage delegates and quarterly credits
# - All changes are logged via AuditLog for compliance
# ============================================================================


class MemberProfileEditForm(forms.ModelForm):
    """
    Form for Benefits Technicians to edit member profiles.
    
    This form allows modification of:
    - first_name / last_name
    - email
    - phone
    - workshop_code (affects which members can see each other)
    - is_active (WP Fusion controlled placeholder)
    
    Note: Changes are automatically logged via signals/AuditLog integration
    """
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'workshop_code', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'workshop_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Workshop code (e.g., "WORKSHOP-2026-Q1")',
                'help_text': 'Members with same workshop code can see each other'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'memberActiveCheckbox'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize with current user context for audit logging"""
        self.changed_by_user = kwargs.pop('changed_by_user', None)
        super().__init__(*args, **kwargs)
        
        # Add help text for is_active field
        self.fields['is_active'].help_text = (
            "Check to activate member account. NOTE: This is a manual toggle. "
            "WP Fusion integration will eventually control this automatically based on subscription status."
        )
    
    def clean_email(self):
        """
        Validate email uniqueness (excluding current user).
        Prevents duplicate emails while allowing user to keep their current email.
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already in use by another account')
        return email
    
    def save(self, commit=True):
        """
        Save changes and log them via AuditLog.
        
        This captures:
        - What fields changed
        - Old vs new values
        - Who made the change (changed_by_user)
        - Timestamp (auto from AuditLog.created_at)
        """
        user = super().save(commit=commit)
        
        # Note: AuditLog entry is created via signal in models.py
        # This ensures consistent logging across all profile changes
        
        return user


class DelegateAccessForm(forms.ModelForm):
    """
    Form for adding/editing delegate access permissions.
    
    Allows Benefits Technicians to grant delegation rights to team members.
    Delegates can be:
    - Other members in the same workshop
    - Support staff members
    
    Permissions control what delegates can do:
    - view: Read-only access to member's cases
    - submit: Can submit new cases on behalf
    - edit: Can submit and edit cases
    - approve: Can submit, edit, and approve (future admin workflows)
    """
    
    class Meta:
        model = DelegateAccess
        fields = ['delegate', 'permission_level', 'grant_reason', 'is_active']
        widgets = {
            'delegate': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select delegate'
            }),
            'permission_level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'grant_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Why is this person being granted access? (optional)',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'delegateActiveCheckbox'
            }),
        }
    
    def __init__(self, member_user, *args, **kwargs):
        """
        Initialize form with context about the member.
        
        Args:
            member_user: The member (advisor) whose delegates are being managed
        """
        super().__init__(*args, **kwargs)
        self.member_user = member_user
        self.changed_by_user = kwargs.pop('changed_by_user', None)
        
        # Filter delegate choices to:
        # 1. Exclude the member themselves
        # 2. Optionally filter to same workshop (future enhancement)
        self.fields['delegate'].queryset = User.objects.exclude(pk=member_user.pk)
        
        # Add help text for each field
        self.fields['delegate'].help_text = (
            'Select a team member to grant delegation rights. '
            'Typically members of the same office/workshop.'
        )
        self.fields['permission_level'].help_text = (
            'Choose what actions this delegate can perform on behalf of the member.'
        )
        self.fields['is_active'].help_text = (
            'Uncheck to temporarily disable access without deleting this delegation.'
        )
    
    def clean_delegate(self):
        """Validate that the delegate is not the member themselves"""
        delegate = self.cleaned_data.get('delegate')
        
        if delegate and delegate.pk == self.member_user.pk:
            raise ValidationError("A member cannot be their own delegate")
        
        return delegate
    
    def clean(self):
        """
        Validate no duplicate active delegations for same member-delegate pair.
        """
        cleaned_data = super().clean()
        delegate = cleaned_data.get('delegate')
        
        if delegate and self.instance.pk is None:
            # New delegation - check for existing
            existing = DelegateAccess.objects.filter(
                member=self.member_user,
                delegate=delegate,
                is_active=True
            ).exists()
            
            if existing:
                raise ValidationError(
                    f'{delegate.get_full_name()} already has active delegation for this member'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Save delegate access and log the action.
        """
        instance = super().save(commit=False)
        instance.member = self.member_user
        instance.granted_by = self.changed_by_user
        
        if commit:
            instance.save()
            # Note: AuditLog entry created via signal in models.py
        
        return instance


class MemberCreditAllowanceForm(forms.ModelForm):
    """
    Form for setting quarterly credit allowances for members.
    
    Benefits Technicians use this to configure how many cases/credits
    each member is allowed to submit per quarter.
    
    This is a per-member, per-quarter setting that can be:
    - Adjusted manually by Benefits Tech
    - Eventually synced from WP product/membership tier
    - Reset automatically at quarter start (future automation)
    """
    
    class Meta:
        model = MemberCreditAllowance
        fields = ['allowed_credits', 'notes']
        widgets = {
            'allowed_credits': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '10000',
                'placeholder': 'Number of credits allowed this quarter'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Admin notes (e.g., "Increased from 75 due to seasonal demand")',
                'rows': 3
            }),
        }
    
    def __init__(self, member_user, fiscal_year, quarter, *args, **kwargs):
        """
        Initialize form with member, year, and quarter context.
        
        Args:
            member_user: The member whose credit allowance is being set
            fiscal_year: Fiscal year (e.g., 2026)
            quarter: Quarter number (1-4)
        """
        super().__init__(*args, **kwargs)
        self.member_user = member_user
        self.fiscal_year = fiscal_year
        self.quarter = quarter
        self.changed_by_user = kwargs.pop('changed_by_user', None)
        
        # Update the display label with member info
        self.fields['allowed_credits'].label = (
            f'Credits for {member_user.get_full_name()} - FY{fiscal_year} Q{quarter}'
        )
    
    def clean_allowed_credits(self):
        """
        Validate that credits is a reasonable number.
        """
        credits = self.cleaned_data.get('allowed_credits')
        
        if credits is not None:
            if credits < 0:
                raise ValidationError('Credits cannot be negative')
            if credits > 10000:
                raise ValidationError('Credits seem unusually high (max 10000)')
        
        return credits
    
    def save(self, commit=True):
        """
        Save credit allowance and log the change.
        """
        instance = super().save(commit=False)
        instance.member = self.member_user
        instance.fiscal_year = self.fiscal_year
        instance.quarter = self.quarter
        instance.configured_by = self.changed_by_user
        
        if commit:
            instance.save()
            # Note: AuditLog entry created via signal in models.py
        
        return instance


class WorkshopDelegateForm(forms.ModelForm):
    """
    Form for managing workshop-level delegates.
    
    Allows Benefits Technicians and Admins to assign delegates to workshop codes.
    Unlike DelegateAccessForm (member-centric), this is workshop-centric:
    - One delegate can serve multiple members in a workshop
    - Assignment is by workshop code, not individual member
    - Delegate can submit cases on behalf of ANY member in that workshop
    """
    
    workshop_code = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter workshop code (e.g., WS-001, DENVER, etc.)',
            'list': 'workshop_list'  # For autocomplete (optional)
        }),
        help_text='Workshop code this delegate has access to'
    )
    
    class Meta:
        model = WorkshopDelegate
        fields = ['workshop_code', 'delegate', 'permission_level', 'grant_reason', 'is_active']
        widgets = {
            'delegate': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select delegate'
            }),
            'permission_level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'grant_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Why is this delegate being assigned? (optional)',
                'rows': 3
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'delegateActiveCheckbox'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form and set up delegate choices."""
        self.changed_by_user = kwargs.pop('changed_by_user', None)
        super().__init__(*args, **kwargs)
        
        # Filter delegate choices to only staff/technician users
        # Exclude regular members (role='member')
        self.fields['delegate'].queryset = User.objects.exclude(role='member')
        self.fields['delegate'].help_text = (
            'Select a staff member or technician to assign to this workshop. '
            'They will be able to submit cases on behalf of workshop members.'
        )
    
    def clean_workshop_code(self):
        """Validate workshop code format."""
        code = self.cleaned_data.get('workshop_code', '').strip().upper()
        
        if not code:
            raise ValidationError('Workshop code is required')
        
        if len(code) < 2:
            raise ValidationError('Workshop code must be at least 2 characters')
        
        if len(code) > 50:
            raise ValidationError('Workshop code must be 50 characters or less')
        
        return code
    
    def clean(self):
        """Check for duplicate workshop + delegate assignments."""
        cleaned_data = super().clean()
        workshop_code = cleaned_data.get('workshop_code', '').upper()
        delegate = cleaned_data.get('delegate')
        
        if workshop_code and delegate:
            # Check if this delegate is already assigned to this workshop
            existing = WorkshopDelegate.objects.filter(
                workshop_code=workshop_code,
                delegate=delegate
            )
            
            # Allow if editing existing assignment
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'This delegate is already assigned to workshop {workshop_code}'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save workshop delegate assignment."""
        instance = super().save(commit=False)
        instance.workshop_code = self.cleaned_data['workshop_code'].upper()
        instance.granted_by = self.changed_by_user
        
        if commit:
            instance.save()
        
        return instance