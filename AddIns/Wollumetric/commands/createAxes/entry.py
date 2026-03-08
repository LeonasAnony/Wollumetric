import adsk.core
import os
from ...lib import fusionAddInUtils as futil
from ... import config
import sys
import math
import numpy as np
from scipy.spatial import KDTree
app = adsk.core.Application.get()
ui = app.userInterface


CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_createAxes'
CMD_NAME = 'Create Axes'
CMD_Description = 'Create perpendicular Axes to all points in selected sketch.'

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

	inputs = args.command.commandInputs

	inputs.addSelectionInput('sketch', 'Sketch', 'Select the sketch to create axes on.').addSelectionFilter('Sketches')

	futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
	futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Command Execute Event')

	inputs = args.command.commandInputs
	selection_input = inputs.itemById('sketch')

	# Get the active sketch
	sketch = selection_input.selection(0).entity if selection_input.selectionCount > 0 else None
	if not sketch or not isinstance(sketch, adsk.fusion.Sketch):
		ui.messageBox('Kein aktiver Sketch gefunden. Bitte öffne / bearbeite einen Sketch.')
		return
	
	# Sammle alle Sketchpunkte
	points = []

	sketchPoints = sketch.sketchPoints
	
	# Durchsuche alle SketchPoints im Sketch
	for i in range(sketchPoints.count):
		if i == 0:
			continue
		sketchPoint = sketchPoints.item(i)
		points.append(sketchPoint)
	
	if len(points) == 0:
		ui.messageBox('Keine Punkte im aktuellen Sketch gefunden.')
		return

	design = app.activeProduct
	rootComp = design.rootComponent
	axes = rootComp.constructionAxes

	# Referenzebene des Sketches
	refPlane = sketch.referencePlane

	# Erstelle eine offset ConstructionPlane (1 cm Abstand) als Hilfsebene
	planes = rootComp.constructionPlanes
	planeInput = planes.createInput()
	offsetValue = adsk.core.ValueInput.createByReal(100.0)  # 1 cm
	planeInput.setByOffset(refPlane, offsetValue)
	offsetPlane = planes.add(planeInput)

	# Erstelle einen Hilfs-Sketch auf der Offset-Ebene
	helperSketch = rootComp.sketches.addWithoutEdges(offsetPlane)
	helperSketch.name = '_createAxes'
	helperSketchPoints = helperSketch.sketchPoints

	# Erstelle Punkte mit 1mm z-Offset für die Achsenerstellung
	helperPoints = []
	for point in points:
		helperPoint = helperSketchPoints.add(adsk.core.Point3D.create(point.geometry.x, point.geometry.y, point.geometry.z))
		helperPoints.append(helperPoint)

	# Create progress dialog
	createProgress = ui.createProgressDialog()
	createProgress.cancelButtonText = 'Cancel'
	createProgress.isBackgroundTranslucent = False
	createProgress.isCancelButtonShown = True
	createProgress.show('Creating Axes', 'Percentage: %p, Point: %v', 0, len(points), 0)
	
	# Achsen auf allen Punkten erstellen
	for i, point in enumerate(points):
		if createProgress.wasCancelled:
			break
		# Update progress dialog
		createProgress.progressValue = i
	
		# Erstelle eine Achse durch den Original-Punkt und den projizierten Punkt
		con_axis_input = axes.createInput()
		con_axis_input.setByTwoPoints(point, helperPoints[i])
		axes.add(con_axis_input)
	
	# Close progress dialog
	createProgress.hide()

	# Hilfs-Sketch und Offset-Ebene unsichtbar machen
	helperSketch.isVisible = False
	offsetPlane.isLightBulbOn = False

	# Erfolgsmeldung
	ui.messageBox(f'{len(points)} Achsen erfolgreich erstellt!')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
	# General logging for debug.
	futil.log(f'{CMD_NAME} Validate Input Event')

	inputs = args.inputs

	args.areInputsValid = True  # Assume all inputs are valid to start with.
	
	selection_input = inputs.itemById('sketch')
	if selection_input.selectionCount == 0:
		args.areInputsValid = False
