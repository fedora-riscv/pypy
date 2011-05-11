Name:           pypy
Version:        1.5
Release:        1%{?dist}
Summary:        Python implementation with a Just-In-Time compiler

Group:          Development/Languages
# LGPL and another free license we'd need to ask spot about are present in some
# java jars that we're not building with atm (in fact, we're deleting them
# before building).  If we restore those we'll have to work out the new
# licensing terms
License:        MIT and Python and UCD
URL:            http://pypy.org/
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

# High-level configuration of the build:

# PyPy consists of an implementation of an interpreter (with JIT compilation)
# for the full Python language  written in a high-level language, leaving many
# of the implementation details as "pluggable" policies.
#
# The implementation language is then compiled down to .c code, from which we
# obtain a binary.
#
# This allows us to build a near-arbitrary collection of different
# implementations of Python with differing tradeoffs
#
# (As it happens, the implementation language is itself Python, albeit a
# restricted subset "RPython", chosen to making it amenable to being compiled.
# The result implements the full Python language though)

# We could build many different implementations of Python.
# For now, let's focus on the implementation that appears to be receiving the
# most attention upstream: the JIT-enabled build, with all standard
# optimizations

# Building a configuration can take significant time:

# A build of pypy (with jit) on i686 took 77 mins:
#  [Timer] Timings:
#  [Timer] annotate                       ---  583.3 s
#  [Timer] rtype_lltype                   ---  760.9 s
#  [Timer] pyjitpl_lltype                 ---  567.3 s
#  [Timer] backendopt_lltype              ---  375.6 s
#  [Timer] stackcheckinsertion_lltype     ---   54.1 s
#  [Timer] database_c                     ---  852.2 s
#  [Timer] source_c                       --- 1007.3 s
#  [Timer] compile_c                      ---  419.9 s
#  [Timer] ===========================================
#  [Timer] Total:                         --- 4620.5 s
#
# A build of pypy (nojit) on x86_64 took about an hour:
#  [Timer] Timings:
#  [Timer] annotate                       ---  537.5 s
#  [Timer] rtype_lltype                   ---  667.3 s
#  [Timer] backendopt_lltype              ---  385.4 s
#  [Timer] stackcheckinsertion_lltype     ---   42.5 s
#  [Timer] database_c                     ---  625.3 s
#  [Timer] source_c                       --- 1040.2 s
#  [Timer] compile_c                      ---  273.9 s
#  [Timer] ===========================================
#  [Timer] Total:                         --- 3572.0 s
#
#
# A build of pypy-stackless on i686 took about 87 mins:
#  [Timer] Timings:
#  [Timer] annotate                       ---  584.2 s
#  [Timer] rtype_lltype                   ---  777.3 s
#  [Timer] backendopt_lltype              ---  365.9 s
#  [Timer] stackcheckinsertion_lltype     ---   39.3 s
#  [Timer] database_c                     --- 1089.6 s
#  [Timer] source_c                       --- 1868.6 s
#  [Timer] compile_c                      ---  490.4 s
#  [Timer] ===========================================
#  [Timer] Total:                         --- 5215.3 s


# We will build a "pypy" binary.
#
# Unfortunately, the JIT support is only available on some architectures.
#
# pypy-1.4/pypy/jit/backend/detect_cpu.py:getcpuclassname currently supports the
# following options:
#  'i386', 'x86'
#  'x86-without-sse2':
#  'x86_64'
#  'cli'
#  'llvm'
#
# We will only build with JIT support on those architectures, and build without
# it on the other archs.  The resulting binary will typically be slower than
# CPython for the latter case.
#
%ifarch %{ix86} x86_64
# FIXME: is there a better way of expressing "intel" here?
%global with_jit 1
%else
%global with_jit 0
%endif

# Should we build a "pypy-stackless" binary?
%global with_stackless 0


# Easy way to enable/disable verbose logging:
%global verbose_logs 0

%global pypyprefix %{_libdir}/pypy-%{version}
%global pylibver 2.7

# We refer to this subdir of the source tree in a few places during the build:
%global goal_dir pypy/translator/goal


# Turn off the brp-python-bytecompile postprocessing script
# We manually invoke it later on, using the freshly built pypy binary
%global __os_install_post \
  %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

# Source and patches:
Source0:        http://pypy.org/download/pypy-%{version}-src.tar.bz2

# Edit a translator file for linux in order to configure our cflags and dynamic libffi
Patch0:         pypy-1.5-config.patch

# By default, if built at a tty, the translation process renders a Mandelbrot
# set to indicate progress.
# This obscures useful messages, and may waste CPU cycles, so suppress it, and
# merely render dots:
Patch1:         pypy-1.2-suppress-mandelbrot-set-during-tty-build.patch

# test_commmands fails on SELinux systems due to a change in the output
# of "ls" (http://bugs.python.org/issue7108)
Patch2: fix-test_commands-expected-ls-output-issue7108.patch

# When locating the pypy standard libraries, look first within
# LIBRARY_INSTALLATION_PATH.
# We convert this from being a non-existant variable into a string literal
# with the value of "pypyprefix" in the "prep" phase below.
#
# We still use the scanning relative to the binary location when invoking a
# pypy binary during the build (e.g. during "check")
#
# Sent upstream (with caveats) as:
#   https://codespeak.net/issue/pypy-dev/issue614
Patch3: pypy-1.4.1-add-LIBRARY_INSTALLATION_PATH.patch

# Try to improve the readability of the generated .c code, by adding in the
# RPython source as comments where possible.
# A version of this was sent upstream as:
#  http://codespeak.net/pipermail/pypy-dev/2010q4/006532.html
# TODO: get this into the upstream bug tracker, and finish inlining
# support (rhbz#666963)
Patch4: pypy-1.5-more-readable-c-code.patch


