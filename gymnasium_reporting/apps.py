from django.apps import AppConfig
from openedx.core.djangoapps.plugins.constants import (
    ProjectType, SettingsType, PluginURLs, PluginSettings
)


class GymnasiumReportingConfig(AppConfig):
    """
    Provides application configuration for Gymnasium Reporting.
    """

    name = 'gymnasium_reporting'
    verbose_name = 'gymnasium_reporting'

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: u'gymnasium_reporting',
                PluginURLs.REGEX: u'^',
                PluginURLs.RELATIVE_PATH: u'urls',
            }
        },
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.COMMON: {
                    PluginSettings.RELATIVE_PATH: u'settings.common'
                },
            }
        }
    }