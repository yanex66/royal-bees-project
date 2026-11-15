from whitenoise.storage import CompressedManifestStaticFilesStorage


class RoyalBeesStaticFilesStorage(CompressedManifestStaticFilesStorage):
    def stored_name(self, name):
        if name == 'vendor/bootswatch':
            return name
        return super().stored_name(name)
