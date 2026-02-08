from rest_framework import serializers

from authentication.models import CustomUser


class FriendsListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id',
            'username',
            'status'
        )

    def get_status(self, obj):
        return obj.get_online_status_display()

    def get_id(self, obj):
        return f"{obj.username}@{obj.id}"


class RequestFriendshipSerializer(serializers.Serializer):
    user_id = serializers.CharField()
