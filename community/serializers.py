from rest_framework import serializers

from authentication.models import CustomUser


class FriendsListSerializer(serializers.ModelSerializer):
    # Return id and username as separate fields — avoids the fragile "username@id" string
    # that breaks if a username contains '@'.
    status = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'status')

    def get_status(self, obj):
        return obj.get_online_status_display()


class RequestFriendshipSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
