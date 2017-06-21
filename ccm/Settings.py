# -*- coding: UTF-8 -*-

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors: Quinn Storm (quinn@beryl-project.org)
#          Patrick Niklaus (patrick.niklaus@student.kit.edu)
#          Guillaume Seguin (guillaume@segu.in)
#          Christopher Williams (christopherw@verizon.net)
#          Sorokin Alexei (sor.alexei@meowr.ru)
# Copyright (C) 2007 Quinn Storm

from gi.repository import GObject, Gtk, Gdk, GLib
from gi.repository import Pango, PangoCairo
import os

from ccm.Constants import *
from ccm.Conflicts import *
from ccm.Widgets import *
from ccm.Utils import *
from ccm.Pages import *
from ccm.Cursors import *

import locale
import gettext

locale.setlocale(locale.LC_ALL, "")
gettext.bindtextdomain("ccsm", DataDir + "/locale")
gettext.textdomain("ccsm")
_ = gettext.gettext

NAItemText = _("N/A")


class Setting(object):

    NoneValue = ''

    def __init__(self, Setting=None, Settings=None, List=False):
        self.Setting = Setting
        self.Settings = Settings # for multi-list settings
        self.List = List
        if List:
            self.CurrentRow = None

        self.Blocked = 0
        self.EBox = Gtk.EventBox()
        self.Box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.EBox.set_visible_window(False)
        if Setting:
            self.EBox.set_sensitive(not Setting.ReadOnly)
        self.Box.set_spacing(5)
        self.EBox.add(self.Box)
        self.Reset = Gtk.Button()
        if not Settings:
            self.MakeLabel()
            markup = "%s\n<small><i>%s</i></small>" % \
                     (protect_pango_markup(self.Setting.LongDesc),
                      protect_pango_markup(self.Setting.Name))
            self.EBox.set_tooltip_markup(markup)
            self.Reset.set_tooltip_text(_("Reset setting to the default value"))
        self.Reset.set_image(Gtk.Image.new_from_icon_name("edit-clear",
                                                          Gtk.IconSize.BUTTON))
        self.Reset.connect('clicked', self.DoReset)
        self._Init()

        self.EBox.connect("destroy", self.OnDestroy)

        self.AddUpdater()

    def AddUpdater(self):
        GlobalUpdater.Append(self)

    def RemoveUpdater(self):
        GlobalUpdater.Remove(self)

    def OnDestroy(self, widget):
        self.RemoveUpdater()

    def GetColumn(self, num):
        return (str, Gtk.TreeViewColumn(self.Setting.ShortDesc, Gtk.CellRendererText(), text=num))

    def PureVirtual (self, func):
        message = "Missing %(function)s function for %(name)s setting (%(class)s)"

        msg_dict = {'function': func,
                    'name': self.Setting.Name,
                    'class': self}

        value = message % msg_dict
        raise PureVirtualError(value)

    def _Init(self):
        self.PureVirtual('_Init')

    def DoReset(self, foo):
        self.Setting.Reset()
        self.Setting.Plugin.Context.Write()
        self.Read()

    def MakeLabel(self):

        if not self.Setting:
            return

        label = Gtk.Label()
        desc = protect_pango_markup (self.Setting.ShortDesc)
        style = "%s"
        if self.Setting.Integrated:
            style = "<i>%s</i>"
        label.set_markup(style % desc)
        label.props.xalign = 0
        label.set_max_width_chars(-1)
        label.set_size_request(160, -1)
        label.props.wrap_mode = Pango.WrapMode.WORD
        label.set_line_wrap(True)
        self.Label = label

    def Block(self):
        self.Blocked += 1

    def UnBlock(self):
        self.Blocked -= 1

    def Read(self):
        self.Block()
        self._Read()
        self.UnBlock()

    def _Read(self):
        self.PureVirtual('_Read')

    def Changed(self, *args, **kwargs):
        if self.Blocked <= 0:
            self._Changed()
            self.Setting.Plugin.Context.Write()

    def _Changed(self):
        self.PureVirtual('_Changed')

    def Get(self):
        if self.List:
            if self.CurrentRow is not None:
                return self.Setting.Value[self.CurrentRow]
            else:
                return self.NoneValue
        else:
            return self.Setting.Value

    def GetForRenderer(self):
        return self.Setting.Value

    def Set(self, value):
        if self.List:
            if self.CurrentRow is not None:
                vlist = self.Setting.Value
                vlist[self.CurrentRow] = value
                self.Setting.Value = vlist
        else:
            self.Setting.Value = value

    def Swap(self, a, b):
        vlist = self.Setting.Value
        vlist.insert(b, vlist.pop(a))
        self.Setting.Value = vlist

    def _SetHidden(self, visible):

        self.EBox.set_no_show_all(not visible)

        if visible:
            self.EBox.show()
        else:
            self.EBox.hide()

    def _Filter(self, text, level):
        visible = False
        if text is not None:
            if level & FilterName:
                visible = (text in self.Setting.Name.lower()
                    or text in self.Setting.ShortDesc.lower())
            if not visible and level & FilterLongDesc:
                visible = text in self.Setting.LongDesc.lower()
            if not visible and level & FilterValue:
                visible = text in str(self.Setting.Value).lower()
        else:
            visible = True
        return visible

    def Filter(self, text, level=FilterAll):
        visible = self._Filter(text, level=level)
        self._SetHidden(visible)
        return visible

    def __hash__(self):
        if self.Setting is not None:
            return hash(self.Setting)
        else:
            raise TypeError

class StockSetting(Setting):

    def _Init(self):
        self.Box.pack_start(self.Label, False, False, 0)
        self.Box.pack_end(self.Reset, False, False, 0)

class StringSetting(StockSetting):
    def _Init(self):
        StockSetting._Init(self)
        self.Entry = Gtk.Entry()
        self.Entry.connect('activate', self.Changed)
        self.Entry.connect('focus-out-event', self.Changed)
        self.Widget = self.Entry
        self.Box.pack_start(self.Widget, True, True, 0)

    def _Read(self):
        self.Entry.set_text(self.Get())

    def _Changed(self):
        self.Set(self.Entry.get_text())

class MatchSetting(StringSetting):
    def _Init(self):
        StringSetting._Init(self)
        self.MatchButton = MatchButton(self.Entry)
        self.Box.pack_start(self.MatchButton, False, False, 0)

class FamilyStringSetting(StockSetting):
    def _Init(self):
        StockSetting._Init(self)

        self.PreviewEntry = Gtk.Entry()
        self.PreviewEntry.set_text(_("The Quick Brown Fox Jumps Over The Lazy Dog"))
        self.PreviewEntry.set_property("editable", False)

        self.font_button = Gtk.FontButton()
        self.font_button.set_use_font(True)
        self.font_button.set_show_size(True)
        self.font_button.set_use_size(False)
        self.font_button.connect('font-set', self.Changed)
        self.Box.pack_start(self.PreviewEntry, True, True, 0)
        self.Box.pack_start(self.font_button, False, False, 0)

    def DoReset(self, foo):
        StockSetting.DoReset(self, foo)

    def _Read(self):
        self.font_button.set_font_name(self.Get())
        self._Changed()

    def _Changed(self):
        font_button = self.font_button
        CurrFont = font_button.get_font_name()
        font_desc = Pango.FontDescription(CurrFont)
        if Gtk.check_version(3, 0, 0) is None:
            tmpStyle = self.PreviewEntry.get_style_context()
            fd = tmpStyle.get_property("font", tmpStyle.get_state()).copy()
        else:
            tmpStyle = self.PreviewEntry.get_style()
            fd = tmpStyle.font_desc.copy()

        fd.set_family(font_desc.get_family())
        fd.set_style(font_desc.get_style())
        fd.set_weight(font_desc.get_weight())

        if GTK_VERSION >= (3, 0, 0):
            self.PreviewEntry.override_font(fd)
        else:
            self.PreviewEntry.modify_font(fd)

        self.Set(CurrFont)