# Build-time requirements:

# pypy's can be rebuilt using itself, rather than with CPython; doing so
# halves the build time.
#
# Turn it off with this boolean, to revert back to rebuilding using CPython
# and avoid a cycle in the build-time dependency graph:

# I'm disabling the self-hosting for now, due to a fatal error seen inside the
# JIT, presumably whilst JIT-compiling something within the translator's
# inliner.
# 
# Specifically, building pypy-1.4.1-7.fc15.src.rpm on x86_64 using pypy-1.4.1-5.fc15.x86_64 
#   http://koji.fedoraproject.org/koji/taskinfo?taskID=2721517
# failed with this RPython traceback:
#     ... snip ...
#   [rtyper:WARNING] prebuilt instance <pypy.rpython.memory.gctransform.asmgcroot.ShapeDecompressor instance at 0x00000000f0b5bc80> has no attribute 'addr'
#   [rtyper] specializing: 179300 / 180508 blocks   (99%)
#   [rtyper] specializing: 180500 / 180566 blocks   (99%)
#   [rtyper] -=- specialized 1363 more blocks -=-
#   [rtyper] specializing: 180600 / 180777 blocks   (99%)
#   [rtyper] -=- specialized 211 more blocks -=-
#   [backendopt:inlining] phase with threshold factor: 32.4
#   [backendopt:inlining] heuristic: pypy.translator.backendopt.inline.inlining_heuristic
#   [x86/regalloc] Bogus arg in operation 76 at 0
#   RPython traceback:
#     File "implement_62.c", line 39979, in send_bridge_to_backend
#     File "implement_69.c", line 65301, in Assembler386_assemble_bridge
#     File "implement_72.c", line 8078, in RegAlloc_prepare_bridge
#     File "implement_40.c", line 53061, in RegAlloc__prepare
#     File "implement_44.c", line 14305, in RegAlloc__compute_vars_longevity
#   Fatal RPython error: NotImplementedError
#
# This appears to be deep within pypy/jit/backend/x86/regalloc.py which has
# called "not_implemented" to emit this message to stderr, before raising the
# exception:
#   [x86/regalloc] Bogus arg in operation 76 at 0

%global use_self_when_building 0
%if 0%{use_self_when_building}
BuildRequires: pypy
%global bootstrap_python_interp pypy
%else
BuildRequires: python-devel
%global bootstrap_python_interp python
%endif



# FIXME: I'm seeing errors like this in the logs:
#   [translation:WARNING] The module '_rawffi' is disabled
#   [translation:WARNING] because importing pypy.rlib.libffi raised ImportError
#   [translation:WARNING] 'libffi.a' not found in ['/usr/lib/libffi', '/usr/lib']
# Presumably we need to fix things to support dynamically-linked libffi
BuildRequires:  libffi-devel

BuildRequires:  zlib-devel
BuildRequires:  bzip2-devel
BuildRequires:  ncurses-devel
BuildRequires:  expat-devel
BuildRequires:  openssl-devel
%ifarch %{ix86} x86_64 ppc ppc64 s390x
BuildRequires:  valgrind-devel
%endif

# Used by the selftests, though not by the build:
BuildRequires:  gc-devel

BuildRequires:  /usr/bin/execstack

# pypy is bundling these so we delete them in %%prep.  I don't think they are
# needed unless we build pypy targetted at running on the jvm.
#BuildRequires:  jna
#BuildRequires: jasmin  # Not yet in Fedora


# Metadata for the core package (the JIT build):
Requires: pypy-libs = %{version}-%{release}

%description
PyPy's implementation of Python, featuring a Just-In-Time compiler on some CPU
architectures, and various optimized implementations of the standard types
(strings, dictionaries, etc)

%if 0%{with_jit}
This build of PyPy has JIT-compilation enabled.
%else
This build of PyPy has JIT-compilation disabled, as it is not supported on this
CPU architecture.
%endif


%package libs
Group:    Development/Languages
Summary:  Run-time libraries used by PyPy implementations of Python
%description libs
Libraries required by the various PyPy implementations of Python.


%package devel
Group:    Development/Languages
Summary:  Development tools for working with PyPy
%description devel
Header files for building C extension modules against PyPy

Requires: pypy = %{version}-%{release}


%if 0%{with_stackless}
%package stackless
Group:    Development/Languages
Summary:  Stackless Python interpreter built using PyPy
Requires: pypy-libs = %{version}-%{release}
%description stackless
Build of PyPy with support for micro-threads for massive concurrency
%endif

%if 0%{with_stackless}
%package stackless
Group:    Development/Languages
Summary:  Stackless Python interpreter built using PyPy
Requires: pypy-libs = %{version}-%{release}
%description stackless
Build of PyPy with support for micro-threads for massive concurrency
%endif


%prep
%setup -q -n pypy-%{version}-src
%patch0 -p1 -b .configure-fedora
%patch1 -p1 -b .suppress-mandelbrot-set-during-tty-build

pushd lib-python/%{pylibver}
%patch2 -p0
popd

# Look for the pypy libraries within LIBRARY_INSTALLATION_PATH first:
%patch3 -p1
# Fixup LIBRARY_INSTALLATION_PATH to be a string literal containing our value
# for "pypyprefix":
sed -i \
  -e 's|LIBRARY_INSTALLATION_PATH|"%{pypyprefix}"|' \
  pypy/translator/goal/app_main.py

%patch4 -p1 -b .more-readable-c-code


