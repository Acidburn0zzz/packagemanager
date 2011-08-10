#!/usr/bin/python2.6
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
# Copyright (c) 2008, 2011, Oracle and/or its affiliates.  All rights reserved.
#

import errno
import fnmatch
import os
import platform
import stat
import sys
import shutil
import re
import subprocess
import tarfile
import tempfile
import urllib
import py_compile
import hashlib
import time

from distutils.errors import DistutilsError
from distutils.core import setup, Extension
from distutils.cmd import Command
from distutils.command.install import install as _install
from distutils.command.build import build as _build
from distutils.command.build_ext import build_ext as _build_ext
from distutils.command.build_py import build_py as _build_py
from distutils.command.bdist import bdist as _bdist
from distutils.command.clean import clean as _clean
from distutils.dist import Distribution

from distutils.sysconfig import get_python_inc
import distutils.file_util as file_util
import distutils.dir_util as dir_util
import distutils.util as util
import distutils.ccompiler
from distutils.unixccompiler import UnixCCompiler

osname = platform.uname()[0].lower()
ostype = arch = 'unknown'
if osname == 'sunos':
        arch = platform.processor()
        ostype = "posix"
elif osname == 'linux':
        arch = "linux_" + platform.machine()
        ostype = "posix"
elif osname == 'windows':
        arch = osname
        ostype = "windows"
elif osname == 'darwin':
        arch = osname
        ostype = "posix"
elif osname == 'aix':
        arch = "aix"
        ostype = "posix"

pwd = os.path.normpath(sys.path[0])

#
# Unbuffer stdout and stderr.  This helps to ensure that subprocess output
# is properly interleaved with output from this program.
#
sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 0)
sys.stderr = os.fdopen(sys.stderr.fileno(), "w", 0)

dist_dir = os.path.normpath(os.path.join(pwd, os.pardir, "proto", "dist_" + arch))
build_dir = os.path.normpath(os.path.join(pwd, os.pardir, "proto", "build_" + arch))
if "ROOT" in os.environ and os.environ["ROOT"] != "":
        root_dir = os.environ["ROOT"]
else:
        root_dir = os.path.normpath(os.path.join(pwd, os.pardir, "proto", "root_" + arch))
pkgs_dir = os.path.normpath(os.path.join(pwd, os.pardir, "packages", arch))
extern_dir = os.path.normpath(os.path.join(pwd, "extern"))

py_install_dir = 'usr/lib/python2.6/vendor-packages'

scripts_dir = 'usr/bin'
lib_dir = 'usr/lib'
svc_method_dir = 'lib/svc/method'

man1_dir = 'usr/share/man/man1'
man1m_dir = 'usr/share/man/man1m'
man5_dir = 'usr/share/man/man5'
resource_dir = 'usr/share/lib/pkg'
smf_app_dir = 'lib/svc/manifest/application/pkg'
execattrd_dir = 'etc/security/exec_attr.d'
authattrd_dir = 'etc/security/auth_attr.d'
sysrepo_dir = 'etc/pkg/sysrepo'
sysrepo_logs_dir = 'var/log/pkg/sysrepo'
sysrepo_cache_dir = 'var/cache/pkg/sysrepo'


# A list of source, destination tuples of modules which should be hardlinked
# together if the os supports it and otherwise copied.
hardlink_modules = []

