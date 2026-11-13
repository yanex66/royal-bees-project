from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Event, NewsItem


class StaticSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return [
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
        ]

    def location(self, item):
        return reverse(item)


class NewsSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return NewsItem.objects.all()

    def lastmod(self, item):
        return item.published_date

    def location(self, item):
        published = item.published_date
        return reverse(
            'news_detail',
            kwargs={
                'year': published.year,
                'month': published.month,
                'day': published.day,
                'slug': item.slug,
            },
        )


class EventSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Event.objects.all()

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        start = item.start_datetime
        return reverse(
            'event_detail',
            kwargs={
                'year': start.year,
                'month': start.month,
                'day': start.day,
                'slug': item.slug,
            },
        )
