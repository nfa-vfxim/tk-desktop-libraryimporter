# experimental powershell script to build Qt .ui files for SGTK
# using the pyside-uic present in Shotgun TK's python
# to run this
# powershell.exe -noprofile -executionpolicy unrestricted -file .\build_resources.ps1

$python='C:\Program Files\Shotgun\Python\python.exe'
$pyside_uic='C:\Program Files\Shotgun\Python\Scripts\pyside-uic-script.py'

function build_ui
{
    $uiname = $args[0] + '.ui'
    $pyname = $args[0] + '.py'
    & $python $pyside_uic --from-imports $uiname > $pyname
    (Get-content $pyname) | Foreach-Object {$_ -replace "^from PySide import QtCore, QtGui$", "from tank.platform.qt import QtCore, QtGui"} | Set-Content E:\shotgun\tk-desktop-libraryimporter\python\app\ui/$pyname
    Remove-Item $pyname
}

build_ui dialog
