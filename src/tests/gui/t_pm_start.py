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

# Copyright (c) 2009, 2011, Oracle and/or its affiliates. All rights reserved.

import testutils
if __name__ == "__main__":
        testutils.setup_environment("../../../proto")
import pkg5unittest
import unittest

try:
        import ldtp
        import ldtputils
        if not "getmin" in dir(ldtp):
            raise ImportError
except ImportError:
        raise ImportError, "ldtp 2.X package not installed."

class TestPkgGuiStartBasics(pkg5unittest.SingleDepotTestCase):

        # pygtk requires unicode as the default encoding.
        default_utf8 = True

        foo10 = """
            open sample_package@1.0,5.11-0
            add set name="description" value="Some package description"
            close """

        def setUp(self):
                pkg5unittest.SingleDepotTestCase.setUp(self)

        def tearDown(self):
                pkg5unittest.SingleDepotTestCase.tearDown(self)

        def testStartPackagemanager(self):
                pm_str = "%s/usr/bin/packagemanager" % pkg5unittest.g_proto_area

                self.pkgsend_bulk(self.rurl, self.foo10)
                self.image_create(self.rurl)

                ldtp.launchapp(pm_str,["-R", self.get_img_path()])
                ldtp.waittillguiexist('Package Manager', state = ldtp.state.ENABLED)
                ldtp.selectmenuitem('Package Manager', 'mnuFile;mnuQuit')

if __name__ == "__main__":
        unittest.main()
