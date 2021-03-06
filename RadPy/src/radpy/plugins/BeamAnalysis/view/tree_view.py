################################################################################
# Copyright (c) 2011, Stephen Terry and RadPy contributors
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are 
# met: 
# 
# 1. Redistributions of source code must retain the above copyright 
# notice, this list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright 
# notice, this list of conditions and the following disclaimer in the 
# documentation and/or other materials provided with the distribution. 
# 3. The name of Stephen Terry may not be used to endorse or promote products 
# derived from this software without specific prior written permission. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS 
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED 
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT 
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED 
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING 
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
# 
# RADPY IS NOT CERTIFIED AS A MEDICAL DEVICE.  IT IS INTENDED ONLY FOR RESEARCH 
# PURPOSES.  ANY OTHER USE IS ENTIRELY AT THE DISCRETION AND RISK OF THE USER.
################################################################################

# This tree model class is based heavily on the tree model class in 
# "Rapid GUI Programming with Qt and Python" by Mark Summerfield.  
# Chapter 16 of that book in the section titled "Representing Tabular
# Data in Trees" provides the best description of the operation of this
# class.   

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy

import Model as Model
COLUMNS = ['Plot Type', 'Depth']
from radpy.plugins.BeamAnalysis.view.ChacoPlot import ChacoPlot, ChacoPlotEditor
from radpy.plugins.BeamAnalysis.view.Plot3D import Plot3D, Plot3DEditor
from radpy.plugins.BeamAnalysis.preferences.api import BeamAnalysisPreferencesHelper
from radpy.plugins.BeamAnalysis.view.beam_xml import Beam

# Enthought library imports.
from enthought.pyface.workbench.api import View
from enthought.traits.api import HasTraits, Str, List, Dict
from enthought.traits.ui.api import Item, SetEditor
from enthought.traits.ui.api import View as TraitsView
from enthought.traits.ui.menu import OKButton, CancelButton

class MatchDialog(HasTraits):
    choices = List(Str)
    selection = List(Str)
    
    view = TraitsView(Item('selection', editor=SetEditor(name='choices',
                    can_move_all=True, ordered=False),show_label=False),
                    buttons = [OKButton, CancelButton],kind='modal',
                    title='Parameters to match')


    


