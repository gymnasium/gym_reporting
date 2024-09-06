import io
import re
import csv
import time
import os
import datetime
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

MARKET_MAPPING = {
    10: "Not Applicable",
    36: "Australia - Melbourne",
    39: "Australia - Sydney",
    40: "Canada - Toronto",
    47: "Canada - Vancouver",
    35: "France - Paris",
    115: "Germany",
    92: "Japan - Fukuoka",
    64: "Japan - Osaka",
    79: "Japan - Nagoya",
    44: "Japan - Tokyo",
    43: "Netherlands - Amsterdam",
    29: "UK - London",
    120: "USA - Alabama",
    122: "USA - Arkansas",
    23: "USA - Atlanta",
    60: "USA - Austin",
    46: "USA - Baltimore",
    102: "USA - Boise",
    10: "USA - Boston",
    61: "USA - Charlotte",
    14: "USA - Chicago",
    34: "USA - Connecticut",
    22: "USA - Dallas",
    27: "USA - Denver",
    24: "USA - Detroit",
    826: "USA - Houston",
    58: "USA - Indianapolis",
    116: "USA - Kentucky",
    13: "USA - Los Angeles",
    117: "USA - Louisiana",
    33: "USA - Miami",
    20: "USA - Minneapolis",
    118: "USA - Mississippi",
    807: "USA - Moline",
    30: "USA - New Jersey",
    11: "USA - New York City",
    51: "USA - Northern Virginia",
    32: "USA - Ohio",
    119: "USA - Oklahoma",
    19: "USA - Orange County",
    72: "USA - Orlando",
    121: "USA - Pensacola, FL",
    18: "USA - Philadelphia",
    31: "USA - Phoenix",
    41: "USA - Portland, OR",
    73: "USA - Providence",
    803: "USA - Raleigh/Durham",
    78: "USA - Richmond",
    16: "USA - San Diego",
    12: "USA - San Francisco",
    17: "USA - Seattle",
    15: "USA - Silicon Valley",
    37: "USA - St. Louis",
    68: "USA - Tampa",
    63: "USA - Tennessee",
    25: "USA - Washington, DC",
    881: "USA - Wisconsin",
}

def encode_for_csv(data):
    """
    Encodes all strings in a list for CSV output, ensuring Unicode strings are properly handled.
    """
    return [s.encode('utf-8') if isinstance(s, unicode) else s for s in data]

def save_locally(filename, content):
    """Saves content to a local file."""
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    file_path = os.path.join(reports_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(content.getvalue())
    print(f"Content saved to {file_path}")

def list_files(prefix, max_results=7):
    """List files in the local reports directory."""
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports', prefix)
    files = [f for f in os.listdir(reports_dir) if os.path.isfile(os.path.join(reports_dir, f))]
    
    def extract_datetime_from_filename(filename):
        match = re.search(r'_(\d{4}-\d{2}-\d{2}_\d{6})\.csv$', filename)
        if match:
            return datetime.datetime(*(time.strptime(match.group(1), '%Y-%m-%d_%H%M%S')[0:6]))
        return datetime.datetime.min
    
    files.sort(key=extract_datetime_from_filename, reverse=True)
    return [os.path.join(prefix, f) for f in files[:max_results]]

def generate_registration_report_csv():
    users = User.objects.select_related('profile', 'extrainfo').all()
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = 'registration_report_{}.csv'.format(current_datetime)
    destination_path = os.path.join('registrations', filename)
    content = io.BytesIO()
    writer = csv.writer(content)
    writer.writerow(['ID', 'Username', 'Email', 'Full Name', 'Date Joined', 'Market'])
    for user in users:
        try:
            fullname = user.profile.name
        except AttributeError:
            fullname = 'N/A'
        try:
            market_number = user.extrainfo.market
            market = MARKET_MAPPING.get(int(market_number), 'Unknown Market')
        except AttributeError:
            market = 'N/A'
        user_data = [
            user.id,
            user.username,
            user.email,
            fullname,
            user.date_joined.strftime('%Y-%m-%d'),
            market,
        ]
        writer.writerow(encode_for_csv(user_data))
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
    content = io.BytesIO()
    writer = csv.writer(content)
    writer.writerow(['Course ID', 'Course Name', 'User ID', 'Username', 'Email', 'Full Name', 'Enrollment Date', 'Final Score', 'Completion Date'])
    for enrollment in enrollments:
        enrollment_date = enrollment['created'].strftime('%Y-%m-%d') if enrollment['created'] else ''
        completion_date = enrollment['completion_date'].strftime('%Y-%m-%d') if enrollment.get('completion_date') else ''
        writer.writerow(encode_for_csv([
            enrollment['course_id'],
            enrollment['course__display_name'],
            enrollment['user_id'],
            enrollment['user__username'],
            enrollment['user__email'],
            enrollment.get('user__profile__name', 'N/A'),
            enrollment_date,
            enrollment.get('grade', 'N/A'),
            completion_date,
        ]))
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