from setuptools import setup, find_packages

setup(
    name='gymnasium_reporting',
    version='0.0.3',
    license='MIT',
    description='Reporting and data retrieval for Open edX',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'gymnasium_reporting': ['templates/*.html', 'templates/**/*.html'],
    },
    entry_points={
        'lms.djangoapp': [
            'gymnasium_reporting = gymnasium_reporting.apps:GymnasiumReportingConfig',
        ],
},
)
