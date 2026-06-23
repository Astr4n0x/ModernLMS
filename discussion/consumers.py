import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message
from courses.models import Course

class DiscussionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.course_id = self.scope['url_route']['kwargs']['course_id']
        self.room_group_name = f'discussion_{self.course_id}'

        # Ensure user is authenticated
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
            
        # TODO: verify user is enrolled or is teacher
            
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json.get('message', '')
        attachment_url = text_data_json.get('attachment_url', '')

        # Save message
        if message_content or attachment_url:
            msg = await self.save_message(message_content, attachment_url)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': msg.content,
                    'attachment_url': attachment_url,
                    'user_id': msg.user.user_id,
                    'user_name': msg.user.get_full_name() or msg.user.user_id,
                    'is_teacher': msg.user.is_teacher(),
                    'created_at': msg.created_at.strftime("%I:%M %p")
                }
            )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'attachment_url': event.get('attachment_url', ''),
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_teacher': event['is_teacher'],
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def save_message(self, content, attachment_url):
        # We don't save attachment here because the file is uploaded via HTTP POST separately
        # The attachment_url is just to broadcast the URL of the already uploaded file.
        # But we could fetch the message by attachment_url later, or we can just save it. 
        # Actually, in HTTP upload view, we will just broadcast directly, 
        # but if we upload via HTTP and it creates the Message object, 
        # we don't need to save again here.
        # Wait, if this receive gets text with attachment_url, it means standard text chat.
        # So we just save the text content.
        # If it's an HTTP upload, the HTTP view will trigger `group_send` directly.
        course = Course.objects.get(id=self.course_id)
        msg_obj = Message.objects.create(
            course=course,
            user=self.scope["user"],
            content=content
        )
        return msg_obj