class FileStringSetting(StringSetting):

    def __init__(self, setting, List=False, isImage=False, isDirectory=False):
        self.isImage = isImage
        self.isDirectory = isDirectory
        StringSetting.__init__(self, setting, List=List)

    def _Init(self):
        self.Msg = ""
        StringSetting._Init(self)
        self.FileButton = FileButton(self.Setting.Plugin.Context, self.Entry,
            self.isDirectory, self.isImage)
        if self.isImage and has_mate_desktop:
            size_normal = MateDesktop.DesktopThumbnailSize.NORMAL
            self.thumbnailer = MateDesktop.DesktopThumbnailFactory.new(size_normal)
            self.BtnPixmap = None
            self.NeedUpdate = False
            self.FileButton.connect ('query-tooltip', self.query_tooltip_callback)
            self.FileButton.props.has_tooltip = True
            self.Entry.connect ('query-tooltip', self.query_tooltip_callback)
            self.Entry.props.has_tooltip = True
        else:
            self.thumbnailer = None
        self.Box.pack_start(self.FileButton, False, False, 0)

    def reload_thumb(self, path):
        self.NeedUpdate = False
        if self.thumbnailer:
           thumb_128, info = get_image_thumbnail(path, self.thumbnailer)
           if thumb_128:
              mime_type = info.get_attribute_as_string(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
              width, height = get_thumb_annotations (thumb_128, path)
              w, h = thumb_128.get_width(), thumb_128.get_height()
              self.BtnPixmap = thumb_128.scale_simple(w/2, h/2, GdkPixbuf.InterpType.BILINEAR)

              size = _("%(width)s pixels by %(height)s pixels") % {'width': width, 'height': height}
              names = os.path.split(get_normalized_name(path))
              msg_dict = {'size': size,
                    'mime': type_map.get(mime_type,_("unknown")),
                    'folder': names[0],
                    'name': names[1]}
              self.Msg =  _("<b>%(name)s</b>\nFolder: %(folder)s\n%(mime)s, %(size)s") % msg_dict
           else:
              self.BtnPixmap = None
              self.Msg = ""

    def GetColumn(self, num):
        if self.isImage:
           column = Gtk.TreeViewColumn(self.Setting.ShortDesc)
           column.props.resizable = True
           cell_icon = CellRendererImage()
           cell_icon.props.follow_state = True
           cell_icon.set_padding(3, 3)
           column.pack_start(cell_icon, False)
           column.add_attribute(cell_icon, "text", num)

           cell_name = Gtk.CellRendererText()
           cell_name.props.width_chars = 30
           cell_name.props.ellipsize = Pango.EllipsizeMode.START
           cell_name.props.underline = Pango.Underline.SINGLE
           column.pack_end(cell_name, True)
           column.add_attribute(cell_name, "text", num)
           return (str, column)
        else:
           return (str, Gtk.TreeViewColumn(self.Setting.ShortDesc, Gtk.CellRendererText(), text=num))

    def _Read(self):
        self.Entry.set_text(self.Get())
        if self.isImage:
           self.BtnPixmap = None
           self.NeedUpdate = True

    def _Changed(self):
        self.Set(self.Entry.get_text())
        if self.isImage:
           self.BtnPixmap = None
           self.NeedUpdate = True

    def query_tooltip_callback (self, widget, x, y, keyboard_mode, tooltip):
        if self.NeedUpdate:
           self.reload_thumb(self.Get())
        if self.BtnPixmap:
           tooltip.set_icon(self.BtnPixmap)
           tooltip.set_markup(self.Msg)
           return True
        else:
           return False

class EnumSetting(StockSetting):

    NoneValue = 0

    def _Init(self):
        StockSetting._Init(self)
        self.Combo = Gtk.ComboBoxText.new()
        if self.List:
            self.Info = self.Setting.Info[1][2]
        else:
            self.Info = self.Setting.Info[2]
        self.SortedItems = sorted(self.Info.items(), key=EnumSettingKeyFunc)
        for name, value in self.SortedItems:
            self.Combo.append_text(name)
        self.Combo.connect('changed', self.Changed)

        self.Widget = self.Combo
        self.Box.pack_start(self.Combo, True, True, 0)

    def _CellEdited(self, cell, path, new_text):
        try:
            self.CurrentRow = path.get_indices()[0]
        except (AttributeError, TypeError):
            self.CurrentRow = path.get_indices_with_depth()[0]
        value = self.Info[new_text]
        self.Store[path][self.Num] = new_text
        self.Set(value)
        self.Setting.Plugin.Context.Write()

    def GetColumn(self, num):
        self.Num = num
        cell = Gtk.CellRendererCombo()
        column = Gtk.TreeViewColumn(self.Setting.ShortDesc, cell, text=num)
        model = Gtk.ListStore(str)
        for property, value in [("model", model), ("text_column", 0),
                                ("editable", False), ("has_entry", False)]:
            cell.set_property (property, value)
        cell.connect("edited", self._CellEdited)
        for item, i in self.SortedItems:
            model.append([item])

        return (str, column)

    def GetForRenderer(self):
        return [self.SortedItems[pos][0] for pos in self.Setting.Value]

    def _Read(self):
        self.Combo.set_active(self.Get())

    def _Changed(self):
        try:
            active = self.Combo.do_get_active_text(self.Combo)
        except (AttributeError, NameError, TypeError):
            active = self.Combo.get_active_text()

        self.Set(self.Info[active])

    def _Filter(self, text, level):
        visible = Setting._Filter(self, text, level=level)
        if text is not None and not visible and level & FilterValue:
            visible = any(text in s.lower() for s in self.Info)
        return visible

class RestrictedStringSetting(StockSetting):

    NoneValue = ''

    def _Init(self):
        StockSetting._Init(self)
        self.Combo = Gtk.ComboBoxText.new()
        if self.List:
            info = self.Setting.Info[1]
        else:
            info = self.Setting.Info

        self.ItemsByName = info[0]
        self.ItemsByValue = info[1]
        self.SortedItems = info[2]

        # Use the first item in the list as the default value
        self.NoneValue = self.ItemsByName[self.SortedItems[0][0]]

        for (i, (name, value)) in enumerate(self.SortedItems):
            self.Combo.append_text(name)
        self.Combo.connect('changed', self.Changed)

        self.Widget = self.Combo
        self.Box.pack_start(self.Combo, True, True, 0)

        self.OriginalValue = None
        self.NAItemShift = 0

    def _CellEdited(self, cell, path, new_text):
        try:
            self.CurrentRow = path.get_indices()[0]
        except (AttributeError, TypeError):
            self.CurrentRow = path.get_indices_with_depth()[0]
        value = self.ItemsByName[new_text]
        self.Store[path][self.Num] = new_text
        self.Set(value)
        self.Setting.Plugin.Context.Write()

    def GetColumn(self, num):
        self.Num = num
        cell = Gtk.CellRendererCombo()
        column = Gtk.TreeViewColumn(self.Setting.ShortDesc, cell, text=num)
        model = Gtk.ListStore(str)
        for property, value in [("model", model), ("text_column", 0),
                                ("editable", False), ("has_entry", False)]:
            cell.set_property (property, value)
        cell.connect("edited", self._CellEdited)
        for item, i in self.SortedItems:
            model.append([item])

        return (str, column)

    def GetItemText (self, val):
        text = self.ItemsByValue.get(val)
        if text is None:
            return NAItemText
        return self.SortedItems[text[1]][0]

    def GetForRenderer(self):
        return [self.GetItemText(val) for val in self.Setting.Value]

    def _Read(self):
        value = self.Get()

        if not self.OriginalValue:
            self.OriginalValue = value

            # if current value is not provided by any restricted string extension,
            # insert an N/A item at the beginning
            if self.OriginalValue not in self.ItemsByValue:
                self.NAItemShift = 1
                self.Combo.insert_text(0, NAItemText)

        if value in self.ItemsByValue:
            self.Combo.set_active(self.ItemsByValue[self.Get()][1] + \
                                  self.NAItemShift)
        else:
            self.Combo.set_active(0)

    def _Changed(self):
        try:
            active = self.Combo.do_get_active_text(self.Combo)
        except (AttributeError, NameError, TypeError):
            active = self.Combo.get_active_text()

        if active == NAItemText:
            activeValue = self.OriginalValue
        else:
            activeValue = self.ItemsByName[active]
        self.Set(activeValue)

    def _Filter(self, text, level):
        visible = Setting._Filter(self, text, level=level)
        if text is not None and not visible and level & FilterValue:
            visible = any(text in s.lower() for s in self.ItemsByName)
        return visible

class BoolSetting (StockSetting):

    NoneValue = False

    def _Init (self):
        StockSetting._Init(self)
        self.Label.set_size_request(-1, -1)
        self.CheckButton = Gtk.CheckButton ()
        self.Box.pack_end(self.CheckButton, False, False, 0)
        self.CheckButton.connect ('toggled', self.Changed)

    def _Read (self):
        self.CheckButton.set_active (self.Get())

    def _Changed (self):
        self.Set(self.CheckButton.get_active ())

    def CellToggled (self, cell, path):
        try:
            self.CurrentRow = path.get_indices()[0]
        except (AttributeError, TypeError):
            self.CurrentRow = path.get_indices_with_depth()[0]
        self.Set(not cell.props.active)
        self.Store[path][self.Num] = self.Get()
        self.Setting.Plugin.Context.Write()

    def GetColumn (self, num):
        self.Num = num
        cell = Gtk.CellRendererToggle()
        cell.set_property("activatable", True)
        cell.connect('toggled', self.CellToggled)
        return (bool, Gtk.TreeViewColumn(self.Setting.ShortDesc, cell, active=num))

class NumberSetting(StockSetting):

    NoneValue = 0

    def _Init(self):
        StockSetting._Init(self)
        if self.List:
            self.Info = info = self.Setting.Info[1]
        else:
            self.Info = info = self.Setting.Info

        if self.Inc is None:
            self.Inc = info[2]
        inc = self.Inc
        self.NoneValue = info[0]
        self.Adj = Gtk.Adjustment(value=0, lower=info[0], upper=info[1], step_increment=inc, page_increment=inc*10)
        self.Spin = Gtk.SpinButton(adjustment=self.Adj)
        self.Spin.set_value(self.Get())
        self.Spin.connect("value-changed", self.Changed)
        self.Widget = self.Spin

        self.Box.pack_end(self.Spin, False, False, 0)

    def _Read(self):
        self.Adj.set_value(self.Get())

    def _Changed(self):
        self.Set(self.Adj.get_value())

class IntSetting(NumberSetting):

    def _Init(self):
        self.Inc = 1
        NumberSetting._Init(self)
        self.Spin.set_digits(0)

class FloatSetting(NumberSetting):

    NoneValue = 0.0

    def _Init(self):
        self.Inc = None
        NumberSetting._Init(self)
        self.Spin.set_digits(4)


class ColorSetting(StockSetting):

    NoneValue = (0, 0, 0, 0xFFFF) # opaque black

    def _Init(self):
        StockSetting._Init(self)
        self.Button = Gtk.ColorButton()
        self.Button.set_size_request (100, -1)
        self.Button.set_use_alpha(True)
        self.Button.connect('color-set', self.Changed)

        if GTK_VERSION >= (3, 0, 0):
            self.Button.set_halign(Gtk.Align.END)
            self.Box.pack_start(self.Button, True, True, 0)
        else:
            alignment = Gtk.Alignment(xalign=1.0, xscale=0.0, yscale=0.0)
            alignment.add(self.Button)
            self.Box.pack_start(alignment, True, True, 0)

    def GetForRenderer(self):
        return ["#%.4x%.4x%.4x%.4x" %tuple(seq) for seq in self.Setting.Value]

    def GetColumn(self, num):
        return (str, Gtk.TreeViewColumn(self.Setting.ShortDesc, CellRendererColor(), text=num))

    def _Read(self):
        if GTK_VERSION >= (3, 0, 0):
            color = Gdk.RGBA()
            value = self.Get()
            color.red = value[0] / 65535.0
            color.green = value[1] / 65535.0
            color.blue = value[2] / 65535.0
            color.alpha = value[3] / 65535.0
            self.Button.set_rgba(color)
        else:
            color = Gdk.Color(red=0, green=0, blue=0)
            value = self.Get()
            color.red, color.green, color.blue = value[:3]
            self.Button.set_color(color)
            self.Button.set_alpha(value[3])

    def _Changed(self):
        if GTK_VERSION >= (3, 0, 0):
            color = self.Button.get_rgba()
            self.Set([color.red * 0xFFFF, color.green * 0xFFFF,
                      color.blue * 0xFFFF, color.alpha * 0xFFFF])
        else:
            try:
                color = self.Button.get_color()
            except TypeError:
                color = Gdk.Color(0, 0, 0)
                self.Button.get_color(color)
            alpha = self.Button.get_alpha()
            self.Set([color.red, color.green, color.blue, alpha])

class BaseListSetting(Setting):
    def _Init(self):
        self.Widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.EditDialog = None
        self.PageToBeRefreshed = None

        self.Widgets = []
        for i, setting in enumerate(self.Settings):
            self.Widgets.append(MakeSetting(setting, List=True))

        types, cols = self.ListInfo()
        self.Types = types
        self.Store = Gtk.ListStore(*types)
        self.View = Gtk.TreeView(model=self.Store)
        self.View.set_headers_visible(True)

        cols[0].set_expand(True)
        for widget in self.Widgets:
            widget.Store = self.Store
            widget.Box.remove(widget.Reset)
            widget.ListWidget = self
        for col in cols:
            self.View.append_column(col)

        self.View.connect('row-activated', self.Activated)
        self.View.connect('button-press-event', self.ButtonPressEvent)
        self.View.connect('key-press-event', self.KeyPressEvent)
        self.Select = self.View.get_selection()
        self.Select.set_mode(Gtk.SelectionMode.SINGLE)
        self.Select.connect('changed', self.SelectionChanged)
        self.Widget.set_spacing(5)
        self.Scroll = Gtk.ScrolledWindow()
        self.Scroll.set_policy(hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                               vscrollbar_policy=Gtk.PolicyType.NEVER)
        self.Scroll.add(self.View)
        self.Widget.pack_start(self.Scroll, True, True, 0)
        buttonBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                            homogeneous=False)
        buttonBox.set_spacing(5)
        if GTK_VERSION >= (3, 0, 0):
            buttonBox.props.margin = 5
        else:
            buttonBox.set_border_width(5)
        self.Widget.pack_start(buttonBox, False, False, 0)
        buttonTypes = ((_("_New"), "document-new", self.Add, None, True),
                       (_("_Delete"), "edit-delete", self.Delete, None, False),
                       (_("_Edit"), "gtk-edit", self.Edit, None, False),
                       (_("_Up"), "go-up", self.Move, "up", False),
                       (_("_Down"), "go-down", self.Move, "down", False),)
        self.Buttons = {}
        for label, icon_name, callback, data, sensitive in buttonTypes:
            b = Gtk.Button.new_with_mnemonic(label)
            b.set_image(Gtk.Image.new_from_icon_name(icon_name,
                                                     Gtk.IconSize.BUTTON))
            buttonBox.pack_start(b, False, False, 0)
            if data is not None:
                b.connect('clicked', callback, data)
            else:
                b.connect('clicked', callback)
            b.set_sensitive(sensitive)
            self.Buttons[icon_name] = b

        self.Popup = Gtk.Menu()
        self.PopupItems = {}
        edit = Gtk.ImageMenuItem.new_with_mnemonic(_("Edit"))
        edit.set_image(Gtk.Image.new_from_icon_name("gtk-edit",
                                                    Gtk.IconSize.MENU))
        edit.set_sensitive(False)
        edit.connect("activate", self.Edit)
        self.Popup.append(edit)
        self.PopupItems["gtk-edit"] = edit
        delete = Gtk.ImageMenuItem.new_with_mnemonic(_("_Delete"))
        delete.set_image(Gtk.Image.new_from_icon_name("edit-delete",
                                                      Gtk.IconSize.MENU))
        delete.set_sensitive(False)
        delete.connect("activate", self.Delete)
        self.Popup.append(delete)
        self.PopupItems["edit-delete"] = delete
        self.Popup.show_all()

        buttonBox.pack_end(self.Reset, False, False, 0)

        self.Box.pack_start(self.Widget, True, True, 0)

    def AddUpdater(self):
        pass

    def RemoveUpdater(self):
        if self.Settings:
            for widget in self.Widgets:
                widget.EBox.destroy()

    def DoReset(self, widget):
        for setting in self.Settings:
            setting.Reset()
        self.Settings[0].Plugin.Context.Write()
        self.Read()

    def MakeLabel(self):
        pass

    def Add(self, *args):
        for widget, setting in zip(self.Widgets, self.Settings):
            vlist = setting.Value
            vlist.append(widget.NoneValue)
            setting.Value = vlist
        self.Settings[0].Plugin.Context.Write()
        self.Read()
        self._Edit(len(self.Store)-1)

    def _Delete(self, row):

        for setting in self.Settings:
            vlist = setting.Value
            del vlist[row]
            setting.Value = vlist
        self.Settings[0].Plugin.Context.Write()

    def Delete(self, *args):
        model, it = self.Select.get_selected()
        if it is not None:
            path = model.get_path(it)
            if path is not None:
                try:
                    row = path.get_indices()[0]
                except (AttributeError, TypeError):
                    row = path.get_indices_with_depth()[0]
            else:
                return

            model.remove(it)

            self._Delete(row)

    def _MakeEditDialog(self, parent):
        dlg = Gtk.Dialog(title=_("Edit"), transient_for=parent)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=GridRow)
        vbox.props.border_width = 6
        dlg.vbox.pack_start(vbox, True, True, 0)
        dlg.set_default_size(500, -1)

        button = dlg.add_button(_("_Close"), Gtk.ResponseType.CLOSE)
        button.set_image (Gtk.Image.new_from_icon_name("window-close",
                                                       Gtk.IconSize.BUTTON))
        button.grab_default ()

        group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        for widget in self.Widgets:
            vbox.pack_start(widget.EBox, False, False, 0)
            group.add_widget(widget.Label)
        return dlg

    def Edit(self, widget):
        model, it = self.Select.get_selected()
        if it:
            path = model.get_path(it)
            if path is not None:
                try:
                    row = path.get_indices()[0]
                except (AttributeError, TypeError):
                    row = path.get_indices_with_depth()[0]
            else:
                return

            self._Edit(row)

    def _Edit(self, row):
        if not self.EditDialog:
            self.EditDialog = self._MakeEditDialog(self.Widget.get_toplevel())

        for widget in self.Widgets:
            widget.CurrentRow = row
            widget.Read()

        self.EditDialog.show_all()
        response = self.EditDialog.run()
        self.EditDialog.hide()

        if self.PageToBeRefreshed:
            self.PageToBeRefreshed[0].RefreshPage(self.PageToBeRefreshed[1],
                                                  self.PageToBeRefreshed[2])
            self.PageToBeRefreshed = None

        self.Read()

    def Move(self, widget, direction):
        model, it = self.Select.get_selected()
        if it is not None:
            path = model.get_path(it)
            if path is not None:
                try:
                    row = path.get_indices()[0]
                except (AttributeError, TypeError):
                    row = path.get_indices_with_depth()[0]
            else:
                return
            if direction == 'up':
                dest = row - 1
                model.iter_different = model.iter_previous
            elif direction == 'down':
                dest = row + 1
                model.iter_different = model.iter_next
            for widget in self.Widgets:
                widget.Swap(row, dest)

            try:
                it2 = model.iter_different(it.copy())
                model.swap(it, it2)
            except (AttributeError, TypeError):
                try:
                    it2 = it.copy()
                    model.iter_different(it2)
                    model.swap(it, it2)
                except (AttributeError, TypeError):
                    order = list(range(len(model)))
                    order.insert(dest, order.pop(row))
                    model.reorder(order)

            self.Settings[0].Plugin.Context.Write()

            self.SelectionChanged(self.Select)

    def SelectionChanged(self, selection):

        model, it = selection.get_selected()
        for widget in (self.Buttons["gtk-edit"], self.Buttons["edit-delete"],
                       self.PopupItems["gtk-edit"], self.PopupItems["edit-delete"]):
            widget.set_sensitive(it is not None)

        if it is not None:
            path = model.get_path(it)
            if path is not None:
                try:
                    row = path.get_indices()[0]
                except (AttributeError, TypeError):
                    row = path.get_indices_with_depth()[0]
                self.Buttons["go-up"].set_sensitive(row > 0)
                self.Buttons["go-down"].set_sensitive(row < (len(model) - 1))
        else:
            self.Buttons["go-up"].set_sensitive(False)
            self.Buttons["go-down"].set_sensitive(False)

    def ButtonPressEvent(self, treeview, event):
        if event.button == 3:
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                if GTK_VERSION >= (3, 22, 0):
                    self.Popup.popup_at_pointer(event)
                else:
                    try:
                        self.Popup.popup(None, None, None, None,
                                         event.button, event.time)
                    except (AttributeError, NameError, TypeError):
                        pass
            return True

    def KeyPressEvent(self, treeview, event):
        if Gdk.keyval_name(event.keyval) == "Delete":
            model, it = treeview.get_selection().get_selected()
            if it is not None:
                path = model.get_path(it)
                if path is not None:
                    try:
                        row = path.get_indices()[0]
                    except (AttributeError, TypeError):
                        row = path.get_indices_with_depth()[0]
                    model.remove(it)
                    self._Delete(row)
                    return True

    def ListInfo(self):
        types = []
        cols = []
        for i, widget in enumerate(self.Widgets):
            t, col = widget.GetColumn(i)
            types.append(t)
            cols.append(col)
        return types, cols

    def Activated(self, obj, path, col):
        try:
            self._Edit(path.get_indices()[0])
        except (AttributeError, TypeError):
            self._Edit(path.get_indices_with_depth()[0])

    def _Read(self):
        self.Store.clear()
        valuesList = []
        for w in self.Widgets:
            values = []
            i = 0
            for value in w.GetForRenderer():
                type = w.GetColumn(i)[0]
                values.append(type(value))
                i = i + 1
            valuesList.append(values)
        for values in zip(*valuesList):
            self.Store.append(values)

    def OnDestroy(self, widget):
        for w in self.Widgets:
            w.EBox.destroy()

