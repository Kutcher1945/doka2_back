from authentication.models import CustomUser
from community import FriendshipStatuses
from community.models import Friendship
from community.serializers import FriendsListSerializer, RequestFriendshipSerializer
from django.db.models import Q
from django.http.response import Http404
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class FriendsListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FriendsListSerializer

    def get_queryset(self):
        user = self.request.user

        sent_friends = user.sent_friends.filter(status=FriendshipStatuses.APPROVED).values_list('addressee_user',
                                                                                                flat=True)
        received_friends = user.receive_friends.filter(status=FriendshipStatuses.APPROVED).values_list('requested_user',
                                                                                                       flat=True)
        users_list = list(sent_friends) + list(received_friends)
        return CustomUser.objects.filter(id__in=users_list)


class ReceivedFriendshipRequestsView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FriendsListSerializer

    def get_queryset(self):
        user = self.request.user
        received_recs_list = Friendship.objects.filter(addressee_user=user,
                                                       status=FriendshipStatuses.REQUESTED).values_list(
            'requested_user',
            flat=True)
        return CustomUser.objects.filter(id__in=received_recs_list)


class FindUserView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FriendsListSerializer
    queryset = CustomUser.objects.all()

    def get_object(self):
        request = self.request
        user_id = request.GET.get('user_id', None)
        user_id = user_id.split('@')[-1]
        if not user_id:
            raise Http404
        users = CustomUser.objects.filter(id=user_id)
        if not users.exists():
            raise Http404
        else:
            return users.last()


class RequestFriendshipView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        request_user = request.user
        user_id = user_id.split('@')[-1]
        addressee_user = CustomUser.objects.get(id=user_id)
        if Friendship.objects.filter(Q(
                Q(requested_user=request_user) & Q(addressee_user=addressee_user) | Q(addressee_user=request_user) & Q(
                    requested_user=addressee_user))
        ).filter(status=FriendshipStatuses.APPROVED).exists():
            return Response(status=400, data={"error": "Already in friend"})
        Friendship.objects.get_or_create(requested_user=request_user,
                                         addressee_user=addressee_user,
                                         status=FriendshipStatuses.REQUESTED)
        return Response(status=200)


class AcceptRequestView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id', None)
        user_id = user_id.split('@')[-1]
        request_user = request.user
        try:
            friendship = Friendship.objects.get(addressee_user=request_user,
                                                requested_user_id=user_id,
                                                status=FriendshipStatuses.REQUESTED)
        except Exception as e:
            return Response(status=404)
        friendship.status = FriendshipStatuses.APPROVED
        friendship.datetime_approve = timezone.now()
        friendship.save()
        return Response(status=200)


class RejectRequestView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id', None)
        user_id = user_id.split('@')[-1]
        request_user = request.user
        try:
            friendship = Friendship.objects.get(addressee_user=request_user,
                                                requested_user_id=user_id,
                                                status=FriendshipStatuses.REQUESTED)
        except Exception as e:
            return Response(status=404)
        friendship.status = FriendshipStatuses.REJECTED
        friendship.save()
        return Response(status=200)


class RemoveFriendView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id', None)
        user_id = user_id.split('@')[-1]
        request_user = request.user

        friendship = Friendship.objects.filter(Q(Q(addressee_user=request_user) & Q(requested_user_id=user_id)) |
                                               Q(Q(addressee_user_id=user_id) & Q(requested_user=request_user)),
                                               status=FriendshipStatuses.APPROVED)
        if not friendship.exists():
            raise Http404

        friendship = friendship.last()
        friendship.status = FriendshipStatuses.DELETED
        friendship.save()
        return Response(status=200)
