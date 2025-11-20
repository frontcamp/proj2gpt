#!/usr/bin/env python3

# Naming convention:
#   UPPER_CASE - constants
#   lower_case - variables
#   *_file - file handler
#   *_name - file or folder name
#   *_path - relative path to file or folder
#   *_root - absolute path to file or folder
#   *_nls - no leading slash

import configparser
import hashlib
import os
import re
import shutil
import sys
import unicodedata
from collections import deque
from datetime import datetime, timezone
from fnmatch import fnmatch
from textwrap import dedent

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
    if display:
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

def log_divider(display=True):
    log_output('='*20, LOG_TDIV, display)

def log_separator(display=True):
    log_output('-'*10, LOG_TSEP, display)

def log_message(message, display=True, date=False):
    log_output(message, type=LOG_TMSG, display=display, date=date)

#
# COMMON FUNCTIONALITY
#

def rm_leading_slash(path):
    return path.lstrip('/\\') if path.startswith(('/', '\\')) else path

def op_normpath(path): return os.path.normpath(path)
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

def list_dirs(path):
    """Return a list of subfolder names in the given path."""
    try:
        dirs = [
            name for name in os.listdir(path)
            if os.path.isdir(os.path.join(path, name))
        ]
        return sorted(dirs, reverse=True)
    except OSError:
        return []

def gitignore2masks(dir_root, dir_path):
    file_root = op_normjoin(dir_root, '.gitignore')
    masks = []
    if not os.path.isfile(file_root):
        return masks

    with open(file_root, encoding="utf-8") as git_file:
        for line in git_file:
            mask = line.strip()
            if not mask or mask.startswith("#"):
                continue

            if mask.startswith(('/', '\\')):  # anchored mask (rel. to this .gitignore dir)
                mask = rm_leading_slash(mask)
                if dir_path:
                    full = op_normjoin(OS_SEP + dir_path, mask)
                else:
                    full = OS_SEP + mask
            else:                             # non-anchored mask
                full = mask

            masks.append(op_normpath(full))

    return masks

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
TOC_NAME = 'toc.txt'
INS_NAME = 'instructions.txt'
DFF_NAME = 'diff.txt'

DEFAULTS = {
    'SETTINGS': {
        'debug': '0',    # log debug information
        'verbose': '1',  # show status & progress information
        'build_keep_count': '5',  # how many builds to keep, 0 = unlimited
        'log_rewrite': '1',       # start a new log each run; True disables max_log_lines
        'max_log_lines': '50000',
    },
    'PROJECT': {
        'project_title': 'Common',
        'project_descr': 'Working on the project',
        'group_paths': '',    # <group_path1>[, <group_path2> ...]
        'group_roots': '',    # <group_root1>[, <group_root2> ...]
        'auto_secrets': '1',  # auto replace everything to <name>.gpt
    },
    'TRAVERSAL': {
        'names_allowed': '*.cfg,*.conf,*.css,*.html,*.ini,*.js,*.json,*.md,*.php,*.py,*.txt,*.xml',
        'names_ignored': '.git*,/logs*,/temp*,/test*',
        'use_gitignore': '1',
        'max_file_size': '1000000',  # bytes
    },
    'GENERATOR': {
        'dest_path': '/proj2gpt',
        'max_text_size': '3000000',  # bytes
    },
}

def _parse_ini_list(s):
    s = (s or '').strip()
    items = [x.strip() for x in re.split(r'[,\n]+', s) if x.strip()]
    return [op_normpath(x) for x in items]

