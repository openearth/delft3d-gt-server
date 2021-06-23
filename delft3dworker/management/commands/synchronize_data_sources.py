from __future__ import print_function

import datetime
from os import listdir, walk
from os.path import dirname, join, split
from shutil import rmtree

from django.conf import settings  # noqa
from django.core.management.base import BaseCommand, CommandError

from delft3dworker.models import Scene


class Command(BaseCommand):
    help = """
        This command should be executed when the two data sources of Delft3D-GT
        (i.e. the Postgres database and the "/data" directory) are no longer
        synchronized. Executing this will guide you through a recovery process.
    """

    def handle(self, *args, **options):

        with open("synchronize_data_sources.log", "a") as file:

            file.write(
                "==================== Data Sync started -- {}\n".format(
                    str(datetime.datetime.now())
                )
            )

            scenedirs = [
                scene.workingdir.encode("ascii", "ignore")
                for scene in Scene.objects.all()
            ]
            linked = set()

            # ######################################### check which file directories are no longer in the dB:

            self.stdout.write(
                "################################################################################"
            )
            self.stdout.write(" SYNCHRONIZATION PROCEDURE START")
            self.stdout.write(
                "################################################################################"
            )
            self.stdout.write("")

            self.stdout.ending = ""
            self.stdout.write(
                "Checking for inconsistencies in the data storage components..."
            )

            for scenedir in scenedirs:
                if scenedir[-1] == "/":
                    scenedir = scenedir[:-1]
                linked.add(scenedir)

            r, d, f = next(walk(settings.WORKER_FILEDIR))
            existing = set([join(r, directory) for directory in d])

            unlinked = existing - linked
            unstored = linked - existing

            self.stdout.write("done.\n")
            self.stdout.ending = "\n"

            # ######################################### get input on what to do next:

            if len(unlinked) > 0:

                self.stdout.write("")
                self.stdout.write(
                    "================================================================================"
                )
                self.stdout.write(" SYNCHRONIZE FILE SYSTEM")
                self.stdout.write(
                    "================================================================================"
                )
                self.stdout.write("")
                self.stdout.write(
                    "## The following directories do not have any entries in the Postgres database:"
                )
                self.stdout.write("")

                for directory in unlinked:
                    self.stdout.write("{}".format(directory))
                self.stdout.write("")

                resp = ""
                while not resp in ["y", "n"]:
                    self.stdout.write(
                        "## You can now enter a procedure which allows you to remove these directories."
                    )
                    resp = (
                        raw_input("## Do you want to proceed? [y/N]: ").lower() or "n"
                    )

                removedirs = True if resp == "y" else False

                # ######################################### remove dirs

                self.stdout.write("\n")
                self.stdout.ending = ""

                if removedirs:

                    rem = "s"

                    for directory in unlinked:

                        try:
                            if not rem == "a":
                                rem = (
                                    raw_input(
                                        "{}: skip (default), delete, all? [S/d/a]: ".format(
                                            directory
                                        )
                                    ).lower()
                                    or "s"
                                )

                            if rem in ["d", "a"]:
                                self.stdout.write(
                                    "-- Removing {}... ".format(directory)
                                )
                                rmtree(directory)
                                file.write("removed directory: {}\n".format(directory))
                                self.stdout.write("done\n")
                            else:
                                self.stdout.write("-- Skipping {}\n".format(directory))

                        except KeyboardInterrupt as e:
                            self.stdout.write("\n")
                            exit(1)

                        except Exception as e:
                            self.stdout.write(
                                "-- Couldn't delete {}!\n".format(directory)
                            )
                            print(e)

                else:
                    self.stdout.write("-- Skipping remove directory procedure...\n")

                self.stdout.ending = "\n"

            else:

                self.stdout.write("")
                self.stdout.write('No "orphaned" simulation results found on disk.')

            # ######################################### get input on what to do next:

            if len(unstored) > 0:

                self.stdout.write("")
                self.stdout.write(
                    "================================================================================"
                )
                self.stdout.write(" SYNCHRONIZE DATABASE")
                self.stdout.write(
                    "================================================================================"
                )
                self.stdout.write("")
                self.stdout.write(
                    "## The following simulations in the Postgres database do not have files stored"
                )
                self.stdout.write("## on disk:")
                self.stdout.write("")
                for directory in unstored:
                    scene = Scene.objects.get(workingdir=directory + "/")
                    self.stdout.write(
                        "{} (current phase: {}, owner: {})".format(
                            scene, scene.get_phase_display(), scene.owner
                        )
                    )

                resp = ""
                while not resp in ["y", "n"]:
                    self.stdout.write(
                        "\n## You can now enter a procedure which allows you to reset these simulations."
                    )
                    resp = (
                        raw_input("## Do you want to proceed? [y/N]: ").lower() or "n"
                    )

                resetsims = True if resp == "y" else False

                # ######################################### reset simulations

                self.stdout.write("\n")
                self.stdout.ending = ""

                if resetsims:

                    rem = "s"

                    for sim in unstored:

                        try:
                            scene = Scene.objects.get(workingdir=directory + "/")

                            rem = (
                                raw_input(
                                    "{}: skip (default), reset, delete? [S/r/d]: ".format(
                                        scene
                                    )
                                ).lower()
                                or "s"
                            )

                            if rem in ["r"]:

                                if scene.phase == scene.phases.fin:
                                    self.stdout.write(
                                        '-- Resetting Scene "{}"... '.format(scene)
                                    )
                                    scene.reset()
                                    file.write("reset scene: {}\n".format(scene))
                                    self.stdout.write("done\n")
                                else:
                                    self.stdout.write(
                                        '-- Skipping "{}": scene not finished (current phase: {})\n'.format(
                                            scene, scene.get_phase_display()
                                        )
                                    )

                            elif rem in ["d"]:

                                self.stdout.write(
                                    '-- Deleting Scene "{}"... '.format(scene)
                                )
                                scene.delete()
                                file.write("deleted scene: {}\n".format(scene))
                                self.stdout.write("done\n")

                            else:

                                self.stdout.write('-- Skipping "{}"\n'.format(scene))

                        except KeyboardInterrupt as e:
                            self.stdout.write("\n")
                            exit(1)

                        except Exception as e:
                            self.stdout.write(
                                '-- Couldn\'t reset Scene "{}" with working directory {}!\n'.format(
                                    scene, directory
                                )
                            )
                            print(e)

                else:
                    self.stdout.write("-- Skipping reset simulations procedure...\n")

            else:

                self.stdout.write("")
                self.stdout.write('No "orphaned" simulation entries found in database.')

            self.stdout.ending = "\n"

            self.stdout.write("")
            self.stdout.write(
                "################################################################################"
            )
            self.stdout.write(" SYNCHRONIZATION PROCEDURE DONE")
            self.stdout.write("")
            self.stdout.write(
                " A log is written to file: synchronize_data_sources.log".format(file)
            )
            self.stdout.write("")
            self.stdout.write(
                "################################################################################"
            )
