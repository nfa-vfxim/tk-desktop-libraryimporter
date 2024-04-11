[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/nfa-vfxim/tk-desktop-libraryimporter?include_prereleases)](https://github.com/nfa-vfxim/tk-desktop-libraryimporter) 
[![GitHub issues](https://img.shields.io/github/issues/nfa-vfxim/tk-desktop-libraryimporter)](https://github.com/nfa-vfxim/tk-desktop-libraryimporter/issues) 


# ShotGrid Library importer <img src="icon_256.png" alt="Icon" height="24"/>

App to import footage from library into ShotGrid.

This desktop app will provide a GUI to import a complete stock library.
It will create an asset grouped per scene, transcode with FFMPEG a preview for ShotGrid, and create a version for every asset.

![ShotGrid Library Importer user interface](resources/tk-desktop-libraryimporter.png)


## Requirements

| ShotGrid version | Core version | Engine version |
|------------------|--------------|----------------|
| -                | v0.14.28     | -              |

## Configuration

### Integers

| Name         | Description                               | Default value |
|--------------|-------------------------------------------|---------------|
| `project_id` | Default project to upload the library to. | 1546          |


### Strings

| Name               | Description                                                                              | Default value                              |
|--------------------|------------------------------------------------------------------------------------------|--------------------------------------------|
| `library_status`   | Setting for the default status that is assigned to the created sequences/assets/versions | wtg                                        |
| `library_location` | Default location that is opened when using the file browser.                             | //nfa-vfxim-education.ahk.nl/vfxim/Library |
| `permission_group` | Permission group that is allowed to use the library importer                             | Admin                                      |


