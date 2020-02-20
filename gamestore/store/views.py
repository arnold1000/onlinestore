from django.shortcuts import HttpResponse, render, redirect
import os
from django.template import loader, Context
from django.contrib.auth.decorators import login_required
from .forms import AddGameForm, UserRegisterForm, DeleteGame
from .models import Game, Payment, PersonalGameInfo, HighScore, Save
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from urllib.parse import urlencode
from hashlib import md5
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
import json
from django.contrib.auth import login, authenticate
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .helpers.tokens import account_activation_token
from django.core.mail import EmailMessage, EmailMultiAlternatives


def getUrl(request, urlName):
    # a helper method that returns a url
    domain = request.META['HTTP_HOST']
    retUrl = ""
    if "localhost" in domain:
        retUrl = "http://" + domain + reverse(urlName)
    else:
        retUrl = "https://" + domain + reverse(urlName)
    return retUrl


def getBaseUrl(request):
    domain = request.META['HTTP_HOST']
    retUrl = ""
    if "localhost" in domain:
        retUrl = "http://" + domain
    else:
        retUrl = "https://" + domain
    return retUrl


def getUsersGames(userProfile):
    personalGameInfos = userProfile.games.all()
    games = list(map(lambda info: info.game, personalGameInfos))
    return games


def messagesJsonResponse(request, status):
    messages_json = []
    for message in messages.get_messages(request):
        messages_json.append({
            'level': message.level,
            'message': message.message
        })
    return JsonResponse({'messages': messages_json}, status=status)


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            user.profile.is_developer = form.cleaned_data.get('is_developer')
            user.save()
            current_site = get_current_site(request)
            mail_subject = 'Activate your account.'
            base64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            activation_link = getBaseUrl(
                request) + reverse('activate', kwargs={"uidb64": base64, "token": token})

            messagehtml = render_to_string('users/acc_active_email.html', {
                'activation_link': activation_link,
                'user': user

            })
            to_email = form.cleaned_data.get('email')
            email = EmailMultiAlternatives(
                mail_subject, messagehtml
            )
            email.attach_alternative(messagehtml, "text/html")
            email.to = [to_email]
            email.send()
            messages.success(request, f'Your account has been created!')
            if user.profile.is_developer:
                messages.success(request, f'Your account is set to: Developer')
            messages.warning(
                request, "Please confirm your email to access your account.")
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


def activate(request, uidb64, token, backend='django.contrib.auth.backends.ModelBackend'):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Your account has been verified!')
        return redirect('login')
    else:
        messages.error(request, f'Something went wrong :(')
        return redirect('login')


@login_required
def shop(request):
    is_developer = request.user.profile.is_developer
    if not is_developer:
        games = Game.objects.all()
        return render(request, 'shop.html', {'games': games, 'is_developer': is_developer})
    else:
        messages.warning(request, "Developers don't have access to this page")
        return redirect('games')


@login_required
def buy(request, game_id):
    game = Game.objects.get(pk=game_id)
    user = request.user
    is_developer = user.profile.is_developer

    if not is_developer:
        if game.id not in map(lambda gameInfo: gameInfo.game_id, user.profile.games.all()):
            if request.method == 'POST':
                payment = Payment(game=game, user=user.profile)
                payment.save()
                sid = os.environ['WSD_SID']
                secret = os.environ['WSD_SECRET']
                pid = str(payment.id)
                amount = str(game.price)

                checksumstr = f"pid={pid:s}&sid={sid:s}&amount={amount:s}&token={secret:s}"
                checksum = md5(checksumstr.encode('utf-8')).hexdigest()

                bankapi = 'https://tilkkutakki.cs.aalto.fi/payments/pay'
                responseUrl = getUrl(request, 'buy_response')
                query = urlencode({
                    'pid': pid, 'sid': sid, 'amount': amount,
                    'checksum': checksum,
                    'success_url': responseUrl,
                    'cancel_url': responseUrl,
                    'error_url': responseUrl})

                return redirect(bankapi + '?' + query)
            return render(request, 'buy.html', {'game': game})
        else:
            messages.warning(
                request, f'You already have the game: {game.title}')
            return redirect('games')
    else:
        messages.warning(request, "Developers don't have access to this page")
        return redirect('games')


