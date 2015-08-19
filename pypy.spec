Name:           pypy
Version:        2.6.0
Release:        3%{?dist}
Summary:        Python implementation with a Just-In-Time compiler

Group:          Development/Languages
# LGPL and another free license we'd need to ask spot about are present in some
# java jars that we're not building with atm (in fact, we're deleting them
# before building).  If we restore those we'll have to work out the new
# licensing terms
License:        MIT and Python and UCD
URL:            http://pypy.org/

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
# rpython/jit/backend/detect_cpu.py:getcpuclassname currently supports the
# following options:
#  'i386', 'x86'
#  'x86-without-sse2':
#  'x86_64'
#  'armv6', 'armv7' (versions 6 and 7, hard- and soft-float ABI)
#  'cli'
#  'llvm'
#
# We will only build with JIT support on those architectures, and build without
# it on the other archs.  The resulting binary will typically be slower than
# CPython for the latter case.

%ifarch %{ix86} x86_64 %{arm}
%global with_jit 1
%else
%global with_jit 0
%endif

# Should we build a "pypy-stackless" binary?
%global with_stackless 0

# Should we build the emacs JIT-viewing mode?
%if 0%{?rhel} == 5 || 0%{?rhel} == 6
%global with_emacs 0
%else
%global with_emacs 1
%endif

# Easy way to enable/disable verbose logging:
%global verbose_logs 0

# Forcibly use the shadow-stack option for detecting GC roots, rather than
# relying on hacking up generated assembler with regexps:
%global shadow_stack 1

# Easy way to turn off the selftests:
%global run_selftests 1

%global pypy_include_dir  %{pypyprefix}/include
%global pypyprefix %{_libdir}/%{name}-%{version}
%global pylibver 2.7

# We refer to this subdir of the source tree in a few places during the build:
%global goal_dir pypy/goal


# Turn off the brp-python-bytecompile postprocessing script
# We manually invoke it later on, using the freshly built pypy binary
%global __os_install_post \
  %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

# Source and patches:
Source0: https://bitbucket.org/pypy/pypy/downloads/%{name}-%{version}-src.tar.bz2

# Supply various useful RPM macros for building python modules against pypy:
#  __pypy, pypy_sitelib, pypy_sitearch
Source2: macros.%{name}

# By default, if built at a tty, the translation process renders a Mandelbrot
# set to indicate progress.
# This obscures useful messages, and may waste CPU cycles, so suppress it, and
# merely render dots:
Patch0: pypy-1.2-suppress-mandelbrot-set-during-tty-build.patch

# Patch pypy.translator.platform so that stdout from "make" etc gets logged,
# rather than just stderr, so that the command-line invocations of the compiler
# and linker are captured:
Patch1: 006-always-log-stdout.patch

# Disable the printing of a quote from IRC on startup (these are stored in
# ROT13 form in lib_pypy/_pypy_irc_topic.py).  Some are cute, but some could
# cause confusion for end-users (and many are in-jokes within the PyPy
# community that won't make sense outside of it).  [Sorry to be a killjoy]
Patch2: 007-remove-startup-message.patch

# Fix bug in pypy installing script package.py
Patch3: pypy_tool_release_package.patch

# Build-time requirements:

# pypy's can be rebuilt using itself, rather than with CPython; doing so
# halves the build time.
#
# Turn it off with this boolean, to revert back to rebuilding using CPython
# and avoid a cycle in the build-time dependency graph:

%global use_self_when_building 1
%if 0%{use_self_when_building}
BuildRequires: pypy
%global bootstrap_python_interp pypy
%else

# Python 2.6 or later is needed, so on RHEL5 (2.4) we need to use the alternate
# python26 rpm:
%if 0%{?rhel} == 5
BuildRequires: python26-devel
%global bootstrap_python_interp python26
%else
BuildRequires: python-devel
%global bootstrap_python_interp python
%endif

%endif

BuildRequires:  libffi-devel
BuildRequires:  tcl-devel
BuildRequires:  tk-devel

BuildRequires:  sqlite-devel

BuildRequires:  zlib-devel
BuildRequires:  bzip2-devel
BuildRequires:  ncurses-devel
BuildRequires:  expat-devel
BuildRequires:  openssl-devel
BuildRequires:  chrpath
%ifnarch s390
BuildRequires:  valgrind-devel
%endif

