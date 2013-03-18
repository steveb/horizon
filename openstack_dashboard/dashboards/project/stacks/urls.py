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

from django.conf.urls.defaults import patterns, url

from .views import DetailView, IndexView, LaunchStackView, ResourceView

urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^launch$', LaunchStackView.as_view(), name='launch'),
    url(r'^stack/(?P<stack_id>[^/]+)/$',
                      DetailView.as_view(), name='detail'),
    url(r'^stack/(?P<stack_id>[^/]+)/(?P<resource_name>[^/]+)/$',
                      ResourceView.as_view(), name='resource'),
)
