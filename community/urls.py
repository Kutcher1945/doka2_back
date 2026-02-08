from django.urls import include, path
from community.views import (
    FriendsListView,
    ReceivedFriendshipRequestsView,
    FindUserView,
    RequestFriendshipView,
    AcceptRequestView,
    RejectRequestView,
    RemoveFriendView,

)

urlpatterns = [
    path('friends/list/', FriendsListView.as_view()),
    path('friends/received_requests/', ReceivedFriendshipRequestsView.as_view()),
    path('friends/find/', FindUserView.as_view()),
    path('friends/request/', RequestFriendshipView.as_view()),
    path('friends/accept/', AcceptRequestView.as_view()),
    path('friends/reject/', RejectRequestView.as_view()),

    path('friends/remove/', RemoveFriendView.as_view())

]
