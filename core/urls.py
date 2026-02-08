"""cybert_baack URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from .swagger import swagger_urlpatterns

urlpatterns = [
    path("auth/", include('authentication.urls')),
    path('', include('djoser.urls.authtoken')),
    path('admin/', admin.site.urls),
    path('dota/', include('dota.urls')),
    # path('paybox/', include('paybox.urls')),
    path('monetix/', include('payments.monetix.urls')),
    path('community/', include('community.urls')),
    path('achievements/', include('achievements.urls')),
    path('api/', include('chat.urls')),
    path('site-status/', include('sitestatus.urls'))
]
urlpatterns += swagger_urlpatterns

urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
