import logging
import os

from django.conf import settings  # noqa
from django.core.management import BaseCommand
from svn.remote import RemoteClient
from svn.common import SvnException

from delft3dworker.models import Version_SVN


class Command(BaseCommand):
    help = """Update local Delft3D SVN repository and updates
    VERSION_SVN models based on the available tags."""

    def handle(self, *args, **options):

        # Handle svn credentials
        user = os.environ.get('SVN_USER')
        password = os.environ.get('SVN_PASS')
        if user is None or password is None:
            logging.error("No credentials found.")
            return

        # Connect external repos and update
        # Could've used local repos file:/// without user & pass
        try:
            r = RemoteClient(settings.REPOS_URL + '/tags/')
        except SvnException as e:
            logging.error("Error {} connecting to {}".format(
                e, settings.REPOS_URL))
            return

        updates_available = False

        folders = r.list(extended=True)
        for folder in folders:
            if folder['is_directory']:
                tag = folder['name']

                # Does this tag already exist?
                if not Version_SVN.objects.filter(release=tag).exists():
                    # Get general info
                    t = RemoteClient(
                        settings.REPOS_URL + '/tags/' + tag, username=user, password=password)
                    info = t.info()
                    revision = info['commit#revision']
                    log = list(t.log_default(stop_on_copy=True))[0].msg
                    url = settings.REPOS_URL + '/tags/' + tag

                    # Get revisions for all folders in the script folder
                    versions = {}
                    e = RemoteClient(
                        settings.REPOS_URL + '/tags/' + tag + '/scripts/')
                    entries = e.list(extended=True)
                    for entry in entries:
                        if entry['is_directory']:
                            versions[entry['name']] = entry['commit_revision']

                    # Create model
                    updates_available = True
                    logging.info("Creating tag {}".format(tag))
                    version = Version_SVN(
                        release=tag, revision=revision, versions=versions, url=url, changelog=log)
                    version.save()

        if not updates_available:
            logging.info("No updates found.")
