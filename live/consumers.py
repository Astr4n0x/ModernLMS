import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from courses.models import ContentNode
from .models import LiveComment

class LiveClassConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.node_id = self.scope['url_route']['kwargs']['node_id']
        self.room_group_name = f'live_class_{self.node_id}'
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        new_count = await self.increment_viewer_count()
        if new_count is not None:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'viewer_count_update',
                    'count': new_count
                }
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            new_count = await self.decrement_viewer_count()
            if new_count is not None:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'viewer_count_update',
                        'count': new_count
                    }
                )

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'comment':
                text = text_data_json.get('text', '').strip()
                if not text:
                    return

                comment_data = await self.save_comment(text)
                if comment_data:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'new_comment',
                            'comment': comment_data
                        }
                    )
        except json.JSONDecodeError:
            pass

    async def viewer_count_update(self, event):
        count = event['count']
        await self.send(text_data=json.dumps({
            'type': 'viewer_count',
            'count': count
        }))

    async def new_comment(self, event):
        comment = event['comment']
        await self.send(text_data=json.dumps({
            'type': 'comment',
            'comment': comment
        }))

    @database_sync_to_async
    def increment_viewer_count(self):
        try:
            node = ContentNode.objects.get(pk=self.node_id, node_type='class')
            session = node.live_sessions_new.filter(is_live=True).first()
            if session:
                session.viewer_count += 1
                session.save(update_fields=['viewer_count'])
                return session.viewer_count
        except ContentNode.DoesNotExist:
            pass
        return None

    @database_sync_to_async
    def decrement_viewer_count(self):
        try:
            node = ContentNode.objects.get(pk=self.node_id, node_type='class')
            session = node.live_sessions_new.filter(is_live=True).first()
            if session:
                if session.viewer_count > 0:
                    session.viewer_count -= 1
                    session.save(update_fields=['viewer_count'])
                return session.viewer_count
        except ContentNode.DoesNotExist:
            pass
        return None

    @database_sync_to_async
    def save_comment(self, text):
        try:
            node = ContentNode.objects.get(pk=self.node_id, node_type='class')
            session = node.live_sessions_new.filter(is_live=True).first()
            if session:
                comment = LiveComment.objects.create(
                    session=session,
                    author=self.user,
                    text=text
                )
                return {
                    'id': comment.id,
                    'author': comment.author.get_full_name() or comment.author.user_id,
                    'text': comment.text,
                    'timestamp': comment.timestamp.isoformat(),
                    'time_display': comment.timestamp.strftime('%H:%M'),
                }
        except ContentNode.DoesNotExist:
            pass
        return None