class ListSetting(BaseListSetting):

    def _Init(self):
        self.Settings = [self.Setting]
        BaseListSetting._Init(self)

class MultiListSetting(BaseListSetting):

    def _Init(self):
        self.EBox.set_tooltip_text(_("Multi-list settings. You can double-click a row to edit the values."))
        BaseListSetting._Init(self)

    def Filter(self, text, level=FilterAll):
        visible = False
        for setting in self.Widgets:
            if setting._Filter(text, level=level):
                visible = True
        self._SetHidden(visible)
        return visible

class EnumFlagsSetting(Setting):

    def _Init(self):
        frame = Gtk.Frame(label=self.Setting.ShortDesc)
        if GTK_VERSION >= (3, 10, 0):
            grid = Gtk.Grid(row_spacing=GridRow, column_spacing=GridRow)
            grid.props.margin = GridRow
        else:
            grid = Gtk.Table()

        row = col = 0
        self.Checks = []
        sortedItems = sorted(self.Setting.Info[1][2].items(), key=EnumSettingKeyFunc)
        self.minVal = sortedItems[0][1]
        for key, value in sortedItems:
            box = Gtk.CheckButton(label=key)
            self.Checks.append((key, box))
            if GTK_VERSION >= (3, 10, 0):
                box.set_hexpand(True)
                grid.attach(box, col, row, 1, 1)
            else:
                grid.attach(box, col, col + 1, row, row + 1,
                            Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND,
                            Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND,
                            GridRow, GridRow)
            box.connect('toggled', self.Changed)
            col = col+1
            if col >= 3:
                col = 0
                row += 1

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.Reset, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(grid, True, True, 0)
        hbox.pack_start(vbox, False, False, 0)

        frame.add(hbox)
        self.Box.pack_start(frame, True, True, 0)

    def _Read(self):
        for key, box in self.Checks:
            box.set_active(False)
        for setVal in self.Setting.Value:
            self.Checks[setVal-self.minVal][1].set_active(True)

    def _Changed(self):
        values = []
        for key, box in self.Checks:
            if box.get_active():
                values.append(self.Setting.Info[1][2][key])
        self.Setting.Value = values

    def _Filter(self, text, level=FilterAll):
        visible = Setting._Filter(self, text, level=level)
        if text is not None and not visible and level & FilterValue:
            visible = any(text in s.lower() for s in self.Setting.Info[1][2])
        return visible

