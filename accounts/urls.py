from django.conf.urls import url
from django.contrib.auth.views import LogoutView

from .views import (
    guest_register_view,
    RegisterView,
    LoginView,
    AccountHomeView,
    AccountEmailActivationView
)

urlpatterns = [
    url(r'^$', AccountHomeView.as_view(), name='home'),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),
    url(r'^register/$', RegisterView.as_view(), name='register'),
    url(r'^register/guest/$', guest_register_view, name='guest_register'),

    url(r'^email/confirm/(?P<key>[0-9A-Za-z]+)/$', AccountEmailActivationView.as_view(), name='email_activate'),
]
