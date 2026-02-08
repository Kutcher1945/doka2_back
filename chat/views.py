from rest_framework.response import Response
from rest_framework.views import APIView

from .pusher import pusher_client
from django.shortcuts import render
import pika
from django.conf import settings
from django.http import HttpResponse
import json


def chat_room(request):
    return render(request, 'chat_room.html', {})


def send_message(request):
    if request.method == 'POST':
        message = request.POST.get('message', '')
        if message:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOSTNAME,
                    port=settings.RABBITMQ_PORT,
                    credentials=pika.credentials.PlainCredentials(
                        username=settings.RABBITMQ_USERNAME,
                        password=settings.RABBITMQ_PASSWORD
                    )
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue='chat')
            channel.basic_publish(
                exchange='',
                routing_key='chat',
                body=json.dumps({'message': message}),
            )
            connection.close()
    return HttpResponse('OK')


def receive_message(request):
    if request.method == 'GET':
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOSTNAME,
                port=settings.RABBITMQ_PORT,
                credentials=pika.credentials.PlainCredentials(
                    username=settings.RABBITMQ_USERNAME,
                    password=settings.RABBITMQ_PASSWORD
                )
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue='chat')
        method_frame, header_frame, body = channel.basic_get(queue='chat', auto_ack=True)
        if method_frame:
            message = json.loads(body)
            return HttpResponse(message['message'])
        else:
            return HttpResponse('')


class ChatAPIView(APIView):

    def post(self, request):
        pusher_client.trigger('chat', 'message', {
            'username': request.data['username'],
            'message': request.data['message'],
        })

        return Response([])