scripts_sunos = {
        scripts_dir: [
                ['client.py', 'pkg'],
                ['pkgdep.py', 'pkgdepend'],
                ['pkgrepo.py', 'pkgrepo'],
                ['util/publish/pkgdiff.py', 'pkgdiff'],
                ['util/publish/pkgfmt.py', 'pkgfmt'],
                ['util/publish/pkglint.py', 'pkglint'],
                ['util/publish/pkgmerge.py', 'pkgmerge'],
                ['util/publish/pkgmogrify.py', 'pkgmogrify'],
                ['publish.py', 'pkgsend'],
                ['pull.py', 'pkgrecv'],
                ['sign.py', 'pkgsign'],
                ['packagemanager.py', 'packagemanager'],
                ['updatemanager.py', 'pm-updatemanager'],
                ],
        lib_dir: [
                ['depot.py', 'pkg.depotd'],
                ['checkforupdates.py', 'pm-checkforupdates'],
                ['updatemanagernotifier.py', 'updatemanagernotifier'],
                ['launch.py', 'pm-launch'],
                ['sysrepo.py', 'pkg.sysrepo'],
                ],
        svc_method_dir: [
                ['svc/svc-pkg-depot', 'svc-pkg-depot'],
                ['svc/svc-pkg-mdns', 'svc-pkg-mdns'],
                ['svc/svc-pkg-sysrepo', 'svc-pkg-sysrepo'],
                ],
        }

scripts_windows = {
        scripts_dir: [
                ['client.py', 'client.py'],
                ['pkgrepo.py', 'pkgrepo.py'],
                ['publish.py', 'publish.py'],
                ['pull.py', 'pull.py'],
                ['scripts/pkg.bat', 'pkg.bat'],
                ['scripts/pkgsend.bat', 'pkgsend.bat'],
                ['scripts/pkgrecv.bat', 'pkgrecv.bat'],
                ],
        lib_dir: [
                ['depot.py', 'depot.py'],
                ['scripts/pkg.depotd.bat', 'pkg.depotd.bat'],
                ],
        }

scripts_other_unix = {
        scripts_dir: [
                ['client.py', 'client.py'],
                ['pkgdep.py', 'pkgdep'],
                ['util/publish/pkgdiff.py', 'pkgdiff'],
                ['util/publish/pkgfmt.py', 'pkgfmt'],
                ['util/publish/pkgmogrify.py', 'pkgmogrify'],
                ['pull.py', 'pull.py'],
                ['publish.py', 'publish.py'],
                ['scripts/pkg.sh', 'pkg'],
                ['scripts/pkgsend.sh', 'pkgsend'],
                ['scripts/pkgrecv.sh', 'pkgrecv'],
                ],
        lib_dir: [
                ['depot.py', 'depot.py'],
                ['scripts/pkg.depotd.sh', 'pkg.depotd'],
                ],
        }

# indexed by 'osname'
scripts = {
        "sunos": scripts_sunos,
        "linux": scripts_other_unix,
        "windows": scripts_windows,
        "darwin": scripts_other_unix,
        "aix" : scripts_other_unix,
        "unknown": scripts_sunos,
        }

man1_files = [
        'man/packagemanager.1',
        'man/pkg.1',
        'man/pkgdepend.1',
        'man/pkgdiff.1',
        'man/pkgfmt.1',
        'man/pkglint.1',
        'man/pkgmerge.1',
        'man/pkgmogrify.1',
        'man/pkgsend.1',
        'man/pkgsign.1',
        'man/pkgrecv.1',
        'man/pkgrepo.1',
        'man/pm-updatemanager.1',
        ]
man1m_files = [
        'man/pkg.depotd.1m',
        'man/pkg.sysrepo.1m'
        ]
man5_files = [
        'man/pkg.5'
        ]
packages = [
        'pkg',
        'pkg.actions',
        'pkg.bundle',
        'pkg.client',
        'pkg.client.linkedimage',
        'pkg.client.transport',
        'pkg.file_layout',
        'pkg.flavor',
        'pkg.lint',
        'pkg.portable',
        'pkg.publish',
        'pkg.server'
        ]

pylint_targets = [
        'pkg.altroot',
        'pkg.client.linkedimage',
        'pkg.client.pkgdefs',
        ]

web_files = []
for entry in os.walk("web"):
        web_dir, dirs, files = entry
        if not files:
                continue
        web_files.append((os.path.join(resource_dir, web_dir), [
            os.path.join(web_dir, f) for f in files
            if f != "Makefile"
            ]))

