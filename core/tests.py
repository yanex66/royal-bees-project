from django.test import TestCase, override_settings
from django.urls import reverse


class PublicLaunchSmokeTests(TestCase):
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
