import adsk.core
import os
from ...lib import fusionAddInUtils as futil
from ... import config
import numpy as np
app = adsk.core.Application.get()
ui = app.userInterface


CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_loadPoints'
CMD_NAME = 'Load Points'
CMD_Description = 'Load Woolumetric Points from a .npy file.\nCreates the loaded points in a new sketch.'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

INPUT_PATH = None

# Executed when add-in is run.
def start():
	# Create a command Definition.
	cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

	# Define an event handler for the command created event. It will be called when the button is clicked.
	futil.add_handler(cmd_def.commandCreated, command_created)

	# ******** Add a button into the UI so the user can run the command. ********
	# Get the target workspace the button will be created in.
	workspace = ui.workspaces.itemById(WORKSPACE_ID)

	# Get the panel the button will be created in.
	panel = workspace.toolbarPanels.itemById(PANEL_ID)

	# Create the button command control in the UI after the specified existing command.
	control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

	# Specify if the command is promoted to the main toolbar. 
	control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
	# Get the various UI elements for this command
	workspace = ui.workspaces.itemById(WORKSPACE_ID)
	panel = workspace.toolbarPanels.itemById(PANEL_ID)
	command_control = panel.controls.itemById(CMD_ID)
	command_definition = ui.commandDefinitions.itemById(CMD_ID)

	# Delete the button command control
	if command_control:
		command_control.deleteMe()

	# Delete the command definition
	if command_definition:
		command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Created Event')

	# https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
	inputs = args.command.commandInputs

	resource_folder = os.path.join(ICON_FOLDER, 'folder', '')
	inputs.addBoolValueInput('file_dialog', 'Select File', False, resource_folder, False)

	futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
	futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
	futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
	global INPUT_PATH
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Execute Event')

	design = app.activeProduct

	# Get the root component of the active design.
	rootComp = design.rootComponent

	# Create a new sketch on the xy plane.
	sketches = rootComp.sketches
	xyPlane = rootComp.xYConstructionPlane
	sketch = sketches.add(xyPlane)
	sketch.name = str(os.path.basename(INPUT_PATH)).replace('.npy', '') if INPUT_PATH else 'Error: No File Loaded'

	# Get sketch points
	sketchPoints = sketch.sketchPoints

	# Load points from .npy file
	abs_path = os.path.abspath(INPUT_PATH)
	futil.log(f'Loading points from: {abs_path}')
	points = np.load(abs_path)
	angle_arr = np.array([point[0] for point in points])
	x_arr = np.array([point[1] for point in points])
	y_arr = np.array([point[2] for point in points])

	# Convert cords from cm to mm
	x_arr *= 10
	y_arr *= 10

	# Create progress dialog
	createProgress = ui.createProgressDialog()
	createProgress.cancelButtonText = 'Cancel'
	createProgress.isBackgroundTranslucent = False
	createProgress.isCancelButtonShown = True
	createProgress.show('Creating Points', 'Percentage: %p, Point: %v', 0, len(y_arr), 0)

	for i, y in enumerate(y_arr):
		if createProgress.wasCancelled:
			break
		
		# Update progress dialog
		createProgress.progressValue = i + 1

		# Create point
		point = adsk.core.Point3D.create(x_arr[i]*0.1, y*0.1, 0)
		sketchPoints.add(point)

	# Close progress dialog
	createProgress.hide()

	adsk.doEvents()
	ui.messageBox(f'Finished creating {len(y_arr)} points from: {abs_path}', 'Finished')


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
	changed_input = args.input
	
	if changed_input.id == 'file_dialog' and changed_input.value:
		global INPUT_PATH
		file_dialog = ui.createFileDialog()
		file_dialog.isMultiSelectEnabled = False
		file_dialog.filter = 'NumPy Files (*.npy)'
		file_dialog.title = 'Select .npy file to load points from'
		if file_dialog.showOpen() == adsk.core.DialogResults.DialogOK:
			INPUT_PATH = os.path.abspath(file_dialog.filename)
			futil.log(f'Selected file: {INPUT_PATH}')
		else:
			futil.log('No file selected.')
			changed_input.value = False  # Reset the checkbox if no file was selected

	# General logging for debug.
	futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Validate Input Event')

	inputs = args.inputs

	args.areInputsValid = True  # Assume all inputs are valid to start with.

	file_dialog_input: adsk.core.BoolValueCommandInput = inputs.itemById('file_dialog')
	if not file_dialog_input.value and INPUT_PATH is None:
		args.areInputsValid = False