smf_app_files = [
        'svc/pkg-mdns.xml',
        'svc/pkg-server.xml',
        'svc/pkg-update.xml',
        'svc/pkg-system-repository.xml',
        'svc/zoneproxy-client.xml',
        'svc/zoneproxyd.xml'
        ]
resource_files = [
        'util/opensolaris.org.sections',
        'util/pkglintrc',
        ]
sysrepo_files = [
        'util/apache2/sysrepo/sysrepo_httpd.conf.mako',
        'util/apache2/sysrepo/sysrepo_publisher_response.mako',
        ]
sysrepo_log_stubs = [
        'util/apache2/sysrepo/logs/access_log',
        'util/apache2/sysrepo/logs/error_log',
        ]
execattrd_files = [
        'util/misc/exec_attr.d/package:pkg',
        'util/misc/exec_attr.d/package:pkg:package-manager'
]
authattrd_files = ['util/misc/auth_attr.d/package:pkg']
syscallat_srcs = [
        'modules/syscallat.c'
        ]
pspawn_srcs = [
        'modules/pspawn.c'
        ]
elf_srcs = [
        'modules/elf.c',
        'modules/elfextract.c',
        'modules/liblist.c',
        ]
arch_srcs = [
        'modules/arch.c'
        ]
_actions_srcs = [
        'modules/actions/_actions.c'
        ]
solver_srcs = [
        'modules/solver/solver.c', 
        'modules/solver/py_solver.c'
        ]
solver_link_args = ["-lm", "-lc"]
if osname == 'sunos':
        solver_link_args = ["-ztext"] + solver_link_args

# Runs lint on the extension module source code
class pylint_func(Command):
        description = "Runs pylint tools over IPS python source code"
        user_options = []

        def initialize_options(self):
                pass

        def finalize_options(self):
                pass

        # Make string shell-friendly
        @staticmethod
        def escape(astring):
                return astring.replace(' ', '\\ ')

        def run(self, quiet=False):
                proto = os.path.join(root_dir, py_install_dir)
                sys.path.insert(0, proto)

                # Insert tests directory onto sys.path so any custom checkers
                # can be found.
                sys.path.insert(0, os.path.join(pwd, 'tests'))
                # assumes pylint is accessible on the sys.path
                from pylint import lint

                #
                # For some reason, the load-plugins option, when used in the
                # rcfile, does not work, so we put it here instead, to load
                # our custom checkers.
                #
                # Unfortunately, pylint seems pretty fragile and will crash if
                # we try to run it over all the current pkg source.  Hence for
                # now we only run it over a subset of the source.  As source
                # files are made pylint clean they should be added to the
                # pylint_targets list.
                #
                args = ['--load-plugins=multiplatform']
                if quiet:
                        args += ['--reports=no']
                args += ['--rcfile', os.path.join(pwd, 'tests', 'pylintrc')]
                args += pylint_targets
                lint.Run(args)


class pylint_func_quiet(pylint_func):

        def run(self, quiet=False):
                pylint_func.run(self, quiet=True)


include_dirs = [ 'modules' ]
lint_flags = [ '-u', '-axms', '-erroff=E_NAME_DEF_NOT_USED2' ]

