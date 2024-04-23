# Gymnasium Reporting Plugin

## Introduction
This repository contains a plugin for Open edX that adds a new URL to the platform `/reporting/download` to provide registrations and enrollments reports. The URL is only accessible to superusers of the platofmr and when the user is not authenticated and not superuser they shouldn't see this page.


## Features
- Generate CSV reports for user registrations with custom market field.
- Generate CSV reports for course enrollments with detailed user and course information.
- When user generates a report, It uploades the csv file to GCS
- Download reports directly from Google Cloud Storage.
- View and download the latest generated reports from the Open edX interface.

## Prerequisites
- Open edX Hawthorn.
- Python 2.7 and Django 1.11.18.

## Installation
Activate Open edX environment variable and install the repo

```bash
sudo su edxapp -s /bin/bash
source /edx/app/edxapp/edxapp_env
cd /edx/app/edxapp/edx-platform/
pip install -e git+https://github.com/gymnasium/gym_reporting@main#egg=gymnasium-reporting
```

## Usage
1. Navigate to `/reporting/downloads` in your Open edX LMS.
2. Use the "Generate New Registration Report" and "Generate New Enrollment Report" buttons to create reports.
3. Download the latest reports from the displayed list.

## Support
For support and bug reports, please [submit an issue](https://github.com/gymnasium/gym_reporting/issues) in this repository.

## Author
- [Amir Tadrisi](amirtds@gmail.com)