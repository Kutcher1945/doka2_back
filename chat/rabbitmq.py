import pika
from django.conf import settings

# Connect to RabbitMQ
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

# Create a channel
channel = connection.channel()

# Declare the queue
channel.queue_declare(queue='chat')

# Bind the queue to the exchange
channel.queue_bind(queue='chat', exchange='')

# Set up a consumer on the queue
channel.basic_consume(queue='chat', on_message_callback=handle_message, auto_ack=True)

# Define the message handler
def handle_message(channel, method, properties, body):
    # Handle the message here
    pass