# Runs lint on the extension module source code
class clint_func(Command):
        description = "Runs lint tools over IPS C extension source code"
        user_options = []

        def initialize_options(self):
                pass

        def finalize_options(self):
                pass

        # Make string shell-friendly
        @staticmethod
        def escape(astring):
                return astring.replace(' ', '\\ ')

        def run(self):
                # assumes lint is on the $PATH
                if osname == 'sunos' or osname == "linux":
                        archcmd = ['lint'] + lint_flags + ['-D_FILE_OFFSET_BITS=64'] + \
                            ["%s%s" % ("-I", k) for k in include_dirs] + \
                            ['-I' + self.escape(get_python_inc())] + \
                            arch_srcs
                        elfcmd = ['lint'] + lint_flags + \
                            ["%s%s" % ("-I", k) for k in include_dirs] + \
                            ['-I' + self.escape(get_python_inc())] + \
                            ["%s%s" % ("-l", k) for k in elf_libraries] + \
                            elf_srcs
                        _actionscmd = ['lint'] + lint_flags + \
                            ["%s%s" % ("-I", k) for k in include_dirs] + \
                            ['-I' + self.escape(get_python_inc())] + \
                            _actions_srcs
                        pspawncmd = ['lint'] + lint_flags + ['-D_FILE_OFFSET_BITS=64'] + \
                            ["%s%s" % ("-I", k) for k in include_dirs] + \
                            ['-I' + self.escape(get_python_inc())] + \
                            pspawn_srcs
                        syscallatcmd = ['lint'] + lint_flags + ['-D_FILE_OFFSET_BITS=64'] + \
                            ["%s%s" % ("-I", k) for k in include_dirs] + \
                            ['-I' + self.escape(get_python_inc())] + \
                            syscallat_srcs

                        print(" ".join(archcmd))
                        os.system(" ".join(archcmd))
                        print(" ".join(elfcmd))
                        os.system(" ".join(elfcmd))
                        print(" ".join(_actionscmd))
                        os.system(" ".join(_actionscmd))
                        print(" ".join(pspawncmd))
                        os.system(" ".join(pspawncmd))
                        print(" ".join(syscallatcmd))
                        os.system(" ".join(syscallatcmd))


# Runs both C and Python lint
class lint_func(Command):
        description = "Runs C and Python lint checkers"
        user_options = []

        def initialize_options(self):
                pass

        def finalize_options(self):
                pass

        # Make string shell-friendly
        @staticmethod
        def escape(astring):
                return astring.replace(' ', '\\ ')

        def run(self):
                clint_func(Distribution()).run()
                pylint_func(Distribution()).run()

