#!/usr/bin/env python3

# Naming convention:
#   UPPER_CASE - constants
#   lower_case - variables
#   *_file - file name
#   *_path - relative path to file or folder
#   *_root - absolute path to file or folder
#   *_nls - no leading slash

import os
import re
import sys
import configparser
import unicodedata
from datetime import datetime, timezone
from fnmatch import fnmatch
from pprint import pprint

#
# GLOBALS
#

OS_SEP = os.sep
DEF_GROUP_PATH = OS_SEP
DEF_GROUP_NAME = 'context'

#
# LOGGING
#

DEBUG = False

LOG_NAME = 'proj2gpt.log'
LOG_ROOT = os.path.join(os.getcwd(), LOG_NAME)

LOG_TMSG = 1
LOG_TDIV = 2
LOG_TSEP = 4

def log_output(message, type=LOG_TMSG, display=True, date=False):
    if type == LOG_TMSG and display:
        print(message)
    with open(LOG_ROOT, 'a', encoding='utf-8') as f:
        if type != LOG_TMSG:
            f.write(message+'\n')
        else:
            now = datetime.now(timezone.utc)
            if date:
                ts = f"[{now:%Y-%m-%d %H:%M:%S}.{now.microsecond//1000:03d} Z] "
            else:
                ts = f"[{now:%H:%M:%S}.{now.microsecond//1000:03d} Z] "
            f.write(f'{ts}{message}\n')

def log_divider():
    log_output('='*20, LOG_TDIV)

def log_separator():
    log_output('-'*10, LOG_TSEP)

def log_message(message, display=True, date=False):
    log_output(message, type=LOG_TMSG, display=display, date=date)

#
# COMMON FUNCTIONALITY
#

def rm_leading_slash(path):
    return path.lstrip('/\\') if path.startswith(('/', '\\')) else path

def op_normpath(path): return os.path.normcase(os.path.normpath(path))
def op_normjoin(*paths): return op_normpath(os.path.join(*paths))
def op_absjoin(*paths): return os.path.abspath(op_normjoin(*paths))

def bool2str(b): return 'Yes' if b else 'No'
def str2bool(s): return str(s).strip().lower() in ('1', 'true', 'yes', 'on')

def natsort_key(s):
    parts = re.split(r'(\d+)', s)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p)))
        else:
            key.append((1, unicodedata.normalize('NFKD', p).casefold()))
    return key

#
# INTRO
#

__app__ = 'proj2gpt'
__version__ = '0.1.0'
__author__ = 'Maksym Plaksin <maxim.plaksin@gmail.com>'
__repo__ = 'https://github.com/frontcamp/proj2gpt'

INTRO_MAIN = f'''{__app__} {__version__}'''
INTRO_MORE = f'''Pack project text sources into TXT containers for ChatGPT.
Copyright (C) 2025 {__author__}
{__repo__}'''

def print_intro(verbose):
    print(INTRO_MAIN)
    if verbose:
        print(INTRO_MORE)
    print()

#
# CONFIGURATION
#

INI_NAME = 'proj2gpt.ini'

DEFAULTS = {
    'SETTINGS': {
        'debug': '0',    # log debug information
        'verbose': '1',  # show status & progress information
    },
    'PROJECT': {
        'project_title': 'Super-duper project',
        'project_descr': 'Short project description',
        'group_paths': '',    # <group_path1>[, <group_path2> ...]
        'group_roots': '',    # <group_root1>[, <group_root2> ...]
        'secrets_auto': '1',  # auto replace everything to <name>.gpt
        'secrets_list': '',   # <secret_path>@<dummy_filename>[, ...]
    },
    'TRAVERSAL': {
        'names_allowed': '*.cfg,*.conf,*.css,*.html,*.ini,*.js,*.json,*.md,*.php,*.py,*.txt,*.xml',
        'names_ignored': '.git*,/logs*,/temp*,/test*',
        'use_gitignore': '1',
        'max_file_size': '1000000',
    },
    'GENERATOR': {
        'dest_path': '/proj2gpt',
        'txt_size_max': '3000000',
        'log_lines_max': '3000', 
    },
}

def _parse_ini_list(s):
    s = (s or '').strip()
    return [x.strip() for x in re.split(r'[,\n]+', s) if x.strip()]

