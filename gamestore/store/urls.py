from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.games, name='store-home'),
    path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
         views.activate, name='activate'),
    path('games/', views.games, name='games'),
    path('games/<int:game_id>/', views.game, name='game'),
    path('games/<int:game_id>/score', views.save_score, name='save_score'),
    path('games/<int:game_id>/save', views.save_game, name='save_game'),
    path('games/<int:game_id>/load', views.load_game, name='load_game'),
    path('games/new/', views.add_new, name='add_game'),
    path('games/<int:game_id>/modify', views.modify, name='modify'),
    path('games/<int:game_id>/delete', views.delete, name='delete'),
    path('shop/', views.shop, name='shop'),
    path('shop/<int:game_id>/', views.buy, name="buy"),
    path('shop/payment/', views.buy_response, name="buy_response")
]
