#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

from ast import Delete
from typing import OrderedDict
from xmlrpc.client import Boolean
import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk
import os
import sys
from collections import OrderedDict

def N_(message): return message
def _(message): return GLib.dgettext(None, message)

class ArgsFromDict:
    def __init__(self, **entries):
        self.__dict__.update(entries)

class Plugin (Gimp.PlugIn):
    def __init__(self):
        GimpUi.init("TilesFinder.py")
        path:str = os.path.dirname(os.path.realpath(__file__))
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(path, "ui.glade"))
        self.image = None

    ## GimpPlugIn virtual methods ##
    def do_query_procedures(self):
        return [ "fl-tile-selector-python" ]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(self, name,
                                            Gimp.PDBProcType.PLUGIN,
                                            self.run, None)

        procedure.set_image_types("RGB*")
        procedure.set_sensitivity_mask (Gimp.ProcedureSensitivityMask.DRAWABLE)

        procedure.set_menu_label(_("Tile selector"))
        procedure.set_icon_name(GimpUi.ICON_GEGL)
        procedure.add_menu_path('<Image>/Filters/My Scripts/')

        procedure.set_documentation(_("Tile selector"),
                                    _("Select the tile of the given address (hexadecimal value)"),
                                    name)
        procedure.set_attribution("Fabrice", "Lambert", "2025")
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        try:
            if len(drawables) != 1:
                msg = _("Procedure '{}' only works with one drawable." + str(len(drawables))).format(procedure.get_name())
                error = GLib.Error.new_literal(Gimp.PlugIn.error_quark(), msg, 0)
                return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, error)

            if run_mode == Gimp.RunMode.INTERACTIVE:
                self.image = image
                self.builder.get_object("Dialog").show()
                result = self.handleEvents()
        except Exception as e:
            Gimp.message("Exception: " + str(e))
            return procedure.new_return_values(Gimp.PDBStatus.EXECUTION_ERROR, GLib.Error())
        return procedure.new_return_values(result, GLib.Error())

    def handleEvents(self)->Gtk.ResponseType:
        dialog = self.builder.get_object("Dialog")
        result = Gimp.PDBStatusType.SUCCESS
        loop = True
        while (loop):
            response = dialog.run()
            if ((response == Gtk.ResponseType.CANCEL) or (response == Gtk.ResponseType.DELETE_EVENT)):
                dialog.destroy()
                result = Gimp.PDBStatusType.CANCEL
                loop = False
            elif (response == Gtk.ResponseType.OK):
                context = self.getInput()
                if(self.checkInput(context)):
                    self.execute(context)
                    loop = False
                else:
                    self.messageBox("Please enter an hexadecimal address")
                    loop = True
        return result

    def messageBox(self, message:str):
        dialog = self.builder.get_object("MessageBox")
        label = self.builder.get_object("Message")
        label.set_text(message)
        loop = True
        while(loop):
            response = dialog.run()
            if((response == Gtk.ResponseType.OK)  (response == Gtk.ResponseType.DELETE_EVENT)):
                dialog.destroy()
                loop = False


    def getInput(self):
        return ArgsFromDict(**{
            'address' : self.builder.get_object("Address").get_text(),
            'tileWidth' : self.builder.get_object("TileWidth").get_value_as_int(),
            'tileHeight' : self.builder.get_object('TileHeight').get_value_as_int(),
            'image' : self.image,
            })

    def checkInput(self, context):
        if (context.address == ""):
            return False
        try:
            int(context.address, 16)
            return True
        except ValueError:
            return False

    def execute(self, context):
        address = int(context.address, 16)
        columns = context.image.get_width() / context.tileWidth
        x, y = self.getCoordinates(address, columns)
        x = x * context.tileWidth
        y = y * context.tileHeight
        context.image.select_rectangle(Gimp.ChannelOps.REPLACE, x, y, context.tileWidth, context.tileHeight)

    def getCoordinates(self, address, columns):
        y = address // columns
        x = address % columns
        return x, y


Gimp.main(Plugin.__gtype__, sys.argv)