%if %{run_selftests}
# Used by the selftests, though not by the build:
BuildRequires:  gc-devel

# For use in the selftests, for recording stats:
BuildRequires:  time

# For use in the selftests, for imposing a per-test timeout:
BuildRequires:  perl
%endif


# No prelink on these arches
%ifnarch aarch64 ppc64le
BuildRequires:  /usr/bin/execstack
%endif

# For byte-compiling the JIT-viewing mode:
%if %{with_emacs}
BuildRequires:  emacs
%endif

# Metadata for the core package (the JIT build):
Requires: %{name}-libs%{?_isa} = %{version}-%{release}

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

# We supply an emacs mode for the JIT viewer.
# (This doesn't bring in all of emacs, just the directory structure)
%if %{with_emacs}
Requires: emacs-filesystem >= %{_emacs_version}
%endif

%description libs
Libraries required by the various PyPy implementations of Python.


%package devel
Group:    Development/Languages
Summary:  Development tools for working with PyPy
Requires: %{name}%{?_isa} = %{version}-%{release}

%description devel
Header files for building C extension modules against PyPy


%if 0%{with_stackless}
%package stackless
Group:    Development/Languages
Summary:  Stackless Python interpreter built using PyPy
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
%description stackless
Build of PyPy with support for micro-threads for massive concurrency
%endif


%prep
%setup -n %{name}-%{version}-src
%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
# Replace /usr/local/bin/python shebangs with /usr/bin/python:
find -name "*.py" -exec \
  sed \
    -i -e "s|/usr/local/bin/python|/usr/bin/python|" \
    "{}" \
    \;

for f in rpython/translator/goal/bpnn.py ; do
   # Detect shebang lines && remove them:
   sed -e '/^#!/Q 0' -e 'Q 1' $f \
      && sed -i '1d' $f
   chmod a-x $f
done

rm -rf lib-python/3

# Replace all lib-python python shebangs with pypy
find lib-python/%{pylibver} -name "*.py" -exec \
  sed -r -i '1s|^#!\s*/usr/bin.*python.*|#!/usr/bin/%{name}|' \
    "{}" \
    \;

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

  # How will we track garbage-collection roots in the generated code?
  #   http://pypy.readthedocs.org/en/latest/config/translation.gcrootfinder.html

%if 0%{shadow_stack}
  # This is the most portable option, and avoids a reliance on non-guaranteed
  # behaviors within GCC's code generator: use an explicitly-maintained stack
  # of root pointers:
  %global gcrootfinder_options --gcrootfinder=shadowstack

  export CFLAGS=$(echo "$RPM_OPT_FLAGS")

%else
  # Go with the default, which is "asmgcc"

  %global gcrootfinder_options %{nil}

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

%endif

  # The generated C code leads to many thousands of warnings of the form:
  #   warning: variable 'l_v26003' set but not used [-Wunused-but-set-variable]
  # Suppress them:
  export CFLAGS=$(echo "$CFLAGS" -Wno-unused -fPIC)

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
  RPM_BUILD_ROOT= \
  PYPY_USESSION_DIR=$(pwd) \
  PYPY_USESSION_BASENAME=$ExeName \
  $INTERP ../../rpython/bin/rpython  \
  %{gcrootfinder_options} \
  $Options \
  targetpypystandalone

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
  %{name} \
%if 0%{with_jit}
  "-Ojit" \
%else
  "-O2" \
%endif
  %{nil}

%if 0%{with_stackless}
BuildPyPy \
  %{name}-stackless \
   "--stackless"
%endif

%if %{with_emacs}
%{_emacs_bytecompile} rpython/jit/tool/pypytrace-mode.el
%endif


%install

mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{pypyprefix}

#%if 0%{with_stackless}
#InstallPyPy %{name}-stackless
#%endif


# Run installing script,  archive-name  %{name}-%{version} in %{buildroot}/%{_libdir} == %{pypyprefix} 
%{__python} pypy/tool/release/package.py --without-gdbm --archive-name %{name}-%{version} --builddir %{buildroot}/%{_libdir}

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


%ifnarch aarch64 ppc64le
    execstack --clear-execstack %{buildroot}/%{pypyprefix}/bin/pypy
