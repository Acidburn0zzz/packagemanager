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

# Copyright 2007 Sun Microsystems, Inc.  All rights reserved.
# Use is subject to license terms.

import os
import unittest
import tempfile
import pkg.client.imageconfig as imageconfig


class TestImageConfig(unittest.TestCase):
        def setUp(self):

		fd, self.sample_conf = tempfile.mkstemp()
                f = os.fdopen(fd, "w")

		f.write("""\
[policy]
Display-Copyrights: False

[authority_sfbay.sun.com]
prefix: sfbay.sun.com
origin: http://zruty.sfbay:10001
mirrors:
""")
                f.close()
		self.ic = imageconfig.ImageConfig()

        def tearDown(self):
		try:
			os.remove(self.sample_conf)
		except:
			pass

	def test_read(self):
		self.ic.read(self.sample_conf)

	def test_missing_conffile(self):
		#
		#  See what happens if the conf file is missing.
		#
		os.remove(self.sample_conf)
		self.assertRaises(RuntimeError, self.ic.read, self.sample_conf)

# XXX more test cases needed.

if __name__ == "__main__":
        unittest.main()