class install_func(_install):
        def initialize_options(self):
                _install.initialize_options(self)

                # PRIVATE_BUILD set in the environment tells us to put the build
                # directory into the .pyc files, rather than the final
                # installation directory.
                private_build = os.getenv("PRIVATE_BUILD", None)

                if private_build is None:
                        self.install_lib = py_install_dir
                        self.install_data = os.path.sep
                        self.root = root_dir
                else:
                        self.install_lib = os.path.join(root_dir, py_install_dir)
                        self.install_data = root_dir

                # This is used when installing scripts, below, but it isn't a
                # standard distutils variable.
                self.root_dir = root_dir

        def run(self):
                """
                At the end of the install function, we need to rename some files
                because distutils provides no way to rename files as they are
                placed in their install locations.
                Also, make sure that cherrypy and other external dependencies
                are installed.
                """

                _install.run(self)

                for o_src, o_dest in hardlink_modules:
                        for e in [".py", ".pyc"]:
                                src = util.change_root(self.root_dir, o_src + e)
                                dest = util.change_root(
                                    self.root_dir, o_dest + e)
                                if ostype == "posix":
                                        if os.path.exists(dest) and \
                                            os.stat(src)[stat.ST_INO] != \
                                            os.stat(dest)[stat.ST_INO]:
                                                os.remove(dest)
                                        file_util.copy_file(src, dest,
                                            link="hard", update=1)
                                else:
                                        file_util.copy_file(src, dest, update=1)

                for d, files in scripts[osname].iteritems():
                        for (srcname, dstname) in files:
                                dst_dir = util.change_root(self.root_dir, d)
                                dst_path = util.change_root(self.root_dir,
                                       os.path.join(d, dstname))
                                dir_util.mkpath(dst_dir, verbose = True)
                                file_util.copy_file(srcname, dst_path, update = True)
                                # make scripts executable
                                os.chmod(dst_path,
                                    os.stat(dst_path).st_mode
                                    | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def hash_sw(swname, swarc, swhash):
        if swhash == None:
                return True

        print "checksumming %s" % swname
        hash = hashlib.sha1()
        f = open(swarc, "rb")
        while True:
                data = f.read(65536)
                if data == "":
                        break
                hash.update(data)
        f.close()

        if hash.hexdigest() == swhash:
                return True
        else:
                print >> sys.stderr, "bad checksum! %s != %s" % \
                    (swhash, hash.hexdigest())
                return False

def prep_sw(swname, swarc, swdir, swurl, swhash):
        swarc = os.path.join(extern_dir, swarc)
        swdir = os.path.join(extern_dir, swdir)
        if not os.path.exists(extern_dir):
                os.mkdir(extern_dir)

        if not os.path.exists(swarc):
                print "downloading %s" % swname
                try:
                        fname, hdr = urllib.urlretrieve(swurl, swarc)
                except IOError:
                        pass
                if not os.path.exists(swarc):
                        print >> sys.stderr, "Unable to retrieve %s.\n" \
                            "Please retrieve the file " \
                            "and place it at: %s\n" % (swurl, swarc)
                        # remove a partial download or error message from proxy
                        remove_sw(swname)
                        sys.exit(1)
        if not os.path.exists(swdir):
                if not hash_sw(swname, swarc, swhash):
                        sys.exit(1)

                print "unpacking %s" % swname
                tar = tarfile.open(swarc)
                # extractall doesn't exist until python 2.5
                for m in tar.getmembers():
                        tar.extract(m, extern_dir)
                tar.close()

        # If there are patches, apply them now.
        patchdir = os.path.join("patch", swname)
        already_patched = os.path.join(swdir, ".patched")
        if os.path.exists(patchdir) and not os.path.exists(already_patched):
                patches = os.listdir(patchdir)
                for p in patches:
                        patchpath = os.path.join(os.path.pardir,
                            os.path.pardir, patchdir, p)
                        print "Applying %s to %s" % (p, swname)
                        args = ["patch", "-d", swdir, "-i", patchpath, "-p0"]
                        if osname == "windows":
                                args.append("--binary")
                        ret = subprocess.Popen(args).wait()
                        if ret != 0:
                                print >> sys.stderr, \
                                    "patch failed and returned %d." % ret
                                print >> sys.stderr, \
                                    "Command was: %s" % " ".join(args)
                                sys.exit(1)
                file(already_patched, "w").close()

def run_cmd(args, swdir, env=None):
                if env is None:
                        env = os.environ
                ret = subprocess.Popen(args, cwd=swdir, env=env).wait()
                if ret != 0:
                        print >> sys.stderr, \
                            "install failed and returned %d." % ret
                        print >> sys.stderr, \
                            "Command was: %s" % " ".join(args)
                        sys.exit(1)

def remove_sw(swname):
        print("deleting %s" % swname)
        for file in os.listdir(extern_dir):
                if fnmatch.fnmatch(file, "%s*" % swname):
                        fpath = os.path.join(extern_dir, file)
                        if os.path.isfile(fpath):
                                os.unlink(fpath)
                        else:
                                shutil.rmtree(fpath, True)

class build_func(_build):
        def initialize_options(self):
                _build.initialize_options(self)
                self.build_base = build_dir

def get_hg_version():
        try:
                p = subprocess.Popen(['hg', 'id', '-i'], stdout = subprocess.PIPE)
                return p.communicate()[0].strip()
        except OSError:
                print >> sys.stderr, "ERROR: unable to obtain mercurial version"
                return "unknown"

def syntax_check(filename):
        """ Run python's compiler over the file, and discard the results.
            Arrange to generate an exception if the file does not compile.
            This is needed because distutil's own use of pycompile (in the
            distutils.utils module) is broken, and doesn't stop on error. """
        try:
                py_compile.compile(filename, os.devnull, doraise=True)
        except py_compile.PyCompileError, e:
                res = ""
                for err in e.exc_value:
                        if isinstance(err, basestring):
                                res += err + "\n"
                                continue

                        # Assume it's a tuple of (filename, lineno, col, code)
                        fname, line, col, code = err
                        res += "line %d, column %s, in %s:\n%s" % (line,
                            col or "unknown", fname, code)

                raise DistutilsError(res)

# On Solaris, ld inserts the full argument to the -o option into the symbol
# table.  This means that the resulting object will be different depending on
# the path at which the workspace lives, and not just on the interesting content
# of the object.
#
# In order to work around that bug (7076871), we create a new compiler class
# that looks at the argument indicating the output file, chdirs to its
# directory, and runs the real link with the output file set to just the base
# name of the file.
#
# Unfortunately, distutils isn't too customizable in this regard, so we have to
# twiddle with a couple of the names in the distutils.ccompiler namespace: we
# have to add a new entry to the compiler_class dict, and we have to override
# the new_compiler() function to point to our own.  Luckily, our copy of
# new_compiler() gets to be very simple, since we always know what we want to
# return.
class MyUnixCCompiler(UnixCCompiler):

        def link(self, *args, **kwargs):

                output_filename = args[2]
                output_dir = kwargs.get('output_dir')
                cwd = os.getcwd()

                assert(not output_dir)
                output_dir = os.path.join(cwd, os.path.dirname(output_filename))
                output_filename = os.path.basename(output_filename)
                nargs = args[:2] + (output_filename,) + args[3:]
                os.chdir(output_dir)

                UnixCCompiler.link(self, *nargs, **kwargs)

                os.chdir(cwd)

distutils.ccompiler.compiler_class['myunix'] = (
    'unixccompiler', 'MyUnixCCompiler',
    'standard Unix-style compiler with a link stage modified for Solaris'
)

def my_new_compiler(plat=None, compiler=None, verbose=0, dry_run=0, force=0):
        return MyUnixCCompiler(None, dry_run, force)

if osname == 'sunos':
        distutils.ccompiler.new_compiler = my_new_compiler

class build_ext_func(_build_ext):

        def initialize_options(self):
                _build_ext.initialize_options(self)
                if osname == 'sunos':
                        self.compiler = 'myunix'

class build_py_func(_build_py):

        def __init__(self, dist):
                ret = _build_py.__init__(self, dist)

                # Gather the timestamps of the .py files in the gate, so we can
                # force the mtimes of the built and delivered copies to be
                # consistent across builds, causing their corresponding .pyc
                # files to be unchanged unless the .py file content changed.

                self.timestamps = {}

                p = subprocess.Popen(
                    [sys.executable, os.path.join(pwd, "pydates")],
                    stdout=subprocess.PIPE)

                for line in p.stdout:
                        stamp, path = line.split()
                        stamp = float(stamp)
                        self.timestamps[path] = stamp

                if p.wait() != 0:
                        print >> sys.stderr, "ERROR: unable to gather .py " \
                            "timestamps"
                        sys.exit(1)

                return ret

        # override the build_module method to do VERSION substitution on pkg/__init__.py
        def build_module (self, module, module_file, package):

                if module == "__init__" and package == "pkg":
                        versionre = '(?m)^VERSION[^"]*"([^"]*)"'
                        # Grab the previously-built version out of the build
                        # tree.
                        try:
                                ocontent = \
                                    file(self.get_module_outfile(self.build_lib,
                                        [package], module)).read()
                                ov = re.search(versionre, ocontent).group(1)
                        except IOError:
                                ov = None
                        v = get_hg_version()
                        vstr = 'VERSION = "%s"' % v
                        # If the versions haven't changed, there's no need to
                        # recompile.
                        if v == ov:
                                return

                        mcontent = file(module_file).read()
                        mcontent = re.sub(versionre, vstr, mcontent)
                        tmpfd, tmp_file = tempfile.mkstemp()
                        os.write(tmpfd, mcontent)
                        os.close(tmpfd)
                        print "doing version substitution: ", v
                        rv = _build_py.build_module(self, module, tmp_file, package)
                        os.unlink(tmp_file)
                        return rv

                # Will raise a DistutilsError on failure.
                syntax_check(module_file)

                return _build_py.build_module(self, module, module_file, package)

        def copy_file(self, infile, outfile, preserve_mode=1, preserve_times=1,
            link=None, level=1):

                # If the timestamp on the source file (coming from mercurial if
                # unchanged, or from the filesystem if changed) doesn't match
                # the filesystem timestamp on the destination, then force the
                # copy to make sure the right data is in place.

                try:
                        dst_mtime = os.stat(outfile).st_mtime
                except OSError, e:
                        if e.errno != errno.ENOENT:
                                raise
                        dst_mtime = time.time()

                # The timestamp for __init__.py is the timestamp for the
                # workspace itself.
                if outfile.endswith("/pkg/__init__.py"):
                        src_mtime = self.timestamps["."]
                else:
                        src_mtime = self.timestamps[os.path.join("src", infile)]

                if dst_mtime != src_mtime:
                        f = self.force
                        self.force = True
                        dst, copied = _build_py.copy_file(self, infile, outfile,
                            preserve_mode, preserve_times, link, level)
                        self.force = f
                else:
                        dst, copied = outfile, 0

                # If we copied the file, then we need to go and readjust the
                # timestamp on the file to match what we have in our database.
                if copied and dst.endswith(".py"):
                        os.utime(dst, (src_mtime, src_mtime))

                return dst, copied

class clean_func(_clean):
        def initialize_options(self):
                _clean.initialize_options(self)
                self.build_base = build_dir

class clobber_func(Command):
        user_options = []
        description = "Deletes any and all files created by setup"

        def initialize_options(self):
                pass
        def finalize_options(self):
                pass
        def run(self):
                # nuke everything
                print("deleting " + dist_dir)
                shutil.rmtree(dist_dir, True)
                print("deleting " + build_dir)
                shutil.rmtree(build_dir, True)
                print("deleting " + root_dir)
                shutil.rmtree(root_dir, True)
                print("deleting " + pkgs_dir)
                shutil.rmtree(pkgs_dir, True)
                print("deleting " + extern_dir)
                shutil.rmtree(extern_dir, True)

class test_func(Command):
        # NOTE: these options need to be in sync with tests/run.py and the
        # list of options stored in initialize_options below. The first entry
        # in each tuple must be the exact name of a member variable.
        user_options = [
            ("archivedir=", 'a', "archive failed tests <dir>"),
            ("baselinefile=", 'b', "baseline file <file>"),
            ("coverage", "c", "collect code coverage data"),
            ("genbaseline", 'g', "generate test baseline"),
            ("only=", "o", "only <regex>"),
            ("parseable", 'p', "parseable output"),
            ("port=", "z", "lowest port to start a depot on"),
            ("timing", "t", "timing file <file>"),
            ("verbosemode", 'v', "run tests in verbose mode"),
            ("enableguitests", 'u', "enable IPS GUI tests, disabled by default"),
            ("stoponerr", 'x', "stop when a baseline mismatch occurs"),
            ("debugoutput", 'd', "emit debugging output"),
            ("showonexpectedfail", 'f',
                "show all failure info, even for expected fails"),
            ("startattest=", 's', "start at indicated test"),
            ("jobs=", 'j', "number of parallel processes to use"),
            ("quiet", "q", "use the dots as the output format"),
        ]
        description = "Runs unit and functional tests"

        def initialize_options(self):
                self.only = ""
                self.baselinefile = ""
                self.verbosemode = 0
                self.parseable = 0
                self.genbaseline = 0
                self.timing = 0
                self.coverage = 0
                self.stoponerr = 0
                self.debugoutput = 0
                self.showonexpectedfail = 0
                self.startattest = ""
                self.archivedir = ""
                self.port = 12001
                self.jobs = 1
                self.quiet = False

        def finalize_options(self):
                pass

        def run(self):

                os.putenv('PYEXE', sys.executable)
                os.chdir(os.path.join(pwd, "tests"))

                # Reconstruct the cmdline and send that to run.py
                cmd = [sys.executable, "run.py"]
                args = ""
                if "test" in sys.argv:
                        args = sys.argv[sys.argv.index("test")+1:]
                        cmd.extend(args)
                subprocess.call(cmd)

class dist_func(_bdist):
        def initialize_options(self):
                _bdist.initialize_options(self)
                self.dist_dir = dist_dir

# These are set to real values based on the platform, down below
compile_args = None
if osname in ("sunos", "linux", "darwin"):
        compile_args = [ "-O3" ]
if osname == "sunos":
        link_args = [ "-zstrip-class=nonalloc" ]
else:
        link_args = []
ext_modules = [
        Extension(
                'actions._actions',
                _actions_srcs,
                include_dirs = include_dirs,
                extra_compile_args = compile_args,
                extra_link_args = link_args
                ),
        Extension(
                'solver',
                solver_srcs,
                include_dirs = include_dirs + ["."],
                extra_compile_args = compile_args,
                extra_link_args = link_args + solver_link_args,
                define_macros = [('_FILE_OFFSET_BITS', '64')]
                ),
        ]
elf_libraries = None
data_files = web_files
cmdclasses = {
        'install': install_func,
        'build': build_func,
        'build_ext': build_ext_func,
        'build_py': build_py_func,
        'bdist': dist_func,
        'lint': lint_func,
        'clint': clint_func,
        'pylint': pylint_func,
        'pylint_quiet': pylint_func_quiet,
        'clean': clean_func,
        'clobber': clobber_func,
        'test': test_func,
        }

# all builds of IPS should have manpages
data_files += [
        (man1_dir, man1_files),
        (man1m_dir, man1m_files),
        (man5_dir, man5_files),
        (resource_dir, resource_files),
        ]

if osname == 'sunos':
        # Solaris-specific extensions are added here
        data_files += [
                (smf_app_dir, smf_app_files),
                (execattrd_dir, execattrd_files),
                (authattrd_dir, authattrd_files),
                (sysrepo_dir, sysrepo_files),
                (sysrepo_logs_dir, sysrepo_log_stubs),
                (sysrepo_cache_dir, {})
                ]

if osname == 'sunos' or osname == "linux":
        # Unix platforms which the elf extension has been ported to
        # are specified here, so they are built automatically
        elf_libraries = ['elf']
        ext_modules += [
                Extension(
                        'elf',
                        elf_srcs,
                        include_dirs = include_dirs,
                        libraries = elf_libraries,
                        extra_compile_args = compile_args,
                        extra_link_args = link_args
                        ),
                ]

        # Solaris has built-in md library and Solaris-specific arch extension
        # All others use OpenSSL and cross-platform arch module
        if osname == 'sunos':
            elf_libraries += [ 'md' ]
            ext_modules += [
                    Extension(
                            'arch',
                            arch_srcs,
                            include_dirs = include_dirs,
                            extra_compile_args = compile_args,
                            extra_link_args = link_args,
                            define_macros = [('_FILE_OFFSET_BITS', '64')]
                            ),
                    Extension(
                            'pspawn',
                            pspawn_srcs,
                            include_dirs = include_dirs,
                            extra_compile_args = compile_args,
                            extra_link_args = link_args,
                            define_macros = [('_FILE_OFFSET_BITS', '64')]
                            ),
                    Extension(
                            'syscallat',
                            syscallat_srcs,
                            include_dirs = include_dirs,
                            extra_compile_args = compile_args,
                            extra_link_args = link_args,
                            define_macros = [('_FILE_OFFSET_BITS', '64')]
                            ),
                    ]
        else:
            elf_libraries += [ 'ssl' ]

setup(cmdclass = cmdclasses,
    name = 'pkg',
    version = '0.1',
    package_dir = {'pkg':'modules'},
    packages = packages,
    data_files = data_files,
    ext_package = 'pkg',
    ext_modules = ext_modules,
    )
