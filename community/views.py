from authentication.models import CustomUser
from community import FriendshipStatuses
from community.models import Friendship
from community.serializers import FriendsListSerializer, RequestFriendshipSerializer
from django.db.models import Q
from django.http.response import Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class FriendsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendsListSerializer

    def get_queryset(self):
        user = self.request.user
        sent = user.sent_friends.filter(status=FriendshipStatuses.APPROVED).values_list('addressee_user', flat=True)
        received = user.receive_friends.filter(status=FriendshipStatuses.APPROVED).values_list('requested_user', flat=True)
        return CustomUser.objects.filter(id__in=list(sent) + list(received))


class ReceivedFriendshipRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendsListSerializer

    def get_queryset(self):
        user = self.request.user
        ids = Friendship.objects.filter(
            addressee_user=user, status=FriendshipStatuses.REQUESTED
        ).values_list('requested_user', flat=True)
        return CustomUser.objects.filter(id__in=ids)


class FindUserView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendsListSerializer
    queryset = CustomUser.objects.all()

    def get_object(self):
        user_id = self.request.GET.get('user_id')
        if not user_id:
            raise Http404
        try:
            return CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            raise Http404


class RequestFriendshipView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        try:
            addressee = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        already_friends = Friendship.objects.filter(
            Q(requested_user=request.user, addressee_user=addressee) |
            Q(requested_user=addressee, addressee_user=request.user),
            status=FriendshipStatuses.APPROVED,
        ).exists()
        if already_friends:
            return Response({'error': 'Already friends.'}, status=status.HTTP_400_BAD_REQUEST)

        Friendship.objects.get_or_create(
            requested_user=request.user,
            addressee_user=addressee,
            status=FriendshipStatuses.REQUESTED,
        )
        return Response(status=status.HTTP_200_OK)


class AcceptRequestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        try:
            friendship = Friendship.objects.get(
                addressee_user=request.user,
                requested_user_id=user_id,
                status=FriendshipStatuses.REQUESTED,
            )
        except Friendship.DoesNotExist:
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

        friendship.status = FriendshipStatuses.APPROVED
        friendship.datetime_approve = timezone.now()
        friendship.save()
        return Response(status=status.HTTP_200_OK)


class RejectRequestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        try:
            friendship = Friendship.objects.get(
                addressee_user=request.user,
                requested_user_id=user_id,
                status=FriendshipStatuses.REQUESTED,
            )
        except Friendship.DoesNotExist:
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

        friendship.status = FriendshipStatuses.REJECTED
        friendship.save()
        return Response(status=status.HTTP_200_OK)


class RemoveFriendView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestFriendshipSerializer

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        friendship = Friendship.objects.filter(
            Q(addressee_user=request.user, requested_user_id=user_id) |
            Q(requested_user=request.user, addressee_user_id=user_id),
            status=FriendshipStatuses.APPROVED,
        ).last()

        if not friendship:
            raise Http404

        friendship.status = FriendshipStatuses.DELETED
        friendship.save()
        return Response(status=status.HTTP_200_OK)
