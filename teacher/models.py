from django.db import models


FILE_TYPE_CHOICES = [
    ('pdf', 'PDF'),
    ('slide', 'Slide'),
    ('note', 'Note'),
    ('link', 'External Link'),
    ('other', 'Other'),
]


class Attachment(models.Model):

    content_node = models.ForeignKey('courses.ContentNode', on_delete=models.CASCADE, related_name='attachments_new', null=True, blank=True)
    name = models.CharField(max_length=300)
    file = models.FileField(upload_to='attachments/%Y/%m/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_url(self):
        if self.file:
            return self.file.url
        return self.external_url

    def get_icon(self):
        icons = {
            'pdf': 'fa-file-pdf',
            'slide': 'fa-file-powerpoint',
            'note': 'fa-file-alt',
            'link': 'fa-external-link-alt',
            'other': 'fa-file',
        }
        return icons.get(self.file_type, 'fa-file')

    def __str__(self):
        return self.name