class TreeWidget(QTreeView):
    #The window that organizes scans from opened files in a tree
    #structure.  The branches of the tree are defined by the 
    #COLUMNS global variable defined at the top of this file.
    #activate_event = Event
    
    def __init__(self, parent=None):
        super(TreeWidget, self).__init__(parent)
        self.setSelectionBehavior(QTreeView.SelectItems)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        
        model = Model.TreeModel(COLUMNS, self)
        
        #The ProxyModel acts as a wrapper to the underlying
        #tree model and enables custom sorting of tree columns.
        #For example, it can sort field sizes by equivalent 
        #square instead of strictly alphabetically.
        proxy = Model.ProxyModel(self)
        proxy.setDynamicSortFilter(True)
        proxy.setSourceModel(model)
        self.setModel(proxy)
        
        
        self.connect(self, SIGNAL("activated(QModelIndex)"),
                     self.activated)
        self.connect(self, SIGNAL("expanded(QModelIndex)"),
                     self.expanded)
        
        #self.load("radpy/plugins/BeamAnalysis/view/RFB/Unit Tests/Test1.rfb")
        #self.load("c:/users/steve/desktop/xml test/test.xml")
        #self.load("radpy/plugins/BeamAnalysis/view/DicomRT/tests/3d_dose_wedge.dcm")
        #self.load('e:/trilogy09')
        self.expanded()
        
    def load(self, filename):
        #Passes lists of scans to tree model class.
        nesting = 5
        try:
            progress = QProgressBar()
            self.model().load(filename, nesting, COLUMNS, progress=progress)
        except IOError, e:
            QMessageBox.warning(self, "Server Info - Error",
                                unicode(e))
            
    def currentFields(self):
        return self.model().asRecord(self.currentIndex())


    def activated(self, index):
       
        self.emit(SIGNAL("activated"), self.model().asRecord(index))
        #self.activated = self.model().asRecord(index)

    def expanded(self):
        for column in range(self.model().columnCount(QModelIndex())):
            self.resizeColumnToContents(column)
            
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        if isinstance(self.model().nodeFromIndex(self.currentIndex()),
                      Model.LeafNode):
                     
            addAction = menu.addAction("&Add to plot")        
            self.connect(addAction, SIGNAL("triggered()"), self.addPlot)
            
            editAction = menu.addAction("&Edit beam parameters")
            self.connect(editAction, SIGNAL("triggered()"), self.editTraits)
            
            delAction = menu.addAction("&Remove beam")
            self.connect(delAction, SIGNAL("triggered()"), self.delBeam)
            
        else:
            
            addMultiAction = menu.addAction("&Add all to plot")
            self.connect(addMultiAction, SIGNAL("triggered()"), self.addMultiPlot)
            
            addAsRefAction = menu.addAction("Add &matching beams")
            self.connect(addAsRefAction, SIGNAL("triggered()"), self.addAsRef)
            
            editAllAction = menu.addAction("&Edit parameters for all beams")
            self.connect(editAllAction, SIGNAL("triggered()"), self.editAll)
            
            delAction = menu.addAction("&Close")
            self.connect(delAction, SIGNAL("triggered()"), self.delBeam)
            
        menu.exec_(event.globalPos())
        
    def editAll(self):
        
        global_beam = Beam()
        beams = self.model().asRecord(self.currentIndex())
        global_dict = global_beam.trait_get()
        for key in global_dict.keys():
            if key == 'Data_Abscissa' or key == 'Data_Ordinate':
                continue
            traits = [getattr(beam[1], key) for beam in beams]
            #Test if all traits in the list are the same
            if all(traits[0] == trait for trait in traits):
                setattr(global_beam, key, traits[0])
                
        #removeRecord returns True if the root node is deleted.  This will
        #require a reset of the TreeView.  (the second parameter of addRecord
        #must be True)
        root_reset = self.model().removeRecord(self.currentIndex())
        
        #Since traitsUI windows cannot be set to be application modal, the
        #tree view must be disabled to prevent the user from making changes
        #to the tree model during editing.  Allowing changes can lead to 
        #unexpected behavior.
        self.setEnabled(False)
        global_beam.edit_traits()
        self.setEnabled(True)
        
        global_dict = global_beam.trait_get()
        for beam in beams:
            for key in global_dict.keys():
                if key == 'Data_Abscissa' or key == 'Data_Ordinate':
                    continue
                try:
                    global_val = getattr(global_beam, key)
                    trait_val = getattr(beam[1], key)
                    if  global_val != trait_val and not global_beam.is_null(key):
                        setattr(beam[1], key, global_val)
                except AttributeError:
                    pass
            self.model().addRecord(beam[1], root_reset)
            
    def delBeam(self):
        
        self.model().removeRecord(self.currentIndex())
        
    def editTraits(self):
        index = self.currentIndex()
        beam = self.currentFields()[1]
        self.model().removeRecord(index=index) 
        
        #Since traitsUI windows cannot be set to be application modal, the
        #tree view must be disabled to prevent the user from making changes
        #to the tree model during editing.  Allowing changes can lead to 
        #unexpected behavior.
        self.setEnabled(False)
        beam.edit_traits()
        self.setEnabled(True)
        
        self.model().addRecord(beam, False)

    def addPlot(self):
        self.emit(SIGNAL("activated"), self.currentFields())
        
    def addMultiPlot(self):
        temp  = self.model().asRecord(self.currentIndex())
        for i in temp:
            self.emit(SIGNAL('activated'), i)
    
    def addAsRef(self):
        
        helper = BeamAnalysisPreferencesHelper()
        choices = {'Energy':'BeamDetails_Energy',
                   'Field Size':'field_size',
                   'Scan Type':'scan_type',
                   'SSD':'BeamDetails_SSD',
                   'Wedge Angle':'BeamDetails_Wedge_Angle',
                   'Applicator':'BeamDetails_Applicator',
                   'Linac Model':'BeamDetails_RadiationDevice_Model',
                   'Depth': 'depth'}
        
        dialog = MatchDialog(choices=choices.keys())
        dialog.selection = helper.match_traits
        
        #Since traitsUI windows cannot be set to be application modal, the
        #tree view must be disabled to prevent the user from making changes
        #to the tree model during editing.  Allowing changes can lead to 
        #unexpected behavior.
        self.setEnabled(False)
        dialog.configure_traits()
        self.setEnabled(True)
        
        match_traits = [choices[x] for x in dialog.selection[:]]
        helper.match_traits = dialog.selection
        helper.preferences.flush()
        
        temp  = self.model().asRecord(self.currentIndex())
        for i in temp:
            self.emit(SIGNAL('reference'), i, match_traits)
            
   
