from django.conf import settings
from django.core.files.storage import FileSystemStorage


def get_gallery_storage():
    if settings.CLOUDINARY_URL:
        from cloudinary_storage.storage import MediaCloudinaryStorage

        return MediaCloudinaryStorage()
    return FileSystemStorage()