def load_config(proj_root):

    global DEBUG, LOG_ROOT

    ini_path = op_normjoin(proj_root, INI_NAME)

    cp = configparser.ConfigParser()
    cp.read_dict(DEFAULTS)
    if os.path.isfile(ini_path):
        cp.read(ini_path, encoding='utf-8')

    settings = {}
    settings['project_root'] = proj_root

    # SETTINGS
    settings['debug'] = cp.getboolean('SETTINGS', 'debug')
    settings['verbose'] = cp.getboolean('SETTINGS', 'verbose')
    settings['build_keep_count'] = cp.getint('SETTINGS', 'build_keep_count')
    settings['log_rewrite'] = cp.getboolean('SETTINGS', 'log_rewrite')
    settings['max_log_lines'] = cp.getint('SETTINGS', 'max_log_lines')

    # PROJECT
    settings['project_title'] = cp.get('PROJECT', 'project_title')
    settings['project_descr'] = cp.get('PROJECT', 'project_descr')
    settings['group_paths'] = _parse_ini_list(cp.get('PROJECT', 'group_paths'))
    settings['group_roots'] = _parse_ini_list(cp.get('PROJECT', 'group_roots'))
    settings['auto_secrets'] = cp.getboolean('PROJECT', 'auto_secrets')

    # TRAVERSAL
    settings['names_allowed'] = _parse_ini_list(cp.get('TRAVERSAL', 'names_allowed'))
    settings['names_ignored'] = _parse_ini_list(cp.get('TRAVERSAL', 'names_ignored'))
    settings['use_gitignore'] = cp.getboolean('TRAVERSAL', 'use_gitignore')
    settings['max_file_size'] = cp.getint('TRAVERSAL', 'max_file_size')

    # GENERATOR
    settings['dest_path'] = op_normpath(cp.get('GENERATOR', 'dest_path').strip())
    settings['max_text_size'] = cp.getint('GENERATOR', 'max_text_size')

    # set global debug mode
    DEBUG = settings['debug']

    # define destination folder
    dest_path_nls = rm_leading_slash(settings['dest_path'])
    settings['dest_root'] = op_absjoin(proj_root, dest_path_nls)

    # define context folder
    settings['context_name'] = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    settings['context_path'] = op_normjoin(settings['dest_path'], settings['context_name'])
    settings['context_root'] = op_normjoin(settings['dest_root'], settings['context_name'])

    # add self files & folders to ignored
    settings['names_ignored'].append(INI_NAME)
    settings['names_ignored'].append(settings['dest_path'] + '*')
    settings['names_ignored'].append('*.gpt')

    # set log root to destination folder
    LOG_ROOT = os.path.join(settings['dest_root'], LOG_NAME)

    # delete old log if log_rewrite == True
    if settings['log_rewrite'] and os.path.isfile(LOG_ROOT):
        os.remove(LOG_ROOT)

    return settings