class TreeView(View):
    
    name = 'Tree View'
    id = 'radpy.plugins.BeamAnalysis.TreeView'         
    def __init__(self, *args, **kwds):    
        super(TreeView, self).__init__()
        self.widget = TreeWidget()
        QObject.connect(self.widget, SIGNAL('activated'),self.activated)
        QObject.connect(self.widget, SIGNAL('reference'), self.reference)
        
#        #If there is no plot editor window, open one
#        if self.window.active_editor is None:
#            plot = ChacoPlot()
#            self.window.workbench.edit(plot, kind=ChacoPlotEditor)

    def reference(self, record, parameters):
        label, beam = record
        if (self.window.active_editor) is not None and isinstance(
                                        self.window.active_editor.obj,ChacoPlot):
            #Check all beams in the active window to see if there is a match
            for i in self.window.active_editor.obj.beams.values():
#                traits_to_match =  beam.trait_get(parameters)
                traits_to_match = i.trait_get(parameters)
                try:
#                    if i.does_it_match(traits_to_match):
                    if beam.does_it_match(traits_to_match):
                        if beam.get_scan_descriptor()[0] == 'Dicom_3D_Dose':
                            start = [float(i.MeasurementDetails_StartPosition_x),
                                     float(i.MeasurementDetails_StartPosition_y),
                                     float(i.MeasurementDetails_StartPosition_z)]
                            stop = [float(i.MeasurementDetails_StopPosition_x),
                                    float(i.MeasurementDetails_StopPosition_y),
                                     float(i.MeasurementDetails_StopPosition_z)]
                            axis_len = len(i.Data_Abscissa)
                            ref_beam = beam.get_beam(start, stop, axis_len)
                            
                            #Setup new beam object label/tree path.
                            new_label = label.split('|')[:-2]                         
                            new_label.extend(ref_beam.get_scan_descriptor())                        
                            label = '|'.join(new_label).replace(' ','_')
                        
                        else:
                            ref_beam = beam                       
                        title = self.window.active_editor.obj.add_plot(label, ref_beam)
                        if title is not None:
                            self.window.active_editor.name = title
                except NotImplementedError:
                    pass
                except ValueError as e:
                    QMessageBox.warning(self.widget, "Warning", unicode(e))
            
        
    def activated(self, record):
        """ Adds the selected beam object to the active Chaco Plot editor.  If
        there is no active window, it creates one first.  If the active editor
        is not the right scan type (crossplane etc.) then it creates a new one.
        """
        
        label, beam = record
        scan_type = beam.get_scan_type()
        if scan_type == 'Dicom 3D Dose':
            scan_type_list = [scan_type]
        else:
            scan_type_list = ['None', scan_type]
        if self.window.active_editor is not None:
            
            if self.window.active_editor.obj.plot_type in scan_type_list:
                title = self.window.active_editor.obj.add_plot(label, beam)
                if title is not None:
                    self.window.active_editor.name = title
            else:
                self.create_new_plot_editor(label, beam)
        
        #If the tree view is undocked, there may not be an active_editor 
        #property, even if there is an active editor. 
          
        elif len(self.window.editors) > 0:   
            
            if self.window.editors[-1].obj.plot_type in scan_type_list:
                title = self.window.editors[-1].obj.add_plot(label, beam)
                if title is not None:
                    self.window.editors[-1].name = title
            else: 
                self.create_new_plot_editor(label, beam)
        
        else:
            
            self.create_new_plot_editor(label, beam)
            
        self.window.status_bar_manager.message = label
          
    def create_new_plot_editor(self, label, beam):
        """Create new ChacoPlot editor window"""
        if beam.get_scan_descriptor()[0] == "Dicom_3D_Dose":
            plot = Plot3D()
            self.window.workbench.edit(plot, kind=Plot3DEditor)
        else:   
            plot = ChacoPlot()
            self.window.workbench.edit(plot, kind=ChacoPlotEditor)
        title = self.window.editors[-1].obj.add_plot(label, beam)
        self.window.editors[-1].name = title
        self.window.editors[-1].set_focus()
        
    

    #### Methods ##############################################################

    def create_control(self, parent):
        #self._qt4_dock.setStyleSheet('QDockWidget {font: bold 14pt "Calibri"} QDockWidget::title {background-color: #c08e8b}')
        return self.widget
        
    

#### EOF ######################################################################
