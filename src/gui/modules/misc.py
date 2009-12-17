#!/usr/bin/python
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at usr/src/OPENSOLARIS.LICENSE
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at usr/src/OPENSOLARIS.LICENSE.
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#
# Copyright 2009 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.
#

SPECIAL_CATEGORIES = ["locale", "plugin"] # We should cut all, but last part of the
                                          # new name scheme as part of fix for #7037.
                                          # However we need to have an exception rule
                                          # where we will cut all but three last parts.

RELEASE_URL = "http://www.opensolaris.org" # Fallback url for release notes if api
                                           # does not gave us one.

import os
import sys
import urllib2
import urlparse
import socket
try:
        import gobject
        import gnome
        import gtk
        import pango
except ImportError:
        sys.exit(1)
import pkg.misc as misc
import pkg.client.api_errors as api_errors
import pkg.client.api as api
from pkg.gui.misc_non_gui import get_api_object as ngao
from pkg.gui.misc_non_gui import setup_logging as su_logging
from pkg.gui.misc_non_gui import shutdown_logging as sd_logging

def setup_logging(client_name):
        su_logging(client_name)
        
def shutdown_logging():
        sd_logging()
        
def get_icon_pixbuf(application_dir, icon_name):
        return get_pixbuf_from_path(os.path.join(application_dir,
            "usr/share/icons/package-manager"), icon_name)

def get_pixbuf_from_path(path, icon_name):
        icon = icon_name.replace(' ', '_')

        # Performance: Faster to check if files exist rather than catching
        # exceptions when they do not. Picked up open failures using dtrace
        png_path = os.path.join(path, icon + ".png")
        png_exists = os.path.exists(png_path)
        svg_path = os.path.join(path, icon + ".png")
        svg_exists = os.path.exists(png_path)

        if not png_exists and not svg_exists:
                return None
        try:
                return gtk.gdk.pixbuf_new_from_file(png_path)
        except gobject.GError:
                try:
                        return gtk.gdk.pixbuf_new_from_file(svg_path)
                except gobject.GError:
                        return None

def get_icon(icon_theme, name, size=16):
        try:
                return icon_theme.load_icon(name, size, 0)
        except gobject.GError:
                return None

def init_for_help(application_dir="/"):
        props = { gnome.PARAM_APP_DATADIR : os.path.join(application_dir,
                    'usr/share/package-manager/help') }
        gnome.program_init('package-manager', '0.1', properties=props)

def display_help(help_id=None):
        if help_id != None:
                gnome.help_display('package-manager', link_id=help_id)
        else:
                gnome.help_display('package-manager')

def get_pkg_name(pkg_name):
        index = -1
        try:
                index = pkg_name.rindex("/")
        except ValueError:
                # Package Name without "/"
                return pkg_name
        pkg_name_bk = pkg_name
        test_name = pkg_name[index:]
        pkg_name = pkg_name[:index]
        try:
                index = pkg_name.rindex("/")
        except ValueError:
                # Package Name with only one "/"
                return pkg_name_bk
        if pkg_name[index:].strip("/") not in SPECIAL_CATEGORIES:
                return test_name.strip("/")
        else:
                # The package name contains special category
                converted_name = pkg_name[index:] + test_name
                pkg_name = pkg_name[:index]
                try:
                        index = pkg_name.rindex("/")
                except ValueError:
                        # Only three parts "part1/special/part2"
                        return pkg_name + converted_name
                return pkg_name[index:].strip("/") + converted_name
        return pkg_name_bk

def get_api_object(img_dir, progtrack, parent_dialog):
        api_o = None
        message = None
        try:
                api_o = ngao(img_dir, progtrack)
        except api_errors.VersionException, ex:
                message = _("Version mismatch: expected version %d, got version %d") % \
                    (ex.expected_version, ex.received_version)
        except api_errors.ImageNotFoundException, ex:
                message = _("%s is not an install image") % ex.user_dir
        if message != None:
                if parent_dialog != None:
                        error_occurred(parent_dialog,
                            message, _("API Error"))
                        sys.exit(0)
                else:
                        print message
        return api_o

def error_occurred(parent, error_msg, msg_title = None,
    msg_type=gtk.MESSAGE_ERROR, use_markup = False):
        msgbox = gtk.MessageDialog(parent =
            parent,
            buttons = gtk.BUTTONS_CLOSE,
            flags = gtk.DIALOG_MODAL,
            type = msg_type,
            message_format = None)
        if use_markup:
                msgbox.set_markup(error_msg)
        else:
                msgbox.set_property('text', error_msg)
        if msg_title != None:
                title = msg_title
        else:
                title = _("Error")

        msgbox.set_title(title)
        msgbox.run()
        msgbox.destroy()

