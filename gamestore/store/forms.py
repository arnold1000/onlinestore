from django import forms
from .models import Game
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class AddGameForm(ModelForm):
    class Meta:
        model = Game
        fields = ['url', 'thumbnail', 'price', 'title', 'description']


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    is_developer = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1',
                  'password2', 'is_developer']


class DeleteGame(forms.ModelForm):
    class Meta:
        model = Game
        fields = []