def load_config(proj_root):
    
    global DEBUG

    ini_path = op_normjoin(proj_root, INI_NAME)
    
    cp = configparser.ConfigParser()
    cp.read_dict(DEFAULTS)
    if os.path.isfile(ini_path):
        cp.read(ini_path, encoding='utf-8')

    settings = {}
    settings['project_root'] = proj_root

    settings['debug'] = cp.getboolean('SETTINGS', 'debug')
    settings['verbose'] = cp.getboolean('SETTINGS', 'verbose')

    settings['project_title'] = cp.get('PROJECT', 'project_title')
    settings['project_descr'] = cp.get('PROJECT', 'project_descr')
    settings['group_paths'] = _parse_ini_list(cp.get('PROJECT', 'group_paths'))
    settings['group_roots'] = _parse_ini_list(cp.get('PROJECT', 'group_roots'))
    settings['secrets_auto'] = cp.getboolean('PROJECT', 'secrets_auto')
    settings['secrets_list'] = _parse_ini_list(cp.get('PROJECT', 'secrets_list'))

    settings['names_allowed'] = _parse_ini_list(cp.get('TRAVERSAL', 'names_allowed'))
    settings['names_ignored'] = _parse_ini_list(cp.get('TRAVERSAL', 'names_ignored'))
    settings['use_gitignore'] = cp.getboolean('TRAVERSAL', 'use_gitignore')
    settings['max_file_size'] = cp.getint('TRAVERSAL', 'max_file_size')

    settings['dest_path'] = cp.get('GENERATOR', 'dest_path').strip()
    settings['txt_size_max'] = cp.getint('GENERATOR', 'txt_size_max')
    settings['log_lines_max'] = cp.getint('GENERATOR', 'log_lines_max')

    # set global debug mode
    DEBUG = settings['debug']

    # define destination root folder
    dest_path = op_normpath(settings['dest_path'])
    dest_path_nls = rm_leading_slash(dest_path)
    settings['dest_root'] = op_absjoin(proj_root, dest_path_nls)

    # add self files & folders to ignored
    settings['names_ignored'].append(INI_NAME)
    settings['names_ignored'].append(dest_path + '*')
    settings['names_ignored'].append('*.gpt')

    return settings

def summarize_settings(settings):
    lines = [
        'SETTINGS:',
        ' [P] project_root: %s' % settings['project_root'],
        ' [P] project_title: %s' % settings['project_title'],
        ' [P] project_descr: %s' % settings['project_descr'],
        ' [P] group_paths: %s' % (', '.join(settings['group_paths']) if settings['group_paths'] else '<none>'),
        ' [P] group_roots: %s' % (', '.join(settings['group_roots']) if settings['group_roots'] else '<none>'),
        ' [P] secrets_auto: %s' % bool2str(settings['secrets_auto']),
        ' [P] secrets_list: %s' % (', '.join(settings['secrets_list']) if settings['secrets_list'] else '<none>'),
        ' [T] names_allowed: %s' % (', '.join(settings['names_allowed']) if settings['names_allowed'] else '<none>'),
        ' [T] names_ignored: %s' % (', '.join(settings['names_ignored']) if settings['names_ignored'] else '<none>'),
        ' [T] use_gitignore: %s' % bool2str(settings['use_gitignore']),
        ' [T] max_file_size: %s' % settings['max_file_size'],
        ' [G] dest_path: %s' % (settings['dest_path'])  ,
        ' [G] dest_root: %s' % (settings['dest_root'])  ,
        ' [G] txt_size_max: %s' % settings['txt_size_max'],
        ' [G] log_lines_max: %s' % settings['log_lines_max'],
    ]
    return '\n'.join(lines)

#
# COLLECTING DATA
#