class RestrictedStringFlagsSetting(Setting):

    def _Init(self):
        frame = Gtk.Frame(label=self.Setting.ShortDesc)
        if GTK_VERSION >= (3, 10, 0):
            grid = Gtk.Grid(row_spacing=GridRow, column_spacing=GridRow)
            grid.props.margin = GridRow
        else:
            grid = Gtk.Table()

        row = col = 0
        self.Checks = []
        info = self.Setting.Info[1]
        self.ItemsByName = info[0]
        self.ItemsByValue = info[1]
        sortedItems = info[2]
        for key, value in sortedItems:
            box = Gtk.CheckButton(label=key)
            self.Checks.append((key, box))
            if GTK_VERSION >= (3, 10, 0):
                box.set_hexpand(True)
                grid.attach(box, col, row, 1, 1)
            else:
                grid.attach(box, col, col + 1, row, row + 1,
                            Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND,
                            Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND,
                            GridRow, GridRow)
            box.connect('toggled', self.Changed)
            col = col+1
            if col >= 3:
                col = 0
                row += 1

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.Reset, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(grid, True, True, 0)
        hbox.pack_start(vbox, False, False, 0)

        frame.add(hbox)
        self.Box.pack_start(frame, True, True, 0)

    def _Read(self):
        for key, box in self.Checks:
            box.set_active(False)
        for setVal in self.Setting.Value:
            if setVal in self.ItemsByValue:
                self.Checks[self.ItemsByValue[setVal][1]][1].set_active(True)

    def _Changed(self):
        values = []
        for key, box in self.Checks:
            if box.get_active():
                values.append(self.ItemsByName[key])
        self.Setting.Value = values

    def _Filter(self, text, level=FilterAll):
        visible = Setting._Filter(self, text, level=level)
        if text is not None and not visible and level & FilterValue:
            visible = any(text in s.lower() for s in self.ItemsByName)
        return visible

