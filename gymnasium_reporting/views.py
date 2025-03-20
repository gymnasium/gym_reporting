import io
import re
import csv
import time
import os
import datetime
import logging
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseRedirect
from django.db.models import OuterRef, Subquery, F
from django.core.exceptions import SuspiciousOperation
from django.conf import settings

from common.djangoapps.student.models import CourseEnrollment
from lms.djangoapps.certificates.models import GeneratedCertificate
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user

LOGGER = logging.getLogger(__name__)

MARKET_MAPPING = {
    "NA": "Not Applicable",
    36: "Melbourne",
    39: "Sydney",
    40: "Toronto",
    47: "Vancouver",
    35: "Paris",
    115: "Germany",
    92: "Fukuoka",
    64: "Osaka",
    79: "Nagoya",
    44: "Tokyo",
    43: "Amsterdam",
    29: "London",
    120: "Alabama",
    122: "Arkansas",
    23: "Atlanta",
    60: "Austin",
    46: "Baltimore",
    102: "Boise",
    10: "Boston",
    61: "Charlotte",
    14: "Chicago",
    34: "Connecticut",
    22: "Dallas",
    27: "Denver",
    24: "Detroit",
    826: "Houston",
    58: "Indianapolis",
    116: "Kentucky",
    13: "Los Angeles",
    117: "Louisiana",
    33: "Miami",
    20: "Minneapolis",
    118: "Mississippi",
    807: "Moline",
    30: "New Jersey",
    11: "New York City",
    51: "Northern Virginia",
    32: "Ohio",
    119: "Oklahoma",
    19: "Orange County",
    72: "Orlando",
    121: "Pensacola, FL",
    18: "Philadelphia",
    31: "Phoenix",
    41: "Portland, OR",
    73: "Providence",
    803: "Raleigh/Durham",
    78: "Richmond",
    16: "San Diego",
    12: "San Francisco",
    17: "Seattle",
    15: "Silicon Valley",
    37: "St. Louis",
    68: "Tampa",
    63: "Tennessee",
    25: "Washington, DC",
    881: "Wisconsin",
}

