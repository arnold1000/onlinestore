from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    is_developer = models.BooleanField(default=False)
    email_validated = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Game(models.Model):
    url = models.URLField(
        default='https://users.aalto.fi/~oseppala/game/example_game.html')
    thumbnail = models.URLField(
        default='https://pbs.twimg.com/profile_images/964283409425227776/xqQi0oIM.jpg')
    price = models.FloatField()
    title = models.CharField(max_length=255, default='Nameless game')
    description = models.CharField(max_length=255)
    times_played = models.PositiveIntegerField(default=0)
    times_downloaded = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    last_played = models.DateTimeField()
    last_download = models.DateTimeField(null=True)
    creator = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name=('created_games')
    )
    revenue = models.FloatField(default=0.0)


class Save(models.Model):
    player = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name=('saves')
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name=('saves')
    )
    data = models.TextField(default="")


class PersonalGameInfo(models.Model):
    high_score = models.FloatField(default=0.0)
    times_played = models.PositiveIntegerField(default=0)
    last_played = models.DateTimeField()
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name=('players')
    )
    player = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name=('games')
    )


class HighScore(models.Model):
    score = models.FloatField()
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name=('+')
    )
    player = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name=('+')
    )


class Payment(models.Model):
    user = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name=('payments')
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name=('+')
    )