class EditableActionSetting (StockSetting):

    def _Init (self, widget, action):
        StockSetting._Init(self)
        self.Label.set_size_request(-1, -1)

        editButton = Gtk.Button ()
        editButton.add (Gtk.Image.new_from_icon_name ("gtk-edit",
                                                      Gtk.IconSize.BUTTON))
        editButton.set_tooltip_text(_("Edit %s" % self.Setting.ShortDesc))
        editButton.connect ("clicked", self.RunEditDialog)

        action = ActionImage (action)
        self.Box.pack_start (action, False, False, 0)
        self.Box.reorder_child (action, 0)
        self.Box.pack_end (editButton, False, False, 0)
        self.Box.pack_end (widget, False, False, 0)
        self.Widget = widget


    def RunEditDialog (self, widget):
        dlg = Gtk.Dialog (title=_("Edit %s") % self.Setting.ShortDesc,
                          transient_for=widget.get_toplevel ())
        dlg.set_position (Gtk.WindowPosition.CENTER_ON_PARENT)

        button = dlg.add_button (_("_Cancel"), Gtk.ResponseType.CANCEL)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-cancel",
                                                        Gtk.IconSize.BUTTON))
        button = dlg.add_button (_("_OK"), Gtk.ResponseType.OK)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-ok",
                                                        Gtk.IconSize.BUTTON))
        button.grab_default ()
        dlg.set_default_response (Gtk.ResponseType.OK)

        entry = Gtk.Entry ()
        entry.set_max_length (200)
        entry.set_text (self.GetDialogText ())
        entry.set_tooltip_text(self.Setting.LongDesc)
        entry.connect ("activate", lambda *a: dlg.response (Gtk.ResponseType.OK))

        if GTK_VERSION >= (3, 0, 0):
            entry.props.margin = 10
            dlg.vbox.pack_start (entry, True, True, 0)
        else:
            alignment = Gtk.Alignment ()
            alignment.set_padding (10, 10, 10, 10)
            alignment.add (entry)
            dlg.vbox.pack_start (alignment, True, True, 0)

        dlg.vbox.show_all ()
        ret = dlg.run ()

        entryText = entry.get_text ().strip ()

        dlg.destroy ()

        if ret != Gtk.ResponseType.OK:
            return

        self.HandleDialogText (entryText)

    def GetDialogText (self):
        self.PureVirtual ('GetDialogText')

    def HandleDialogText (self, text):
        self.PureVirtual ('HandleDialogText')

class KeySetting (EditableActionSetting):

    current = ""
    new = ""

    def _Init (self):

        self.Button = SizedButton (minWidth = 100)
        self.Button.connect ("clicked", self.RunKeySelector)
        self.SetButtonLabel ()

        EditableActionSetting._Init (self, self.Button, "keyboard")

    def DoReset (self, widget):
        conflict = KeyConflict (widget.get_toplevel (),
                                self.Setting, self.Setting.DefaultValue)
        if conflict.Resolve (GlobalUpdater):
            self.Setting.Reset ()
            self.Setting.Plugin.Context.Write ()
            self.Read ()

    def GetDialogText (self):
        return self.current

    def HandleDialogText (self, accel):
        name = UpdateAcceleratorName (accel)
        if len (accel) != len (name):
            accel = protect_pango_markup (accel)
            ErrorDialog (self.Widget.get_toplevel (),
                         _("\"%s\" is not a valid shortcut") % accel)
            return
        self.BindingEdited (accel)

    def GetLabelText (self, text):
        text = UpdateAcceleratorName (text)
        if not text:
            text = _("Disabled")
        return text

    def SetButtonLabel (self):
        self.Button.set_label (self.GetLabelText (self.current))

    def RunKeySelector (self, widget):

        def ShowHideBox (button, box, dialog):
            if button.get_active ():
                box.show ()
            else:
                box.hide ()
                dialog.resize (1, 1)

        def HandleGrabberChanged (grabber, label, selector):
            self.new = GetAcceleratorName (grabber.key, grabber.mods)
            label.set_text (self.GetLabelText (self.new))

            mods = ""
            for mod in KeyModifier:
                if "<%s>" % mod in self.new:
                    mods += "%s|" % mod
            mods.rstrip ("|")
            selector.current = mods

        def HandleModifierAdded (selector, modifier, label):
            if self.new:
                new = "<%s>%s" % (modifier, self.new)
            else:
                new = "<%s>" % modifier
            self.new = UpdateAcceleratorName (new)
            label.set_text (self.GetLabelText (self.new))

        def HandleModifierRemoved (selector, modifier, label):
            new = UpdateAcceleratorName (self.new)
            if "<%s>" % modifier in new:
                new = new.replace ("<%s>" % modifier, "")
            self.new = new
            label.set_text (self.GetLabelText (self.new))

        dlg = Gtk.Dialog (title=_("Edit %s") % self.Setting.ShortDesc,
                          transient_for=widget.get_toplevel ())
        dlg.set_position (Gtk.WindowPosition.CENTER_ALWAYS)
        dlg.set_icon (self.Widget.get_toplevel ().get_icon ())
        dlg.set_modal (True)

        button = dlg.add_button (_("_Cancel"), Gtk.ResponseType.CANCEL)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-cancel",
                                                        Gtk.IconSize.BUTTON))
        button = dlg.add_button (_("_OK"), Gtk.ResponseType.OK)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-ok",
                                                        Gtk.IconSize.BUTTON))
        button.grab_default ()
        dlg.set_default_response (Gtk.ResponseType.OK)

        mainBox = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        if GTK_VERSION >= (3, 0, 0):
            mainBox.props.margin = 10
            dlg.vbox.pack_start (mainBox, True, True, 0)
        else:
            alignment = Gtk.Alignment ()
            alignment.set_padding (10, 10, 10, 10)
            alignment.add (mainBox)
            dlg.vbox.pack_start (alignment, True, True, 0)

        self.new = UpdateAcceleratorName (self.current)

        checkButton = Gtk.CheckButton (label=_("Enabled"))
        active = len (self.new) > 0
        checkButton.set_active (active)
        checkButton.set_tooltip_text(self.Setting.LongDesc)
        mainBox.pack_start (checkButton, True, True, 0)

        box = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        checkButton.connect ("toggled", ShowHideBox, box, dlg)
        mainBox.pack_start (box, True, True, 0)

        currentMods = ""
        for mod in KeyModifier:
            if "<%s>" % mod in self.new:
                currentMods += "%s|" % mod
        currentMods.rstrip ("|")
        modifierSelector = ModifierSelector (currentMods)
        modifierSelector.set_tooltip_text (self.Setting.LongDesc)
        if GTK_VERSION >= (3, 0, 0):
            modifierSelector.set_halign (Gtk.Align.CENTER)
            box.pack_start (modifierSelector, True, True, 0)
        else:
            alignment = Gtk.Alignment (yalign=0.0, xscale=0.0, yscale=0.0)
            alignment.add (modifierSelector)
            box.pack_start (alignment, True, True, 0)

        key, mods = Gtk.accelerator_parse (self.new)
        grabber = KeyGrabber (key = key, mods = mods,
                              label = _("Grab key combination"))
        grabber.set_tooltip_text (self.Setting.LongDesc)
        box.pack_start (grabber, True, True, 0)

        label = Gtk.Label (label=self.GetLabelText(self.new))
        label.set_tooltip_text (self.Setting.LongDesc)
        if GTK_VERSION >= (3, 0, 0):
            label.set_margin_top (15)
            box.pack_start (label, True, True, 0)
        else:
            alignment = Gtk.Alignment (xscale=0.0, yscale=0.0)
            alignment.set_padding (15, 0, 0, 0)
            alignment.add (label)
            box.pack_start (alignment, True, True, 0)

        modifierSelector.connect ("added", HandleModifierAdded, label)
        modifierSelector.connect ("removed", HandleModifierRemoved, label)
        grabber.connect ("changed", HandleGrabberChanged, label,
                         modifierSelector)
        grabber.connect ("current-changed", HandleGrabberChanged, label,
                         modifierSelector)

        dlg.vbox.show_all ()
        ShowHideBox (checkButton, box, dlg)
        ret = dlg.run ()

        checkButtonActive = checkButton.get_active ()

        dlg.destroy ()

        if ret != Gtk.ResponseType.OK:
            return

        if self.new and checkButtonActive:
            self.BindingEdited (self.new)
        else:
            self.BindingEdited ("Disabled")

    def BindingEdited (self, accel):
        '''Binding edited callback'''
        # Update & save binding
        conflict = KeyConflict (self.Button.get_toplevel (),
                                self.Setting, accel)
        if conflict.Resolve (GlobalUpdater):
            self.current = accel
            self.Changed ()
        self.SetButtonLabel ()

    def _Read (self):
        self.current = self.Get()
        self.SetButtonLabel ()

    def _Changed (self):
        self.Set(self.current)


