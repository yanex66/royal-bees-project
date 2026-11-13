# Production deployment checklist

The Render service definition runs migrations and collects static files, but it does not provision school records or payment credentials.

## Render environment

Configure these values in the Render service dashboard (never commit them):

- `DJANGO_SECRET_KEY`: use a unique, generated value.
- `DJANGO_DEBUG`: `False`.
- `DJANGO_ALLOWED_HOSTS`: include the Render hostname and any custom domain.
- `DATABASE_URL`: use a persistent PostgreSQL database URL. Without it, Django falls back to SQLite, whose data can be lost when a Render free instance restarts or redeploys.
- `TEACHER_PORTAL_PASSWORD`: set a long, unique secret. Teacher access stays disabled if it is missing.
- `PAYSTACK_PUBLIC_KEY` and `PAYSTACK_SECRET_KEY`: configure a matching pair from the same Paystack environment. Test with test keys first; only use live keys after the school explicitly approves real charges.
- `EMAIL_USER` and `EMAIL_PASSWORD`: configure the mailbox used for admissions, contact messages, and receipts.
- `CLOUDINARY_URL`: configure the Cloudinary connection URL so uploaded gallery images persist across Render deploys and restarts. Add this as a secret environment variable in Render; do not commit or share it. Without it, gallery uploads use local filesystem storage and will not be available on the production site.

After changing environment variables, redeploy the service.

Do not enable HSTS for subdomains or browser preload on a shared Render hostname. Only opt in after moving to a domain whose subdomains you control and have confirmed are HTTPS-only.

## Required school data

In Django admin, create and verify:

1. The current academic session, marked current.
2. The school's terms and class levels.
3. Fee records for every class/term in the current session, with the approved fee amounts.
4. Students with unique IDs, active status, and the correct current class.

The fee payment page intentionally stays disabled until it can find a current session, fee options, and both Paystack keys. Do not enter placeholder or unapproved fee amounts.

## Before opening to families

- Confirm the academic calendar dates with the school office and update the calendar page before advertising dates.
- Test a Paystack test-mode payment from initiation through verification and receipt email.
- Check admissions and contact submissions in admin and verify email delivery.
- Confirm student results, teacher access, and media uploads with authorized staff.
- Ensure database backups and persistent media storage are configured. Render's local filesystem is not a permanent store on the free plan.
- After setting `CLOUDINARY_URL`, re-upload existing gallery images through Django admin. Existing database records only contain media paths; the original files on Render's temporary filesystem are not copied automatically to Cloudinary.
- Repeat the checks against the public domain after deployment.
