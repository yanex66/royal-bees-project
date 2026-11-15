from django.contrib import admin
from django.utils.html import format_html
from .payment_utils import get_fee_balances
from .models import (
    PaymentConfiguration, AcademicSession, Term, ClassLevel, ClassFee,
    Student, Subject, Result, FeePayment
)

# --- INLINES (For "One-Page" Management) ---

class StudentInline(admin.TabularInline):
    """Allows viewing students directly inside the ClassLevel page."""
    model = Student
    extra = 0
    # Removed 'collapse' so the list is always visible
    fields = ('student_id', 'last_name', 'first_name', 'active')
    readonly_fields = ('student_id', 'last_name', 'first_name')
    show_change_link = True
    can_delete = False
    verbose_name_plural = "Quick Student Roster"

class ClassFeeInline(admin.TabularInline):
    """Shows the fee breakdown inside the ClassLevel page."""
    model = ClassFee
    extra = 0
    fields = ('term', 'session', 'tuition_fee', 'total_amount')
    readonly_fields = ('total_amount',)

# --- ADMIN CLASSES ---

@admin.register(PaymentConfiguration)
class PaymentConfigurationAdmin(admin.ModelAdmin):
    fields = ('minimum_payment_amount', 'processing_fee')
    list_display = ('minimum_payment_amount', 'processing_fee')

    def has_add_permission(self, request):
        return not PaymentConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ('year', 'is_current')
    list_editable = ('is_current',)
    list_filter = ('is_current',)

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order',)

@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    # Added student_count to help you see if students are linked correctly
    list_display = ('name', 'student_count')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [StudentInline, ClassFeeInline]

    def student_count(self, obj):
        """Returns the number of students currently in this class."""
        return obj.student_set.count()
    
    student_count.short_description = "Total Students"

@admin.register(ClassFee)
class ClassFeeAdmin(admin.ModelAdmin):
    list_display = ('class_level', 'term', 'session', 'tuition_fee', 'total_amount')
    list_filter = ('class_level', 'term', 'session')
    fieldsets = (
        ('Academic Period', {
            'fields': (('class_level', 'term', 'session'),)
        }),
        ('Fee Structure (₦)', {
            'fields': (
                ('tuition_fee', 'examination_fee'), 
                ('medical_fee', 'development_levy'), 
                'other_fees'
            )
        }),
    )

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'student_id', 'current_class', 'payment_status', 'active')
    list_filter = ('current_class', 'active')
    search_fields = ('first_name', 'last_name', 'student_id')
    list_editable = ('current_class', 'active')
    
    fieldsets = (
        ('Identification', {
            'fields': (('first_name', 'last_name'), 'other_names', ('student_id', 'photo'))
        }),
        ('School Assignment', {
            'fields': (('current_class', 'active'), ('pin', 'date_admitted'))
        }),
        ('Personal Details', {
            'classes': ('collapse',),
            'fields': ('date_of_birth',),
        }),
    )
    readonly_fields = ('date_admitted',)

    def payment_status(self, obj):
        """Displays whether current-session fees are unpaid, partial, or paid."""
        current_session = AcademicSession.objects.filter(is_current=True).first()
        if not current_session or not obj.current_class_id:
            return "N/A"

        fee_configs, balances = get_fee_balances(obj, current_session)
        total_due = sum(config.total_amount for config in fee_configs)
        if total_due <= 0:
            return "N/A"

        outstanding = sum(balances.values())
        if outstanding <= 0:
            label, color = 'PAID', '#28a745'
        elif outstanding < total_due:
            label, color = 'PARTIAL', '#d39e00'
        else:
            label, color = 'OWING', '#dc3545'

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 12px; border-radius: 12px; font-weight: bold; font-size: 10px;">{}</span>',
            color,
            label,
        )
    
    payment_status.short_description = 'Payment'

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject_code')
    search_fields = ('name', 'subject_code')

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'term', 'total_score', 'grade')
    list_filter = ('academic_session', 'term', 'grade')
    autocomplete_fields = ['student', 'subject']
    
    fieldsets = (
        ('Academic Metadata', {
            'fields': (('student', 'subject'), ('academic_session', 'term'))
        }),
        ('Grading System', {
            'fields': (('test_score_1', 'test_score_2', 'exam_score'), ('total_score', 'grade'))
        }),
        ('Staff Comments', {
            'fields': ('remarks',)
        }),
    )
    readonly_fields = ('total_score', 'grade')

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount_paid', 'processing_fee', 'total_transaction_amount', 'status', 'created_at')
    list_filter = ('status', 'fee_config__term')
    search_fields = ('student__last_name', 'paystack_reference')

    @admin.display(description='Total Charged')
    def total_transaction_amount(self, obj):
        return obj.total_transaction_amount
    
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False