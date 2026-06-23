from django.db import models

class Testimonial(models.Model):
    student_name = models.CharField(max_length=150)
    student_photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, help_text="Rating 1-5")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.rating} Stars"
