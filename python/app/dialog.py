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
import sys
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
        self.libraryLocation =  self._app.get_setting("library_location")
        self.permissionGroup = self._app.get_setting("permission_group")

        # Connecting logic
        self.ui.browseDirectory.clicked.connect(self.fileBrowser)
        self.ui.executeButton.clicked.connect(self.executeImporting)





    def fileBrowser(self):
        # Creating file browser
        ### Should be made a link in info.yml and convert method for Windows/Linux.
        openDirectory = self.libraryLocation
        directory = QtGui.QFileDialog()
        directory.setFileMode( QtGui.QFileDialog.FileMode() )
        directory = directory.getExistingDirectory( None, 'Open directory to import into the library', openDirectory )

        # Print message
        self.outputToConsole("Set directory: " + directory)

        self.ui.directoryPath.setText(directory)


    def outputToConsole(self, message):
        # Printing to Shotgun console
        logger.info(message)

        # Getting previous messages
        previousText = self.ui.console.toPlainText()
        currentTime = datetime.now()
        currentTime = currentTime.strftime("%H:%M:%S")
        currentTime = "[" + str(currentTime) + "] "

        if not previousText ==  "":
            self.ui.console.insertPlainText("\n" + currentTime + message)
        else:
            self.ui.console.insertPlainText(currentTime + message)

    def executeImporting(self):
        # Getting directory path
        directoryPath = self.ui.directoryPath.text()
        directoryPath = directoryPath.replace(os.sep, '/')

        isAllowedImporting = self.checkPermissions()

        if isAllowedImporting:
            if self.ui.importSubfolders.isChecked():
                self.outputToConsole("Importing subfolders is activated, will import the complete library. This can take a while.")
                for subdir in os.listdir(directoryPath):
                    subDirectory = os.path.join(directoryPath, subdir)
                    subDirectory = subDirectory.replace(os.sep, '/')
                    if os.path.isdir(subDirectory):
                        self.importLibrary(subDirectory)
            else:
                self.importLibrary(directoryPath)

    def checkPermissions(self):
        # Getting ShotGrid object
        sg = self.sg

        # Getting current user ID
        user = sgtk.util.get_current_user(sg)
        userID = user.get('id')

        filters = [['id', 'is', userID]]
        columns =  ['permission_rule_set']

        # Find permission group
        userPermissionGroup = sg.find_one('HumanUser', filters, columns)
        userPermissionGroup = userPermissionGroup.get('permission_rule_set')
        userPermissionGroup = userPermissionGroup.get('name')

        isAllowedImporting = False

        # Allow importing when permission group is admin or specified permission group
        if userPermissionGroup == 'Admin' or userPermissionGroup == self.permissionGroup:
            self.outputToConsole("User is allowed to start importing.")
            isAllowedImporting = True

        else:
            self.outputToConsole("User is not allowed to start importing.")

        return isAllowedImporting


    def importLibrary(self, directoryPath):

        self.outputToConsole("Executing importing on: " + directoryPath)

        # Getting ShotGrid object
        sg = self.sg

        # Setting values for Library entity
        libraryProjectID = self.projectID
        status = self.libraryStatus
        categoryName = os.path.basename(directoryPath)
        libraryDescription = categoryName.replace("_", " ")

        # Searching if Sequence exists already
        categoryFilters = [ ['project', 'is', {'type': 'Project', 'id': libraryProjectID}],
                    ['code', 'is', categoryName] ]
        category = sg.find_one('Sequence', categoryFilters)

        # If sequence doesn't exist, create one
        if not category:
            categoryData = {
                'project': {"type":"Project","id": libraryProjectID},
                'code': categoryName,
                'description': libraryDescription,
                'sg_status_list': status
            }
            category = sg.create('Sequence', categoryData)
            categoryID = category.get('id')

            # Output result to console
            self.outputToConsole("Created new category with id " + str(categoryID) + ".")

        else:
            # Define category id
            categoryID = category.get('id')

            # Output result to console
            self.outputToConsole("Found existing category with id " + str(categoryID) + ", adding stock to this category.")



        # Creating asset per filename and generate quicktime, afterwards upload to ShotGrid
        for subdir, dir, files in os.walk(directoryPath):
            dirList = os.listdir(subdir)

            if any(".exr" in dirNames for dirNames in dirList):
                # exr logic
                fileSequences = self.getFrameSequences(subdir)
                for sequence in fileSequences:
                    # Defining variables
                    filePath = sequence[0]
                    filePath = filePath.replace(os.sep, '/')

                    fileName = os.path.dirname(filePath)
                    fileName = os.path.basename(fileName) + ' (exr)'


                    frameList = sequence[1]
                    startFrame = min(frameList)
                    lastFrame = max(frameList)

                    # Starting submission
                    assetID = self.generateAsset(libraryProjectID, categoryID, fileName, status)

                    # Making sure only to create version if allowed
                    createVersion = True
                    if not self.ui.overwriteExisting.isChecked():
                        if self.checkExistingVersions(libraryProjectID, assetID):
                            createVersion = False

                            self.outputToConsole("Skipping " + fileName + ". Version exists already.")


                    if createVersion:
                        versionID = self.createVersion(libraryProjectID, assetID, fileName, filePath, 'sequence', startFrame, lastFrame)

                        # Transcoding to mov and upload to ShotGrid
                        self.generateQuicktime(filePath, fileName, versionID, 'sequence', startFrame)



            else:
                for fileName in files:
                    # Logic for mp4/mov's
                    videoFiles = ('.mov', '.mp4')
                    if fileName.endswith(videoFiles):
                        filePath = os.path.join(subdir, fileName)
                        filePath = filePath.replace(os.sep, '/')
                        fileExtension = " (" + os.path.splitext(filePath)[1][1:] + ")"
                        fileName = os.path.splitext(fileName)[0] + fileExtension

                        assetID = self.generateAsset(libraryProjectID, categoryID, fileName, status)


                        # Making sure only to create version if allowed
                        createVersion = True
                        if not self.ui.overwriteExisting.isChecked():
                            if self.checkExistingVersions(libraryProjectID, assetID):
                                createVersion = False

                                self.outputToConsole("Skipping " + fileName + ". Version exists already.")

                        if createVersion:
                            versionID = self.createVersion(libraryProjectID, assetID, fileName, filePath, 'file')
                            self.generateQuicktime(filePath, fileName, versionID, 'file')

        # Message when everything is done
        self.outputToConsole("Done importing.")


    def generateAsset(self, projectID, categoryID, fileName, status):
        # Getting ShotGrid object
        sg = self.sg

        # Searching if Asset exists already
        assetFilters = [ ['project', 'is', {'type': 'Project', 'id': projectID}],
                    ['sequences', 'is', {'type': 'Sequence', 'id': categoryID}],
                    ['code', 'is', fileName] ]
        asset = sg.find_one('Asset', assetFilters)

        assetDescription = fileName.replace("_", " ")

        # If sequence doesn't exist, create one
        if not asset:
            assetData = {
                        'project': {"type":"Project","id": projectID},
                        'sequences': [{"type":"Sequence","id": categoryID}],
                        'code': fileName,
                        'sg_asset_type': 'Library',
                        'description': assetDescription,
                        'sg_status_list': status
                        }
            asset = sg.create('Asset', assetData)
            assetID = asset.get('id')

            # Output result to console
            self.outputToConsole("Created library asset for " + fileName + ".")

        else:
            # Define category id
            assetID = asset.get('id')

            # Output result to console
            self.outputToConsole("Found existing library asset for " + fileName + ". Adding version to this one.")

        return assetID

    def createVersion(self, projectID, assetID, fileName, filePath, type, startFrame=None, lastFrame=None):
        # Getting ShotGrid object
        sg = self.sg

        versionDescription = fileName.replace("_", " ")

        # Adding all the necessary data
        versionData = { 'project': {'type': 'Project','id': projectID},
                 'code': fileName,
                 'description': versionDescription,
                 'sg_status_list': 'vwd',
                 'entity': {'type': 'Asset', 'id': assetID}}

        # Add to sequence field or movie field
        if type == 'sequence':
            versionPath = {'sg_path_to_frames': filePath}

        else:
            versionPath = {'sg_path_to_movie': filePath}

        # Add the data to dictionary
        versionData.update(versionPath)

        if not startFrame == None and not lastFrame == None:
            frameData = {'sg_first_frame': int(startFrame),
                        'sg_last_frame': int(lastFrame)}
            versionData.update(frameData)

        # Create version entity linked to asset
        createdVersion = sg.create('Version', versionData)
        versionID = createdVersion.get('id')

        self.outputToConsole("Created version on ShotGrid for " + fileName + ".")

        return versionID

    def generateQuicktime(self, filePath, fileName, versionID, type, startFrame=None):
        # Set initial value
        outputComplete = False

        if not type == '':
            # Getting ShotGrid object
            sg = self.sg

            try:
                # Create temp file location
                tempLocation = tempfile.mkdtemp()

                # Transcode movie
                tempVideoLocation = os.path.join(tempLocation, fileName + '.mov')
                tempVideoLocation = tempVideoLocation.replace(os.sep, '/')

                if type == 'file':
                    subprocess.call(['ffmpeg', '-y', '-i', filePath, '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-acodec', 'aac', tempVideoLocation])

                if type == 'sequence':
                    startFrame = str(startFrame)
                    subprocess.call(['ffmpeg', '-y', '-gamma', '2.2', '-start_number', startFrame, '-i', filePath, '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-r', '25', tempVideoLocation])

                # Upload to ShotGrid
                uploadedMovie = sg.upload('Version', versionID, tempVideoLocation, 'sg_uploaded_movie')

                # Remove temp file
                shutil.rmtree(tempLocation)

                self.outputToConsole("Uploaded transcoded movie for " + fileName + ".")

                outputComplete = True

            except:
                self.outputToConsole("Quicktime creation failed for " + fileName + ".")


        else:
            # If no type specified, return error
            raise ValueError('No type specified.')
            self.outputToConsole('No type specified.')

        return outputComplete

    def checkExistingVersions(self, projectID, assetID):
        sg = self.sg

        # Set initial value
        versionExists = False

        # Search for
        versionFilters = [ ['project', 'is', {'type': 'Project', 'id': projectID}],
                            ['entity', 'is', {'type': 'Asset', 'id': assetID}]]
        version = sg.find_one('Version', versionFilters)

        # Set value if versions were found
        if version:
            versionExists = True

        return versionExists

    def getFrameSequences(self, folder, extensions=None, frame_spec=None):
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