def set_package_details(pkg_name, local_info, remote_info, textview,
    installed_icon, not_installed_icon, update_available_icon, 
    is_all_publishers_installed=None, pubs_disabled_status=None):
        installed = True

        if not local_info:
                # Package is not installed
                local_info = remote_info
                installed = False

        if not remote_info:
                remote_info = local_info
                installed = True

        labs = {}
        labs["name"] = _("Name:")
        labs["desc"] = _("Description:")
        labs["size"] = _("Size:")
        labs["cat"] = _("Category:")
        labs["ins"] = _("Installed:")
        labs["available"] = _("Version Available:")
        labs["lat"] = _("Latest Version:")
        labs["repository"] = _("Publisher:")

        description = _("None")
        if local_info.summary:
                description = local_info.summary

        text = {}
        text["name"] = pkg_name
        text["desc"] = description
        if installed:
                yes_text = _("Yes, %(version)s (Build %(build)s-%(branch)s)")
                text["ins"] = yes_text % \
                    {"version": local_info.version,
                    "build": local_info.build_release,
                    "branch": local_info.branch}
                labs["available"] =  _("Latest Version:")
                if not same_pkg_versions(local_info, remote_info):
                        text["available"] = yes_text % \
                            {"version": remote_info.version,
                            "build": remote_info.build_release,
                            "branch": remote_info.branch}
                else:
                        text["available"] = _("No")
        else:
                text["ins"] = _("No")
                labs["available"] =  _("Latest Version:")
                text["available"] = _(
                    "%(version)s (Build %(build)s-%(branch)s)") % \
                    {"version": remote_info.version,
                    "build": remote_info.build_release,
                    "branch": remote_info.branch}
        if local_info.size != 0:
                text["size"] = misc.bytes_to_str(local_info.size)
        else:
                text["size"] = "0"
        categories = _("None")
        if local_info.category_info_list:
                verbose = len(local_info.category_info_list) > 1
                categories = ""
                categories += local_info.category_info_list[0].__str__(verbose)
                if len(local_info.category_info_list) > 1:
                        for ci in local_info.category_info_list[1:]:
                                categories += ", " + ci.__str__(verbose)

        text["cat"] = categories
        text["repository"] = local_info.publisher
        # pubs_disabled_status: dict of publisher disabled status:
        # pub_status[pub_name] = True disabled or False enabled
        if is_all_publishers_installed and pubs_disabled_status != None:
                if local_info.publisher in pubs_disabled_status:
                        if pubs_disabled_status[local_info.publisher]:
                                text["repository"] = local_info.publisher + \
                                _(" (disabled)")
                else:
                        text["repository"] = local_info.publisher + _(" (removed)")
        set_package_details_text(labs, text, textview, installed_icon,
                not_installed_icon, update_available_icon)
        return (labs, text)


def set_package_details_text(labs, text, textview, installed_icon,
    not_installed_icon, update_available_icon):
        max_len = 0
        for lab in labs:
                if len(labs[lab]) > max_len:
                        max_len = len(labs[lab])

        style = textview.get_style()
        font_size_in_pango_unit = style.font_desc.get_size()
        font_size_in_pixel = font_size_in_pango_unit / pango.SCALE
        tab_array = pango.TabArray(2, True)
        tab_array.set_tab(1, pango.TAB_LEFT, max_len * font_size_in_pixel)
        textview.set_tabs(tab_array)

        infobuffer = textview.get_buffer()
        infobuffer.set_text("")
        i = 0
        __add_line_to_generalinfo(infobuffer, i, labs["name"], text["name"])
        i += 1
        __add_line_to_generalinfo(infobuffer, i, labs["desc"], text["desc"])
        i += 1
        installed = False
        if text["ins"] == _("No"):
                icon = not_installed_icon
        else:
                icon = installed_icon
                installed = True
        __add_line_to_generalinfo(infobuffer, i, labs["ins"],
            text["ins"], icon, font_size_in_pixel)
        i += 1
        if installed and text["available"] != _("No"):
                __add_line_to_generalinfo(infobuffer, i,
                    labs["available"], text["available"],
                    update_available_icon, font_size_in_pixel)
        else:
                __add_line_to_generalinfo(infobuffer, i,
                    labs["available"], text["available"])
        i += 1
        if text["size"] != "0":
                __add_line_to_generalinfo(infobuffer, i, labs["size"], text["size"])
                i += 1
        __add_line_to_generalinfo(infobuffer, i, labs["cat"], text["cat"])
        i += 1
        __add_line_to_generalinfo(infobuffer, i, labs["repository"],
            text["repository"])

