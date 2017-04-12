from celery.result import AsyncResult
import logging
from django.conf import settings  # noqa
from django.core.management import BaseCommand
from os.path import join
import svn.local

from delft3dworker.models import Version_SVN


class Command(BaseCommand):
    help = """Update local Delft3D SVN repository and updates
    VERSION_SVN models based on the available tags."""

    def handle(self, *args, **options):
        # Connect local repos and update
        r = svn.local.LocalClient(settings.SVN_PATH)
        r.update()

        folders = r.list(extended=True)
        for folder in folders:
            if folder['is_directory']:
                tag = folder['name']

                # Does this tag already exist?
                if not Version_SVN.objects.filter(release=tag).exists():

                    # Get general info
                    t = svn.local.LocalClient(join(settings.SVN_PATH, tag))
                    info = t.info()
                    log = t.log_default(stop_on_copy=False).msg
                    url = settings.REPOS_URL + '/tags/' + tag

                    # Get revisions for all folders in the script folder
                    versions = {}
                    e = svn.local.LocalClient(join(settings.SVN_PATH, tag, 'scripts'))
                    entries = e.list(extended=True)
                    for entry in entries:
                        if entry['is_directory']:
                            versions[entry['name']] = entry['commit_revision']

                    # Create model
                    version = Version_SVN(
                        release=tag, revision=info.revision, versions=versions, url=url, changelog=log)
                    version.save()
