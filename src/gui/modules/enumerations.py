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
# Copyright 2008 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.
#

"""
This module consists of user readable enumerations for the data models
used in the IPS GUI
"""

(
MARK_COLUMN,
STATUS_ICON_COLUMN,
NAME_COLUMN,
DESCRIPTION_COLUMN,
STATUS_COLUMN,
FMRI_COLUMN,             # This should go once, the api will be fully functionall
STEM_COLUMN,
DISPLAY_NAME_COLUMN,
IS_VISIBLE_COLUMN,       # True indicates that the package is visible in ui
CATEGORY_LIST_COLUMN,    # list of categories to which package belongs
) = range(10)

#For the STATUS_COLUMN
(
INSTALLED,
NOT_INSTALLED,
UPDATABLE,
) = range(3)

#Categories
(
CATEGORY_ID,
CATEGORY_NAME,
CATEGORY_DESCRIPTION,
CATEGORY_ICON,
CATEGORY_ICON_VISIBLE,
CATEGORY_VISIBLE,
SECTION_LIST_OBJECT,     #List with the sections to which category belongs 
) = range(7)

#Sections
(
SECTION_ID,
SECTION_NAME,
SECTION_SUBCATEGORY,
SECTION_ENABLED,
) = range(4)

#Filter
(
FILTER_ID,
FILTER_NAME,
) = range(2)

#Filter
(
FILTER_ALL,
FILTER_INSTALLED,
FILTER_UPDATES,
FILTER_NOT_INSTALLED,
FILTER_SEPARATOR,
FILTER_SELECTED,
) = range(6)

#Repositories switch
(
REPOSITORY_ID,
REPOSITORY_NAME,
) = range(2)

(
INSTALL_UPDATE,
REMOVE,
IMAGE_UPDATE
) = range(3)

#Repository List in Manage Repositories Dialog
(
PUBLISHER_NAME,
PUBLISHER_PREFERRED,
PUBLISHER_URL,
PUBLISHER_SSL_KEY,
PUBLISHER_SSL_CERT,
PUBLISHER_MIRRORS,
PUBLISHER_ENABLED,
) = range(7)


