from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

from .models import Event, NewsItem


class PublicLaunchSmokeTests(TestCase):
    def test_authenticated_admin_index_and_password_change_render(self):
        admin_user = User.objects.create_superuser(
            username='admin-test',
            email='admin-test@example.com',
            password='test-only-password',
        )
        self.client.force_login(admin_user)

        for path in ('/admin/', '/admin/password_change/', '/admin/core/galleryimage/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_public_page_routes_render(self):
        routes = (
            'home',
            'about',
            'contact_us',
            'news_list',
            'event_list',
            'academic_calendar',
            'academics_overview',
            'curriculum',
            'departments',
            'admissions',
            'gallery',
            'results:pay_fees',
            'results:check_results',
        )

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)

    def test_homepage_renders_only_unique_testimonials(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.content.count(b'class="testimonial-item"'), 6)
        self.assertEqual(
            response.content.count(b'Royal Bees Schools has been a blessing to my family'),
            1,
        )

    def test_homepage_read_more_links_to_news_detail(self):
        news_item = NewsItem.objects.create(
            title='Confirmed school update',
            content='Verified announcement text.',
            slug='confirmed-school-update',
        )

        response = self.client.get(reverse('home'))
        detail_url = (
            f'/news/{news_item.published_date.year}/'
            f'{news_item.published_date.month:02d}/'
            f'{news_item.published_date.day:02d}/{news_item.slug}/'
        )

        self.assertContains(response, f'href="{detail_url}"')

    def test_news_page_displays_existing_news_records(self):
        NewsItem.objects.create(
            title='Existing school announcement',
            content='Verified announcement text.',
            slug='existing-school-announcement',
        )

        response = self.client.get(reverse('news_list'))

        self.assertContains(response, 'Existing school announcement')

    def test_events_page_displays_existing_upcoming_and_past_events(self):
        now = timezone.now()
        Event.objects.create(
            title='Existing upcoming event',
            slug='existing-upcoming-event',
            start_datetime=now + timedelta(days=1),
        )
        Event.objects.create(
            title='Existing past event',
            slug='existing-past-event',
            start_datetime=now - timedelta(days=1),
        )
        ongoing_event = Event.objects.create(
            title='Existing ongoing event',
            slug='existing-ongoing-event',
            start_datetime=now - timedelta(hours=1),
            end_datetime=now + timedelta(hours=1),
        )

        response = self.client.get(reverse('event_list'))

        self.assertContains(response, 'Existing upcoming event')
        self.assertContains(response, 'Existing past event')
        self.assertIn(ongoing_event, response.context['upcoming_events'])
        self.assertNotIn(ongoing_event, response.context['past_events'])
        self.assertTrue(ongoing_event.is_upcoming)
        self.assertFalse(ongoing_event.is_past)

        homepage_response = self.client.get(reverse('home'))
        self.assertIn(ongoing_event, homepage_response.context['upcoming_events'])

    def test_academic_calendar_renders(self):
        response = self.client.get(reverse('academic_calendar'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Academic Calendar')
        self.assertContains(response, 'First Term')


class TeacherGateTests(TestCase):
    @override_settings(TEACHER_PORTAL_PASSWORD='')
    def test_teacher_gate_fails_closed_without_configured_password(self):
        response = self.client.get(reverse('teacher_gate'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher access is temporarily unavailable')

        response = self.client.post(reverse('teacher_gate'), {'admin_password': 'anything'})

        self.assertRedirects(response, reverse('teacher_gate'), fetch_redirect_response=False)
        self.assertNotIn('is_teacher', self.client.session)

    @override_settings(TEACHER_PORTAL_PASSWORD='a-test-only-password')
    def test_configured_teacher_can_enter_portal(self):
        response = self.client.post(
            reverse('teacher_gate'),
            {'admin_password': 'a-test-only-password'},
        )

        self.assertRedirects(
            response,
            reverse('results:teacher_search_student'),
            fetch_redirect_response=False,
        )
        self.assertTrue(self.client.session['is_teacher'])