def group_roots_to_paths(proj_root, settings):
    
    group_paths = settings['group_paths']  # [] - relative paths list
    paths_seen = set()

    group_roots = settings['group_roots']  # [] - relative paths list
    roots_seen = set()

    # normalize group paths
    paths = []
    for group_path in group_paths:
        _rel_path = op_normpath(group_path)
        _rel_path_nls = rm_leading_slash(_rel_path)
        group_root = op_absjoin(proj_root, _rel_path_nls)
        if os.path.isdir(group_root):
            paths.append(_rel_path)
            paths_seen.add(_rel_path)
        else:
            log_message(f'Error: Group not found: {group_path} ({group_root})')
    group_paths = paths  # reinit with checked and normalized paths

    for _rel_root in group_roots:
        _rel_root = op_normpath(_rel_root)
        _rel_root_nls = rm_leading_slash(_rel_root)
        group_root = op_absjoin(proj_root, _rel_root_nls)
        if not os.path.isdir(group_root):
            log_message(f'Error: Group root not found: {_rel_root} ({group_root})')
            continue
        roots_seen.add(_rel_root)
        try:
            entries = sorted(os.listdir(group_root), key=str.casefold)
        except PermissionError:
            log_message(f'Error: Access denied to: {_rel_root} ({group_root})')
            continue
        for group_name in entries:
            sub_group_root = op_normjoin(group_root, group_name)
            if (os.path.islink(sub_group_root)       # symlink
             or not os.path.isdir(sub_group_root)):  # not folder
                continue
            sub_group_path = op_normjoin(_rel_root, group_name)
            if sub_group_path not in paths_seen:
                group_paths.append(sub_group_path)
                paths_seen.add(sub_group_path)

    settings['group_paths'] = sorted(paths_seen, key=natsort_key)
    settings['group_roots'] = sorted(roots_seen, key=natsort_key)

def gpath_to_fname(group_path):
    return 'group' + group_path.replace(OS_SEP, '__')

def traverse(settings, proj_root):

    global DEBUG

    group_paths = settings['group_paths']
    names_allowed = settings['names_allowed']
    names_ignored = settings['names_ignored']

    groups = {
        OS_SEP: {
            'name': DEF_GROUP_NAME,
            'files': []
        },
    }
    for gpath in group_paths:
        groups[gpath] = {
            'name': gpath_to_fname(gpath),
            'files': []
        }

    def rel(p): return os.path.relpath(p, proj_root)

    def walk(d_abs: str):
        d_rel = '' if d_abs == proj_root else rel(d_abs)
        d_name = os.path.basename(d_abs)

        files, dirs = [], []
        with os.scandir(d_abs) as it:
            for e in it:
                if e.is_file(follow_symlinks=False):
                    files.append(e)
                elif e.is_dir(follow_symlinks=False):
                    dirs.append(e)

        files.sort(key=lambda e: e.name.lower())
        dirs.sort(key=lambda e: e.name.lower())

        for e in files:
            
            fpath = op_normpath(OS_SEP + d_rel)
            
            allowed_file = any(fnmatch(e.name, mask) for mask in names_allowed)
            allowed_path = any(fnmatch(fpath, mask) for mask in names_allowed)
            
            ignored_file = any(fnmatch(e.name, mask) for mask in names_ignored)
            ignored_path = any(fnmatch(fpath, mask) for mask in names_ignored)

            if not allowed_file and not allowed_path:
                file_path = op_normjoin(d_rel, e.name)
                if DEBUG:
                    log_message(f'Notice: Skipped: {file_path}', display=False)
                continue

            if ignored_file or ignored_path:
                file_path = op_normjoin(d_rel, e.name)
                if DEBUG:
                    log_message(f'Notice: Ignored: {file_path}', display=False)
                continue
            
            st = e.stat(follow_symlinks=False)

            group_path = DEF_GROUP_PATH
            for gpath in groups:
                if gpath == DEF_GROUP_PATH:
                    continue
                if (OS_SEP + d_rel).startswith(gpath):
                    group_path = gpath
                    break

            groups[group_path]['files'].append({
                'dir_name': d_name,
                'dir_path': d_rel,
                'dir_root': d_abs,
                'file_name': e.name,
                'file_path': d_rel,
                'file_size': st.st_size,
                'is_symlink': e.is_symlink(),
            })

        for sub in dirs:
            walk(sub.path)

    walk(proj_root)
    
    pprint(groups)
    return groups


def main():
    global LOG_ROOT

    proj_root = os.getcwd()
    settings = load_config(proj_root)
    verbose = settings['verbose']

    os.makedirs(settings['dest_root'], exist_ok=True)

    LOG_ROOT = os.path.join(settings['dest_root'], LOG_NAME)
    log_divider()
    log_message(f'START {__app__} v{__version__}', display=False, date=True)

    print_intro(verbose)
    
    log_message(summarize_settings(settings), display=verbose)
    
    group_roots_to_paths(proj_root, settings)
    
    if verbose and settings.get('group_paths'):
        group_paths = ', '.join(settings['group_paths'])
        log_message(f'Compiled group paths: {group_paths}')
        
    if verbose and settings.get('group_roots'):
        group_roots = ', '.join(settings['group_roots'])
        log_message(f'Compiled group roots: {group_roots}')

    traverse(settings, proj_root)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