@login_required
def buy_response(request):
    is_developer = request.user.profile.is_developer
    if not is_developer:
        try:
            response = request.GET
            result = str(response.get('result'))
            pid = str(response.get("pid"))
            ref = str(response.get('ref'))
            payment = Payment.objects.get(pk=pid)
            game = payment.game
            user = payment.user
            responseChecksum = response.get("checksum")
            secret = os.environ['WSD_SECRET']

            checksumstr = f"pid={pid:s}&ref={ref:s}&result={result:s}&token={secret:s}"
            checksum = md5(checksumstr.encode('utf-8')).hexdigest()
            if not result == "error" and checksum == responseChecksum:
                if result == "success":
                    if game.id not in map(lambda gameInfo: gameInfo.game_id, user.games.all()):
                        myGame = PersonalGameInfo(
                            player=user, game=game, last_played=timezone.now())
                        myGame.save()
                        game.times_downloaded += 1
                        game.last_download = timezone.now()
                        game.revenue += game.price
                        game.save()
                    messages.success(
                        request, f'Your payment for the game: {game.title} was successful'
                    )
                    return redirect('games')
                elif result == "cancel":
                    messages.error(
                        request, f'Your payment was canceled'
                    )
                    return redirect('shop')
            else:
                messages.error(
                    request, f'Something went wrong :('
                )
                return redirect('shop')
        except:
            return redirect('shop')
    else:
        messages.warning(request, "Developers don't have access to this page")
        return redirect('games')


@login_required
def base(request):
    is_developer = request.user.profile.is_developer
    return render(request, 'base.html', {'is_developer': is_developer})


@login_required
def games(request):
    user = request.user
    is_developer = user.profile.is_developer
    if is_developer:
        games = user.profile.created_games.all()
        no_games = len(games) == 0
        return render(request, 'developer/games.html', {'games': games, 'is_developer': is_developer, "no_games": no_games})
    else:
        games = getUsersGames(user.profile)
        no_games = len(games) == 0
        return render(request, 'games.html', {'games': games, "no_games": no_games})


@login_required
def game(request, game_id):
    user = request.user
    try:
        game = Game.objects.get(pk=game_id)
        is_developer = user.profile.is_developer
        if is_developer:
            return redirect('modify', game_id)
        else:
            if game in getUsersGames(user.profile):
                split = game.url.split("/")
                origin = split[0] + "//" + split[2]
                gameUrl = getUrl(request, 'games') + str(game.id) + "/"
                gameInfo = PersonalGameInfo.objects.get(
                    game=game, player=user.profile)
                personal_score = "{:1.2f}".format(gameInfo.high_score)
                average_score = "{:1.2f}".format(game.average_score)
                score = None
                high_score = 0.0
                try:
                    score = HighScore.objects.get(game=game)
                    high_score = "{:1.2f}".format(score.score)
                except HighScore.DoesNotExist:
                    "foo"
                return render(request, 'game.html', {'game': game, 'origin': origin, 'game_url': gameUrl, "high_score": high_score, 'personal_score': personal_score, "average_score": average_score, "gameInfo": gameInfo})
            else:
                messages.warning(
                    request, f"You don't have the game: {game.title}")
                messages.warning(request, f"You can buy it here")
                return redirect('buy', game_id=game.id)
    except Exception as e:
        messages.error(
            request, f'The game_id: {game_id} does not correspond with any game')
        messages.error(request, e)
        return redirect('games')


@login_required
def save_score(request, game_id):
    user = request.user
    is_developer = user.profile.is_developer
    game = Game.objects.get(pk=game_id)

    if not is_developer and request.method == 'POST':
        score = float(request.POST.get('score'))
        gameInfo = PersonalGameInfo.objects.get(player=user.profile, game=game)
        gameInfo.last_played = timezone.now()
        gameInfo.times_played += 1
        game.last_played = timezone.now()
        newTimesPlayed = game.times_played + 1
        game.average_score = ((newTimesPlayed - 1) *
                              game.average_score + score) / newTimesPlayed
        game.times_played = newTimesPlayed
        game.save()
        gameInfo.save()

        try:
            globalScore = HighScore.objects.get(game=game)
            if score > globalScore.score:
                messages.success(
                    request, f"Nice!! You made a global high score")
                messages.success(
                    request, f"Your score: {score}  previous high score: {globalScore.score}")
                globalScore.score = score
                globalScore.player = user.profile
                gameInfo.high_score = score
                globalScore.save()
                gameInfo.save()
                return messagesJsonResponse(request, 200)
        except HighScore.DoesNotExist:
            globalScore = HighScore(
                score=score, game=game, player=user.profile)
            messages.success(
                request, f"Nice!! You made a global high score")
            messages.success(
                request, f"Your score: {score}")
            gameInfo.high_score = score
            globalScore.save()
            gameInfo.save()
            return messagesJsonResponse(request, 200)

        currentHighScore = gameInfo.high_score
        if score > currentHighScore:
            messages.success(
                request, 'You made a personal high score!!')
            messages.success(
                request, f'Your score: {score}  your previous high score: {gameInfo.high_score}')
            gameInfo.high_score = score
            gameInfo.save()
        else:
            messages.success(request, f'Your score: {score}')

        return messagesJsonResponse(request, 200)
    else:
        return redirect('games')


