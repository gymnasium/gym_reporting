import io
import re
import csv
import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.db.models import OuterRef, Subquery, F
from django.core.exceptions import SuspiciousOperation

from student.models import CourseEnrollment
from lms.djangoapps.certificates.models import GeneratedCertificate
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.user_api.accounts.image_helpers import get_profile_image_urls_for_user
from google.cloud import storage

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

def upload_to_gcs(bucket_name, destination_blob_name, content, json_key_path):
    """Uploads content to the bucket."""
    storage_client = storage.Client.from_service_account_json(json_key_path)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(content.getvalue(), content_type='text/csv')
    print("Content uploaded to {}.".format(destination_blob_name))

def list_files(bucket_name, prefix, json_key_path, max_results=15):
    """List files in a specific GCS bucket using a service account key."""
    # Create a storage client using the service account key
    storage_client = storage.Client.from_service_account_json(json_key_path)
    # Get the bucket
    bucket = storage_client.bucket(bucket_name)
    # List blobs in the specified bucket with the given prefix
    blobs = bucket.list_blobs(prefix=prefix, max_results=max_results)
    return [blob.name for blob in blobs]

def download_gcs_file(bucket_name, blob_name, json_key_path):
    """Streams a file from GCS to the user."""
    storage_client = storage.Client.from_service_account_json(json_key_path)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    response = StreamingHttpResponse(blob.download_as_string())
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(os.path.basename(blob_name))
    return response

def generate_registration_report_csv():
    users = User.objects.select_related('profile', 'extrainfo').all()
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = 'registration_report_{}.csv'.format(current_datetime)
    destination_blob_name = 'reports/registrations/{}'.format(filename)
    # Using BytesIO to write CSV content in-memory
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
    # Reset the cursor of the content
    content.seek(0)
    # Now upload the content to GCS
    json_key_path = '/etc/gcp/service_key.json'
    bucket_name = 'prod-hawthorn-gymnasium-backups'
    upload_to_gcs(bucket_name, destination_blob_name, content, json_key_path)
    print('Registration report generated and uploaded.')

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
    destination_blob_name = 'reports/enrollments/{}'.format(filename)
    # Using BytesIO to hold CSV content in memory
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
            enrollment.get('user__profile__name', 'N/A'),  # Assuming profile name might be missing
            enrollment_date,
            enrollment.get('grade', 'N/A'),  # Assuming grade might be missing
            completion_date,
        ]))
    # Reset the content cursor to the beginning
    content.seek(0)
    # Upload the content to GCS
    json_key_path = '/etc/gcp/service_key.json'  # Ensure correct path
    bucket_name = 'prod-hawthorn-gymnasium-backups'
    upload_to_gcs(bucket_name, destination_blob_name, content, json_key_path)
    print('Enrollment report generated and uploaded.')

def is_safe_path(blob_name, path_prefix):
    # Check if the path is safe to use
    return blob_name.startswith(path_prefix) and '..' not in blob_name and '\x00' not in blob_name

@login_required
def reporting_download(request):
    if not request.user.is_superuser:
        return redirect('/')

    json_key_path = '/etc/gcp/service_key.json'
    bucket_name = 'prod-hawthorn-gymnasium-backups'
    registrations_prefix = 'reports/registrations/'
    enrollments_prefix = 'reports/enrollments/'
    
    # Fetch the latest 15 registration and enrollment reports
    registration_files = list_files(bucket_name, registrations_prefix, json_key_path)
    enrollment_files = list_files(bucket_name, enrollments_prefix, json_key_path)

    context = {
        'bucket_name': bucket_name,
        'registration_files': registration_files,
        'enrollment_files': enrollment_files,
    }

    # Generate reports if the respective button is clicked
    if request.method == 'POST':
        if 'generate_registration' in request.POST:
            generate_registration_report_csv()
        elif 'generate_enrollment' in request.POST:
            generate_enrollment_report_csv()

    if request.method == 'GET' and 'download' in request.GET:
        blob_name = request.GET.get('download')
        
        # Ensure the file name is safe and matches the expected pattern
        expected_pattern = r'^reports/(registrations|enrollments)/[a-zA-Z0-9_\-]+\.csv$'
        if not re.match(expected_pattern, blob_name) or not is_safe_path(blob_name, 'reports/'):
            raise SuspiciousOperation('Invalid file path')

        return download_gcs_file(bucket_name, blob_name, json_key_path)

    
    return render(request, 'reporting_download.html', context)