def ensure_dir_exists(directory):
    """Ensure that a directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)

def save_locally(filename, content):
    """Saves content to a local file."""
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    ensure_dir_exists(reports_dir)
    file_path = os.path.join(reports_dir, filename)
    with open(file_path, 'w', newline='', encoding='utf-8') as f:  # Change to text mode
        f.write(content.getvalue())
    LOGGER.info(f"Content saved to {file_path}")

def list_files(prefix, max_results=7):
    """List files in the local reports directory."""
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports', prefix)
    ensure_dir_exists(reports_dir)
    files = [f for f in os.listdir(reports_dir) if os.path.isfile(os.path.join(reports_dir, f))]
    
    def extract_datetime_from_filename(filename):
        match = re.search(r'_(\d{4}-\d{2}-\d{2}_\d{6})\.csv$', filename)
        if match:
            return datetime.datetime(*(time.strptime(match.group(1), '%Y-%m-%d_%H%M%S')[0:6]))
        return datetime.datetime.min
    
    files.sort(key=extract_datetime_from_filename, reverse=True)
    return [os.path.join(prefix, f) for f in files[:max_results]]

from io import StringIO  # Change this import

def generate_registration_report_csv():
    users = User.objects.select_related('profile', 'extrainfo').all()
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = 'registration_report_{}.csv'.format(current_datetime)
    destination_path = os.path.join('registrations', filename)
    content = StringIO()  # Change to StringIO
    writer = csv.writer(content)
    writer.writerow(['ID', 'Username', 'Email', 'Full Name', 'Date Joined', 'Market ID', 'Market Name', 'Country'])  # Remove encoding
    for user in users:
        # set initial defaults
        country = '(not set)'
        fullname = '(not set)'
        market_id = '(not set)'
        market_name = market_id
        try:
            if hasattr(user, 'profile'):
                if hasattr(user.profile, 'name') and user.profile.name != '':
                    try:
                        fullname = user.profile.name
                    except (AttributeError, KeyError) as e:
                        LOGGER.exception(e)
                if hasattr(user.profile, 'country') and user.profile.country != '':
                    try:
                        country = user.profile.country
                    except (AttributeError, KeyError) as e:
                        LOGGER.exception(e)
            if hasattr(user, 'extrainfo'):
                if hasattr(user.extrainfo, 'market') and user.extrainfo.market != '':
                    try:
                        market_id = user.extrainfo.market
                    except (AttributeError, KeyError) as e:
                        LOGGER.exception(e)
        except (AttributeError, KeyError) as e:
            LOGGER.exception(e)
        try:
            if market_id == 'NA' or market_id == '(not set)':
                market_name = market_id
            else:
                market_name = MARKET_MAPPING.get(int(market_id), '(unknown market)')
        except (AttributeError, KeyError, TypeError) as e:
            LOGGER.exception(e)
        user_data = [
            str(user.id),
            user.username,
            user.email,
            fullname,
            user.date_joined.strftime('%Y-%m-%d'),
            market_id,
            market_name,
            country,
        ]
        writer.writerow(user_data)
    content.seek(0)
    save_locally(destination_path, content)
    print('Registration report generated and saved locally.')

def generate_enrollment_report_csv():
    enrollments = CourseEnrollment.objects.filter(is_active=True).select_related(
        'user', 'course_overview'
    ).annotate(
        grade=Subquery(
            GeneratedCertificate.objects.filter(
                user_id=OuterRef('user_id'),
                course_id=OuterRef('course_id')
            ).values('grade')[:1]
        ),
        completion_date=Subquery(
            GeneratedCertificate.objects.filter(
                user_id=OuterRef('user_id'),
                course_id=OuterRef('course_id')
            ).values('created_date')[:1]
        )
    ).values(
        'course_id', 'course__display_name', 'user_id', 'user__username', 'user__email', 'user__profile__name', 'created', 'grade', 'completion_date'
    )
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = 'enrollment_report_{}.csv'.format(current_datetime)
    destination_path = os.path.join('enrollments', filename)
    content = StringIO()  # Change to StringIO
    writer = csv.writer(content)
    writer.writerow(['Course ID', 'Course Name', 'User ID', 'Username', 'Email', 'Full Name', 'Enrollment Date', 'Final Score', 'Completion Date'])  # Remove encoding
    for enrollment in enrollments:
        enrollment_date = enrollment['created'].strftime('%Y-%m-%d') if enrollment['created'] else ''
        completion_date = enrollment['completion_date'].strftime('%Y-%m-%d') if enrollment.get('completion_date') else ''
        writer.writerow([
            str(enrollment['course_id']),
            enrollment['course__display_name'],
            str(enrollment['user_id']),
            enrollment['user__username'],
            enrollment['user__email'],
            enrollment.get('user__profile__name', 'NA'),
            enrollment_date,
            str(enrollment.get('grade', 'NA')),
            completion_date,
        ])
    content.seek(0)
    save_locally(destination_path, content)
    print('Enrollment report generated and saved locally.')

def is_safe_path(file_path, base_dir):
    # Check if the path is safe to use
    return os.path.abspath(file_path).startswith(base_dir) and '..' not in file_path and '\x00' not in file_path

@login_required
def reporting_download(request):
    if not request.user.is_superuser:
        return redirect('/')

    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    registrations_prefix = 'registrations'
    enrollments_prefix = 'enrollments'
    
    # Ensure directories exist
    ensure_dir_exists(os.path.join(reports_dir, registrations_prefix))
    ensure_dir_exists(os.path.join(reports_dir, enrollments_prefix))
    
    # Fetch the latest 7 registration and enrollment reports
    registration_files = list_files(registrations_prefix)
    enrollment_files = list_files(enrollments_prefix)

    context = {
        'registration_files': registration_files,
        'enrollment_files': enrollment_files,
    }

    # Handle POST request: Generate reports
    if request.method == 'POST':
        if 'generate_registration' in request.POST:
            generate_registration_report_csv()
        elif 'generate_enrollment' in request.POST:
            generate_enrollment_report_csv()
        return HttpResponseRedirect(reverse('gymnasium_reporting:reporting_download'))

    # Handle GET request for file download
    if request.method == 'GET' and 'download' in request.GET:
        file_path = request.GET.get('download')
        full_path = os.path.join(reports_dir, file_path)
        if not is_safe_path(full_path, reports_dir):
            raise SuspiciousOperation('Invalid file path')
        return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
    
    return render(request, 'reporting_download.html', context)
