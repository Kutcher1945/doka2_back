import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.roomGroupName = 'group_chat_gfg'
        await self.channel_layer.group_add(
            self.roomGroupName,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'roomGroupName'):
            await self.channel_layer.group_discard(
                self.roomGroupName,
                self.channel_name,
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        # Username always comes from the authenticated session, never from client
        username = self.scope['user'].username
        await self.channel_layer.group_send(
            self.roomGroupName, {
                'type': 'sendMessage',
                'message': message,
                'username': username,
            })

    async def sendMessage(self, event):
        message = event['message']
        username = event['username']
        await self.send(text_data=json.dumps({'message': message, 'username': username}))
