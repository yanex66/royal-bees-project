from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# --- Academic Structure Models ---

class AcademicSession(models.Model):
    year = models.CharField(max_length=10, unique=True, help_text="e.g., 2024/2025")
    is_current = models.BooleanField(default=False, help_text="Mark if this is current.")

    class Meta:
        ordering = ['-year']

    def __str__(self):
        return f"{self.year}{' (Current)' if self.is_current else ''}"

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicSession.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Term(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text="First Term, Second Term, etc.")
    order = models.PositiveIntegerField(unique=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

# --- Global Fee Management ---

class ClassFee(models.Model):
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="fees")
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    examination_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    medical_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    development_levy = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('class_level', 'term', 'session')
        verbose_name = "Class Fee Configuration"

    @property
    def total_amount(self):
        return (self.tuition_fee + self.examination_fee + self.medical_fee + 
                self.development_levy + self.other_fees)

    def __str__(self):
        return f"{self.class_level.name} - {self.term.name} ({self.session.year})"


# --- People & Results ---

class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True, null=True)
    current_class = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    pin = models.CharField(max_length=10, blank=True, null=True)
    active = models.BooleanField(default=True)
    date_admitted = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['last_name', 'first_name']

    def get_full_name(self):
        if self.other_names:
            return f"{self.last_name}, {self.first_name} {self.other_names}"
        return f"{self.last_name}, {self.first_name}"

    def __str__(self):
        return f"{self.get_full_name()} ({self.student_id})"


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subject_code = models.CharField(max_length=20, blank=True, null=True, unique=True)

    def __str__(self):
        return self.name


class Result(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="results")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    class_level_at_time_of_result = models.ForeignKey(ClassLevel, on_delete=models.SET_NULL, null=True)
    
    test_score_1 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    test_score_2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    grade = models.CharField(max_length=5, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_recorded = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        t1 = self.test_score_1 or 0
        t2 = self.test_score_2 or 0
        ex = self.exam_score or 0
        self.total_score = t1 + t2 + ex
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Result for {self.student.first_name} - {self.subject.name}"


# --- Payment & Reviews ---

class FeePayment(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'), ('Successful', 'Successful'), ('Failed', 'Failed')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments", null=True)
    fee_config = models.ForeignKey(ClassFee, on_delete=models.SET_NULL, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    arrears_cleared = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    email = models.EmailField()
    paystack_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.last_name if self.student else 'Unknown'} - {self.amount_paid} ({self.status})"

class Testimonial(models.Model):
    """Stores parent reviews as seen in image_acec9f.png"""
    parent_name = models.CharField(max_length=100)
    parent_designation = models.CharField(max_length=100, help_text="e.g. Parent of Nursery 2 Pupil")
    review_text = models.TextField()
    is_approved = models.BooleanField(default=False)
    date_submitted = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_submitted']

    def __str__(self):
        return f"Review by {self.parent_name}"