# Replace /usr/local/bin/python shebangs with /usr/bin/python:
find -name "*.py" -exec \
  sed \
    -i -e "s|/usr/local/bin/python|/usr/bin/python|" \
    "{}" \
    \;

find . -name '*.jar' -exec rm \{\} \;

# Remove stray ".svn" directories present within the 1.4.1 tarball
# (reported as https://codespeak.net/issue/pypy-dev/issue612 )
find . -path '*/.svn*' -delete

# Remove DOS batch files:
find -name "*.bat"|xargs rm -f

# The "demo" directory gets auto-installed by virture of being listed in %doc
# Remove shebang lines from demo .py files, and remove executability from them:
for f in demo/bpnn.py ; do
   # Detect shebang lines && remove them:
   sed -e '/^#!/Q 0' -e 'Q 1' $f \
      && sed -i '1d' $f
   chmod a-x $f
done

%build

BuildPyPy() {
  ExeName=$1
  Options=$2

  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"
  echo "STARTING BUILD OF: $ExeName"
  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"

  pushd %{goal_dir}

  # The build involves invoking a python script, passing in particular
  # arguments, environment variables, etc.
  # Some notes on those follow:

  # The generated binary embeds copies of the values of all environment
  # variables.  We need to unset "RPM_BUILD_ROOT" to avoid a fatal error from
  #  /usr/lib/rpm/check-buildroot
  # during the postprocessing of the rpmbuild, complaining about this
  # reference to the buildroot


  # By default, pypy's autogenerated C code is placed in
  #    /tmp/usession-N
  #  
  # and it appears that this stops rpm from extracting the source code to the
  # debuginfo package
  #
  # The logic in pypy-1.4/pypy/tool/udir.py indicates that it is generated in:
  #    $PYPY_USESSION_DIR/usession-$PYPY_USESSION_BASENAME-N    
  # and so we set PYPY_USESSION_DIR so that this tempdir is within the build
  # location, and set $PYPY_USESSION_BASENAME so that the tempdir is unique
  # for each invocation of BuildPyPy

  # Compilation flags for C code:
  #   pypy-1.4/pypy/translator/c/genc.py:gen_makefile
  # assembles a Makefile within
  #   THE_UDIR/testing_1/Makefile
  # calling out to platform.gen_makefile
  # For us, that's
  #   pypy-1.4/pypy/translator/platform/linux.py: class BaseLinux(BasePosix):
  # which by default has:
  #   CFLAGS = ['-O3', '-pthread', '-fomit-frame-pointer',
  #             '-Wall', '-Wno-unused']
  # plus all substrings from CFLAGS in the environment.
  # This is used to generate a value for CFLAGS that's written into the Makefile

  # https://bugzilla.redhat.com/show_bug.cgi?id=588941#c18
  # The generated Makefile compiles the .c files into assembler (.s), rather
  # than direct to .o  It then post-processes this assembler to locate
  # garbage-collection roots (building .lbl.s and .gcmap files, and a
  # "gcmaptable.s").  (The modified .lbl.s files have extra code injected
  # within them).
  # Unfortunately, the code to do this:
  #   pypy-1.4/pypy/translator/c/gcc/trackgcroot.py
  # doesn't interract well with the results of using our standard build flags.
  # For now, filter our CFLAGS of everything that could be conflicting with
  # pypy.  Need to check these and reenable ones that are okay later.
  # Filed as https://bugzilla.redhat.com/show_bug.cgi?id=666966
  export CFLAGS=$(echo "$RPM_OPT_FLAGS" | sed -e 's/-Wp,-D_FORTIFY_SOURCE=2//' -e 's/-fexceptions//' -e 's/-fstack-protector//' -e 's/--param=ssp-buffer-size=4//' -e 's/-O2//' -e 's/-fasynchronous-unwind-tables//' -e 's/-march=i686//' -e 's/-mtune=atom//')

  # If we're already built the JIT-enabled "pypy", then use it for subsequent
  # builds (of other configurations):
  if test -x './pypy' ; then
    INTERP='./pypy'
  else
    # First pypy build within this rpm build?
    # Fall back to using the bootstrap python interpreter, which might be a
    # system copy of pypy from an earlier rpm, or be cpython's /usr/bin/python:
    INTERP='%{bootstrap_python_interp}'
  fi

  # Here's where we actually invoke the build:
  time \
    RPM_BUILD_ROOT= \
    PYPY_USESSION_DIR=$(pwd) \
    PYPY_USESSION_BASENAME=$ExeName \
    $INTERP translate.py \
%if 0%{verbose_logs}
    --translation-verbose \
%endif
    --cflags="$CFLAGS" \
    --batch \
    --output=$ExeName \
    $Options

  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"
  echo "FINISHED BUILDING: $ExeName"
  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"
  echo "--------------------------------------------------------------"

  popd
}

BuildPyPy \
  pypy \
%if 0%{with_jit}
  "-Ojit" \
%else
  "-O2" \
%endif
  %{nil}

%if 0%{with_stackless}
BuildPyPy \
  pypy-stackless \
   "--stackless"
%endif

%install
rm -rf $RPM_BUILD_ROOT


# Install the various executables:

InstallPyPy() {
    ExeName=$1

    install -m 755 %{goal_dir}/$ExeName %{buildroot}/%{_bindir}

    # The generated machine code doesn't need an executable stack,  but
    # one of the assembler files (gcmaptable.s) doesn't have the necessary
    # metadata to inform gcc of that, and thus gcc pessimistically assumes
    # that the built binary does need an executable stack.
    #
    # Reported upstream as: https://codespeak.net/issue/pypy-dev/issue610
    #
    # I tried various approaches involving fixing the build, but the simplest
    # approach is to postprocess the ELF file:
    execstack --clear-execstack %{buildroot}/%{_bindir}/$ExeName
}

