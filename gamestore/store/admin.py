from django.contrib import admin
from .models import Game
from .models import PersonalGameInfo
from .models import HighScore
from .models import Profile

admin.site.register(Game)
admin.site.register(PersonalGameInfo)
admin.site.register(HighScore)
admin.site.register(Profile)

