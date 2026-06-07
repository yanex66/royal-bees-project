from django.contrib import admin
from django.utils.html import format_html # Needed for image previews
from .models import NewsItem, Event, AdmissionApplication, ContactMessage, GalleryImage

# --- ADMIN CONFIGURATION FOR NEWS ---
@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_date', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('published_date', 'author')


# --- ADMIN CONFIGURATION FOR EVENTS ---
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_datetime', 'end_datetime', 'location', 'is_upcoming')
    list_filter = ('start_datetime', 'location')
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'start_datetime'
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'location')
        }),
        ('Date & Time Information', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Audit Information', {
            'classes': ('collapse',), # Make this section collapsible
            'fields': ('created_by',) # created_at and updated_at are auto
        }),
    )

    def get_queryset(self, request):
        # Optimize fetching created_by user
        return super().get_queryset(request).select_related('created_by')


# --- ADMIN CONFIGURATION FOR ADMISSIONS ---
@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    # Columns shown in the main list view
    list_display = ('applicant_name', 'applying_grade', 'parent_name', 'parent_phone', 'submitted_at')
    
    # Adds a search bar at the top (search by child or parent name, phone, or email)
    search_fields = ('applicant_name', 'parent_name', 'parent_phone', 'parent_email')
    
    # Adds a filter sidebar on the right
    list_filter = ('applying_grade', 'submitted_at')
    
    # Prevents the submission timestamp from being accidentally edited
    readonly_fields = ('submitted_at',)
    
    # Organizes the detail page into clean, logical sections
    fieldsets = (
        ('Student Information', {
            'fields': ('applicant_name', 'date_of_birth', 'applying_grade')
        }),
        ('Parent/Guardian Information', {
            'fields': ('parent_name', 'parent_phone', 'parent_email', 'address')
        }),
        ('Application Meta', {
            'fields': ('terms_agreed', 'submitted_at'),
            'classes': ('collapse',), # Keeps the legal stuff neatly tucked away
        }),
    )


# --- ADMIN CONFIGURATION FOR CONTACT MESSAGES ---
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    # Shows who sent it, when, and if you've read it yet
    list_display = ('name', 'email', 'submitted_at', 'is_read')
    
    # Filter by unread messages or by date
    list_filter = ('is_read', 'submitted_at')
    
    # Search by name, email, or words inside the message
    search_fields = ('name', 'email', 'message')
    
    # Prevents accidental edits to what the user actually sent
    readonly_fields = ('name', 'email', 'message', 'submitted_at')
    
    # Let's you check the "Is read" box directly from the list view without opening the message!
    list_editable = ('is_read',)


# --- ADMIN CONFIGURATION FOR GALLERY ---
@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    # Shows the ID, a mini image preview, the caption, and the upload date
    list_display = ('id', 'image_preview', 'caption', 'uploaded_at')
    search_fields = ('caption',)
    readonly_fields = ('uploaded_at', 'image_preview_large')

    # This creates a small thumbnail for the main list view
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 8px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'

    # This creates a larger preview when you click into a specific photo
    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 300px; height: auto; border-radius: 10px;" />', obj.image.url)
        return "No Image"
    image_preview_large.short_description = 'Current Image'
    
    fieldsets = (
        (None, {
            'fields': ('image', 'image_preview_large', 'caption')
        }),
    ) 