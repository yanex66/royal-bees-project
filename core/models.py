from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.text import slugify

class NewsItem(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    published_date = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    slug = models.SlugField(max_length=200, unique=True, blank=True, help_text="A short label for the news item, used in URLs. Will be auto-generated if left blank.")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_date']
        verbose_name = "News Item"
        verbose_name_plural = "News Items"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            original_slug = self.slug
            counter = 1
            queryset = NewsItem.objects.filter(slug=self.slug)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            while queryset.exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
                queryset = NewsItem.objects.filter(slug=self.slug)
                if self.pk:
                    queryset = queryset.exclude(pk=self.pk)
        super().save(*args, **kwargs)


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(blank=True, null=True, help_text="Leave blank if it's a single-day event or duration is not specific.")
    location = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(max_length=250, unique_for_date='start_datetime', blank=True, help_text="A short label for the event, used in URLs. Auto-generated if blank.")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_datetime']
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            original_slug = self.slug
            counter = 1
            queryset = Event.objects.filter(slug=self.slug, start_datetime__date=self.start_datetime.date())
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            while queryset.exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
                queryset = Event.objects.filter(slug=self.slug, start_datetime__date=self.start_datetime.date())
                if self.pk:
                    queryset = queryset.exclude(pk=self.pk)
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.start_datetime > timezone.now()

    @property
    def is_past(self):
        if self.end_datetime:
            return self.end_datetime < timezone.now()
        return self.start_datetime < timezone.now()


# --- MODEL FOR ADMISSIONS FORM ---
class AdmissionApplication(models.Model):
    applicant_name = models.CharField(max_length=255, verbose_name="Child's Name")
    date_of_birth = models.DateField()
    applying_grade = models.CharField(max_length=50, verbose_name="Class Applying For")
    parent_name = models.CharField(max_length=255, verbose_name="Parent's Name")
    parent_phone = models.CharField(max_length=20, verbose_name="Phone Number")
    parent_email = models.EmailField(verbose_name="Email Address")
    address = models.TextField()
    terms_agreed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.applicant_name} - {self.applying_grade}"
    
    class Meta:
        verbose_name = "Admission Application"
        verbose_name_plural = "Admission Applications"
        ordering = ['-submitted_at']


# --- MODEL FOR CONTACT US MESSAGES ---
class ContactMessage(models.Model):
    name = models.CharField(max_length=255, verbose_name="Sender's Name")
    email = models.EmailField(verbose_name="Email Address")
    message = models.TextField(verbose_name="Message Content")
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, verbose_name="Read Status")

    def __str__(self):
        return f"Message from {self.name}"
    
    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ['-submitted_at']


# --- MODEL FOR GALLERY ---
class GalleryImage(models.Model):
    image = models.ImageField(upload_to='gallery/') 
    caption = models.CharField(max_length=255, blank=True, help_text="Optional description of the photo")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.caption if self.caption else f"Gallery Photo #{self.id}"


# --- NEW MODEL FOR SCHOOL FEES PAYMENTS ---
class FeePayment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Successful', 'Successful'),
        ('Failed', 'Failed'),
    )

    student_name = models.CharField(max_length=255, verbose_name="Student's Name")
    admission_number = models.CharField(max_length=50, verbose_name="Admission Number")
    student_class = models.CharField(max_length=50, verbose_name="Class")
    parent_email = models.EmailField(help_text="Paystack receipt will be sent to this email")
    amount = models.PositiveIntegerField(help_text="Amount in Naira (₦)")
    
    paystack_reference = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Fee Payment"
        verbose_name_plural = "Fee Payments"

    def __str__(self):
        return f"{self.student_name} - ₦{self.amount} ({self.status})"