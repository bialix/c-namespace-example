# (c) Alexander Belchenko, 2006

"""Keil tools wrapper.
Launch keil's tool and reformat their output to std way.
Also could suppress return code == 1 when warnings occurs
and returns 0 instead.

Usage:
    [python] keilwrap.py [-w] keil-tool-command-line

Where:
    -w      - suppress return code 1 when warnings occurs and returns 0

    keil-tool-command-line  - original command line for invoking keil's
                              tool (compiler or linker)
"""


import re
import os
from subprocess import Popen, PIPE
import sys


__version__ = "1.4"
__docformat__ = "restructuredtext"


re_err_c51 = re.compile(r'^\*\*\* ([A-Za-z]+) (\w+) IN LINE (\d+) OF ([^:]+): (.*)$')
re_err_a51 = re.compile(r'^\*\*\* ([A-Za-z]+) \#(\w+) IN (\d+) \(([^,]+),[^:]+: (.*)$')


def wrapper(cmd_line, env_vars=None, suppress_warnings=False):
    """wrapper for launching keil's tools

    :param  cmd_line:   command line string to launch keil's tool
    :param  env_vars:   environment variables (dict) for process
    :param  suppress_warnings:  if True suppress return code == 1
                                and return 0 instead
    """
    q = Popen(cmd_line, stdin=PIPE, stdout=PIPE, stderr=PIPE,
              universal_newlines=True, shell=True, env=env_vars)
    output = q.stdout.read()
    error = q.stderr.read()
    status = q.wait()
    if status >= 0:
        # reformat output
        if type(cmd_line) == type(''):
            cmd_line = cmd_line.split()
        pname = os.path.splitext(os.path.basename(cmd_line[0]))[0].lower()
        if pname in ('c51', 'cx51'):
            for s in output.splitlines():
                if s[:3] == '***':
                    mo = re_err_c51.match(s)
                    if mo:
                        print '%s(%s): %s %s: %s' % (_real_filename(mo.group(4)),
                                                     mo.group(3),
                                                     mo.group(1).title(),
                                                     mo.group(2), mo.group(5))
                    else:
                        print s
        elif pname in ('a51', 'ax51'):
            for s in output.splitlines():
                if s[:3] == '***':
                    mo = re_err_a51.match(s)
                    if mo:
                        print '%s(%s): %s %s: %s' % (_real_filename(mo.group(4)),
                                                     mo.group(3),
                                                     mo.group(1).title(),
                                                     mo.group(2), mo.group(5))
                    else:
                        if not s[:5] in ('*** _', '*** ^'):
                            print s
        else:
            for s in output.splitlines():
                if s[:3] in ('***', ' '*3, 'Pro'):
                    print s

        if error:
            print error

        if suppress_warnings:
            if status == 1:
                status = 0

        return status
    else:
        print "Command failed: %s" % error
        return status


_FILENAMES_CACHE = {}

def _real_filename(filename):
    """Returns "real" internal OS filename
    by searching in os.listdir()
    """
    fname = filename.lower()
    if fname in _FILENAMES_CACHE:
        return _FILENAMES_CACHE[fname]

    def lookup_in_dir(d, name):
        for f in os.listdir(d):
            if f.lower() == name:
                return f
        return name

    src_parts = re.split(r'/\\', fname)
    dst_parts = []
    dir_ = ''

    for s in src_parts:
        dst_parts.append(lookup_in_dir(dir_, s))
        if dir_ == '':
            dir_ = s
        else:
            dir_ = os.path.join(dir_, s)

    if len(dst_parts) == 1:
        real = dst_parts[0]
    else:
        real = '\\'.join(dst_parts)

    _FILENAMES_CACHE[fname] = real
    return real


##
# For SCons
def get_keil_root():
    """Obtains Keil's root directory from Windows registry"""
    import _winreg
    try:
        k = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,
                            u'Software\\Keil\\\u00B5Vision2'.encode('latin-1'))
        return _winreg.QueryValueEx(k, 'Path')[0].encode('latin-1')
    except EnvironmentError, WindowsError:
        #raise "Unable to auto-detect location of Keil's tools"
        return None

def c51(target, source, env):
    targets = 'OBJECT(%s)' % target[0]
    if len(target) == 2:    # listing file
        targets += ' PRINT(%s)' % target[1]
    cmd_line = 'c51 %s %s %s' % (source[0], targets, env['C51FLAGS'])
    #print cmd_line
    print 'Compiling', source[0], '...'
    return wrapper(cmd_line, env['ENV'], False)

def c51_asm(target, source, env):
    targets = 'SRC(%s)' % target[0]
    if len(target) == 2:    # listing file
        targets += ' PRINT(%s)' % target[1]
    cmd_line = 'c51 %s %s %s' % (source[0], targets, env['C51FLAGS'])
    #print cmd_line
    print 'Translating', source[0], '...'
    return wrapper(cmd_line, env['ENV'], False)

def a51(target, source, env):
    targets = 'OBJECT(%s)' % target[0]
    if len(target) == 2:    # listing file
        targets += ' PRINT(%s)' % target[1]
    cmd_line = 'a51 %s %s %s' % (source[0], targets, env['A51FLAGS'])
    #print cmd_line
    print 'Assembling', source[0], '...'
    return wrapper(cmd_line, env['ENV'], False)

def bl51(target, source, env):
    targets = 'TO %s' % target[0]
    if len(target) == 2:    # listing file
        targets += ' PRINT(%s)' % target[1]

    cmd_line = 'bl51 %s %s %s' % \
               (', '.join(str(i) for i in source),
                targets,
                env['BL51FLAGS'])
    #print cmd_line
    print 'Linking ...'
    return wrapper(cmd_line, env['ENV'], True)

def oh51(target, source, env):
    cmd_line = 'oh51 %s HEXFILE(%s)' % (source[0], target[0])
    #print cmd_line
    print 'Converting to hex', source[0], '...'
    return wrapper(cmd_line, env['ENV'])

def lib51(target, source, env):
    targets = 'TO %s' % target[0]
    cmd_line = 'lib51  %s %s' % \
               ('TRANSFER ' + ', '.join(str(i) for i in source),
                targets)
    #print cmd_line
    print 'Creating library ...'
    return wrapper(cmd_line, env['ENV'], True)

#/For SCons
##

##
# MAIN point of script
if __name__ == "__main__":
    if sys.argv[1] == '-w':
        suppress_warnings = True
        del sys.argv[1]
    else:
        suppress_warnings = False

    sys.exit(wrapper(sys.argv[1:], suppress_warnings=suppress_warnings))
