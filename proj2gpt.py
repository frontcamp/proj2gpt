#!/usr/bin/env python3

# File naming convention:
#   *_file - file name
#   *_path - relative path to file or folder
#   *_root - absolute path to file or folder


import os, re, sys
import configparser


LOG_NAME = 'proj2gpt.log'

def error_reporting(err_message):
    print(err_message)
    with open(LOG_NAME, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')


__app__ = 'proj2gpt'
__version__ = '0.1.0'
__author__ = 'Maksym Plaksin <maxim.plaksin@gmail.com>'
__repo__ = 'https://github.com/frontcamp/proj2gpt'

INTRO = f'''{__app__} {__version__}
Pack project text sources into TXT containers for ChatGPT.
Copyright (C) 2025 {__author__}
{__repo__}
'''


INI_NAME = 'proj2gpt.ini'

DEFAULTS = {
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
        'names_ignored': '*.gpt,.git*,/logs,/temp,/test',
        'use_gitignore': '1',
        'max_file_size': '1000000',
    },
    'GENERATOR': {
        'dest_path': '/proj2gpt',
        'txt_size_max': '3000000',
        'log_lines_max': '3000', 
    },
}

def bool2str (b): return 'Yes' if b else 'No'

def _parse_ini_list(s):
    return [x.strip() for x in re.split(r'[,\n]+', s.strip()) if x.strip()]

def load_config(project_root):
        
    ini_path = os.path.normpath(os.path.join(project_root, INI_NAME))
    
    cp = configparser.ConfigParser()
    cp.read_dict(DEFAULTS)
    if os.path.isfile(ini_path):
        cp.read(ini_path, encoding='utf-8')

    settings = {}
    settings['project_root'] = project_root

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

    # define destination root folder
    dest_path = settings['dest_path']
    if dest_path.startswith(('/', '\\')):
        dest_path = dest_path.lstrip('/\\')
        settings['dest_path'] = dest_path
    settings['dest_root'] = os.path.abspath(os.path.join(project_root, dest_path))

    return settings


def print_intro():
    print(INTRO)


def summarize_settings(s):
    lines = [
        'SETTINGS:',
        '[P] project_root: %s' % s['project_root'],
        '[P] project_title: %s' % s['project_title'],
        '[P] project_descr: %s' % s['project_descr'],
        '[P] group_paths: %s' % (', '.join(s['group_paths']) if s['group_paths'] else '<none>'),
        '[P] group_roots: %s' % (', '.join(s['group_roots']) if s['group_roots'] else '<none>'),
        '[P] secrets_auto: %s' % bool2str(s['secrets_auto']),
        '[P] secrets_list: %s' % (', '.join(s['secrets_list']) if s['secrets_list'] else '<none>'),
        '[T] names_allowed: %s' % (', '.join(s['names_allowed']) if s['names_allowed'] else '<none>'),
        '[T] names_ignored: %s' % (', '.join(s['names_ignored']) if s['names_ignored'] else '<none>'),
        '[T] use_gitignore: %s' % bool2str(s['use_gitignore']),
        '[T] max_file_size: %s' % s['max_file_size'],
        '[G] dest_path: %s' % (s['dest_path'])  ,
        '[G] dest_root: %s' % (s['dest_root'])  ,
        '[G] txt_size_max: %s' % s['txt_size_max'],
        '[G] log_lines_max: %s' % s['log_lines_max'],
    ]
    return '\n'.join(lines)


def main():

    print_intro()
    root = os.getcwd()
    settings = load_config(root)
    os.makedirs(settings['dest_root'], exist_ok=True)
    print(summarize_settings(settings))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

