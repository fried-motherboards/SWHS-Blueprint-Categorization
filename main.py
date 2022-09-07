import config

import click
import uuid
import datetime
import os
import subprocess
import shutil
import json
import glob


class Bundle:
    def __init__(
            self, bundle_uuid, project_name, building, date, page_count,
            contents
    ):
        self.bundle_uuid = bundle_uuid
        self.project_name = project_name
        self.building = building
        self.date = date
        self.page_count = page_count
        self.contents = contents

    def list_bundle(self):
        click.echo(
            f"Project named {self.project_name} drawn up on {self.date}\
        specifying the {self.building} with {self.page_count} page(s).\
        Registered UUID is {self.bundle_uuid}"
        )

    @classmethod
    def get_bundle_info(cls):
        def get_building():
            # References options dictionary to show what possibilities can be displayed
            # and then forms a prompt for the user to interact with from that list, can
            # be changed to fit more building options if needed (overly-complex for a
            # single prompt, I know).
            options = {0: 'Other', 1: 'District Office',
                       2: 'Primary School', 3: 'Intermediate School',
                       4: 'High School', 5: 'Community Center',
                       6: 'Outdoor Classroom', 7: 'Water Treatment Facility',
                       8: 'Land Surveys', 9: 'Bayview School'}
            validity = False
            while not validity:
                # Cycles through each option available
                for i in options:
                    click.echo(
                        str(i) + '.) ' + options[i]
                    )
                building_choice = int(
                    click.prompt(
                        'Enter the associated building this bundle applies to'
                    ).replace(" ", "-")
                )
                # Determines if the user enters a valid option
                if building_choice > 9 or building_choice < 0:
                    click.echo(
                        "Invalid building choice. "
                        "Please re-enter a value from the list."
                    )
                else:
                    # Breaks loop when a valid option is entered
                    validity = True
                for b in options:
                    if building_choice == b:
                        building_choice = options[b]
            # noinspection PyUnboundLocalVariable
            return str(building_choice).replace(" ", "-")

        def get_date():
            while True:
                try:
                    date_entry = datetime.date(
                        int(click.prompt("Enter cover sheet year")),
                        int(click.prompt("Enter cover sheet month")),
                        int(click.prompt("Enter cover sheet day"))
                    )
                except ValueError:
                    click.echo("Invalid date: Not a number")
                else:
                    if date_entry.year <= 1900 or date_entry.year >= 2020:
                        click.echo("Invalid date: Year out of realistic range")
                    elif date_entry.month <= 0 or date_entry.month > 12:
                        click.echo("Invalid date: Month out of realistic range")
                    elif date_entry.day <= 0 or date_entry.day > 32:
                        click.echo("Invalid date: Day out of realistic range")
                    else:
                        return date_entry

        return Bundle(
            uuid.uuid4(),  # A unique ID for internal references later on
            click.prompt(
                "Enter the name of the project that is the subject of these prints"
            ).replace(
                " ", "-"
            ),  # A human-readable to be used for filenames and memorability
            get_building(),  # A human-readable associated building
            get_date(),  # A valid date and time in YYYY-MM-DD format
            0,  # An integer counter denoting the amount of pages within the bundle
            dict()  # An empty dictionary intended to track contained blueprints
        )


class Blueprint:
    def __init__(
            self, drawing_title, sheet_number
    ):
        self.drawing_title = drawing_title
        self.sheet_number = sheet_number

    @classmethod
    def get_blueprint_info(cls):
        return Blueprint(
            click.prompt(
                "Enter the drawing name as listed on the blueprint"
            ).replace(" ", "-"),  # A human-readable title assigned by the architects on the print
            click.prompt(
                "Enter the sheet number as listed on the blueprint"
            ).replace(
                "/", "-of-"
            ).replace(
                " ", "-"
            )  # The sheet number assigned by the architects on the print
        )


