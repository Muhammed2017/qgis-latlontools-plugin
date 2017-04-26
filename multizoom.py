import os
import re

from PyQt4 import QtGui, uic
from PyQt4.QtGui import QFileDialog, QHeaderView
from PyQt4.QtCore import *
from qgis.core import *
from qgis.gui import *
from LatLon import LatLon

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/multiZoomDialog.ui'))


class MultiZoomWidget(QtGui.QDialog, FORM_CLASS):
    '''Multizoom Dialog box.'''
    def __init__(self, lltools, settings, parent):
        super(MultiZoomWidget, self).__init__(parent)
        self.setupUi(self)
        self.settings = settings
        self.iface = lltools.iface
        self.canvas = self.iface.mapCanvas()
        self.lltools = lltools
        
        self.doneButton.clicked.connect(self.closeDialog)
        self.browseButton.clicked.connect(self.browseDialog)
        self.saveButton.clicked.connect(self.saveDialog)
        self.addButton.clicked.connect(self.addSingleCoord)
        self.removeButton.clicked.connect(self.removeTableRow)
        self.coordTxt.returnPressed.connect(self.addSingleCoord)
        self.clearAllButton.clicked.connect(self.clearAll)
        self.createLayerButton.clicked.connect(self.createLayer)
        self.dirname = ''
        self.numcoord = 0
        self.maxResults = 1000
        self.resultsTable.setColumnCount(3)
        self.resultsTable.setSortingEnabled(False)
        self.resultsTable.setHorizontalHeaderLabels(['Label','Latitude','Longitude'])
        self.resultsTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.resultsTable.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.resultsTable.cellClicked.connect(self.itemClicked)
        self.resultsTable.cellChanged.connect(self.cellChanged)
        self.resultsTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.llitems=[]

    def closeEvent(self, event):
        self.closeDialog()
        
    def closeDialog(self):
        self.resultsTable.clearSelection()
        self.removeMarkers()
        self.hide()
        
    def clearAll(self):
        self.removeMarkers()
        self.llitems=[]
        self.resultsTable.setRowCount(0)
        self.numcoord = 0
        
    def removeMarkers(self):
        if self.numcoord == 0:
            return
        for item in self.llitems:
            if item.marker is not None:
                self.canvas.scene().removeItem(item.marker)
                item.marker = None
        
    def browseDialog(self):
        filename = QFileDialog.getOpenFileName(None, "Input Lat,Lon File", 
                self.dirname, "Lat,Lon File (*.csv *.txt)")
        if filename:
            self.dirname = os.path.dirname(filename)
            self.readFile(filename)
        
    def saveDialog(self):
        filename = QFileDialog.getSaveFileName(None, "Save Lat,Lon File", 
                self.dirname, "Lat,Lon File (*.csv)")
        if filename:
            self.dirname = os.path.dirname(filename)
            self.saveFile(filename)
            
    def readFile(self, fname):
        '''Read a file of coordinates and add them to the list.'''
        try:
            with open(fname) as f:
                for line in f:
                    try:
                        parts = [x.strip() for x in line.split(',')]
                        if len(parts) == 2:
                            lat = LatLon.parseDMSStringSingle(parts[0])
                            lon = LatLon.parseDMSStringSingle(parts[1])
                            self.addCoord(lat, lon, '')
                        elif len(parts) == 3:
                            lat = LatLon.parseDMSStringSingle(parts[1])
                            lon = LatLon.parseDMSStringSingle(parts[2])
                            self.addCoord(lat, lon, parts[0])
                    except:
                        pass
        except:
            pass
    
    def saveFile(self, fname):
        '''Save the zoom locations'''
        if self.numcoord == 0:
            return
        with open(fname,'w') as f:
            for item in self.llitems:
                s = "{},{},{}\n".format(item.label, item.lat, item.lon)
                f.write(s)
        f.close()
            
        
    def removeTableRow(self):
        '''Remove an entry from the coordinate table.'''
        row = int(self.resultsTable.currentRow())
        if row < 0:
            return
        self.resultsTable.removeRow(row)
        del self.llitems[row]
        self.resultsTable.clearSelection()
        self.numcoord -= 1
        
    
    def addSingleCoord(self):
        '''Add a coordinate that was pasted into the coordinate text box.'''
        parts = [x.strip() for x in self.coordTxt.text().split(',')]
        label = ''
        try:
            if len(parts) == 2:
                lat = LatLon.parseDMSStringSingle(parts[0])
                lon = LatLon.parseDMSStringSingle(parts[1])
            elif len(parts) == 3:
                label = parts[0]
                lat = LatLon.parseDMSStringSingle(parts[1])
                lon = LatLon.parseDMSStringSingle(parts[2])
            else:
                self.iface.messageBar().pushMessage("", "Invalid Coordinate" , level=QgsMessageBar.WARNING, duration=3)
                return
        except:
            if self.coordTxt.text():
                self.iface.messageBar().pushMessage("", "Invalid Coordinate" , level=QgsMessageBar.WARNING, duration=3)
            return
        self.addCoord(lat, lon, label)
        self.coordTxt.clear()
        
    def addCoord(self, lat, lon, label):
        '''Add a coordinate to the list.'''
        if self.numcoord >= self.maxResults:
            return
        self.resultsTable.insertRow(self.numcoord)
        self.llitems.append(LatLonItem(lat, lon, label))
        self.resultsTable.blockSignals(True)
        self.resultsTable.setItem(self.numcoord, 0, QtGui.QTableWidgetItem(label))
        item = QtGui.QTableWidgetItem(str(lat))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.resultsTable.setItem(self.numcoord, 1, item)
        item = QtGui.QTableWidgetItem(str(lon))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.resultsTable.setItem(self.numcoord, 2, item)
        self.resultsTable.blockSignals(False)
        self.numcoord += 1
        
    def itemClicked(self, row, col):
        '''An item has been click on so zoom to it'''
        self.removeMarkers()
        selectedRow = self.resultsTable.currentRow()
        # Call the the parent's zoom to function
        pt = self.lltools.zoomTo(self.settings.epsg4326, self.llitems[selectedRow].lat,self.llitems[selectedRow].lon)
        if self.llitems[selectedRow].marker == None:
            self.llitems[selectedRow].marker = QgsVertexMarker(self.canvas)
        self.llitems[selectedRow].marker.setCenter(pt)
        self.llitems[selectedRow].marker.setIconSize(18)
        self.llitems[selectedRow].marker.setPenWidth(2)
        self.llitems[selectedRow].marker.setIconType(QgsVertexMarker.ICON_CROSS)
        
    def cellChanged(self, row, col):
        if col == 0:
            self.llitems[row].label = self.resultsTable.item(row, col)
            
    def createLayer(self):
        '''Create a memory layer from the zoom to locations'''
        if self.numcoord == 0:
            return
        ptLayer = QgsVectorLayer("Point?crs=epsg:4326", u"Lat Lon Locations", "memory")
        provider = ptLayer.dataProvider()
        provider.addAttributes([QgsField("label", QVariant.String),
            QgsField("latitude", QVariant.Double),
            QgsField("longitude", QVariant.Double)])
        ptLayer.updateFields()
        
        for item in self.llitems:
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(item.lon,item.lat)))
            feature.setAttributes([item.label, item.lat, item.lon])
            provider.addFeatures([feature])
        
        ptLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(ptLayer)
        
class LatLonItem():
    def __init__(self, lat, lon, label=u''):
        self.lat = lat
        self.lon = lon
        self.label = label
        self.marker = None