def summarize_settings(settings):

    lines = [
        'SETTINGS:',
        ' [S] debug: %s' % bool2str(settings['debug']),
        ' [S] verbose: %s' % bool2str(settings['verbose']),
        ' [S] build_keep_count: %s' % settings['build_keep_count'],
        ' [S] log_rewrite: %s' % bool2str(settings['log_rewrite']),
        ' [S] max_log_lines: %s' % settings['max_log_lines'],
        ' [P] project_root: %s' % settings['project_root'],
        ' [P] project_title: %s' % settings['project_title'],
        ' [P] project_descr: %s' % settings['project_descr'],
        ' [P] group_paths: %s' % (', '.join(settings['group_paths']) if settings['group_paths'] else '<none>'),
        ' [P] group_roots: %s' % (', '.join(settings['group_roots']) if settings['group_roots'] else '<none>'),
        ' [P] auto_secrets: %s' % bool2str(settings['auto_secrets']),
        ' [T] names_allowed: %s' % (', '.join(settings['names_allowed']) if settings['names_allowed'] else '<none>'),
        ' [T] names_ignored: %s' % (', '.join(settings['names_ignored']) if settings['names_ignored'] else '<none>'),
        ' [T] use_gitignore: %s' % bool2str(settings['use_gitignore']),
        ' [T] max_file_size: %s' % settings['max_file_size'],
        ' [G] dest_path: %s' % (settings['dest_path']),
        ' [G] dest_root: %s' % (settings['dest_root']),
        ' [G] context_name: %s' % (settings['context_name']),
        ' [G] context_path: %s' % (settings['context_path']),
        ' [G] context_root: %s' % (settings['context_root']),
        ' [G] max_text_size: %s' % settings['max_text_size'],
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

    groups = {                    # 1st (root) group
        OS_SEP: {
            'name': DEF_GROUP_NAME,
            'files': []
        },
    }
    for gpath in group_paths:     # other groups
        groups[gpath] = {
            'name': gpath_to_fname(gpath),
            'files': []
        }

    def rel_to_root(dir_root): return os.path.relpath(dir_root, proj_root)

    def walk(dir_root: str, _parent_git_masks=None):
        if _parent_git_masks is None:
            _parent_git_masks = []

        dir_path = '' if dir_root == proj_root else rel_to_root(dir_root)
        dir_name = os.path.basename(dir_root)

        files, dirs = [], []
        with os.scandir(dir_root) as dir_items:
            for dir_item in dir_items:
                if dir_item.is_file(follow_symlinks=False):
                    files.append(dir_item)
                elif dir_item.is_dir(follow_symlinks=False):
                    dirs.append(dir_item)

        files.sort(key=lambda e: e.name.lower())
        dirs.sort(key=lambda e: e.name.lower())

        gmasks = gitignore2masks(dir_root, dir_path)
        local_git = gmasks if settings['use_gitignore'] else []
        names_ignored_git = _parent_git_masks + local_git
        names_ignored_full = names_ignored + names_ignored_git

        for e in files:

            fpath = op_normjoin(OS_SEP + dir_path, e.name)

            #
            # filter

            allowed_file = any(fnmatch(e.name, mask) for mask in names_allowed)
            allowed_path = any(fnmatch(fpath, mask) for mask in names_allowed)

            ignored_file = any(fnmatch(e.name, mask) for mask in names_ignored_full)
            ignored_path = any(fnmatch(fpath, mask) for mask in names_ignored_full)

            if not allowed_file and not allowed_path:
                file_path = op_normjoin(dir_path, e.name)
                if DEBUG:
                    log_message(f'Skipped: {OS_SEP}{file_path}', display=False)
                continue

            if ignored_file or ignored_path:
                file_path = op_normjoin(dir_path, e.name)
                if DEBUG:
                    log_message(f'Ignored: {OS_SEP}{file_path}', display=False)
                continue

            #
            # define group

            group_path = DEF_GROUP_PATH
            for gpath in groups:
                if gpath == DEF_GROUP_PATH:
                    continue
                if (OS_SEP + dir_path).startswith(gpath):
                    group_path = gpath
                    break

            #
            # collect data

            file_stem, file_ext = os.path.splitext(e.name)
            if file_ext.startswith('.'):
                file_ext = file_ext[1:]

            file_stats = e.stat(follow_symlinks=False)

            groups[group_path]['files'].append({
                'dir_name': dir_name,
                'dir_path': dir_path,
                'dir_root': dir_root,
                'file_name': e.name,
                'file_stem': file_stem,
                'file_ext': file_ext,
                'file_path': op_normjoin(dir_path, e.name),
                'file_root': op_normjoin(dir_root, e.name),
                'file_size': file_stats.st_size,
                'file_hash': None,
                'is_symlink': e.is_symlink(),
            })

        for d in dirs:

            dpath = op_normjoin(OS_SEP + dir_path, d.name)
            ignored_name = any(fnmatch(d.name, mask) for mask in names_ignored_full)
            ignored_path = any(fnmatch(dpath, mask) for mask in names_ignored_full)

            if ignored_name or ignored_path:
                if DEBUG:
                    log_message(f'Ignored: {dpath}', display=False)
                continue

            walk(d.path, names_ignored_git)

    walk(proj_root)
    return groups

def groups_limiter(groups, settings):

    new_groups = dict()

    def add_new_group(path, name, files, chunk_num):
        if chunk_num > 0:
            path += ' (' + str(chunk_num) + ')'
            name += '__' + str(chunk_num).zfill(2)
        new_groups[path] = {'name': name, 'files': files}

    for group_path, group_data in groups.items():

        group_name = group_data['name']

        chunk_size = 0
        chunk_num = 0
        chunk_files = []

        for file_data in group_data['files']:

            file_size = file_data['file_size']
            file_path = file_data['file_path']

            if (file_size > settings['max_file_size']
             or file_size > settings['max_text_size']):
                if DEBUG:
                    log_message(f'Notice: Skipped by size ({file_size}), file {OS_SEP}{file_path}', display=False)
                continue

            if chunk_size > 0 and chunk_size + file_size > settings['max_text_size']:

                # create new group chunk
                chunk_size = 0    # reset
                chunk_num += 1    # inc
                add_new_group(group_path, group_name, chunk_files, chunk_num)
                chunk_files = []  # reset

            chunk_size += file_size
            chunk_files.append(file_data)

        if chunk_files:
            if chunk_num > 0:  # the last chunk in the series
                chunk_num += 1
            add_new_group(group_path, group_name, chunk_files, chunk_num)

    return new_groups

#
# GENERATING OUTPUT
#

def sha256_10(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]

def generate_containers(groups, settings):

    context_name = settings['context_name']
    context_path = settings['context_path']
    context_root = settings['context_root']
    os.makedirs(context_root, exist_ok=True)
    global_toc = ''

    for group_path, group_data in groups.items():

        container_name = group_data['name'] + '.txt'
        container_path = op_normjoin(context_path, container_name)
        container_root = op_normjoin(context_root, container_name)

        container_toc = f'\nGROUP ORIG_PATH: "{group_path}"; CONTAINER: "{container_name}"\n'
        container_txt = ''
        container_ofs = 0

        group_file = open(container_root,
                         mode='w',
                         encoding='utf-8',
                         buffering=64*1024,
                         newline='\n')

        for file_data in group_data['files']:

            stub_name = file_data['file_stem'] + '.gpt'
            stub_root = op_normjoin(file_data['dir_root'], stub_name)
            stub_exists = os.path.isfile(stub_root) and os.access(stub_root, os.R_OK)

            file_root = file_data['file_root']

            srce_root = stub_root if settings['auto_secrets'] and stub_exists else file_root

            # read file content, decode as UTF-8

            srce_file = open(srce_root, 'rb')
            try:
                file_content = srce_file.read().decode('utf-8', errors='strict')
            except OSError as e:
                log_message(f'I/O error {srce_root}: {e}', display=False)
                file_content = '[## ERROR: FILE CANNOT BE READ DUE TO I/O ERROR! ##]'
            except UnicodeDecodeError as e:
                log_message(f'Decode error in {srce_root}: {e}', display=False)
                file_content = '[## ERROR: FILE CANNOT BE READ DUE TO UNICODE DECODING ERROR! ##]'
            finally:
                srce_file.close()

            # normalize line breaks

            file_content = file_content.replace('\r\n','\n').replace('\r','\n')
            if not file_content:
                file_content = '[## NOTE: EMPTY FILE ##]'

            # add content frames

            hash10 = sha256_10(file_content)
            head = f'[## BEGIN FILE: "{OS_SEP}{file_data["file_path"]}" ##]\n'
            foot = f'\n[## END FILE: "{OS_SEP}{file_data["file_path"]}" ##]\n'
            file_content = head + file_content + foot

            f_size = len(file_content.encode('utf-8'))
            container_toc += f'FILE PATH: "{OS_SEP}{file_data["file_path"]}"; OFFSET: {container_ofs}; SIZE: {f_size}; HASH: {hash10}\n'
            container_ofs += f_size

            container_txt += file_content

        global_toc += container_toc

        group_file.write(container_txt)
        group_file.close()

        log_message(f'Created: {container_name}')

    # write global TOC

    global_toc_title = f'TOC BUILD: {context_name}\n'
    global_toc = global_toc_title + global_toc

    toc_root = op_normjoin(settings['context_root'], TOC_NAME)
    with open(toc_root, 'w', encoding='utf-8', newline='\n') as toc_file:
        toc_file.write(global_toc)

    log_message(f'Created: {TOC_NAME}')

def generate_instructions(groups, settings):

    s = dedent("""
        [TASK]
        You are helping to work on the project: {%PROJ_TITLE%}
        Project description: {%PROJ_DESCR%}

        [STRUCTURE]
        The following files are attached to the project:

        - toc.txt - project contents (list of groups/containers and the files included in them);
        - context.txt - main project context (default group, if present);
        - group__*.txt - containers of the project’s structural groups, united by something in common, for example: functionally (modules), by time (events), by content (sections);
        - environment.txt - conditions and additional information about the project (optional);
        - instructions.txt - these instructions.

        [NAVIGATION]
        Use toc.txt to determine the text container, offset, and length of the text block that contains the file’s content within the project context.
        The file content is located between the markers [## BEGIN FILE: "..." ##] and [## END FILE: "..." ##] in the corresponding container.

        [FORMAT]
        The project context is generated by the proj2gpt utility; see the (optionally) attached file readme.md for documentation and format details.

        [BEHAVIOR]
        The project discussion is conducted in the same language as the user’s question until something else is explicitly requested.
        When discussing the project, take into account its purpose and architecture, relying on all the provided context.
        In responses, explicitly refer to the project paths and files to simplify navigation.
        If the context is insufficient, specify which files/fragments are missing and stop; do not invent.
        When the user says that files or context were updated, assume that the attached toc.txt, context.txt, and any group__*.txt for this ChatGPT project are fresh and must be re-read and used.

        [BUILD HANDLING]
        The current project build ID is stored in the toc.txt file (first line: "TOC BUILD: ...").
        The assistant should always read this ID before analyzing the project and mention it at the beginning of their response (so that it is clear which build is being answered and so that the build number is preserved in the context of the dialog).
        If the user says he has updated the project files, but the build remains the same, warn the user that an old build may have been loaded and the project files may not contain the expected changes.
        """)

    s = s.replace('{%PROJ_TITLE%}', settings['project_title'])
    s = s.replace('{%PROJ_DESCR%}', settings['project_descr'])

    rul_root = op_normjoin(settings['context_root'], INS_NAME)
    with open(rul_root, 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)

    log_message(f'Created: {INS_NAME}')

def diff_toc_parse(toc_path):
    data = dict()

    if not os.path.isfile(toc_path):
        return data

    current_group = None

    with open(toc_path, 'r', encoding='utf-8') as toc_file:
        for raw_line in toc_file:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('TOC BUILD:'):
                continue

            if line.startswith('GROUP ORIG_PATH:'):
                m = re.match(
                    r'^GROUP ORIG_PATH:\s*"([^"]*)";\s*CONTAINER:\s*"([^"]*)"',
                    line
                )
                if not m:
                    continue

                group_path = m.group(1)
                container = m.group(2)

                current_group = {
                    'container': container,
                    'hashes': [],
                }
                data[group_path] = current_group
                continue

            if line.startswith('FILE PATH:') and current_group is not None:
                m = re.match(
                    r'^FILE PATH:\s*"[^"]*";\s*OFFSET:\s*\d+;'
                    r'\s*SIZE:\s*\d+;\s*HASH:\s*([0-9a-fA-F]+)',
                    line
                )
                if m:
                    file_hash = m.group(1)
                    current_group['hashes'].append(file_hash)

    for group in data.values():
        group['hashes'].sort()
        hashes_str = ''.join(group['hashes'])
        group['hash'] = sha256_10(hashes_str)

    return data

def diff_calc(toc_data_old, toc_data_new):
    report = list()

    has_changes = False

    old_groups = set(toc_data_old.keys())
    new_groups = set(toc_data_new.keys())

    added_groups = sorted(new_groups - old_groups)
    removed_groups = sorted(old_groups - new_groups)
    common_groups = sorted(old_groups & new_groups)

    for gpath in added_groups:
        g = toc_data_new[gpath]
        report.append(f'New group: {gpath} -> {g["container"]}')
        has_changes = True

    for gpath in removed_groups:
        g = toc_data_old[gpath]
        report.append(f'Removed group: {gpath} -> {g["container"]}')
        has_changes = True

    for gpath in common_groups:
        old_hash = toc_data_old[gpath]['hash']
        new_hash = toc_data_new[gpath]['hash']

        if old_hash != new_hash:
            g = toc_data_new[gpath]
            report.append(f'Changed group: {gpath} -> {g["container"]}')
            has_changes = True

    if not report:
        report.append('No differences between last builds.')

    return report, has_changes

def diff_make(settings):
    build_names = list_dirs(settings['dest_root'])
    if len(build_names) < 2:
        log_message('This is the initial build, no diff available.')
        return

    toc_path_new = op_normjoin(settings['dest_root'], build_names[0], TOC_NAME)
    toc_data_new = diff_toc_parse(toc_path_new)

    toc_path_old = op_normjoin(settings['dest_root'], build_names[1], TOC_NAME)
    toc_data_old = diff_toc_parse(toc_path_old)

    diff_report, has_changes = diff_calc(toc_data_old, toc_data_new)

    if has_changes:
        diff_report.append('Changed file: toc.txt')

    for diff_message in diff_report:
        log_message(diff_message)

    dff_root = op_normjoin(settings['context_root'], DFF_NAME)
    with open(dff_root, 'w', encoding='utf-8', newline='\n') as dff_file:
        dff_file.write('\n'.join(diff_report) + '\n')

def cleanup_builds(settings):

    build_keep_count = settings['build_keep_count']
    build_names = list_dirs(settings['dest_root'])

    if build_keep_count <= 0:  # unlimited
        log_message('Builds auto cleanup disabled.')
        return

    if len(build_names) < 2:   # nothing to delete
        log_message('There are no builds to remove.')
        return

    del_count = 0
    for index, build_name in enumerate(build_names, start=1):
        build_root = op_normjoin(settings['dest_root'], build_name)
        if (index > build_keep_count     # build is redundant
        and os.path.isdir(build_root)):  # and is dir..
            shutil.rmtree(build_root)
            del_count += 1
            log_message(f'Removed: /{build_name}')

    if del_count == 0:
        log_message('No builds were removed.')

def cleanup_log(settings):

    TMP_NAME = 'proj2gpt.tmp'
    TMP_ROOT = os.path.join(settings['dest_root'], TMP_NAME)

    max_lines = settings['max_log_lines']

    if settings['log_rewrite']:
        return  # trimming not needed for fresh log

    if max_lines <= 0:
        return
    if not os.path.isfile(LOG_ROOT):
        return

    lines = deque(maxlen=max_lines)

    src = open(LOG_ROOT, 'r', encoding='utf-8', errors='replace')
    try:
        for line in src:
            lines.append(line)
    finally:
        src.close()

    dst = open(TMP_ROOT, 'w', encoding='utf-8', newline='')
    try:
        dst.writelines(lines)
    finally:
        dst.close()

    os.replace(TMP_ROOT, LOG_ROOT)

#
# MAIN
#

def main():

    proj_root = os.getcwd()
    settings = load_config(proj_root)
    verbose = settings['verbose']

    os.makedirs(settings['dest_root'], exist_ok=True)

    log_divider(display=False)
    log_message(f'START {__app__} v{__version__}', display=False, date=True)

    print_intro(verbose)

    log_message(summarize_settings(settings), display=verbose)

    group_roots_to_paths(proj_root, settings)

    if verbose and settings['group_paths']:
        group_paths = ', '.join(settings['group_paths'])
        log_message(f'Compiled group paths: {group_paths}')

    if verbose and settings['group_roots']:
        group_roots = ', '.join(settings['group_roots'])
        log_message(f'Compiled group roots: {group_roots}')

    # collect data

    groups = traverse(settings, proj_root)
    groups = groups_limiter(groups, settings)

    # generate output

    log_separator()
    generate_containers(groups, settings)
    generate_instructions(groups, settings)

    # calc & show diff

    log_separator()
    diff_make(settings)

    # clean up

    log_separator()
    cleanup_builds(settings)
    cleanup_log(settings)

    return 0

if __name__ == '__main__':
    sys.exit(main())