class ButtonSetting (EditableActionSetting):

    current = ""

    def _Init (self):

        self.Button = SizedButton (minWidth = 100)
        self.Button.connect ("clicked", self.RunButtonSelector)
        self.Button.set_tooltip_text(self.Setting.LongDesc)
        self.SetButtonLabel ()

        EditableActionSetting._Init (self, self.Button, "button")

    def DoReset (self, widget):
        conflict = ButtonConflict (widget.get_toplevel (),
                                   self.Setting, self.Setting.DefaultValue)
        if conflict.Resolve (GlobalUpdater):
            self.Setting.Reset ()
            self.Setting.Plugin.Context.Write ()
            self.Read ()

    def GetModsString (self, button):
        accel = ""
        for mod in KeyModifier:
            if "<%s>" % mod in button:
                accel += "<%s>" % mod
        for alias in KeyModifierAlias:
            if "<%s>" % alias[0] in button:
                accel += "<%s>" % alias[1]
        return UpdateAcceleratorName (accel)

    def ReorderButtonString (self, old):
        new = ""
        edges = ["%sEdge" % e for e in Edges]
        for s in edges:
            if "<%s>" % s in old:
                new += "<%s>" % s
        mods = self.GetModsString (old)
        if mods:
            new += mods
        for i in range (99, 0, -1):
            if "Button%d" % i in old:
                new += "Button%d" % i
                break
        return new

    def GetDialogText (self):
        return self.current

    def HandleDialogText (self, button):
        def ShowErrorDialog (button):
            button = protect_pango_markup (button)
            ErrorDialog (self.Widget.get_toplevel (),
                         _("\"%s\" is not a valid button") % button)
        if not button or button.lower ().strip () in ("disabled", "none"):
            self.ButtonEdited ("Disabled")
            return
        new = self.ReorderButtonString (button)
        if len (button) != len (new):
            ShowErrorDialog (button)
            return
        self.ButtonEdited (new)

    def GetLabelText (self, text):
        text = self.ReorderButtonString (text)
        if not text:
            text = _("Disabled")
        return text

    def SetButtonLabel (self):
        self.Button.set_label (self.GetLabelText (self.current))

    def RunButtonSelector (self, widget):
        def ShowHideBox (button, box, dialog):
            if button.get_active ():
                box.show ()
            else:
                box.hide ()
                dialog.resize (1, 1)
        dlg = Gtk.Dialog (title=_("Edit %s") % self.Setting.ShortDesc,
                          transient_for=widget.get_toplevel ())
        dlg.set_position (Gtk.WindowPosition.CENTER_ALWAYS)
        dlg.set_modal (True)

        button = dlg.add_button (_("_Cancel"), Gtk.ResponseType.CANCEL)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-cancel",
                                                        Gtk.IconSize.BUTTON))
        button = dlg.add_button (_("_OK"), Gtk.ResponseType.OK)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-ok",
                                                        Gtk.IconSize.BUTTON))
        button.grab_default ()
        dlg.set_default_response (Gtk.ResponseType.OK)

        mainBox = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        if GTK_VERSION >= (3, 0, 0):
            mainBox.props.margin = 10
            dlg.vbox.pack_start (mainBox, True, True, 0)
        else:
            alignment = Gtk.Alignment ()
            alignment.set_padding (10, 10, 10, 10)
            alignment.add (mainBox)
            dlg.vbox.pack_start (alignment, True, True, 0)

        checkButton = Gtk.CheckButton (label=_("Enabled"))
        active = self.current and \
                 self.current.lower ().strip () not in ("disabled", "none")
        checkButton.set_active (active)
        checkButton.set_tooltip_text (self.Setting.LongDesc)
        mainBox.pack_start (checkButton, True, True, 0)

        box = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        checkButton.connect ("toggled", ShowHideBox, box, dlg)
        mainBox.pack_start (box, True, True, 0)

        currentEdges = ""
        for edge in Edges:
            if "<%sEdge>" % edge in self.current:
                currentEdges += "%s|" % edge
        currentEdges.rstrip ("|")
        edgeSelector = SingleEdgeSelector (currentEdges)
        edgeSelector.set_tooltip_text(self.Setting.LongDesc)
        box.pack_start (edgeSelector, True, True, 0)

        currentMods = ""
        for mod in KeyModifier:
            if "<%s>" % mod in self.GetModsString (self.current):
                currentMods += "%s|" % mod
        currentMods.rstrip ("|")
        modifierSelector = ModifierSelector (currentMods)
        modifierSelector.set_tooltip_text(self.Setting.LongDesc)
        box.pack_start (modifierSelector, True, True, 0)

        buttonCombo = Gtk.ComboBoxText.new ()
        currentButton = 1
        for i in range (99, 0, -1):
            if "Button%d" % i in self.current:
                currentButton = i
                break
        maxButton = 20
        for i in range (1, maxButton + 1):
            button = "Button%d" % i
            buttonCombo.append_text (button)
        if currentButton > maxButton:
            buttonCombo.append_text ("Button%d" % currentButton)
            buttonCombo.set_active (maxButton)
        else:
            buttonCombo.set_active (currentButton - 1)
        buttonCombo.set_tooltip_text(self.Setting.LongDesc)
        box.pack_start (buttonCombo, True, True, 0)

        dlg.vbox.show_all ()
        ShowHideBox (checkButton, box, dlg)
        ret = dlg.run ()

        edges = edgeSelector.current
        modifiers = modifierSelector.current
        try:
            button = buttonCombo.do_get_active_text (buttonCombo)
        except (AttributeError, NameError, TypeError):
            button = buttonCombo.get_active_text ()
        checkButtonActive = checkButton.get_active ()

        dlg.destroy ()

        if ret != Gtk.ResponseType.OK:
            return

        if not checkButtonActive:
            self.ButtonEdited ("Disabled")
            return

        edges = edges.split ("|")
        if len (edges):
            edges = "<%sEdge>" % "Edge><".join (edges)
        else: edges = ""

        modifiers = modifiers.split ("|")
        if len (modifiers):
            modifiers = "<%s>" % "><".join (modifiers)
        else: modifiers = ""

        button = "%s%s%s" % (edges, modifiers, button)
        button = self.ReorderButtonString (button)

        self.ButtonEdited (button)

    def ButtonEdited (self, button):
        '''Button edited callback'''
        if button == "Button1":
            warning = WarningDialog (self.Widget.get_toplevel (),
                                     _("Using Button1 without modifiers can \
prevent any left click and thus break your configuration. Do you really want \
to set \"%s\" button to Button1 ?") % self.Setting.ShortDesc)
            response = warning.run ()
            if response != Gtk.ResponseType.YES:
                return
        conflict = ButtonConflict (self.Button.get_toplevel (),
                                   self.Setting, button)
        if conflict.Resolve (GlobalUpdater):
            self.current = button
            self.Changed ()
        self.SetButtonLabel ()

    def _Read (self):
        self.current = self.Get()
        self.SetButtonLabel ()

    def _Changed (self):
        self.Set(self.current)