%endif

# Header files for C extension modules.
# Upstream's packaging process (pypy/tool/release/package.py)
# creates an "include" subdir and copies all *.h/*.inl from "include" there
# (it also has an apparently out-of-date comment about copying them from
# pypy/_interfaces, but this directory doesn't seem to exist, and it doesn't
# seem to do this as of 2011-01-13)

# Capture the RPython source code files from the build within the debuginfo
# package (rhbz#666975)
#%global pypy_debuginfo_dir /usr/src/debug/pypy-%{version}-src
#mkdir -p %{buildroot}%{pypy_debuginfo_dir}

# copy over everything:
#cp -a pypy %{buildroot}%{pypy_debuginfo_dir}

# ...then delete files that aren't:
#   - *.py files
#   - the Makefile
#   - typeids.txt
#   - dynamic-symbols-*
#find \
#  %{buildroot}%{pypy_debuginfo_dir}  \
#  \( -type f                         \
#     -a                              \
#     \! \( -name "*.py"              \
#           -o                        \
#           -name "Makefile"          \
#           -o                        \
#           -name "typeids.txt"       \
#           -o                        \
#           -name "dynamic-symbols-*" \
#        \)                           \
#  \)                                 \
#  -delete

# Alternatively, we could simply keep everything.  This leads to a ~350MB
# debuginfo package, but it makes it easy to hack on the Makefile and C build
# flags by rebuilding/linking the sources.
# To do so, remove the above "find" command.

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

# Install the JIT trace mode for Emacs:
%if %{with_emacs}
mkdir -p %{buildroot}/%{_emacs_sitelispdir}
cp -a rpython/jit/tool/pypytrace-mode.el %{buildroot}/%{_emacs_sitelispdir}/%{name}trace-mode.el
cp -a rpython/jit/tool/pypytrace-mode.elc %{buildroot}/%{_emacs_sitelispdir}/%{name}trace-mode.elc
%endif

