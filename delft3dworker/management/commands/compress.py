from os import remove, rename, stat, walk
from os.path import basename, join
from subprocess import call

from django.conf import settings  # noqa
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compresses netcdf output of finished Delft3D models"

    def handle(self, *args, **options):
        netcdf = "trim-a.nc"
        netcdf_compressed = "trim-a-compressed.nc"

        for root, dirs, files in walk(settings.WORKER_FILEDIR):
            # If we find the delft3d output folder and the simulation is done
            # and there's a uncompressed netcdf and not yet a compressed one
            if (
                basename(root) == "simulation"
                and "done" in files
                and netcdf in files
                and netcdf_compressed not in files
            ):
                self.stdout.write("Start compression of {} in {}.".format(netcdf, root))

                orisize = stat(join(root, netcdf)).st_size
                # This creates a netCDF4 Classic file, this CAN be INCOMPATIBLE
                # with further (post)processing scripts. Deflate level 1 is used
                # see http://nco.sourceforge.net/nco.html#Deflation
                command = "ncks -4 -L 1 {}/{} {}/{}".format(
                    root, netcdf, root, netcdf_compressed
                )

                if not call(command, shell=True):
                    newsize = stat(join(root, netcdf_compressed)).st_size
                    ratio = newsize / float(orisize)

                    remove(join(root, netcdf))
                    rename(join(root, netcdf_compressed), join(root, netcdf))

                    self.stdout.write(
                        "Compressed {} to with ratio: {}".format(netcdf, ratio)
                    )