class EdgeSetting (EditableActionSetting):

    current = ""

    def _Init (self):

        self.Button = SizedButton (minWidth = 100)
        self.Button.connect ("clicked", self.RunEdgeSelector)
        self.Button.set_tooltip_text(self.Setting.LongDesc)
        self.SetButtonLabel ()

        EditableActionSetting._Init (self, self.Button, "edges")

    def DoReset (self, widget):
        conflict = EdgeConflict (widget.get_toplevel (),
                                 self.Setting, self.Setting.DefaultValue)
        if conflict.Resolve (GlobalUpdater):
            self.Setting.Reset ()
            self.Setting.Plugin.Context.Write ()
            self.Read ()

    def GetDialogText (self):
        return self.current

    def HandleDialogText (self, mask):
        edges = mask.split ("|")
        valid = True
        for edge in edges:
            if edge not in Edges:
                valid = False
                break
        if not valid:
            mask = protect_pango_markup (mask)
            ErrorDialog (self.Widget.get_toplevel (),
                         _("\"%s\" is not a valid edge mask") % mask)
            return
        self.EdgeEdited ("|".join (edges))

    def SetButtonLabel (self):
        label = self.current
        if len (self.current):
            edges = self.current.split ("|")
            edges = [_(s) for s in edges]
            label = ", ".join (edges)
        else:
            label = _("None")
        self.Button.set_label (label)

    def RunEdgeSelector (self, widget):
        dlg = Gtk.Dialog (title=_("Edit %s") % self.Setting.ShortDesc,
                          transient_for=widget.get_toplevel ())
        dlg.set_position (Gtk.WindowPosition.CENTER_ON_PARENT)
        dlg.set_modal (True)

        button = dlg.add_button (_("_Cancel"), Gtk.ResponseType.CANCEL)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-cancel",
                                                        Gtk.IconSize.BUTTON))
        button = dlg.add_button (_("_OK"), Gtk.ResponseType.OK)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-ok",
                                                        Gtk.IconSize.BUTTON))
        button.grab_default ()
        dlg.set_default_response (Gtk.ResponseType.OK)

        selector = SingleEdgeSelector (self.current)
        selector.set_tooltip_text (self.Setting.LongDesc)
        if GTK_VERSION >= (3, 0, 0):
            selector.props.margin = 10
            dlg.vbox.pack_start (selector, True, True, 0)
        else:
            alignment = Gtk.Alignment ()
            alignment.set_padding (10, 10, 10, 10)
            alignment.add (selector)
            dlg.vbox.pack_start (alignment, True, True, 0)

        dlg.vbox.show_all ()
        ret = dlg.run ()
        selectorCurrent = selector.current
        dlg.destroy ()

        if ret != Gtk.ResponseType.OK:
            return

        self.EdgeEdited (selectorCurrent)

    def EdgeEdited (self, edge):
        '''Edge edited callback'''
        conflict = EdgeConflict (self.Button.get_toplevel (),
                                 self.Setting, edge)
        if conflict.Resolve (GlobalUpdater):
            self.current = edge
            self.Changed ()
        self.SetButtonLabel ()

    def _Read (self):
        self.current = self.Get()
        self.SetButtonLabel ()

    def _Changed (self):
        self.Set(self.current)
        self.SetButtonLabel ()

class BellSetting (BoolSetting):

    def _Init (self):
        BoolSetting._Init (self)
        bell = ActionImage ("bell")
        self.Box.pack_start (bell, False, False, 0)
        self.Box.reorder_child (bell, 0)

class CursorStringSetting (StockSetting):
    def _Init(self):
        StockSetting._Init(self)
        self.liststore=Gtk.ListStore(str, str, GdkPixbuf.Pixbuf)
        self.liststore.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.liststore.set_sort_func(0, self.list_compare_func, None)
        self.liststore.append([_("Default cursor"), "builtin", None])
        self.liststore.append(["", "-", None])
        home_icons = os.path.join(GLib.get_user_config_dir(), HomeCursorDir)
        for cursordir in [CursorDir, home_icons]:
            if os.path.isdir(cursordir):
                for filename in os.listdir(cursordir):
                    tmpname = os.path.join(cursordir, filename)
                    fullname = filename
                    example = "left_ptr"
                    if os.path.isdir(os.path.join(tmpname, "cursors")):
                        tmpname = os.path.join(tmpname, "index.theme")
                        if os.path.isfile(tmpname):
                            DeskItem = MateDesktop.DesktopItem.new_from_file(tmpname, \
                                       MateDesktop.DesktopItemLoadFlags.ONLY_IF_EXISTS)
                            if DeskItem:
                               readable = DeskItem.get_localestring("Icon Theme/Name")
                               if readable:
                                  fullname = readable.strip()
                               readable = DeskItem.get_string("Icon Theme/Example")
                               if readable:
                                  example = readable

                        pixbuf = GetCursorPixmap(filename)
                        for row in self.liststore:
                            if row[0]==fullname:
                                self.liststore.remove(row.iter)
                                break
                        self.liststore.append([fullname, filename, pixbuf])

        self.Combo = Gtk.ComboBox.new_with_model(self.liststore)
        self.Combo.set_row_separator_func(self.separator_func, None)

        cell_icon = Gtk.CellRendererPixbuf()
        cell_icon.set_padding(2, 0)
        self.Combo.pack_start(cell_icon, False)
        self.Combo.add_attribute(cell_icon, "pixbuf", 2)

        cell_name = Gtk.CellRendererText()
        self.Combo.pack_end(cell_name, True)
        self.Combo.add_attribute(cell_name, "text", 0)

        self.Combo.connect("changed", self.Changed)

        self.Widget = self.Combo
        self.Box.pack_start(self.Widget, True, True, 0)
    def separator_func(self, treemodel, iter, user_data):
        a = self.liststore.get(iter, 1)
        if a[0]=="-":
            return True
        else:
            return False

    def list_compare_func(self, treemodel, iter1, iter2, user_data):
        a = self.liststore.get(iter1, 0,1)
        b = self.liststore.get(iter2, 0,1)
        if a[1]=="builtin":
            return -1
        else:
            if a[0] == b[0]:
                return 0
            if a[0] < b[0]:
                return -1
            else:
                return 1

    def _Read(self):
        active=self.Get()
        for row in self.liststore:
            if active in row[1]:
                self.Combo.set_active_iter(row.iter)
                break
    def _Changed(self):
        iter = self.Combo.get_active_iter()
        if iter:
            data = self.liststore.get_value(iter, 1)
            self.Set(data)