mkdir -p %{buildroot}/%{_bindir}

InstallPyPy pypy

%if 0%{with_stackless}
InstallPyPy pypy-stackless
%endif


# Install the various support libraries as described at:
#   http://codespeak.net/pypy/dist/pypy/doc/getting-started-python.html#installation
# which refers to a "PREFIX" found relative to the location of the binary.
# Given that the pypy binaries will be in /usr/bin, PREFIX can be
# "../share/pypy-1.2" relative to that directory, i.e. /usr/share/pypy-1.2
# 
# Running "strace" on a built binary indicates that it searches within
#   PREFIX/lib-python/modified-2.5.2
# not
#   PREFIX/lib-python/modified.2.5.2
# as given on the above page, i.e. it uses '-' not '.'

mkdir -p %{buildroot}/%{pypyprefix}
cp -a lib-python %{buildroot}/%{pypyprefix}

cp -a lib_pypy %{buildroot}/%{pypyprefix}

# Remove a text file that documents which selftests fail on Win32:
rm %{buildroot}/%{pypyprefix}/lib-python/win32-failures.txt

# Remove shebang lines from .py files that aren't executable, and
# remove executability from .py files that don't have a shebang line:
find \
  %{buildroot}                                                           \
  -name "*.py"                                                           \
    \(                                                                   \
       \( \! -perm /u+x,g+x,o+x -exec sed -e '/^#!/Q 0' -e 'Q 1' {} \;   \
             -print -exec sed -i '1d' {} \;                              \
          \)                                                             \
       -o                                                                \
       \(                                                                \
             -perm /u+x,g+x,o+x ! -exec grep -m 1 -q '^#!' {} \;         \
             -exec chmod a-x {} \;                                       \
        \)                                                               \
    \)

mkdir -p %{buildroot}/%{pypyprefix}/site-packages


# pypy uses .pyc files by default (--objspace-usepycfiles), but has a slightly
# different bytecode format to CPython.  It doesn't use .pyo files: the -O flag
# is treated as a "dummy optimization flag for compatibility with C Python"
#
# pypy-1.4/pypy/module/imp/importing.py has this comment:
    # XXX picking a magic number is a mess.  So far it works because we
    # have only two extra opcodes, which bump the magic number by +1 and
    # +2 respectively, and CPython leaves a gap of 10 when it increases
    # its own magic number.  To avoid assigning exactly the same numbers
    # as CPython we always add a +2.  We'll have to think again when we
    # get at the fourth new opcode :-(
    #
    #  * CALL_LIKELY_BUILTIN    +1
    #  * CALL_METHOD            +2
    #
    # In other words:
    #
    #     default_magic        -- used by CPython without the -U option
    #     default_magic + 1    -- used by CPython with the -U option
    #     default_magic + 2    -- used by PyPy without any extra opcode
    #     ...
    #     default_magic + 5    -- used by PyPy with both extra opcodes
#

# pypy-1.4/pypy/interpreter/pycode.py has:
#
#  default_magic = (62141+2) | 0x0a0d0000                  # this PyPy's magic
#                                                          # (62131=CPython 2.5.1)
# giving a value for "default_magic" for PyPy of 0xa0df2bf.
# Note that this corresponds to the "default_magic + 2" from the comment above

# In my builds:
#   $ ./pypy --info | grep objspace.opcodes
#                objspace.opcodes.CALL_LIKELY_BUILTIN: False
#                        objspace.opcodes.CALL_METHOD: True
# so I'd expect the magic number to be:
#    0x0a0df2bf + 2 (the flag for CALL_METHOD)
# giving
#    0x0a0df2c1
#
# I'm seeing
#   c1 f2 0d 0a
# as the first four bytes of the .pyc files, which is consistent with this.


# Bytecompile all of the .py files we ship, using our pypy binary, giving us
# .pyc files for pypy.  The script actually does the work twice (passing in -O
# the second time) but it's simplest to reuse that script.
#
# The script has special-casing for .py files below
#    /usr/lib{64}/python[0-9].[0-9]
# but given that we're installing into a different path, the supplied "default"
# implementation gets used instead.
#
# Note that some of the test files deliberately contain syntax errors, so
# we pass 0 for the second argument ("errors_terminate"):
/usr/lib/rpm/brp-python-bytecompile \
  %{buildroot}/%{_bindir}/pypy \
  0


# Header files for C extension modules.
# Upstream's packaging process (pypy/tool/release/package.py)
# creates an "include" subdir and copies all *.h/*.inl from "include" there
# (it also has an apparently out-of-date comment about copying them from
# pypy/_interfaces, but this directory doesn't seem to exist, and it doesn't
# seem to do this as of 2011-01-13)