@login_required
def save_game(request, game_id):
    user = request.user
    is_developer = user.profile.is_developer
    game = Game.objects.get(pk=game_id)
    if not is_developer and request.method == 'POST':
        messages.success(request, "Your game was saved successfully")
        try:
            save = Save.objects.get(game=game, player=user.profile)
            save.data = request.POST.get('gameState')
            save.save()
            return messagesJsonResponse(request, 200)
        except Save.DoesNotExist:
            save = Save(game=game, player=user.profile,
                        data=str(request.POST.get('gameState')))
            save.save()
            return messagesJsonResponse(request, 200)
    else:
        return redirect('games')


@login_required
def load_game(request, game_id):
    user = request.user
    is_developer = user.profile.is_developer
    game = Game.objects.get(pk=game_id)
    if not is_developer and request.method == "POST":
        try:
            save = Save.objects.get(game=game, player=user.profile)
            data = save.data
            return HttpResponse(json.dumps(data), content_type='application/json')
        except Save.DoesNotExist:
            messages.error(request, "No saved game found")
            return messagesJsonResponse(request, 400)
    else:
        return redirect('games')


@login_required
def add_new(request):
    is_developer = request.user.profile.is_developer
    if is_developer:
        if request.method == 'POST':
            newgameform = AddGameForm(request.POST)
            if newgameform.is_valid():
                post = newgameform.save(commit=False)
                post.last_played = timezone.now()
                post.last_download = timezone.now()
                post.creator = request.user.profile
                post.save()
                messages.success(
                    request, f'Your game: {post.title} was added to the store!')
                return redirect('/games', {'is_developer': is_developer})
        else:
            newgameform = AddGameForm()
        return render(request, 'developer/newgame.html', {'form': newgameform, 'is_developer': is_developer})
    else:
        messages.warning(request, 'You are not a developer')
        return redirect('games')


@login_required
def modify(request, game_id):
    is_developer = request.user.profile.is_developer
    game = Game.objects.get(pk=game_id)
    if is_developer:
        if request.method == 'POST':
            newgameform = AddGameForm(request.POST)
            if newgameform.is_valid():

                post = newgameform.save(commit=False)

                game.url = newgameform.cleaned_data['url']
                game.thumbnail = newgameform.cleaned_data['thumbnail']
                game.price = newgameform.cleaned_data['price']
                game.title = newgameform.cleaned_data['title']
                game.description = newgameform.cleaned_data['description']

                game.save()
                messages.success(
                    request, f'Your game: {post.title} was updated!')
                return redirect('/games', {'is_developer': is_developer})
        else:
            newgameform = AddGameForm()
        return render(request, 'developer/modify.html', {'form': newgameform, 'is_developer': is_developer, 'game': game})
    else:
        messages.warning(request, 'You are not a developer')
        return redirect('games')


@login_required
def delete(request, game_id):

    delete = Game.objects.get(pk=game_id)

    user = request.user
    is_developer = user.profile.is_developer
    if is_developer:
        games = user.profile.created_games.all()

        if delete in games:
            if request.method == 'POST':
                form = DeleteGame(request.POST, instance=delete)

                if form.is_valid():  # checks CSRF
                    delete.delete()
                    # wherever to go after deleting
                    return redirect("games")

            else:
                form = DeleteGame(instance=delete)

            template_vars = {'form': form}
            return render(request, 'developer/delete.html', template_vars)

    else:
        messages.warning(request, 'You are not a developer')
        return redirect('games')
