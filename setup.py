from setuptools import setup

setup(
    name='gymnasium_reporting',
    version='0.0.1',
    license='MIT',
    description='Reporting and data retrieval for Open edX',
    entry_points={
        'lms.djangoapp': [
            'gymnasium_reporting = gymnasium_reporting.apps:GymnasiumReportingConfig',
        ],
},
)