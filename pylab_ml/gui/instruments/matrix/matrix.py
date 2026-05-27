# -*- coding: utf-8 -*-
"""
This script defines a GUI class for a matrix instrument, which is part of the PyLab-ML project. 
The GUI allows users to interact with the matrix instrument, send MQTT commands, and receive updates.

Created on Fri Jul 10 13:43:20 2020

TODO:
    Bug: in discardTable funktioniert nicht

    ate/NB200813/instruments    {"matrix": {"type": "set", "cmd": "set", "payload": ["Position1", "close"]}}

    Variablen in Gui dürfen nicht Namen benutzen die als mqtt-Kommandos benutzt werden!
"""

# todo:
#   wenn editfish_label dann in dic_constantsTable ändern, bei save mqtt senden der neuen tabelle
#   Scenarios Set werden noch nicht angezeigt
#       senden einer geänderten dic_constantsTabel + dic_connectionTable
#       farbige Darstellung von connections und wire
#   kleinere Darstellung der Matrix ....
#
import qdarkstyle
import numpy as np
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import QLabel
from pylab_ml.gui.instruments.base_instrument import Gui as Guibase
from pylab_ml.gui.instruments.base_instrument import load_ui
import functools

__author__ = "Zlin526F"
__copyright__ = "Copyright 2020, Lab"
__credits__ = ["Zlin526F"]
__email__ = "Zlin526F@github"
__version__ = "0.0.3"


class VerticalLabel(QLabel):
    """ VerticalLabel is a custom QLabel that displays text vertically. It overrides the paintEvent to rotate the text. """
    
    def __init__(self, *args):
        """Initialize the VerticalLabel."""
        QLabel.__init__(self, *args)

    def mousePressEvent(self, event):
        """Handle mouse press events on the vertical label."""
        # self.clicked.emit()
        QLabel.mousePressEvent(self, event)

    def paintEvent(self, event):
        """Handle the paint event to draw the text vertically."""
        painter = QtGui.QPainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)
        painter.drawText(0, int(self.width() / 2), self.text())
        painter.end()


