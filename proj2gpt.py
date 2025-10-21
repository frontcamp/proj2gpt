#!/usr/bin/env python3


import os
import sys
import configparser
from pathlib import Path


LOG_NAME = 'proj2gpt.log'

def error_reporting(err_message):
    print(err_message)
    # write err_message to log file


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
    'project': {
        'project_title': 'Super-duper project',
        'project_descr': 'Short project description',
    },
    'traversal': {
        'names_allowed': '*.cfg;*.css;*.ini;*.js;*.md;*.php;*.py;*.txt;',
        'names_ignored': '*.gpt;.git;logs;temp;',
        'use_gitignore': '1',
        'max_file_size': '1000000',
    },
    'generator': {
        'dest_folder': 'proj2gpt',
        'txt_size_max': '3000000',
        'log_max_lines': '3000', 
    },
    # [secrets]
    # free-form lines: "replace /path original replacement"
}

def _parse_semicolon_list(value):
    return [p.strip() for p in value.split(';') if p.strip()]

def load_config(project_root):
    ini_path = Path(project_root) / INI_NAME
    cp = configparser.ConfigParser()
    cp.read_dict(DEFAULTS)
    if ini_path.exists():
        cp.read(str(ini_path), encoding='utf-8')

    settings = {}
    settings['project_root'] = Path(project_root)
    settings['project_title'] = cp.get('project', 'project_title').strip('"\'')
    settings['project_descr'] = cp.get('project', 'project_descr').strip('"\'')
    settings['names_allowed'] = _parse_semicolon_list(cp.get('traversal', 'names_allowed'))
    settings['names_ignored'] = _parse_semicolon_list(cp.get('traversal', 'names_ignored'))
    settings['use_gitignore'] = cp.getint('traversal', 'use_gitignore')
    settings['max_file_size'] = cp.getint('traversal', 'max_file_size')
    settings['dest_folder'] = Path(cp.get('generator', 'dest_folder').strip('"\''))
    settings['txt_size_max'] = cp.getint('generator', 'txt_size_max')
    settings['log_max_lines'] = cp.getint('generator', 'log_max_lines')

    secrets = []
    if cp.has_section('secrets'):
        for key, value in cp.items('secrets'):
            line = (key + ' ' + value).strip()
            parts = line.split()
            if len(parts) >= 4 and parts[0].lower() == 'replace':
                secrets.append({
                    'base': Path(parts[1]),
                    'original': parts[2],
                    'replacement': parts[3],
                })
    settings['secrets'] = secrets

    return settings


def print_intro():
    print(INTRO)


def ensure_destination(settings):
    dest = settings['project_root'] / settings['dest_folder']
    os.makedirs(dest, exist_ok=True)
    return dest

def summarize_settings(s):
    lines = [
        'Settings:',
        '  project_root: %s' % s['project_root'],
        '  project_title: %s' % s['project_title'],
        '  project_descr: %s' % s['project_descr'],
        '  names_allowed: %s' % (';'.join(s['names_allowed']) if s['names_allowed'] else '(none)'),
        '  names_ignored: %s' % (';'.join(s['names_ignored']) if s['names_ignored'] else '(none)'),
        '  use_gitignore: %s' % s['use_gitignore'],
        '  max_file_size: %s' % s['max_file_size'],
        '  dest_folder: %s' % (s['project_root'] / s['dest_folder']),
        '  txt_size_max: %s' % s['txt_size_max'],
        '  log_max_lines: %s' % s['log_max_lines'],
        '  secrets rules: %d' % len(s['secrets']),
    ]
    return '\n'.join(lines)


def main():

    print_intro()
    root = Path.cwd()
    settings = load_config(root)
    ensure_destination(settings)
    print(summarize_settings(settings))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