# FIXME: arguably these should be instead put into a subdir below /usr/include,
# it's not yet clear to me how upstream plan to deal with the C extension
# interface going forward, so let's just mimic upstream for now.
%global pypy_include_dir  %{pypyprefix}/include
mkdir -p %{buildroot}/%{pypy_include_dir}
cp include/*.h %{buildroot}/%{pypy_include_dir}


# Capture the RPython source code files from the build within the debuginfo
# package (rhbz#666975)
%global pypy_debuginfo_dir /usr/src/debug/pypy-%{version}-src
mkdir -p %{buildroot}%{pypy_debuginfo_dir}

# copy over everything:
cp -a pypy %{buildroot}%{pypy_debuginfo_dir}

# ...then delete files that aren't .py files:
find \
  %{buildroot}%{pypy_debuginfo_dir} \
  \( -type f                        \
     -a                             \
     \! -name "*.py"                \
  \)                                \
  -delete

# We don't need bytecode for these files; they are being included for reference
# purposes.
# There are some rpmlint warnings from these files:
#   non-executable-script
#   wrong-script-interpreter
#   zero-length
#   script-without-shebang
#   dangling-symlink
# but given that the objective is to preserve a copy of the source code, those
# are acceptable.

%check
topdir=$(pwd)

SkipTest() {
    # Append the given test name to TESTS_TO_SKIP
    TEST_NAME=$1
    TESTS_TO_SKIP="$TESTS_TO_SKIP $TEST_NAME"
}

CheckPyPy() {
    # We'll be exercising one of the freshly-built binaries using the
    # test suite from the standard library (overridden in places by pypy's
    # modified version)
    ExeName=$1

    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
    echo "STARTING TEST OF: $ExeName"
    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"

    pushd %{goal_dir}

    # Gather a list of tests to skip, due to known failures
    # TODO: report these failures to pypy upstream
    # See also rhbz#666967 and rhbz#666969
    TESTS_TO_SKIP=""

    # Test failures relating to missing codecs
    # Hopefully when pypy merges to 2.7 support we'll gain these via a
    # refreshed stdlib:
      # test_codecencodings_cn:
      #   all tests fail, with one of
      #     unknown encoding: gb18030
      #     unknown encoding: gb2312
      #     unknown encoding: gbk
      SkipTest test_codecencodings_cn

      # test_codecencodings_hk:
      #   all tests fail, with:
      #     unknown encoding: big5hkscs
      SkipTest test_codecencodings_hk

      # test_codecencodings_jp:
      #   all tests fail, with one of:
      #     unknown encoding: cp932
      #     unknown encoding: euc_jisx0213
      #     unknown encoding: euc_jp
      #     unknown encoding: shift_jis
      #     unknown encoding: shift_jisx0213
      SkipTest test_codecencodings_jp

      # test_codecencodings_kr:
      #   all tests fail, with one of:
      #     unknown encoding: cp949
      #     unknown encoding: euc_kr
      #     unknown encoding: johab
      SkipTest test_codecencodings_kr

      # test_codecencodings_tw:
      #    all tests fail, with:
      #      unknown encoding: big5
      SkipTest test_codecencodings_tw

      # test_multibytecodec:
      #   14 failures out of 15, due to:
      #     unknown encoding: euc-kr
      #     unknown encoding: gb2312
      #     unknown encoding: jisx0213
      #     unknown encoding: cp949
      #     unknown encoding: iso2022-jp
      #     unknown encoding: gb18030
      SkipTest test_multibytecodec

    #
    # Other failures:
    #
      # test_asynchat:
      #   seems to hang on this test, within test_line_terminator
      SkipTest test_asynchat

      # test_audioop:
      #     test test_audioop crashed -- <type 'exceptions.ImportError'>: No module named audioop
      #     Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/regrtest.py", line 874, in runtest_inner
      #         the_package = __import__(abstest, globals(), locals(), [])
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_audioop.py", line 1, in <module>
      #         import audioop
      #     ImportError: No module named audioop
      SkipTest test_audioop

      # test_capi:
      #   RPython traceback:
      #     RPython traceback:
      #       File "implement.c", line 243013, in _PyObject_New
      #       File "implement_1.c", line 31707, in _PyObject_NewVar
      #       File "implement.c", line 217060, in from_ref
      #     Fatal RPython error: AssertionError
      SkipTest test_capi

      # test_compiler:
      #   4 errors out of 13:
      #     testSourceCodeEncodingsError
      #     testWith
      #     testWithAss
      #     testYieldExpr
      SkipTest test_compiler

      # test_ctypes:
      #   failures=17, errors=20, out of 132 tests
      SkipTest test_ctypes

      # test_distutils:
      #     Warning -- os.environ was modified by test_distutils
      #     test test_distutils failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_distutils

      # test_frozen:
      #   TestFailed: import __hello__ failed:No module named __hello__
      SkipTest test_frozen

      # test_gc:
      #     test test_gc crashed -- <type 'exceptions.AttributeError'>: 'module' object has no attribute 'get_debug'
      SkipTest test_gc

      # test_gdb:
      #     test test_gdb crashed -- <type 'exceptions.KeyError'>: 'PY_CFLAGS'
      SkipTest test_gdb

      # test_generators:
      #     **********************************************************************
      #     File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_generators.py", line ?, in test.test_generators.__test__.coroutine
      #     Failed example:
      #         del g; gc_collect()
      #     Expected:
      #         exiting
      #     Got nothing
      #     **********************************************************************
      #     File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_generators.py", line ?, in test.test_generators.__test__.coroutine
      #     Failed example:
      #         del g; gc_collect()
      #     Expected:
      #         exiting
      #     Got nothing
      #     **********************************************************************
      #     File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_generators.py", line ?, in test.test_generators.__test__.coroutine
      #     Failed example:
      #         del g; gc_collect()
      #     Expected:
      #         finally
      #     Got nothing
      #     **********************************************************************
      #     File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_generators.py", line ?, in test.test_generators.__test__.coroutine
      #     Failed example:
      #         sys.stderr.getvalue().startswith(
      #             "Exception RuntimeError: 'generator ignored GeneratorExit' in "
      #         )
      #     Expected:
      #         True
      #     Got:
      #         False
      #     **********************************************************************
      #     File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_generators.py", line ?, in test.test_generators.__test__.refleaks
      #     Failed example:
      #         try:
      #             sys.stderr = StringIO.StringIO()
      #             class Leaker:
      #                 def __del__(self):
      #                     raise RuntimeError
      #             l = Leaker()
      #             del l
      #             gc_collect()
      #             err = sys.stderr.getvalue().strip()
      #             err.startswith(
      #                 "Exception RuntimeError: RuntimeError() in "
      #             )
      #             err.endswith("> ignored")
      #             len(err.splitlines())
      #         finally:
      #             sys.stderr = old
      #     Expected:
      #         True
      #         True
      #         1
      #     Got:
      #         False
      #         False
      #         0
      #     **********************************************************************
      #     2 items had failures:
      #        4 of 107 in test.test_generators.__test__.coroutine
      #        1 of  11 in test.test_generators.__test__.refleaks
      #     ***Test Failed*** 5 failures.
      #     test test_generators failed -- 5 of 294 doctests failed
      SkipTest test_generators

      # test_getargs2:
      #     test test_getargs2 failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_getargs2

      # test_hotshot:
      #     test test_hotshot crashed -- <type 'exceptions.ImportError'>: No module named _hotshot
      SkipTest test_hotshot

      # test_io:
      #     test test_io failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_io

      # test_ioctl:
      #   Failing in Koji with dist-f15 with:
      #     ======================================================================
      #     FAIL: test_ioctl (test.test_ioctl.IoctlTests)
      #     ----------------------------------------------------------------------
      #     Traceback (most recent call last):
      #       File "/usr/lib/pypy-1.4.1/lib-python/2.5.2/test/test_ioctl.py", line 25, in test_ioctl
      #         self.assert_(rpgrp in ids, "%s not in %s" % (rpgrp, ids))
      #     AssertionError: 0 not in (8304, 17737)
      #     ======================================================================
      #     FAIL: test_ioctl_mutate (test.test_ioctl.IoctlTests)
      #     ----------------------------------------------------------------------
      #     Traceback (most recent call last):
      #       File "/usr/lib/pypy-1.4.1/lib-python/2.5.2/test/test_ioctl.py", line 35, in test_ioctl_mutate
      #         self.assert_(rpgrp in ids, "%s not in %s" % (rpgrp, ids))
      #     AssertionError: 0 not in (8304, 17737)
      #     ----------------------------------------------------------------------
      SkipTest test_ioctl

      # test_iterlen:
      #   24 failures out of 25, apparently all due to TypeError
      SkipTest test_iterlen

      # test_multiprocessing:
      #     test test_multiprocessing failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_multiprocessing

      # test_module:
      #     test test_module failed -- Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_module.py", line 81, in test_clear_dict_in_ref_cycle
      #         self.assertEqual(destroyed, [1])
      #     AssertionError: Lists differ: [] != [1]
      #     Second list contains 1 additional elements.
      #     First extra element 0:
      #     1
      #     - []
      #     + [1]
      #     ?  +
      SkipTest test_module

      # test_parser:
      #   12 failures out of 15
      SkipTest test_parser

      # test_platform:
      #   Koji builds show:
      #    test test_platform failed -- errors occurred in test.test_platform.PlatformTest
      SkipTest test_platform

      # test_posix:
      #     test test_posix failed -- Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_posix.py", line 361, in test_getcwd_long_pathnames
      #         _create_and_do_getcwd(dirname)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_posix.py", line 351, in _create_and_do_getcwd
      #         _create_and_do_getcwd(dirname, current_path_length + len(dirname) + 1)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_posix.py", line 351, in _create_and_do_getcwd
      #         _create_and_do_getcwd(dirname, current_path_length + len(dirname) + 1)
      #       [...repeats...]
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_posix.py", line 351, in _create_and_do_getcwd
      #         _create_and_do_getcwd(dirname, current_path_length + len(dirname) + 1)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_posix.py", line 356, in _create_and_do_getcwd
      #         self.assertEqual(e.errno, expected_errno)
      #     AssertionError: 36 != 34
      SkipTest test_posix

      # test_readline:
      #     test test_readline failed -- Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_readline.py", line 16, in testHistoryUpdates
      #         readline.clear_history()
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib_pypy/pyrepl/readline.py", line 277, in clear_history
      #         del self.get_reader().history[:]
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib_pypy/pyrepl/readline.py", line 186, in get_reader
      #         console = UnixConsole(self.f_in, self.f_out, encoding=ENCODING)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib_pypy/pyrepl/unix_console.py", line 103, in __init__
      #         self._clear = _my_getstr("clear")
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib_pypy/pyrepl/unix_console.py", line 45, in _my_getstr
      #         "terminal doesn't have the required '%s' capability"%cap
      #     InvalidTerminal: terminal doesn't have the required 'clear' capability
      SkipTest test_readline

      # test_scope:
      #     test test_scope failed -- Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_scope.py", line 437, in testLeaks
      #         self.assertEqual(Foo.count, 0)
      #     AssertionError: 100 != 0
      SkipTest test_scope

      # test_socket:
      #   testSockName can fail in Koji with:
      #       my_ip_addr = socket.gethostbyname(socket.gethostname())
      #     gaierror: (-3, 'Temporary failure in name resolution')
      SkipTest test_socket

      # test_sort:
      #   some failures
      SkipTest test_sort

      # test_sqlite:
      #   3 of the sqlite3.test.dbapi.ExtensionTests raise:
      #     ProgrammingError: Incomplete statement ''
      SkipTest test_sqlite

      # test_strop:
      #     test test_strop crashed -- <type 'exceptions.ImportError'>: No module named strop
      SkipTest test_strop

      # test_structmembers:
      #     test test_structmembers failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_structmembers

      # test_subprocess:
      #     debug: WARNING: library path not found, using compiled-in sys.path and sys.prefix will be unset
      #     'import site' failed
      #     .
      #         this bit of output is from a test of stdout in a different process ...
      #     /builddir/build/BUILD/pypy-1.5-src/lib_pypy/ctypes_support.py:26: RuntimeWarning: C function without declared arguments called
      #       return standard_c_lib.__errno_location()
      #     debug: WARNING: library path not found, using compiled-in sys.path and sys.prefix will be unset
      #     'import site' failed
      #     .
      #         this bit of output is from a test of stdout in a different process ...
      #     test test_subprocess failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_subprocess

      # test_symtable:
      #     test test_symtable crashed -- <type 'exceptions.ImportError'>: No module named _symtable
      SkipTest test_symtable

      # test_sys_settrace:
      #     test test_sys_settrace failed -- Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_sys_settrace.py", line 334, in test_13_genexp
      #         self.run_test(generator_example)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_sys_settrace.py", line 280, in run_test
      #         self.run_and_compare(func, func.events)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_sys_settrace.py", line 277, in run_and_compare
      #         tracer.events, events)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/test/test_sys_settrace.py", line 269, in compare_events
      #         [str(x) for x in events])))
      #     AssertionError: events did not match expectation:
      #       (0, 'call')
      #       (2, 'line')
      #       (-6, 'call')
      #       (-5, 'line')
      #       (-4, 'line')
      #       (-4, 'return')
      #     - (-4, 'call')
      #     - (-4, 'exception')
      #     - (-1, 'line')
      #     - (-1, 'return')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (6, 'line')
      #       (5, 'line')
      #       (5, 'return')
      SkipTest test_sys_settrace

      # test_tempfile:
      #     test test_tempfile failed -- multiple errors occurred; run in verbose mode for details
      SkipTest test_tempfile

      # test_thread
      #   Koji build appears to hang here
      SkipTest test_thread

      # test_traceback:
      #   works when run standalone; failures seen when run as part of a suite
      SkipTest test_traceback

      # test_uuid:
      #     ======================================================================
      #     ERROR: test_ifconfig_getnode (test.test_uuid.TestUUID)
      #     ----------------------------------------------------------------------
      #     Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_uuid.py", line 306, in test_ifconfig_getnode
      #         node = uuid._ifconfig_getnode()
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/uuid.py", line 326, in _ifconfig_getnode
      #         ip_addr = socket.gethostbyname(socket.gethostname())
      #     gaierror: [Errno -3] Temporary failure in name resolution
      #     ----------------------------------------------------------------------
      #     Ran 14 tests in 0.369s
      #     FAILED (errors=1)
      SkipTest test_uuid

      # test_zipimport_support:
      #     ======================================================================
      #     ERROR: test_doctest_main_issue4197 (test.test_zipimport_support.ZipSupportTests)
      #     ----------------------------------------------------------------------
      #     Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_zipimport_support.py", line 194, in test_doctest_main_issue4197
      #         exit_code, data = run_python(script_name)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/script_helper.py", line 80, in run_python
      #         p = spawn_python(*args, **kwargs)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/script_helper.py", line 66, in spawn_python
      #         **kwargs)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/subprocess.py", line 672, in __init__
      #         errread, errwrite)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/subprocess.py", line 1206, in _execute_child
      #         raise child_exception
      #     OSError: [Errno 13] Permission denied
      #     ======================================================================
      #     ERROR: test_pdb_issue4201 (test.test_zipimport_support.ZipSupportTests)
      #     ----------------------------------------------------------------------
      #     Traceback (most recent call last):
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/test_zipimport_support.py", line 221, in test_pdb_issue4201
      #         p = spawn_python(script_name)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/2.7/test/script_helper.py", line 66, in spawn_python
      #         **kwargs)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/subprocess.py", line 672, in __init__
      #         errread, errwrite)
      #       File "/builddir/build/BUILD/pypy-1.5-src/lib-python/modified-2.7/subprocess.py", line 1206, in _execute_child
      #         raise child_exception
      #     OSError: [Errno 13] Permission denied
      #     ----------------------------------------------------------------------
      #     Ran 4 tests in 0.726s
      #     FAILED (errors=2)
      SkipTest test_zipimport_support

      # test_zlib:
      #   failure seen in Koji, not sure of reason why:
      #     test test_zlib failed -- Traceback (most recent call last):
      #     File "/builddir/build/BUILD/pypy-1.4.1-src/lib-python/2.5.2/test/test_zlib.py", line 72, in test_baddecompressobj
      #       self.assertRaises(ValueError, zlib.decompressobj, 0)
      #     AssertionError: ValueError not raised
      SkipTest test_zlib

    %if 0%{use_self_when_building}
    # Patch 3 prioritizes the installed copy of pypy's libraries over the
    # build copy.
    # This leads to test failures of test_pep263 and test_tarfile
    # For now, suppress these when building using pypy itself:
    SkipTest test_pep263   # on-disk encoding issues
    SkipTest test_tarfile  # permissions issues
    %endif

    # Run the built binary through the selftests
    # "-w" : re-run failed tests in verbose mode
    time ./$ExeName -m test.regrtest -w -x $TESTS_TO_SKIP

    popd

    # Doublecheck pypy's own test suite, using the built pypy binary:

    # Disabled for now:
    #   x86_64 shows various failures inside:
    #     jit/backend/x86/test
    #   followed by a segfault inside
    #     jit/backend/x86/test/test_runner.py
    #
    #   i686 shows various failures inside:
    #     jit/backend/x86/test
    #   with the x86_64 failure leading to cancellation of the i686 build

    # Here's the disabled code:
    #    pushd pypy
    #    time translator/goal/$ExeName test_all.py
    #    popd

    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
    echo "FINISHED TESTING: $ExeName"
    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
    echo "--------------------------------------------------------------"
}

CheckPyPy pypy

%if 0%{with_stackless}
CheckPyPy pypy-stackless
%endif



%clean
rm -rf $RPM_BUILD_ROOT


%files libs
%defattr(-,root,root,-)
%doc LICENSE README demo

%dir %{pypyprefix}
%dir %{pypyprefix}/lib-python
%{pypyprefix}/lib-python/TODO
%{pypyprefix}/lib-python/stdlib-version.txt
%{pypyprefix}/lib-python/%{pylibver}/
%{pypyprefix}/lib-python/modified-%{pylibver}/
%{pypyprefix}/lib-python/conftest.py*
%{pypyprefix}/lib_pypy/
%{pypyprefix}/site-packages/

%files
%defattr(-,root,root,-)
%doc LICENSE README
%{_bindir}/pypy

%files devel
%defattr(-,root,root,-)
%dir %{pypy_include_dir}
%{pypy_include_dir}/*.h

%if 0%{with_stackless}
%files stackless
%defattr(-,root,root,-)
%doc LICENSE README
%{_bindir}/pypy-stackless
%endif


%changelog
* Mon May  2 2011 David Malcolm <dmalcolm@redhat.com> - 1.5-1
- 1.5

* Wed Apr 20 2011 David Malcolm <dmalcolm@redhat.com> - 1.4.1-10
- build a /usr/bin/pypy (but without the JIT compiler) on architectures that
don't support the JIT, so that they do at least have something that runs

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.1-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Fri Jan 14 2011 David Malcolm <dmalcolm@redhat.com> - 1.4.1-8
- disable self-hosting for now, due to fatal error seen JIT-compiling the
translator

* Fri Jan 14 2011 David Malcolm <dmalcolm@redhat.com> - 1.4.1-7
- skip test_ioctl for now

* Thu Jan 13 2011 David Malcolm <dmalcolm@redhat.com> - 1.4.1-6
- add a "pypy-devel" subpackage, and install the header files there
- in %%check, re-run failed tests in verbose mode

* Fri Jan  7 2011 Dan Horák <dan[at]danny.cz> - 1.4.1-5
- valgrind available only on selected architectures

* Wed Jan  5 2011 David Malcolm <dmalcolm@redhat.com> - 1.4.1-4
- rebuild pypy using itself, for speed, with a boolean to break this cycle in
the build-requirement graph (falling back to using "python-devel" aka CPython)
- add work-in-progress patch to try to make generated c more readable
(rhbz#666963)
- capture the RPython source code files from the build within the debuginfo
package (rhbz#666975)

* Wed Dec 22 2010 David Malcolm <dmalcolm@redhat.com> - 1.4.1-3
- try to respect the FHS by installing libraries below libdir, rather than
datadir; patch app_main.py to look in this installation location first when
scanning for the pypy library directories.
- clarifications and corrections to the comments in the specfile

* Wed Dec 22 2010 David Malcolm <dmalcolm@redhat.com> - 1.4.1-2
- remove .svn directories
- disable verbose logging
- add a %%check section
- introduce %%goal_dir variable, to avoid repetition
- remove shebang line from demo/bpnn.py, as we're treating this as a
documentation file
- regenerate patch 2 to apply without generating a .orig file

* Tue Dec 21 2010 David Malcolm <dmalcolm@redhat.com> - 1.4.1-1
- 1.4.1; fixup %%setup to reflect change in toplevel directory in upstream
source tarball
- apply SELinux fix to the bundled test_commands.py (patch 2)

* Wed Dec 15 2010 David Malcolm <dmalcolm@redhat.com> - 1.4-4
- rename the jit build and subpackge to just "pypy", and remove the nojit and
sandbox builds, as upstream now seems to be focussing on the JIT build (with
only stackless called out in the getting-started-python docs); disable
stackless for now
- add a verbose_logs specfile boolean; leave it enabled for now (whilst fixing
build issues)
- add more comments, and update others to reflect 1.2 -> 1.4 changes
- re-enable debuginfo within CFLAGS ("-g")
- add the LICENSE and README to all subpackages
- ensure the built binaries don't have the "I need an executable stack" flag
- remove DOS batch files during %%prep (idlelib.bat)
- remove shebang lines from .py files that aren't executable, and remove
executability from .py files that don't have a shebang line (taken from
our python3.spec)
- bytecompile the .py files into .pyc files in pypy's bytecode format

* Sun Nov 28 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 1.4-3
- BuildRequire valgrind-devel
- Install pypy library from the new directory
- Disable building with our CFLAGS for now because they are causing a build failure.
- Include site-packages directory

* Sat Nov 27 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 1.4-2
- Add patch to configure the build to use our CFLAGS and link libffi
  dynamically

* Sat Nov 27 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 1.4-1
- Update to 1.4
- Drop patch for py2.6 that's in this build
- Switch to building pypy with itself once pypy is built once as recommended by
  upstream
- Remove bundled, prebuilt java libraries
- Fix license tag
- Fix source url
- Version pypy-libs Req

* Tue May  4 2010 David Malcolm <dmalcolm@redhat.com> - 1.2-2
- cherrypick r72073 from upstream SVN in order to fix the build against
python 2.6.5 (patch 2)

* Wed Apr 28 2010 David Malcolm <dmalcolm@redhat.com> - 1.2-1
- initial packaging