class WallpaperStringSetting (StringSetting):
    def _Init(self):
        StringSetting._Init(self)
        self.Msg = ""
        self.okButton = None
        self.Button = Gtk.Button()
        self.Button.set_tooltip_text(_("Browse..."))
        self.Button.set_image(Gtk.Image.new_from_icon_name("document-open",
                                                    Gtk.IconSize.BUTTON))
        if has_mate_desktop:
            size_normal = MateDesktop.DesktopThumbnailSize.NORMAL
            self.thumbnailer = MateDesktop.DesktopThumbnailFactory.new(size_normal)
            self.BtnPixmap = None
            self.NeedUpdate = False
            self.Button.connect ('query-tooltip', self.query_tooltip_callback)
            self.Button.props.has_tooltip = True
            self.Entry.connect ('query-tooltip', self.query_tooltip_callback)
            self.Entry.props.has_tooltip = True
        else:
            self.thumbnailer = None

        self.Button.connect('clicked', self.on_button_clicked)
        self.Box.pack_start(self.Button, False, False, 0)

    def on_button_clicked(self, widget):
        dlg = Gtk.Dialog (title=_("Edit %s") % self.Setting.ShortDesc,
                          transient_for=widget.get_toplevel ())
        dlg.set_position (Gtk.WindowPosition.CENTER_ALWAYS)
        dlg.set_icon (self.Widget.get_toplevel ().get_icon ())
        dlg.set_modal (True)

        button = dlg.add_button (_("_Cancel"), Gtk.ResponseType.CANCEL)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-cancel",
                                                        Gtk.IconSize.BUTTON))
        button = dlg.add_button (_("_OK"), Gtk.ResponseType.OK)
        button.set_image (Gtk.Image.new_from_icon_name ("gtk-ok",
                                                        Gtk.IconSize.BUTTON))
        self.okButton = button
        self.okButton.set_sensitive(False)
        button.grab_default ()
        dlg.set_default_response (Gtk.ResponseType.OK)

        mainBox = Gtk.Box (orientation=Gtk.Orientation.VERTICAL)
        mainBox.set_size_request(500, 500)

        if GTK_VERSION >= (3, 0, 0):
            mainBox.props.margin = 10
            dlg.vbox.pack_start (mainBox, True, True, 0)
        else:
            alignment = Gtk.Alignment ()
            alignment.set_padding (10, 10, 10, 10)
            alignment.add (mainBox)
            dlg.vbox.pack_start (alignment, True, True, 0)

        self.CurrentName = self.Get()

        wll = WallpaperPeekWindow(self.CurrentName, self.WallChanged, dlg)
        mainBox.pack_start (wll, True, True, 0)

        dlg.vbox.show_all ()
        ret = dlg.run ()
        if ret == Gtk.ResponseType.OK:
           self.Entry.set_text(self.CurrentName)
           self.Changed()

        dlg.destroy ()

    def reload_thumb(self, path):
        self.NeedUpdate = False
        if self.thumbnailer:
           thumb_128, info = get_image_thumbnail(path, self.thumbnailer)
           if thumb_128:
              mime_type = info.get_attribute_as_string(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE)
              width, height = get_thumb_annotations (thumb_128, path)
              w, h = thumb_128.get_width(), thumb_128.get_height()
              self.BtnPixmap = thumb_128.scale_simple(w/2, h/2, GdkPixbuf.InterpType.BILINEAR)

              size = _("%(width)s pixels by %(height)s pixels") % {'width': width, 'height': height}
              names = os.path.split(get_normalized_name(path))
              msg_dict = {'size': size,
                    'mime': type_map.get(mime_type,_("unknown")),
                    'folder': names[0],
                    'name': names[1]}
              self.Msg =  _("<b>%(name)s</b>\nFolder: %(folder)s\n%(mime)s, %(size)s") % msg_dict
           else:
              self.BtnPixmap = None
              self.Msg = ""

    def GetColumn(self, num):
        column = Gtk.TreeViewColumn(self.Setting.ShortDesc)

        cell_icon = CellRendererImage()
        column.props.resizable = True
        cell_icon.props.follow_state = True
        cell_icon.set_padding(3, 3)
        column.pack_start(cell_icon, False)
        column.add_attribute(cell_icon, "text", num)

        cell_name = Gtk.CellRendererText()
        cell_name.props.width_chars = 30
        cell_name.props.ellipsize = Pango.EllipsizeMode.START
        cell_name.props.underline = Pango.Underline.SINGLE
        column.pack_end(cell_name, True)
        column.add_attribute(cell_name, "text", num)

        return (str, column)

    def WallChanged(self, imagename=None):
        if imagename:
           self.CurrentName = imagename
           self.okButton.set_sensitive(True)
        else:
           self.CurrentName = ""
           self.okButton.set_sensitive(False)

    def _Read(self):
        self.Entry.set_text(self.Get())
        self.BtnPixmap = None
        self.NeedUpdate = True

    def _Changed(self):
        self.Set(self.Entry.get_text())
        self.BtnPixmap = None
        self.NeedUpdate = True

    def query_tooltip_callback (self, widget, x, y, keyboard_mode, tooltip):
        if self.NeedUpdate:
           self.reload_thumb(self.Get())
        if self.BtnPixmap:
           tooltip.set_icon(self.BtnPixmap)
           tooltip.set_markup(self.Msg)
           return True
        else:
           return False



def MakeStringSetting (setting, List=False):

    if setting.Hints:
        if "file" in setting.Hints:
            if "cursors" in setting.Hints:
                return CursorStringSetting (setting, List=List)
            elif "image" in setting.Hints:
                return FileStringSetting (setting, isImage=True, List=List)
            elif "wallpaper" in setting.Hints:
                return WallpaperStringSetting (setting, List=List)
            else:
                return FileStringSetting (setting, List=List)
        elif "family" in setting.Hints:
            return FamilyStringSetting (setting)
        elif "directory" in setting.Hints:
            return FileStringSetting (setting, isDirectory=True, List=List)
        else:
            return StringSetting (setting, List=List)
    elif (List and setting.Info[1][2]) or \
        (not List and setting.Info[2]):
        return RestrictedStringSetting (setting, List=List)
    else:
        return StringSetting (setting, List=List)

def MakeIntSetting (setting, List=False):

    if List:
        info = setting.Info[1][2]
    else:
        info = setting.Info[2]

    if info:
        return EnumSetting (setting, List=List)
    else:
        return IntSetting (setting, List=List)

def MakeListSetting (setting, List=False):

    if List:
        raise TypeError ("Lists of lists are not supported")

    if setting.Info[0] == "Int" and setting.Info[1][2]:
        return EnumFlagsSetting (setting)
    elif setting.Info[0] == "String" and setting.Info[1][2]:
        return RestrictedStringFlagsSetting (setting)
    else:
        return ListSetting (setting)

SettingTypeDict = {
    "Match": MatchSetting,
    "String": MakeStringSetting,
    "Bool": BoolSetting,
    "Float": FloatSetting,
    "Int": MakeIntSetting,
    "Color": ColorSetting,
    "List": MakeListSetting,
    "Key": KeySetting,
    "Button": ButtonSetting,
    "Edge": EdgeSetting,
    "Bell": BellSetting,
}

def MakeSetting(setting, List=False):

    if List:
        t = setting.Info[0]
    else:
        t = setting.Type

    stype = SettingTypeDict.get(t, None)
    if not stype:
        return

    return stype(setting, List=List)

class SubGroupArea(object):
    def __init__(self, name, subGroup):
        self.MySettings = []
        self.SubGroup = subGroup
        self.Name = name
        settings = sorted(GetSettings(subGroup), key=SettingKeyFunc)
        if not name:
            self.Widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.Child = self.Widget
        else:
            self.Widget = Gtk.Frame()
            self.Expander = Gtk.Expander(label=name)
            self.Widget.add(self.Expander)
            self.Expander.set_expanded(False)
            self.Child = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.Expander.add(self.Child)

        self.Child.set_spacing(GridRow)
        if GTK_VERSION >= (3, 0, 0):
            self.Child.props.margin = GridRow
        else:
            self.Child.set_border_width(GridRow)

        # create a special widget for list subGroups
        if len(settings) > 1 and HasOnlyType(settings, 'List'):
            multiList = MultiListSetting(Settings=settings)
            multiList.Read()
            self.Child.pack_start(multiList.EBox, True, True, 0)
            self.MySettings.append(multiList)
            self.Empty = False
            if name:
                self.Expander.set_expanded(True)

            return # exit earlier to avoid unneeded logic's

        self.Empty = True
        for setting in settings:
            if not (setting.Plugin.Name == 'core' and setting.Name == 'active_plugins'):
                setting = MakeSetting(setting)
                if setting is not None:
                    setting.Read()
                    self.Child.pack_start(setting.EBox, True, True, 0)
                    self.MySettings.append(setting)
                    self.Empty = False

        if name and len(settings) < 4: # ahi hay magic numbers!
            self.Expander.set_expanded(True)

    def Filter(self, text, level=FilterAll):
        empty = True
        count = 0
        for setting in self.MySettings:
            if setting.Filter(text, level=level):
                empty = False
                count += 1

        if self.Name:
            self.Expander.set_expanded(count < 4)

        self.Widget.set_no_show_all(empty)

        if empty:
            self.Widget.hide()
        else:
            self.Widget.show()

        return not empty
