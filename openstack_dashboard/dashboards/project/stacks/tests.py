# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.core.urlresolvers import reverse
from django.utils import unittest

from openstack_dashboard import api
from openstack_dashboard.test import helpers as test
from . import mappings
from .workflows import LaunchStack


class MockResource(object):
    def __init__(self, resource_type, physical_resource_id):
        self.resource_type = resource_type
        self.physical_resource_id = physical_resource_id


class MappingsTests(test.TestCase):

    def test_mappings(self):
        def assertMappingUrl(url, resource_type, physical_resource_id):
            self.assertEqual(url,
                mappings.resource_to_url(MockResource(
                    resource_type, physical_resource_id)))

        assertMappingUrl(
            '/project/networks/subnets/aaa/detail',
            'OS::Quantum::Subnet',
            'aaa')
        assertMappingUrl(
            None,
            'OS::Quantum::Subnet',
            None)
        assertMappingUrl(
            None,
            None,
            None)
        assertMappingUrl(
            None,
            'AWS::AutoScaling::LaunchConfiguration',
            'aaa')
        assertMappingUrl(
            '/project/instances/aaa/',
            'AWS::EC2::Instance',
            'aaa')
        assertMappingUrl(
            '/project/containers/aaa/',
            'OS::Swift::Container',
            'aaa')
        assertMappingUrl(
            None,
            'Foo::Bar::Baz',
            'aaa')

    def test_stack_output(self):
        self.assertEqual(u'foo', mappings.stack_output('foo'))
        self.assertEqual(u'', mappings.stack_output(None))

        self.assertEqual(
            u'<pre>[\n  "one", \n  "two", \n  "three"\n]</pre>',
            mappings.stack_output(['one', 'two', 'three']))
        self.assertEqual(
            u'<pre>{\n  "foo": "bar"\n}</pre>',
            mappings.stack_output({'foo': 'bar'}))

        self.assertEqual(
            u'<a href="http://www.example.com/foo" target="_blank">'
            'http://www.example.com/foo</a>',
            mappings.stack_output('http://www.example.com/foo'))


class LaunchStackTests(test.TestCase):

    @test.create_stubs({api.heat: ('stack_create', 'template_validate')})
    def test_launch_stack_workflow(self):
        self.mox.ReplayAll()

        url = reverse('horizon:project:stacks:launch')
        res = self.client.get(url)
        workflow = res.context['workflow']
        self.assertTemplateUsed(res, 'project/stacks/launch.html')
        self.assertEqual(workflow.name, LaunchStack.name)
        expected_objs = ['<SetTemplate: settemplateaction>',
                         '<SetParameters: setparametersaction>']
        self.assertQuerysetEqual(workflow.steps, expected_objs)
