#!/usr/bin/env python
# -*- coding: utf-8 -*-

from corehq.apps.commtrack.tests.util import bootstrap_domain
from django.test import TestCase
from corehq.apps.locations.models import make_location, LocationType
from corehq.apps.locations.tests.util import delete_all_locations


class SiteCodeTest(TestCase):

    domain = 'test-site-code'

    def setUp(self):
        self.project = bootstrap_domain(self.domain)
        LocationType(domain=self.domain, name='type').save()

    def tearDown(self):
        self.project.delete()
        delete_all_locations()

    def testSimpleName(self):
        location = make_location(
            name="Some Location",
            domain=self.domain,
            location_type="type"
        )

        location.save()

        self.assertEqual(location.site_code, 'some_location')

    def testOtherCharacters(self):
        location = make_location(
            name=u"Somé$ #Location (Old)",
            domain=self.domain,
            location_type="type"
        )

        location.save()

        self.assertEqual(location.site_code, 'some_location_old')

    def testDoesntDuplicate(self):
        location = make_location(
            name="Location",
            domain=self.domain,
            location_type="type"
        )

        location.save()

        self.assertEqual(location.site_code, 'location')

        location = make_location(
            name="Location",
            domain=self.domain,
            location_type="type"
        )

        location.save()

        self.assertEqual(location.site_code, 'location1')