def main():
    # Sequentially processes each file in the input directory by finding the files,
    # remembering the last processed blueprints and bundles, opening a PDF preview
    # subprocess, prompting the user to input applicable information about the
    # previewed blueprint (creating new bundles as necessary), moving files
    # (and creating directories as needed), logging the results to a json file, and
    # finally closing the preview subprocess.

    first_run = True  # Indicates that this is the first loop iteration

    for scan in sorted(
            glob.glob(os.path.join(config.input_scans_location, '*.PDF')),
            key=os.path.getmtime):
        # Ignore other directories and files not ending in ".PDF"
        """if scan.is_dir() or ".PDF" not in scan.name:
            click.echo(
                f"Ignoring {scan.name}, is either a directory or not a target file"
            )
            continue
        else:
            click.echo("Processing next file in line, filename " + scan.name)"""

        # Displays the file in question as a preview process
        file_view = subprocess.Popen([config.default_viewer, scan],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)

        # Determines if the program has created an initial bundle yet by
        # essentially creating the first bundle, and categorizing the first print,
        # all without extended user input to determine if a new bundle needs to be
        # created.
        if first_run:
            # Notes that the first run condition has now been satisfied
            first_run = False
            # Backs up the last processed json log from a potential past run
            try:
                shutil.copy(config.log_file, config.backup_log_file)
            except FileNotFoundError:
                click.echo("No log files found, new ones will be generated")
            # Starts collecting bundle info for the first time
            current_bundle = Bundle.get_bundle_info()
            # Starts collecting blueprint info for the first time
            current_blueprint = Blueprint.get_blueprint_info()
            # Increments total page count of the bundle in question
            current_bundle.page_count = current_bundle.page_count + 1
            click.echo(
                f"Page count for the project {current_bundle.project_name} is now "
                f"{current_bundle.page_count}"
            )
            # Associates bundle page number with blueprint drawing title by
            # updating the dictionary with a page:drawing keypair
            current_bundle.contents.update(
                {current_bundle.page_count: current_blueprint.drawing_title}
            )
            click.echo(
                f"Pages associated with this bundle: {current_bundle.contents}"
            )
            # Creates output directory structure based upon current bundle
            # characteristics, then moves the now categorized blueprint into the final
            # output directory, a combination of the first directory (named
            # after the building the blueprint depicts), the subdirectory (named after
            # the bundle's project name and date separated by an underscore), and the
            # user-specified output directory as outlined in the config file.
            directory = os.path.join(
                config.output_scans_location, current_bundle.building
            )
            subdirectory = str(
                str(current_bundle.date) + "_" + current_bundle.project_name
            )
            full_output_directory = os.path.join(
                config.output_scans_location, directory, subdirectory
            )
            # Creates directories regardless if they exist
            os.makedirs(full_output_directory, exist_ok=True)

            # Moves the file currently being processed to the final output directory
            # and renames the file as necessary with a trailing copy number
            # depending on how many similar filenames exist

            # NOTE TO SELF: Maybe also have this exist_check condition mark the
            # scan that is a Blueprint class object as "potential duplicate"
            # somehow for easier future sorting?
            if os.path.isfile(
                    os.path.join(
                        full_output_directory,
                        str(current_blueprint.sheet_number +
                            "_" + current_blueprint.drawing_title)
                    )
            ):
                file_exist_check = True
                while file_exist_check is True:
                    rename = 0
                    new_scan_name = str(
                        current_blueprint.drawing_title + "-copy" + str(rename)
                    )
                    rename = rename + 1
                    print("Duplicate file detected, number " + str(rename))
                    if not os.path.isfile(
                            os.path.join(
                                full_output_directory,
                                str(current_blueprint.sheet_number +
                                    "_" + new_scan_name)
                            )
                    ):
                        scan_filename = new_scan_name
                        file_exist_check = False
            else:
                scan_filename = current_blueprint.drawing_title

            # noinspection PyUnboundLocalVariable
            shutil.move(
                scan, os.path.join(
                    full_output_directory,
                    str(current_blueprint.sheet_number + "_" + scan_filename + ".pdf")
                )
            )
            # Kills preview process
            subprocess.Popen.kill(file_view)
            continue
        else:
            # Stores the last processed bundle and blueprint objects into respective
            # buffers known as "last_bundle" and "last_blueprint" unless for any reason
            # it isn't defined - to which the buffers are stored as "None"
            try:
                # noinspection PyUnboundLocalVariable
                last_bundle = current_bundle
                # noinspection PyUnboundLocalVariable
                last_blueprint = current_blueprint
            except NameError:
                last_bundle = None
                last_blueprint = None

            # Determines whether the scan is part of a new bundle based on user input
            if not click.confirm(
                    "Is this blueprint included in the project "
                    + current_bundle.project_name + "? "
            ):
                continue_bundle = False
            else:
                continue_bundle = True

            # If it ain't part of the current bundle, make a new one
            while not continue_bundle:
                # First we log the bundle data collected into a json file before being overwritten
                bundle_data = {
                    "UUID": str(current_bundle.bundle_uuid),
                    "Date": str(current_bundle.date),
                    "Building": current_bundle.building,
                    "Pages": current_bundle.page_count,
                    "Contents": current_bundle.contents
                }
                print(f"DEBUG BUNDLE LOG PREVIEW {bundle_data}")
                with open(config.log_file, 'a+') as file:
                    json.dump(bundle_data, file, indent=4)

                # Creates new instances of bundles and blueprints in their respective class
                # and defaults to a continuation state that prompts the user to build up a
                # defined bundle with information associated with displayed files.
                current_bundle = Bundle.get_bundle_info()
                continue_bundle = True

            # Starts collecting blueprint info
            current_blueprint = Blueprint.get_blueprint_info()
            # Increments total page count of the bundle in question, updates
            # user on how many pages are categorized within the bundle so far
            current_bundle.page_count = current_bundle.page_count + 1
            click.echo(
                f"Page count for the project {current_bundle.project_name} is now "
                f"{current_bundle.page_count}"
            )
            # Associates bundle page number with blueprint drawing title by
            # updating the dictionary with a page:drawing keypair, updates user
            # on all pages associated in the bundle object
            current_bundle.contents.update(
                {current_bundle.page_count: current_blueprint.drawing_title}
            )
            click.echo(
                f"Pages associated with this bundle: {current_bundle.contents}"
            )

        # Creates output directory structure based upon current bundle
        # characteristics, then moves the now categorized blueprint into the final
        # output directory, a combination of the first directory (named
        # after the building the blueprint depicts), the subdirectory (named after
        # the bundle's project name and date separated by an underscore), and the
        # user-specified output directory as outlined in the config file.
        directory = os.path.join(
            config.output_scans_location, current_bundle.building
        )
        subdirectory = str(
            str(current_bundle.date) + "_" + current_bundle.project_name
        )
        full_output_directory = os.path.join(
            config.output_scans_location, directory, subdirectory
        )
        # Creates directories regardless if they exist
        os.makedirs(full_output_directory, exist_ok=True)
        # Creates output directory structure based upon current bundle
        # characteristics, then moves the now categorized blueprint into the final
        # output directory, a combination of the first directory (named
        # after the building the blueprint depicts), the subdirectory (named after
        # the bundle's project name and date separated by an underscore), and the
        # user-specified output directory as outlined in the config file.
        directory = os.path.join(
            config.output_scans_location, current_bundle.building
        )
        subdirectory = str(
            str(current_bundle.date) + "_" + current_bundle.project_name
        )
        full_output_directory = os.path.join(
            config.output_scans_location, directory, subdirectory
        )
        # Creates directories regardless if they exist
        os.makedirs(full_output_directory, exist_ok=True)

        # Moves the file currently being processed to the final output directory
        # and renames the file as necessary with a trailing copy number
        # depending on how many similar filenames exist

        # NOTE TO SELF: Maybe also have this exist_check condition mark the
        # scan that is a Blueprint class object as "potential duplicate"
        # somehow for easier future sorting?
        if os.path.isfile(
                os.path.join(
                    full_output_directory,
                    str(current_blueprint.sheet_number +
                        "_" + current_blueprint.drawing_title)
                )
        ):
            file_exist_check = True
            while file_exist_check is True:
                rename = 0
                new_scan_name = str(
                    current_blueprint.drawing_title + "-copy" + str(rename)
                )
                rename = rename + 1
                print("Duplicate file detected, number " + str(rename))
                if not os.path.isfile(
                        os.path.join(
                            full_output_directory,
                            str(current_blueprint.sheet_number +
                                "_" + new_scan_name)
                        )
                ):
                    scan_filename = new_scan_name
                    file_exist_check = False
        else:
            scan_filename = current_blueprint.drawing_title

        # noinspection PyUnboundLocalVariable
        shutil.move(
            scan, os.path.join(
                full_output_directory,
                str(current_blueprint.sheet_number + "_" + scan_filename + ".pdf")
            )
        )

        # Kills preview process
        subprocess.Popen.kill(file_view)
    # Logs final bundle data before terminating the program
    bundle_data = {
        "UUID": str(current_bundle.bundle_uuid),
        "Date": str(current_bundle.date),
        "Building": current_bundle.building,
        "Pages": current_bundle.page_count,
        "Contents": current_bundle.contents
    }
    print(f"DEBUG BUNDLE LOG PREVIEW {bundle_data}")
    with open(config.log_file, 'a+') as file:
        json.dump(bundle_data, file, indent=4)


if __name__ == "__main__":
    main()