def __add_line_to_generalinfo(text_buffer, index, label, text,
    icon = None, font_size = 1):
        itr = text_buffer.get_iter_at_line(index)
        text_buffer.insert_with_tags_by_name(itr, label, "bold")
        end_itr = text_buffer.get_end_iter()
        if icon == None:
                text_buffer.insert(end_itr, "\t%s\n" % text)
        else:
                resized_icon = resize_icon(icon, font_size)
                text_buffer.insert(end_itr, "\t")
                text_buffer.get_end_iter()
                text_buffer.insert_pixbuf(end_itr, resized_icon)
                text_buffer.insert(end_itr, " %s\n" % text)

def same_pkg_versions(info1, info2):
        if info1 == None or info2 == None:
                return False

        return info1.version == info2.version and \
                info1.build_release == info2.build_release and \
                info1.branch == info2.branch

def resize_icon(icon, font_size):
        width = icon.get_width()
        height = icon.get_height()
        return icon.scale_simple(
            (font_size * width) / height,
            font_size,
            gtk.gdk.INTERP_BILINEAR)

def get_pkg_info(api_o, pkg_stem, local):
        info = None
        try:
                info = api_o.info([pkg_stem], local,
                    api.PackageInfo.ALL_OPTIONS -
                    frozenset([api.PackageInfo.LICENSES]))
        except (api_errors.TransportError):
                return info
        except (api_errors.InvalidDepotResponseException):
                return info
 
        pkgs_info = None
        package_info = None
        if info:
                pkgs_info = info[0]
        if pkgs_info:
                package_info = pkgs_info[0]
        if package_info:
                return package_info
        else:
                return None

def restart_system():
        # "init 6" performs reboot in a clean and orderly manner informing
        # the svc.startd daemon of the change in runlevel which subsequently
        # achieves the appropriate milestone and ultimately executes
        # the rc0 kill scripts.
        command = "init 6"
        return os.system(command)

def set_modal_and_transient(top_window, parent_window = None):
        if parent_window:
                top_window.set_transient_for(parent_window)
        top_window.set_modal(True)

def get_catalogrefresh_exception_msg(cre):
        if not isinstance(cre, api_errors.CatalogRefreshException):
                return ""
        msg = _("Catalog refresh error:\n")
        if cre.succeeded < cre.total:
                msg += _("Only %s out of %s catalogs successfully updated.\n") % \
                (cre.succeeded, cre.total)
        msg += "\n"

        for pub, err in cre.failed:
                if isinstance(err, urllib2.HTTPError):
                        msg += "%s: %s - %s" % \
                            (err.filename, err.code, err.msg)
                elif isinstance(err, urllib2.URLError):
                        if err.args[0][0] == 8:
                                msg += "%s: %s" % \
                                    (urlparse.urlsplit(
                                        pub["origin"])[1].split(":")[0],
                                    err.args[0][1])
                        else:
                                if isinstance(err.args[0], socket.timeout):
                                        msg += "%s: %s" % \
                                            (pub["origin"], "timeout")
                                else:
                                        msg += "%s: %s" % \
                                            (pub["origin"], err.args[0][1])
                else:
                        msg += str(err)

        if cre.message:
                msg += cre.message

        return msg

def change_stockbutton_label(button, text):
        # Gtk.Button->Gtk.Alignment->Gtk.HBox->[Gtk.Image, Gtk.Label]
        # Drill into Button widget to get Gtk.Label and set its text
        children = button.get_children()
        if len(children) == 0:
                return
        align = children[0]
        if not align or not isinstance(align, gtk.Alignment):
                return
        children = align.get_children()
        if len(children) == 0:
                return
        hbox = children[0]
        if not hbox or not isinstance(hbox, gtk.HBox):
                return
        children = hbox.get_children()
        if not (len(children) > 1):
                return
        button_label = children[1]
        if not button_label or not isinstance(button_label, gtk.Label):
                return
        button_label.set_label(text)
