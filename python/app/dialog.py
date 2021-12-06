# MIT License

# Copyright (c) 2021 Netherlands Film Academy

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sgtk
import os
import threading
import subprocess
import tempfile
import shutil
import re
from datetime import datetime

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog

# standard toolkit logger
logger = sgtk.platform.get_logger(__name__)


def show_dialog(app_instance):
    """
    Shows the main dialog window.
    """
    # in order to handle UIs seamlessly, each toolkit engine has methods for launching
    # different types of windows. By using these methods, your windows will be correctly
    # decorated and handled in a consistent fashion by the system.

    # we pass the dialog class to this method and leave the actual construction
    # to be carried out by toolkit.
    app_instance.engine.show_dialog("NFA Library Importer", app_instance, AppDialog)


class AppDialog(QtGui.QWidget):
    """
    Main application dialog window
    """

    def __init__(self):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)

        # now load in the UI that was created in the UI designer
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        self._app = sgtk.platform.current_bundle()

        self.sg = self._app.shotgun

        # Getting app settings
        self.projectID = self._app.get_setting("project_id")
        self.libraryStatus = self._app.get_setting("library_status")
        self.libraryLocation = self._app.get_setting("library_location")
        self.permissionGroup = self._app.get_setting("permission_group")

        # Connecting logic
        self.ui.browseDirectory.clicked.connect(self.file_browser)
        self.ui.executeButton.clicked.connect(self.execute_importing)

    def file_browser(self):
        # Creating file browser
        open_directory = self.libraryLocation
        directory = QtGui.QFileDialog()
        directory.setFileMode(QtGui.QFileDialog.FileMode())
        directory = directory.getExistingDirectory(
            None, "Open directory to import into the library", open_directory
        )

        # Print message
        self.output_to_console("Set directory: %s" % directory)

        self.ui.directoryPath.setText(directory)

    def output_to_console(self, message):
        # Printing to Shotgun console
        logger.info(message)

        # Getting previous messages
        previous_text = self.ui.console.toPlainText()
        current_time = datetime.now()
        current_time = current_time.strftime("%H:%M:%S")
        current_time = "[" + str(current_time) + "] "

        if not previous_text == "":
            self.ui.console.insertPlainText("\n" + current_time + message)
        else:
            self.ui.console.insertPlainText(current_time + message)

    def execute_importing(self):
        # Getting directory path
        directory_path = self.ui.directoryPath.text()
        directory_path = directory_path.replace(os.sep, "/")

        is_allowed_importing = self.check_permissions()

        if is_allowed_importing:
            if self.ui.importSubfolders.isChecked():
                self.output_to_console(
                    "Importing subfolders is activated, will import the complete library. This can take a while."
                )
                for subdir in os.listdir(directory_path):
                    sub_directory = os.path.join(directory_path, subdir)
                    sub_directory = sub_directory.replace(os.sep, "/")
                    if os.path.isdir(sub_directory):
                        self.import_library(sub_directory)
            else:
                self.import_library(directory_path)

    def check_permissions(self):
        # Getting ShotGrid object
        sg = self.sg

        # Getting current user ID
        user = sgtk.util.get_current_user(sg)
        user_id = user.get("id")

        filters = [["id", "is", user_id]]
        columns = ["permission_rule_set"]

        # Find permission group
        user_permission_group = sg.find_one("HumanUser", filters, columns)
        user_permission_group = user_permission_group.get("permission_rule_set")
        user_permission_group = user_permission_group.get("name")

        is_allowed_importing = False

        # Allow importing when permission group is admin or specified permission group
        if (
            user_permission_group == "Admin"
            or user_permission_group == self.permissionGroup
        ):
            self.output_to_console("User is allowed to start importing.")
            is_allowed_importing = True

        else:
            self.output_to_console("User is not allowed to start importing.")

        return is_allowed_importing

    def import_library(self, directory_path):

        self.output_to_console("Executing importing on: " + directory_path)

        # Getting ShotGrid object
        sg = self.sg

        # Setting values for Library entity
        library_project_id = self.projectID
        status = self.libraryStatus
        category_name = os.path.basename(directory_path)
        library_description = category_name.replace("_", " ")

        # Searching if Sequence exists already
        category_filters = [
            ["project", "is", {"type": "Project", "id": library_project_id}],
            ["code", "is", category_name],
        ]
        category = sg.find_one("Sequence", category_filters)

        # If sequence doesn't exist, create one
        if not category:
            category_data = {
                "project": {"type": "Project", "id": library_project_id},
                "code": category_name,
                "description": library_description,
                "sg_status_list": status,
            }
            category = sg.create("Sequence", category_data)
            category_id = category.get("id")

            # Output result to console
            self.output_to_console(
                "Created new category with id " + str(category_id) + "."
            )

        else:
            # Define category id
            category_id = category.get("id")

            # Output result to console
            self.output_to_console(
                "Found existing category with id "
                + str(category_id)
                + ", adding stock to this category."
            )

        # Creating asset per filename and generate quicktime, afterwards upload to ShotGrid
        for subdir, dir, files in os.walk(directory_path):
            dir_list = os.listdir(subdir)

            if any(".exr" in dirNames for dirNames in dir_list):
                # exr logic
                file_sequences = self.get_frame_sequences(subdir)
                for sequence in file_sequences:
                    # Defining variables
                    file_path = sequence[0]
                    file_path = file_path.replace(os.sep, "/")

                    file_name = os.path.dirname(file_path)
                    file_name = os.path.basename(file_name) + " (exr)"

                    frame_list = sequence[1]
                    start_frame = min(frame_list)
                    last_frame = max(frame_list)

                    # Starting submission
                    asset_id = self.generate_asset(
                        library_project_id, category_id, file_name, status
                    )

                    # Making sure only to create version if allowed
                    create_version = True
                    if not self.ui.overwriteExisting.isChecked():
                        if self.check_existing_versions(library_project_id, asset_id):
                            create_version = False

                            self.output_to_console(
                                "Skipping " + file_name + ". Version exists already."
                            )

                    if create_version:
                        version_id = self.create_version(
                            library_project_id,
                            asset_id,
                            file_name,
                            file_path,
                            "sequence",
                            start_frame,
                            last_frame,
                        )

                        # Transcoding to mov and upload to ShotGrid
                        self.generate_quicktime(
                            file_path, file_name, version_id, "sequence", start_frame
                        )

            else:
                for file_name in files:
                    # Logic for mp4/mov's
                    video_files = (".mov", ".mp4")
                    if file_name.endswith(video_files):
                        file_path = os.path.join(subdir, file_name)
                        file_path = file_path.replace(os.sep, "/")
                        file_extension = " (" + os.path.splitext(file_path)[1][1:] + ")"
                        file_name = os.path.splitext(file_name)[0] + file_extension

                        asset_id = self.generate_asset(
                            library_project_id, category_id, file_name, status
                        )

                        # Making sure only to create version if allowed
                        create_version = True
                        if not self.ui.overwriteExisting.isChecked():
                            if self.check_existing_versions(
                                library_project_id, asset_id
                            ):
                                create_version = False

                                self.output_to_console(
                                    "Skipping "
                                    + file_name
                                    + ". Version exists already."
                                )

                        if create_version:
                            version_id = self.create_version(
                                library_project_id,
                                asset_id,
                                file_name,
                                file_path,
                                "file",
                            )
                            self.generate_quicktime(
                                file_path, file_name, version_id, "file"
                            )

        # Message when everything is done
        self.output_to_console("Done importing.")

    def generate_asset(self, project_id, category_id, file_name, status):
        # Getting ShotGrid object
        sg = self.sg

        # Searching if Asset exists already
        asset_filters = [
            ["project", "is", {"type": "Project", "id": project_id}],
            ["sequences", "is", {"type": "Sequence", "id": category_id}],
            ["code", "is", file_name],
        ]
        asset = sg.find_one("Asset", asset_filters)

        asset_description = file_name.replace("_", " ")

        # If sequence doesn't exist, create one
        if not asset:
            asset_data = {
                "project": {"type": "Project", "id": project_id},
                "sequences": [{"type": "Sequence", "id": category_id}],
                "code": file_name,
                "sg_asset_type": "Library",
                "description": asset_description,
                "sg_status_list": status,
            }
            asset = sg.create("Asset", asset_data)
            asset_id = asset.get("id")

            # Output result to console
            self.output_to_console("Created library asset for " + file_name + ".")

        else:
            # Define category id
            asset_id = asset.get("id")

            # Output result to console
            self.output_to_console(
                "Found existing library asset for "
                + file_name
                + ". Adding version to this one."
            )

        return asset_id

    def create_version(
        self,
        project_id,
        asset_id,
        file_name,
        file_path,
        type,
        start_frame=None,
        last_frame=None,
    ):
        # Getting ShotGrid object
        sg = self.sg

        version_description = file_name.replace("_", " ")

        # Adding all the necessary data
        version_data = {
            "project": {"type": "Project", "id": project_id},
            "code": file_name,
            "description": version_description,
            "sg_status_list": "vwd",
            "entity": {"type": "Asset", "id": asset_id},
        }

        # Add to sequence field or movie field
        if type == "sequence":
            version_path = {"sg_path_to_frames": file_path}

        else:
            version_path = {"sg_path_to_movie": file_path}

        # Add the data to dictionary
        version_data.update(version_path)

        if not start_frame == None and not last_frame == None:
            frame_data = {
                "sg_first_frame": int(start_frame),
                "sg_last_frame": int(last_frame),
            }
            version_data.update(frame_data)

        # Create version entity linked to asset
        created_version = sg.create("Version", version_data)
        version_id = created_version.get("id")

        self.output_to_console("Created version on ShotGrid for " + file_name + ".")

        return version_id

    def generate_quicktime(
        self, file_path, file_name, version_id, type, start_frame=None
    ):
        # Set initial value
        output_complete = False

        if not type == "":
            # Getting ShotGrid object
            sg = self.sg

            try:
                # Create temp file location
                temp_location = tempfile.mkdtemp()

                # Transcode movie
                temp_video_location = os.path.join(temp_location, file_name + ".mov")
                temp_video_location = temp_video_location.replace(os.sep, "/")

                if type == "file":
                    subprocess.call(
                        [
                            "ffmpeg",
                            "-y",
                            "-i",
                            file_path,
                            "-vcodec",
                            "libx264",
                            "-pix_fmt",
                            "yuv420p",
                            "-acodec",
                            "aac",
                            temp_video_location,
                        ]
                    )

                if type == "sequence":
                    start_frame = str(start_frame)
                    subprocess.call(
                        [
                            "ffmpeg",
                            "-y",
                            "-gamma",
                            "2.2",
                            "-start_number",
                            start_frame,
                            "-i",
                            file_path,
                            "-vcodec",
                            "libx264",
                            "-pix_fmt",
                            "yuv420p",
                            "-r",
                            "25",
                            temp_video_location,
                        ]
                    )

                # Upload to ShotGrid
                sg.upload(
                    "Version", version_id, temp_video_location, "sg_uploaded_movie"
                )

                # Remove temp file
                shutil.rmtree(temp_location)

                self.output_to_console(
                    "Uploaded transcoded movie for " + file_name + "."
                )

                output_complete = True

            except:
                self.output_to_console(
                    "Quicktime creation failed for " + file_name + "."
                )

        else:
            # If no type specified, return error
            raise ValueError("No type specified.")
            self.output_to_console("No type specified.")

        return output_complete

    def check_existing_versions(self, project_id, asset_id):
        sg = self.sg

        # Set initial value
        versionExists = False

        # Search for
        versionFilters = [
            ["project", "is", {"type": "Project", "id": project_id}],
            ["entity", "is", {"type": "Asset", "id": asset_id}],
        ]
        version = sg.find_one("Version", versionFilters)

        # Set value if versions were found
        if version:
            versionExists = True

        return versionExists

    def get_frame_sequences(self, folder, extensions=None, frame_spec=None):
        """
        Copied from the publisher plugin, and customized to return file sequences with frame lists instead of filenames

        Given a folder, inspect the contained files to find what appear to be
        files with frame numbers.

        :param folder: The path to a folder potentially containing a sequence of
            files.

        :param extensions: A list of file extensions to retrieve paths for.
            If not supplied, the extension will be ignored.

        :param frame_spec: A string to use to represent the frame number in the
            return sequence path.

        :return: A list of tuples for each identified frame sequence. The first
            item in the tuple is a sequence path with the frame number replaced
            with the supplied frame specification. If no frame spec is supplied,
            a python string format spec will be returned with the padding found
            in the file.


            Example::

            get_frame_sequences(
                "/path/to/the/folder",
                ["exr", "jpg"],
                frame_spec="{FRAME}"
            )

            [
                (
                    "/path/to/the/supplied/folder/key_light1.{FRAME}.exr",
                    [<frame_1_framenumber>, <frame_2_framenumber>, ...]
                ),
                (
                    "/path/to/the/supplied/folder/fill_light1.{FRAME}.jpg",
                    [<frame_1_framenumber>, <frame_2_framenumber>, ...]
                )
            ]


        """
        FRAME_REGEX = re.compile(r"(.*)([._-])(\d+)\.([^.]+)$", re.IGNORECASE)

        # list of already processed file names
        processed_names = {}

        # examine the files in the folder
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)

            if os.path.isdir(file_path):
                # ignore subfolders
                continue

            # see if there is a frame number
            frame_pattern_match = re.search(FRAME_REGEX, filename)

            if not frame_pattern_match:
                # no frame number detected. carry on.
                continue

            prefix = frame_pattern_match.group(1)
            frame_sep = frame_pattern_match.group(2)
            frame_str = frame_pattern_match.group(3)
            extension = frame_pattern_match.group(4) or ""

            # filename without a frame number.
            file_no_frame = "%s.%s" % (prefix, extension)

            if file_no_frame in processed_names:
                # already processed this sequence. add the framenumber to the list, later we can use this to determine the framerange
                processed_names[file_no_frame]["frame_list"].append(frame_str)
                continue

            if extensions and extension not in extensions:
                # not one of the extensions supplied
                continue

            # make sure we maintain the same padding
            if not frame_spec:
                padding = len(frame_str)
                frame_spec = "%%0%dd" % (padding,)

            seq_filename = "%s%s%s" % (prefix, frame_sep, frame_spec)

            if extension:
                seq_filename = "%s.%s" % (seq_filename, extension)

            # build the path in the same folder
            seq_path = os.path.join(folder, seq_filename)

            # remember each seq path identified and a list of files matching the
            # seq pattern
            processed_names[file_no_frame] = {
                "sequence_path": seq_path,
                "frame_list": [frame_str],
            }

        # build the final list of sequence paths to return
        frame_sequences = []
        for file_no_frame in processed_names:

            seq_info = processed_names[file_no_frame]
            seq_path = seq_info["sequence_path"]

            frame_sequences.append((seq_path, seq_info["frame_list"]))

        return frame_sequences