class Gui(Guibase):
    """Gui class for the matrix instrument."""

    Fontsize = 8
    X_OFFSET = 5
    X_LLABELWIDTH = 30  # left text label width
    X_RLABELWIDTH = 70  # right text label width
    Y_TLABELWIDTH = 22
    RADIOBUTTONWIDTH = 14
    X_LABELHIGH = 18
    Y_TLABELHIGH = 35  # top label high
    Y_BLABELHIGH = 130  # botton label high
    Y_OFFSET = 30
    X_STEP = RADIOBUTTONWIDTH + 2
    Y_STEP = 20
    COLOR_INAKTIV = 0.6  # from 0.0-1.0 (=0-100%)
    CB_OFFSET_Y = 5
    CB_OFFSET_X = 5
    CB_SPACE_X = 10
    CB_SPACE_Y = 20
    CB_WIDTH = 150

    def __init__(self, parent=None, name="matrix", parentwindow=None):
        """
        Initialize the GUI for the matrix instrument.
        
        Parameters
        ----------
            parent: QWidget, optional
                The parent widget of the GUI.
            name: str, optional
                The name of the instrument.
            parentwindow: QWidget, optional
                The parent window of the GUI.
        """
        super().__init__(grandparent=parent, name=name, parentwindow=parentwindow)
        self.myframe = load_ui(self.gui.myframe, __file__)
        # bgcolor = self.gui.palette().color(QtGui.QPalette.Background).name()    # getRgb()
        self.myadjustUI()
        self.gui.closeEvent = self.close
        self.parent = parent

        self.instName = name
        self.subtopic = []
        self._dic_constantsTable = None
        self._dic_connectionTable = None
        self.matrix_window = None
        self.matrix_array = None
        self.geometry = self.gui.geometry
        self.width = self.gui.width
        self.height = self.gui.height

        self.lcb = []
        self.cb = []
        self.x_max = 0
        self.y_max = 0
        self._loadNames = None
        self._id = None
        self.gui.show()
        self.topinstname = ""
        self.mqtt_initlist = ["load_connectionTable()", "display()"]

    def myadjustUI(self):
        """Adjust the GUI elements for the matrix instrument."""
        self.gui.runToolBar.setVisible(False)
        # set icons:
        # self.windowIcon(qta.icon('ei.file', color='white', scale_factor=1.0, color_active='orange'))

        # create and connect Menue entries
        actiondiscardTable = QtWidgets.QAction(self.gui)
        actiondiscardTable.setText("discard Table")
        actiondiscardTable.triggered.connect(self.discardTable)
        actiondiscardTable.setEnabled(False)
        self.gui.menuSetup.addAction(actiondiscardTable)
        self.gui.actiondiscardTable = actiondiscardTable

        actiongetTable = QtWidgets.QAction(self.gui)
        actiongetTable.setText("get Table")
        actiongetTable.triggered.connect(self.load_connectionTable)
        actiongetTable.setEnabled(True)
        self.gui.menuSetup.addAction(actiongetTable)
        self.gui.actiongetTable = actiongetTable

        actionShow = QtWidgets.QAction(self.gui)
        actionShow.setText("Edit Table")
        actionShow.triggered.connect(self.show_matrix)
        actionShow.setEnabled(False)
        self.gui.menuSetup.addAction(actionShow)
        self.gui.actionShow = actionShow

        # set connection fom Gui-object to functions:
        # self.gui.actionEdit.triggered.connect(self.edit)
        self.myframe.PBclear.clicked.connect(lambda: self.publish("clear()"))

        self.gui.setWindowTitle(f' {os.path.basename(__file__).split(".")[0]}     (Version: {__version__})')
        # geometry = self.gui.geometry()
        # wh = self.myframe.geometry()
        # self.myframe.setGeometry(geometry.x(), geometry.y(), wh.width()+100, wh.height()+250)

    def create_CBox(self, index):
        """
        Create a combo box and its associated label for the given index.
        
        Parameters
        ----------
            index: int
                The index of the combo box to create.
        """
        panel = self.gui.findChild(QtWidgets.QWidget, "tabshow")
        self.lcb.append(QtWidgets.QLabel(panel))
        self.cb.append(QtWidgets.QComboBox(panel))
        lcb = self.lcb[index]
        cb = self.cb[index]
        x = index % 2
        y = index // 2
        lcb.setObjectName("label_{}".format(index))
        lcb.setGeometry(
            QtCore.QRect(
                x * (self.CB_WIDTH + self.CB_SPACE_X) + self.CB_OFFSET_X, 2 * y * self.CB_SPACE_Y, self.CB_WIDTH, 18
            )
        )
        lcb.setStyleSheet("color: rgb{}".format("0 0 0"))
        cb.setGeometry(
            QtCore.QRect(
                x * (self.CB_WIDTH + self.CB_SPACE_X) + self.CB_OFFSET_X,
                (2 * y + 1) * self.CB_SPACE_Y - self.CB_OFFSET_Y,
                self.CB_WIDTH,
                18,
            )
        )
        cb.setStyleSheet("color: rgb{}".format("0 0 0"))
        cb.activated.connect(lambda index, value=index: self._set_(value))
        # lcb.setToolTip("for editing: wait til 2099, or doit yourselve ....")
        return

    def update_mainwindow(self):
        """Update the main window of the GUI based on the current connection table and constants table."""
        index = 0
        if self.lcb != []:
            return
        for key in self._dic_connectionTable.keys():  # create the comboboxes , depends form the connectionTable
            color = self.dic_connectionTable[key]["Color"]
            self.create_CBox(index)
            self.update_CBox(index, key, color)
            values = self._dic_connectionTable[key]["List"].keys()
            cb = self.cb[index]
            cb.addItem("open")
            for value in values:
                cb.addItem(value)
            cb.setCurrentIndex(0)
            index += 1
        height = 2 * self.CB_OFFSET_Y + (index + 1) * self.CB_SPACE_Y
        width = 2 * (self.CB_WIDTH + self.CB_SPACE_X)
        self.gui.centralwidget.setGeometry(0, 0, width, height)
        title = f"     {self.x_max} x {self.y_max}"
        if self._id is not None:
            title = f"{title}  {self._id}"
        self.instNameExtension = title
        self.mqtt_status
        self.myframe.PBclear.setEnabled(True)
        self.gui.actionShow.setEnabled(True)
        self.gui.actiongetTable.setEnabled(False)
        self.gui.actiondiscardTable.setEnabled(True)
        # self.gui.setGeometry(0, 0, width+20, height+50)

    def update_CBox(self, index, name, color):
        """
        Update the combo box and its associated label for the given index, name, and color.
        
        Parameters
        ----------
            index: int
                The index of the combo box to update.
            name: str
                The name to set for the combo box and its label.
            color: tuple
                The RGB color to set for the combo box and its label.
        """
        lcb = self.lcb[index]
        cb = self.cb[index]
        lcb.setText(name)
        lcb.setStyleSheet("color: rgb{}".format(str(color)))
        lcb.show()
        cb.setObjectName("comboBox_{}".format(name))
        cb.setStyleSheet("color: rgb{}".format(str(color)))
        cb.show()

    def show_matrix(self):
        """Show the matrix window with the current connection and constants tables."""
        matrix_window = QtWidgets.QMainWindow()
        matrix_window.setWindowTitle(f"{self.instName} {self.x_max} * {self.y_max}   {self._id}")
        matrix_window.setObjectName("matrix")
        self.netname_y = [None] * (self.y_max + 1)
        self.netname_x = [None] * (self.x_max + 1)
        for nets in self._dic_constantsTable["XLables"]:
            # print(int(self._dic_constantsTable['XLables'][nets]),nets )
            self.netname_x[int(self._dic_constantsTable["XLables"][nets])] = nets
        for nets in self._dic_constantsTable["YLables"]:
            self.netname_y[int(self._dic_constantsTable["YLables"][nets])] = nets
        nets = []
        label_y = []
        label_x = []
        line_x = []
        line_y = []
        for y in range(1, self.y_max + 1):
            self.create_label(matrix_window, -1, y)  # left labels with net numbers
            label_y.append(self.create_label(matrix_window, -2, y, self.netname_y[y]))  # right labels with net names
            line_y.append(self.create_line(matrix_window, -1, y))
            for x in range(1, self.x_max + 1):
                if y == 1:
                    self.create_label(matrix_window, x, -1)  # Top labels with net numbers
                    label_x.append(
                        self.create_label(matrix_window, x, -2, self.netname_x[x])
                    )  # Bottom labels with net names
                    line_x.append(self.create_line(matrix_window, x, -1))
                nets.append(self.create_net(matrix_window, x, y))
        matrix_window.label_y = label_y
        matrix_window.label_x = label_x
        matrix_window.line_x = line_x
        matrix_window.line_y = line_y
        QtCore.QMetaObject.connectSlotsByName(matrix_window)
        self.lineEdit = QtWidgets.QLineEdit(matrix_window)
        self.lineEdit.setGeometry(QtCore.QRect(10, 10, 120, 25))
        self.lineEdit.setObjectName("lineEdit")
        self.lineEdit.editingFinished.connect(self.editfinish_label)
        self.lineEdit.hide()
        self.lineEdit.source_object = None
        self.matrix_window = matrix_window
        self.matrix_window.nets = nets
        matrix_window.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        matrix_window.setMinimumSize(
            self.X_OFFSET + (self.x_max + 1) * self.X_STEP + self.X_RLABELWIDTH + 30,
            self.Y_OFFSET + self.Y_TLABELHIGH + self.y_max * self.Y_STEP + self.Y_BLABELHIGH + 30,
        )
        self.update_matrixarray()
        self.update_matrixcolor()
        self.matrix_window.show()

    def update_matrixarray(self):
        """Update the matrix array based on the current connection table and constants table."""
        if self.matrix_window is not None:
            for y in range(0, self.y_max):
                for x in range(0, self.x_max):
                    # if self.matrix_array[y][x]==1:
                    # if y==1:
                    #    self.matrix_window.label_x[x].setStyleSheet('color: white')
                    #    self.matrix_window.label_x[row].setStyleSheet('color: rgb{}'.format(str(color)))
                    self.matrix_window.nets[y * self.x_max + x].setChecked(
                        self.matrix_array[y][x] == 1
                    )  # set connection

    def update_matrixcolor(self):
        """Update the colors of the matrix labels based on the current connection table and constants table."""
        for categorie in self.dic_connectionTable.keys():
            for scenario in self._dic_connectionTable[categorie]["List"].keys():
                color, nets = self.get_nets(categorie, scenario)
                color = self.color_inaktiv(color)
                # print(categorie,scenario,nets,color)
                for net in nets:
                    row = net[2]
                    self.matrix_window.label_x[row].setStyleSheet("color: rgb{}".format(str(color)))
                    # self.matrix_window.line_x[row].setStyleSheet('color: rgb{}'.format(str(color)))
                # for net in nets:
                # cb = self.gui.findChild(QtWidgets.QComboBox, "comboBox_{}".format(categorie))
                # color finden
                # self.matrix_window.label_x[x].setStyleSheet('color: rgb{}'.format(str(color)))

    def color_inaktiv(self, color):
        """
        Calculate the inactive color based on the given color and the COLOR_INAKTIV factor.
        
        Parameters
        ----------
            color : tuple
                The RGB color to be modified.
        
        Returns
        -------
            result : tuple
                The inactive RGB color.
        """
        color = tuple(map(int, color[1:-1].split(",")))
        result = tuple([int(self.COLOR_INAKTIV * c) for c in color])
        return result

    def get_nets(self, categorie, scenario):
        """
        Get the nets for a given category and scenario from the connection table.
        
        Parameters
        ----------
            categorie : str
                The category of the nets.
            scenario : str
                The scenario of the nets.
        
        Returns
        -------
            color : tuple
                The RGB color associated with the category.
            result : list
                A list of nets, where each net is represented as a list of three integers [x1, x2, y].
        """
        color = self.dic_connectionTable[categorie]["Color"]
        nets = self._dic_connectionTable[categorie]["List"][scenario].split(";")
        result = []
        for net in nets:
            net = net.split(",")
            if len(net) != 3:
                self.logger.error(f"{categorie} {scenario} {net} nets are not correct -> discarded")
                return -1
            result.append([int(net[0]) - 1, int(net[1]) - 1, int(net[2]) - 1])
        return color, result

    def create_net(self, form, x, y):
        """
        Create a radio button representing a net at the given x and y coordinates.
        
        Parameters
        ----------
            form : QWidget
                The parent widget for the radio button.
            x : int
                The x-coordinate of the net.
            y : int
                The y-coordinate of the net.
        
        Returns
        -------
            radioButton : QRadioButton
                The created radio button representing the net.
        """
        radioButton = QtWidgets.QRadioButton(form)
        radioButton.setGeometry(
            QtCore.QRect(
                self.X_OFFSET + self.X_LLABELWIDTH + x * self.X_STEP - 2,
                self.Y_OFFSET + self.Y_TLABELHIGH + (y - 1) * self.Y_STEP + 4,
                self.RADIOBUTTONWIDTH,
                self.RADIOBUTTONWIDTH,
            )
        )
        radioButton.setStyleSheet("QRadioButton::checked { background-color : red;}")
        radioButton.setStyleSheet("QRadioButton::indicator { width: 10px; height: 10px;};")
        # radioButton.setStyleSheet('QRadioButton::indicator \{ width: {}px; height: {}px;\};'.format(self.RADIOBUTTONWIDTH,self.RADIOBUTTONWIDTH))
        radioButton.setText("")
        radioButton.setChecked(False)
        radioButton.setAutoExclusive(False)
        radioButton.setToolTip("{}->{}".format(y, x))
        radioButton.setObjectName("net_{}_{}".format(y, x))
        return radioButton

    def create_label(self, form, x, y, text=None):
        """
        Create a label at the given x and y coordinates with the specified text.
            x== -1   -> place wire numbers left
            x== -2   -> place wire text right
            y== -1   -> pace wire number at top vertical
            y== -2   -> pace wire text at bottom vertical
        
        Parameters
        ----------
            form : QWidget
                The parent widget for the label.
            x : int
                The x-coordinate for the label. Special values:
                    -1: place wire numbers on the left
                    -2: place wire text on the right
            y : int
                The y-coordinate for the label. Special values:
                    -1: place wire numbers at the top
                    -2: place wire text at the bottom
            text : str, optional
                The text to display on the label. If None, default text will be used based on the coordinates.
                
        Returns
        -------
            label : QLabel
                The created label with the specified properties.
        """
        if x < 0:
            label = QtWidgets.QLabel(form)
            label.typ = "horizontal"
        elif y < 0:
            label = VerticalLabel(form)
            label.typ = "vertical"
        label.setFont(QtGui.QFont("Times", self.Fontsize, QtGui.QFont.Bold))
        if x == -1:  # wire numbers horizontal left
            label.setGeometry(
                QtCore.QRect(
                    self.X_OFFSET,
                    self.Y_OFFSET + self.Y_TLABELHIGH + (y - 1) * self.Y_STEP + 3,
                    self.X_LLABELWIDTH,
                    self.X_LABELHIGH,
                )
            )
        elif x == -2:  # net names horizontal.right
            label.setGeometry(
                QtCore.QRect(
                    self.X_OFFSET + (self.x_max + 1) * self.X_STEP + 40,
                    self.Y_OFFSET + self.Y_TLABELHIGH + (y - 1) * self.Y_STEP + 3,
                    self.X_RLABELWIDTH,
                    self.X_LABELHIGH,
                )
            )
        if y == -1:  # wire numbers vertical  top
            label.setGeometry(
                QtCore.QRect(
                    self.X_OFFSET + self.X_LLABELWIDTH + x * self.X_STEP - 1,
                    self.Y_OFFSET - self.Y_TLABELWIDTH,
                    self.Y_TLABELWIDTH,
                    self.Y_TLABELHIGH,
                )
            )
        elif y == -2:  # net names vertical  bottom
            label.setGeometry(
                QtCore.QRect(
                    self.X_OFFSET + self.X_LLABELWIDTH + x * self.X_STEP - 1,
                    self.Y_OFFSET + self.Y_TLABELHIGH + self.y_max * self.Y_STEP,
                    self.Y_TLABELWIDTH,
                    self.Y_BLABELHIGH,
                )
            )
        if text == "":
            text = "_"
        if text is None and x < 0:
            label.setText("{}".format(y))
            if x == -1:
                label.setToolTip("for editing: click labels at right")
        elif text is None and y < 0:
            label.setText("{}".format(x))
            if y == -1:
                label.setToolTip("for editing: click labels at bottom")
        elif text is not None:
            label.setText("{}".format(text))
        label.setObjectName("label_{}_{}".format(y, x))
        if x == -2 or y == -2:
            label.mousePressEvent = functools.partial(self.edit_label, source_object=label)
            label.setToolTip("for editing: click on label")
        return label

    def edit_label(self, event, source_object=None):
        """
        Handle the mouse press event on a label to allow editing of the label's text.
        
        Parameters
        ----------
            event : QMouseEvent
                The mouse event that triggered the label editing.
            source_object : QLabel, optional
                The label that was clicked, triggering the edit. If None, the event's source will be used.
        """
        
        if self.lineEdit.source_object is not None:
            self.editfinish_label()
        if event.button() == 1:
            y = source_object.y()
            if source_object.typ == "vertical":
                y += self.Y_BLABELHIGH - 25
            self.lineEdit.setGeometry(QtCore.QRect(source_object.x(), y, 120, 25))
            self.lineEdit.setText(source_object.text())
            self.lineEdit.source_object = source_object
            self.lineEdit.show()

    def editfinish_label(self):
        """Handle the completion of label editing by updating the label's text and hiding the line edit."""
        self.lineEdit.source_object.setText("{}".format(self.lineEdit.text()))
        self.lineEdit.hide()

    def create_line(self, form, x, y):
        """
        Create a line (horizontal or vertical) in the given form.
        
        Parameters
        ----------
            form : QWidget
                The parent widget in which the line will be created.
            x : int
                The x-coordinate or special value indicating a horizontal line (-1).
            y : int
                The y-coordinate or special value indicating a vertical line (-1).
                
        Returns
        -------
            line : QFrame
                The created line (either horizontal or vertical) with the specified properties.
        """
        line = QtWidgets.QFrame(form)
        if x == -1:  # horizontal  left, top, width and height
            line.setGeometry(
                QtCore.QRect(
                    self.X_OFFSET + self.X_LLABELWIDTH,
                    int(self.Y_OFFSET + self.Y_TLABELHIGH + (y - 1) * self.Y_STEP + self.X_LABELHIGH / 2 + 2),
                    int(self.X_OFFSET + self.x_max * self.X_STEP + 20),
                    2,
                )
            )
            line.setFrameShape(QtWidgets.QFrame.HLine)
        elif y == -1:  # vertical
            line.setGeometry(
                QtCore.QRect(
                    int(self.X_OFFSET + self.X_LLABELWIDTH + self.RADIOBUTTONWIDTH / 2 - 1 + x * self.X_STEP),
                    self.Y_OFFSET + self.Y_TLABELHIGH - 10,
                    2,
                    self.y_max * self.Y_STEP + 20,
                )
            )
            line.setFrameShape(QtWidgets.QFrame.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        line.setObjectName("line_{}_{}".format(y, x))
        return line

    def retranslateUi(self, Form):
        """Set the text for the GUI elements based on the current language settings."""
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.checkBox.setText(_translate("Form", "CheckBox"))
        self.label.setText(_translate("Form", "Label"))

    # =======================================================
    # attributes which connect to an extern call (mqtt-command)
    def mqttreceive(self, instName, msg):
        """
        Handle incoming MQTT messages and update the GUI elements accordingly.
        
        Parameters
        ----------
            instName : str
                The name of the instance sending the MQTT message.
            msg : dict
                The MQTT message containing the command and payload.
        """
        # print(instName, msg)
        if instName != self.instName and msg["cmd"] == "loadNames" and self._loadNames is None:
            self.create_CBox(len(self.lcb))
            self.update_CBox(-1, instName, (255, 255, 255))
            cb = self.cb[-1]
            self._loadNames = msg["payload"]
            for value in self._loadNames:
                cb.addItem(value)
            cb.setCurrentIndex(0)
        elif msg["cmd"] != "loadNames" and len(self.subtopic) > 0 and instName == self.subtopic[0]:
            if msg["cmd"] == "load":
                if type(msg["payload"]) is str:
                    payload = msg["payload"].split("\r")[0]
                else:
                    payload = msg["payload"]
                if self._loadNames is not None:
                    cmd = f"{msg['cmd']}={payload}"
                    for count in range(0, 2, 1):
                        if count == 1:
                            cmd = msg["cmd"]
                        if cmd in self._loadNames.values():
                            for key in self._loadNames:
                                if self._loadNames[key] == cmd:
                                    self.cb[-1].setCurrentText(key)
        elif msg["cmd"] == "show":
            values = msg["payload"]
            if len(values) == 2 and values[0] == "state":
                values = msg["payload"][1].split("\n")
                for value in values:
                    if value != "":
                        scenario = value.split(":")[0].strip()
                        state = value.split(":")[1].strip()
                        if state == "open":
                            self.set = [scenario, state]
                        else:
                            self.set = [state, "close"]

        else:
            self.logger.warning(
                f"{self.instName}.mqttreceive: {instName}, {msg}, subtopic={self.subtopic}  not implemented -> do nothing"
            )

    def reset(self):
        """Reset the GUI to its initial state by clearing the matrix array and resetting the combo boxes."""
        self.cb[-1].setCurrentIndex(0)

    @property
    def id(self):
        """Get the ID of the instrument."""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        self.instNameExtension = f"   {self.x_max} x {self.y_max} {self._id}"

    @property
    def dic_constantsTable(self):
        """Get the constants table dictionary."""
        return self._dic_constantsTable

    @dic_constantsTable.setter
    def dic_constantsTable(self, value):
        self._dic_constantsTable = value
        self.x_max = int(self._dic_constantsTable["XLength"])
        self.y_max = int(self._dic_constantsTable["YLength"])
        self.matrix_array = np.zeros((self.y_max, self.x_max))

    @property
    def dic_connectionTable(self):
        """Get the connection table dictionary."""
        return self._dic_connectionTable

    @dic_connectionTable.setter
    def dic_connectionTable(self, value):
        self._dic_connectionTable = value
        for key in self._dic_connectionTable.keys():
            # translate color from string float to rgb integer
            color = self.dic_connectionTable[key]["Color"][1:-1].split(",")
            color = int(float(color[0]) * 255), int(float(color[1]) * 255), int(float(color[2]) * 255)
            color = "({},{},{})".format(color[0], color[1], color[2])
            self.dic_connectionTable[key].update({"Color": color})
        self.update_mainwindow()

    @property
    def SetCrosspointState(self):
        """Get the current crosspoint state."""
        pass

    @SetCrosspointState.setter
    def SetCrosspointState(self, value):
        if value[0] is None:
            return
        card, y, x, state = value
        if card != 1:
            self.logger.error(
                f"{self.instName} supports only 1 Card, but received Card={card}, if you need this, please extend the software...."
            )
            return
        x -= 1
        y -= 1
        if self.matrix_array is not None:
            self.matrix_array[y][x] = int(state)
        if self.matrix_window is not None:
            self.matrix_window.nets[y * self.x_max + x].setChecked(self.matrix_array[y][x] == 1)
            self.matrix_array[int(y), int(x)] = int(state)

    @property
    def set(self):
        return

    @set.setter
    def set(self, value):
        """set Category in the comboboxes and in the matrix-window the associated color"""
        if self.dic_connectionTable is None:
            return
        scenario = value[0]
        state = value[1]
        # set color in matrix to inactiv
        if self.matrix_window is not None:
            for categorie in self.dic_connectionTable.keys():
                if scenario == categorie or scenario in self.dic_connectionTable[categorie]["List"].keys():
                    for scene in self.dic_connectionTable[categorie]["List"].keys():
                        color, nets = self.get_nets(categorie, scene)
                        color = self.color_inaktiv(color)
                        for net in nets:
                            row = net[2]
                            self.matrix_window.label_x[row].setStyleSheet("color: rgb{}".format(str(color)))
            # QCoreApplication.processEvents()
        # now set connections and the true color
        for categorie in self.dic_connectionTable.keys():
            if scenario == categorie or scenario in self.dic_connectionTable[categorie]["List"].keys():
                cb = self.gui.findChild(QtWidgets.QComboBox, "comboBox_{}".format(categorie))
                if cb is None:
                    self.logger.error("couldn't find the associated comboBox_{}".format(categorie))
                if state == "open":
                    cb.setCurrentText(state)
                else:
                    cb.setCurrentText(scenario)
                    color, nets = self.get_nets(categorie, scenario)
                    if self.matrix_window is not None:
                        for net in nets:
                            row = net[2]
                            self.matrix_window.label_x[row].setStyleSheet("color: rgb{}".format(str(color)))
                            # radioButton.setObjectName("net_{}_{}".format(y,x))
                break

    @property
    def clear(self):
        return

    @clear.setter
    def clear(self, dummy):
        self.matrix_array = np.zeros((self.y_max, self.x_max))  # clear matrix
        self.update_matrixarray()
        if len(self.cb) != 0:
            for categorie in self.dic_connectionTable.keys():  # set all comboboxes = 'open'
                cb = self.gui.findChild(QtWidgets.QComboBox, "comboBox_{}".format(categorie))
                cb.setCurrentIndex(0)
        if self.matrix_window is not None:
            for categorie in self.dic_connectionTable.keys():
                for scene in self.dic_connectionTable[categorie]["List"].keys():
                    color, nets = self.get_nets(categorie, scene)
                    color = self.color_inaktiv(color)
                    for net in nets:
                        row = net[2]
                        self.matrix_window.label_x[row].setStyleSheet("color: rgb{}".format(str(color)))

    @property
    def disconnect(self):
        return

    @disconnect.setter
    def disconnect(self, dummy):
        self.discardTable()

    # end extern calling attributes
    # ======================================================================================
    #
    # connected GUI-function to buttons or menues
    #
    def _set_(self, pos):
        """Handle the activation of a combo box and publish the corresponding command based on the selected scenario."""
        if self.subtopic != [] and self._loadNames is not None and pos == len(self.cb) - 1:
            cmd = self._loadNames[self.cb[pos].currentText()]
            cmd = cmd.split("=")
            value = "" if len(cmd) == 1 else cmd[1]
            cmd = cmd[0]
            self.publish(cmd, value, instName=self.subtopic[0])
        else:
            categorie = self.lcb[pos].text()
            scenario = self.cb[pos].currentText()
            if scenario == "open":
                state = "open"
                value = categorie
            else:
                state = "close"
                value = scenario
            self.publish("set()", (value, state))

    def edit(self):
        """Handle the editing of the matrix by enabling the tab edit and allowing the user to modify the connection and constants tables."""
        self.gui.tabedit.setEnabled(True)

    def close(self, event=None):
        """Handle the closing of the GUI by closing the matrix window and the main GUI window if necessary."""
        super().close()
        if self.matrix_window is not None:
            self.matrix_window.close()
        if event is None:
            self.gui.close()

    def load_connectionTable(self):
        """Handle the loading of the connection table by publishing the corresponding command to retrieve the connection table data."""
        self.publish("load_connectionTable()")
        # if len(self.subtopic) > 0:
        #    self.parent.publish_get(self.subtopic[0], 'loadNames')

    def discardTable(self):
        """Handle the discarding of the table by resetting the instance name extension, MQTT status, and deleting all combo boxes."""
        self.instNameExtension = ""
        self.mqtt_status
        for lcb in self.lcb:
            lcb.deleteLater()
            lcb = None
        for cb in self.cb:
            cb.destroy()
            cb.deleteLater()
            cb = None
        self.lcb = []
        self.cb = []
        self._dic_constantsTable = None
        self._dic_connectionTable = None
        self.myframe.PBclear.setEnabled(False)
        self.gui.actionShow.setEnabled(False)
        self.gui.actiongetTable.setEnabled(True)
        self.gui.actiondiscardTable.setEnabled(False)


if __name__ == "__main__":
    import sys

    # from pytestsharing.instruments.mqtt_client import mqtt_init

    # broker = 127.0.0.1'
    # message_client = 'ate/DT1604092/matrix'
    # mqttclient = mqtt_init()                                                 # prepare mqtt
    # mqttclient.init(None, message_client=message_client.split('/')[0])    # mqtt client connect to broker
    # mqttclient.init()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = Gui(app)
    app.exec_()
    # window.scope.anim.event_source.stop()
