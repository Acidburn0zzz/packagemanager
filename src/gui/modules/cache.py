#!/usr/bin/python2.4
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

import os
import sys
try:
        import gtk
except ImportError:
        sys.exit(1)
from threading import Thread
import pkg.gui.enumerations as enumerations
import pkg.gui.misc as gui_misc

nobe = False

try:
        import libbe as be
except ImportError:
        nobe = True

CACHE_VERSION = 8
INDEX_HASH_LENGTH = 41

class CacheListStores:
        def __init__(self, icon_theme, application_dir, api_o, update_available_icon,
            installed_icon, not_installed_icon):
                self.api_o = api_o
                self.update_available_icon = update_available_icon
                self.installed_icon = installed_icon
                self.not_installed_icon = not_installed_icon
                self.category_icon = gui_misc.get_pixbuf_from_path(
                    os.path.join(application_dir,
                    "usr/share/package-manager/"), "legend_newupdate")

        def check_if_cache_uptodate(self, publisher):
                try:
                        info = self.__load_cache_info(publisher)
                        if info:
                                if info.get("version") != CACHE_VERSION:
                                        return False
                                image_last_modified = \
                                    self.__get_publisher_timestamp(publisher)
                                cache_last_modified = info.get("date")
                                if not cache_last_modified or \
                                    cache_last_modified != image_last_modified:
                                        return False
                                cache_index_hash = info.get("index_hash")
                                file_index_hash = self.get_index_timestamp()
                                if not cache_index_hash or \
                                    cache_index_hash != file_index_hash:
                                        return False
                                be_name = info.get("be_name")
                                if be_name == None or \
                                    be_name != self.__get_active_be_name():
                                        return False
                        else:
                                return False
                except IOError:
                        return False
                return True

        def __get_cache_dir(self):
                return gui_misc.get_cache_dir(self.api_o)

        def get_index_timestamp(self):
                img = self.api_o.img
                index_path = os.path.join(img.imgdir, "state/installed")
                try:
                        return os.path.getmtime(index_path)
                except (OSError, IOError):
                        return None

        def __get_publisher_timestamp(self, publisher):
                dt = self.api_o.get_publisher_last_update_time(prefix=publisher)
                if dt:
                        return dt.ctime()
                return dt

        def remove_datamodel(self, publisher):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                dump_info = {}
                dump_info["version"] = CACHE_VERSION
                dump_info["date"] = None
                dump_info["publisher"] = publisher
                dump_info["index_hash"] = None
                dump_info["be_name"] = None

                try:
                        gui_misc.dump_cache_file(
                            os.path.join(cache_dir, publisher+".cpl"),
                            dump_info)
                except IOError:
                        #Silently return, as probably user doesn't have permissions or
                        #other error which simply doesn't affect the GUI work
                        return

        def dump_datamodels(self, publisher, application_list, category_list, 
            section_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                dump_info = {}
                dump_info["version"] = CACHE_VERSION
                dump_info["date"] = self.__get_publisher_timestamp(publisher)
                dump_info["publisher"] = publisher
                dump_info["index_hash"] = self.get_index_timestamp()
                dump_info["be_name"] = self.__get_active_be_name()

                try:
                        gui_misc.dump_cache_file(
                            os.path.join(cache_dir, publisher+".cpl"),
                            dump_info)
                        self.__dump_category_list(publisher, category_list)
                        self.__dump_application_list(publisher, application_list)
                        self.__dump_section_list(publisher, section_list)
                except IOError:
                        #Silently return, as probably user doesn't have permissions or
                        #other error which simply doesn't affect the GUI work
                        return

        def __dump_category_list(self, publisher, category_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                categories = []
                for category in category_list:
                        cat = {}
                        cat["id"] = category[enumerations.CATEGORY_ID]
                        cat["name"] = category[enumerations.CATEGORY_NAME]
                        cat["description"] = category[enumerations.CATEGORY_DESCRIPTION]
                        # Can't store pixbuf :(
                        # cat["icon"] = category[enumerations.CATEGORY_ICON]
                        cat["iconvisible"] = category[enumerations.CATEGORY_ICON_VISIBLE]
                        cat["visible"] = category[enumerations.CATEGORY_VISIBLE]
                        cat["section_list"] = category[enumerations.SECTION_LIST_OBJECT]
                        categories.append(cat)
                gui_misc.dump_cache_file(os.path.join(cache_dir, 
                    publisher+"_categories.cpl"), categories)

        def __dump_application_list(self, publisher, application_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                apps = []
                for application in application_list:
                        app = {}
                        app["mark"] = application[enumerations.MARK_COLUMN]
                        app["name"] = application[enumerations.NAME_COLUMN]
                        app["status"] = application[enumerations.STATUS_COLUMN]
                        app["fmri"] = application[enumerations.FMRI_COLUMN]
                        app["stem"] = application[enumerations.STEM_COLUMN]
                        app["display_name"] = \
                            application[enumerations.DISPLAY_NAME_COLUMN]
                        app["is_visible"] = application[enumerations.IS_VISIBLE_COLUMN]
                        app["category_list"] = \
                            application[enumerations.CATEGORY_LIST_COLUMN]
                        app["pkg_authority"] = application[enumerations.AUTHORITY_COLUMN]
                        apps.append(app)
                gui_misc.dump_cache_file(
                    os.path.join(cache_dir, publisher+"_packages.cpl"), apps)

        def __dump_section_list(self, publisher, section_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                sections = []
                for section in section_list:
                        sec = {}
                        sec["id"] = section[enumerations.SECTION_ID]
                        sec["name"] = section[enumerations.SECTION_NAME]
                        sec["subcategory"] = section[enumerations.SECTION_SUBCATEGORY]
                        sec["enabled"] = section[enumerations.SECTION_ENABLED]
                        sections.append(sec)
                gui_misc.dump_cache_file(
                    os.path.join(cache_dir, publisher+"_sections.cpl"),
                    sections)

        def __load_cache_info(self, publisher):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return None
                info = gui_misc.read_cache_file(os.path.join(cache_dir, publisher+".cpl"))
                return info

        def load_category_list(self, publisher, category_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                categories = gui_misc.read_cache_file(
                    os.path.join(cache_dir, publisher+"_categories.cpl"))
                cat_count = 0
                for cat in categories:
                        cat_id = cat.get("id")
                        name = cat.get("name")
                        description = cat.get("description")
                        icon = None
                        icon_visible = cat.get("iconvisible")
                        if icon_visible:
                                icon = self.category_icon
                        visible = cat.get("visible")
                        section_list = cat.get("section_list")               
                        cat = \
                            [
                                cat_id, name, description, icon, icon_visible,
                                visible, section_list
                            ]
                        category_list.insert(cat_count, cat)
                        cat_count += 1

        def load_application_list(self, publisher, application_list, 
            selected_pkgs=None):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                applications = gui_misc.read_cache_file(
                    os.path.join(cache_dir, publisher+"_packages.cpl"))
                app_count = len(application_list)
                if app_count > 0:
                        app_count += 1
                selected_pkgs_pub = None
                if selected_pkgs != None:
                        selected_pkgs_pub = selected_pkgs.get(publisher)
                for app in applications:
                        marked = False
                        status_icon = None
                        name = app.get("name")
                        status = app.get("status")
                        if status == enumerations.INSTALLED:
                                status_icon = self.installed_icon
                        elif status == enumerations.UPDATABLE:
                                status_icon = self.update_available_icon
                        else:
                                status_icon = self.not_installed_icon
                        fmri = app.get("fmri")
                        stem = app.get("stem")
                        if selected_pkgs_pub != None:
                                if stem in selected_pkgs_pub:
                                        marked = True
                        display_name = app.get("display_name")
                        is_visible = app.get("is_visible")
                        category_list = app.get("category_list")
                        pkg_authority = app.get("pkg_authority")
                        #Not Caching Descriptions, set to "..." so they will be refetched
                        app = \
                            [
                                marked, status_icon, name, "...", status,
                                fmri, stem, display_name, is_visible, 
                                category_list, pkg_authority
                            ]
                        application_list.insert(app_count, app)
                        app_count += 1

        def load_section_list(self, publisher, section_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                sections = gui_misc.read_cache_file(
                    os.path.join(cache_dir, publisher+"_sections.cpl"))
                sec_count = 0
                for sec in sections:
                        sec_id = sec.get("id")
                        name = sec.get("name")
                        subcategory = None
                        enabled = sec.get("enabled")
                        section = \
                            [
                                sec_id, name, subcategory, enabled
                            ]
                        section_list.insert(sec_count, section)
                        sec_count += 1

        @staticmethod
        def __get_active_be_name():
                if nobe:
                        return None
                be_list = be.beList()
                error_code = None
                be_list_loop = None
                if len(be_list) > 1 and type(be_list[0]) == type(-1):
                        error_code = be_list[0]
                if error_code != None and error_code == 0:
                        be_list_loop = be_list[1]
                elif error_code != None and error_code != 0:
                        return None
                else:
                        be_list_loop = be_list
                for bee in be_list_loop:
                        if bee.get("orig_be_name"):
                                name = bee.get("orig_be_name")
                                active = bee.get("active")                        
                                if active:
                                        return name
                return None

        def __dump_search_completion_info(self, completion_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                texts = []
                for text in completion_list:
                        txt = {}
                        txt["text"] = text[0]
                        texts.append(txt)
                try:
                        gui_misc.dump_cache_file(
                            os.path.join(cache_dir, ".__search__completion.cpl"), texts)
                except IOError:
                        return

        def __load_search_completion_info(self, completion_list):
                cache_dir = self.__get_cache_dir()
                if not cache_dir:
                        return
                texts = []
                try:
                        texts = gui_misc.read_cache_file(
                            os.path.join(cache_dir, ".__search__completion.cpl"))
                except IOError:
                        return gtk.ListStore(str)

                txt_count = 0
                for txt in texts:
                        txt_val = txt.get("text")
                        text = [ txt_val ]
                        completion_list.insert(txt_count, text)
                        txt_count += 1

        def dump_search_completion_info(self, completion_list):
                Thread(target = self.__dump_search_completion_info,
                    args = (completion_list, )).start()

        def load_search_completion_info(self, completion_list):
                Thread(target = self.__load_search_completion_info,
                    args = (completion_list, )).start()