# Move files to the right places and remove unnecessary files
mkdir %{buildroot}/%{_includedir}
mv %{buildroot}/%{pypy_include_dir}/*.h %{buildroot}/%{_includedir}
mv %{buildroot}/%{pypy_include_dir}/numpy/ %{buildroot}/%{_includedir}
ln -sf %{pypyprefix}/bin/%{name} %{buildroot}/%{_bindir}/%{name}
mv %{buildroot}/%{pypyprefix}/bin/libpypy-c.so %{buildroot}/%{_libdir}
rm -rf %{buildroot}/%{_libdir}/%{name}-%{version}.tar.bz2
rm -rf %{buildroot}/%{pypyprefix}/LICENSE
rm -rf %{buildroot}/%{pypyprefix}/README.rst
rm -rf %{buildroot}/%{pypyprefix}/README.rst
rm -rf %{buildroot}/%{pypy_include_dir}
chrpath --delete %{buildroot}/%{pypyprefix}/bin/%{name}

# Install macros for rpm:
mkdir -p %{buildroot}/%{_rpmconfigdir}/macros.d
install -m 644 %{SOURCE2} %{buildroot}/%{_rpmconfigdir}/macros.d

# Remove build script from the package
#rm %{buildroot}/%{pypyprefix}/lib_pypy/ctypes_config_cache/rebuild.py

%check
topdir=$(pwd)

SkipTest() {
    TEST_NAME=$1
    sed -i -e"s|^$TEST_NAME$||g" testnames.txt
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

    # I'm seeing numerous cases where tests seem to hang, or fail unpredictably
    # So we'll run each test in its own process, with a timeout

    # Use regrtest to explicitly list all tests:
    ( ./$ExeName -c \
         "from test.regrtest import findtests; print('\n'.join(findtests()))"
    ) > testnames.txt

    # Skip some tests:
      # "audioop" doesn't exist for pypy yet:
      SkipTest test_audioop

      # The gdb CPython hooks haven't been ported to cpyext:
      SkipTest test_gdb

      # hotshot relies heavily on _hotshot, which doesn't exist:
      SkipTest test_hotshot

      # "strop" module doesn't exist for pypy yet:
      SkipTest test_strop

      # I'm seeing Koji builds hanging e.g.:
      #   http://koji.fedoraproject.org/koji/getfile?taskID=3386821&name=build.log
      # The only test that seems to have timed out in that log is
      # test_multiprocessing, so skip it for now:
      SkipTest test_multiprocessing

    echo "== Test names =="
    cat testnames.txt
    echo "================="

    echo "" > failed-tests.txt

    for TestName in $(cat testnames.txt) ; do

        echo "===================" $TestName "===================="

        # Use /usr/bin/time (rather than the shell "time" builtin) to gather
        # info on the process (time/CPU/memory).  This passes on the exit
        # status of the underlying command
        #
        # Use perl's alarm command to impose a timeout
        #   900 seconds is 15 minutes per test.
        # If a test hangs, that test should get terminated, allowing the build
        # to continue.
        #
        # Invoke pypy on test.regrtest to run the specific test suite
        # verbosely
        #
        # For now, || true, so that any failures don't halt the build:
        ( /usr/bin/time \
           perl -e 'alarm shift @ARGV; exec @ARGV' 900 \
             ./$ExeName -m test.regrtest -v $TestName ) \
        || (echo $TestName >> failed-tests.txt) \
        || true
    done

    echo "== Failed tests =="
    cat failed-tests.txt
    echo "================="

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

#python testrunner/runner.py --logfile=pytest-A.log --config=pypy/pytest-A.cfg --config=pypy/pytest-A.py --root=pypy --timeout=3600
#python pypy/test_all.py --pypy=pypy/goal/pypy --timeout=3600 --resultlog=cpython.log lib-python
#python pypy/test_all.py --pypy=pypy/goal/pypy --resultlog=pypyjit.log pypy/module/pypyjit/test
#pypy/goal/pypy pypy/test_all.py --resultlog=pypyjit_new.log

%if %{run_selftests}
CheckPyPy %{name}-c

%if 0%{with_stackless}
CheckPyPy %{name}-c-stackless
%endif

%endif # run_selftests

# Because there's a bunch of binary subpackages and creating
# /usr/share/licenses/pypy3-this and /usr/share/licenses/pypy3-that
# is just confusing for the user.
%global _docdir_fmt %{name}

%files libs
%license LICENSE
%doc README.rst

%dir %{pypyprefix}
%dir %{pypyprefix}/lib-python
%{_libdir}/libpypy-c.so
%{pypyprefix}/lib-python/%{pylibver}/
%{pypyprefix}/lib_pypy/
%{pypyprefix}/site-packages/
%if %{with_emacs}
%{_emacs_sitelispdir}/%{name}trace-mode.el
%{_emacs_sitelispdir}/%{name}trace-mode.elc
%endif

%files
%license LICENSE
%doc README.rst
%{_bindir}/%{name}
%{pypyprefix}/bin/%{name}

%files devel
%dir %{_includedir}
%{_includedir}/*.h
%{_includedir}/numpy/*.h
%{_rpmconfigdir}/macros.d/macros.%{name}

%if 0%{with_stackless}
%files stackless
%license LICENSE
%doc README.rst
%{_bindir}/%{name}-stackless
%endif


%changelog
* Tue Aug 18 2015 Michal Cyprian <mcyprian@redhat.com> - 2.6.0-3
- Use script package.py in install section 

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed May 27 2015 Matej Stuchlik <mstuchli@redhat.com> - 2.6.0-1
- Update to 2.6.0

* Wed Mar  4 2015 Ville Skyttä <ville.skytta@iki.fi> - 2.5.0-2
- Do not mark macros file as %%config (#1074266)

* Tue Feb 17 2015 Matej Stuchlik <mstuchli@redhat.com> - 2.5.0-1
- Update to 2.5.0

* Wed Sep 10 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.4.0-1
- Update to 2.4.0

* Tue Sep 02 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.3.1-4
- Move devel subpackage requires so that it gets picked up by rpm

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Mon Jul  7 2014 Peter Robinson <pbrobinson@fedoraproject.org> 2.3.1-2
- ARMv7 is supported for JIT
- no prelink on aarch64/ppc64le

* Sun Jun 08 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.3.1-1
- Update to 2.3.1

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Tue May 27 2014 Dennis Gilmore <dennis@ausil.us> - 2.3-4
- valgrind is available everywhere except 31 bit s390

* Wed May 21 2014 Jaroslav Škarvada <jskarvad@redhat.com> - 2.3-3
- Rebuilt for https://fedoraproject.org/wiki/Changes/f21tcl86

* Thu May 15 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.3-2
- Rebuilt (f21-python)

* Tue May 13 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.3-1
- Updated to 2.3

* Mon Mar 10 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.2.1-3
- Put RPM macros in proper location

* Thu Jan 16 2014 Matej Stuchlik <mstuchli@redhat.com> - 2.2.1-2
- Fixed errors due to missing __pycache__

* Thu Dec 05 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.2.1-1
- Updated to 2.2.1
- Several bundled modules (tkinter, sqlite3, curses, syslog) were
  not bytecompiled properly during build, that is now fixed
- prepared new tests, not enabled yet

* Thu Nov 14 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.2.0-1
- Updated to 2.2.0

* Thu Aug 15 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.1-1
- Updated to 2.1.0

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Mon Jun 24 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.0.2-4
- Patch1 fix

* Mon Jun 24 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.0.2-3
- Yet another Sources fix

* Mon Jun 24 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.0.2-2
- Fixed Source URL

* Mon Jun 24 2013 Matej Stuchlik <mstuchli@redhat.com> - 2.0.2-1
- 2.0.2, patch 8 does not seem necessary anymore

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0-0.2.b1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Tue Dec 11 2012 David Malcolm <dmalcolm@redhat.com> - 2.0-0.1.b1
- 2.0b1 (drop upstreamed patch 9)

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.9-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jul 10 2012 David Malcolm <dmalcolm@redhat.com> - 1.9-3
- log all output from "make" (patch 6)
- disable the MOTD at startup (patch 7)
- hide symbols from the dynamic linker (patch 8)
- add PyInt_AsUnsignedLongLongMask (patch 9)
- capture the Makefile, the typeids.txt, and the dynamic-symbols file within
the debuginfo package

* Mon Jun 18 2012 Peter Robinson <pbrobinson@fedoraproject.org> - 1.9-2
- Compile with PIC, fixes FTBFS on ARM

* Fri Jun  8 2012 David Malcolm <dmalcolm@redhat.com> - 1.9-1
- 1.9

* Fri Feb 10 2012 David Malcolm <dmalcolm@redhat.com> - 1.8-2
- disable C readability patch for now (patch 4)

* Thu Feb  9 2012 David Malcolm <dmalcolm@redhat.com> - 1.8-1
- 1.8; regenerate config patch (patch 0); drop selinux patch (patch 2);
regenerate patch 5

* Tue Jan 31 2012 David Malcolm <dmalcolm@redhat.com> - 1.7-4
- fix an incompatibility with virtualenv (rhbz#742641)

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.7-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Dec 16 2011 David Malcolm <dmalcolm@redhat.com> - 1.7-2
- use --gcrootfinder=shadowstack, and use standard Fedora compilation flags,
with -Wno-unused (rhbz#666966 and rhbz#707707)

* Mon Nov 21 2011 David Malcolm <dmalcolm@redhat.com> - 1.7-1
- 1.7: refresh patch 0 (configuration) and patch 4 (readability of generated
code)

* Tue Oct  4 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-7
- skip test_multiprocessing

* Tue Sep 13 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-6
- don't ship the emacs JIT-viewer on el5 and el6 (missing emacs-filesystem;
missing _emacs_bytecompile macro on el5)

* Mon Sep 12 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-5
- build using python26 on el5 (2.4 is too early)
* Thu Aug 25 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-4
- fix SkipTest function to avoid corrupting the name of "test_gdbm"

* Thu Aug 25 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-3
- add rpm macros file to the devel subpackage (source 2)
- skip some tests that can't pass yet

* Sat Aug 20 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-2
- work around test_subprocess failure seen in koji (patch 5)

* Thu Aug 18 2011 David Malcolm <dmalcolm@redhat.com> - 1.6-1
- 1.6
- rewrite the %%check section, introducing per-test timeouts

* Tue Aug  2 2011 David Malcolm <dmalcolm@redhat.com> - 1.5-2
- add pypytrace-mode.el to the pypy-libs subpackage, for viewing JIT trace
logs in emacs

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

