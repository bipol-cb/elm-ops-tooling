#! /usr/bin/env python
from __future__ import print_function

import elm_deps_upgrade as upgrader
from collections import OrderedDict
import json
import requests
import argparse
import sys
import re
import os
import glob

module_ident = 'module'
space_before_module_name = '\\s+'
module_name = '(\\S+)'
space_between_name_and_expose = '\\s+?'
expose = '(.*?)'
space_between_expose_and_where = '\\s+?'
where_ident = 'where'


module_pattern = ''.join(
        [ module_ident
        , space_before_module_name
        , module_name
        , space_between_name_and_expose
        , expose
        , space_between_expose_and_where
        , where_ident
        ]
        )

KNOWN_MOVES = {
    'evancz/elm-html' : 'elm-lang/html'
    , 'evancz/virtual-dom': 'elm-lang/virtual-dom'
    , 'evancz/elm-effects' : ''
    , 'evancz/start-app' : ''
    , 'maxsnew/lazy' : 'elm-lang/lazy'
    , 'lukewestby/elm-http-extra' : 'lukewestby/elm-http-builder'
    }


def upgrade_elm_version(version):
    return "0.17.0 <= v < 0.18.0"

def upgrade_module_syntax(module_name, exposing):
    module_name = module_name.strip()
    exposing = exposing.strip()

    if not exposing:
        exposing = '(..)'
    #print(exposing)

    return 'module {name} exposing {exposing}'.format(name=module_name, exposing=exposing)


def replace_module_line(text, replacement):
    return re.sub(module_pattern, replacement, text, count=1, flags=re.MULTILINE | re.DOTALL)

def get_module_name_and_exposing(text):
    matches = re.search(module_pattern, text, flags=re.MULTILINE | re.DOTALL)

    if not matches:
        return ('', '')

    return matches.groups()

def new_packages():
    r = requests.get("http://package.elm-lang.org/new-packages")
    return r.json()

def update_elm_package(root_folder, dry=False):
    with open(root_folder + '/elm-package.json') as f:
        package_data = json.load(f, object_pairs_hook=OrderedDict)

    package_data['elm-version'] = upgrade_elm_version(package_data['elm-version'])

    packages = package_data['dependencies']
    upgraded_packages = new_packages()
    print(upgraded_packages)

    notes = []
    errors = []
    upgradable_packages = {}



    for (package, version) in list(packages.items())[:]:
        if package in KNOWN_MOVES:
            new_name = KNOWN_MOVES[package]

            if new_name == '':
                errors.append('Package {name} has been removed'.format(name=package))
            else:
                notes.append('Package {name} renamed to {new_name}'.format(name=package, new_name=new_name))

                version = '1.0.0 <= v <= 1.0.0'
                upgradable_packages[new_name] = version
                del package_data['dependencies'][package]

            continue

        if package not in upgraded_packages:
            errors.append('Package {name} not upgraded yet!'.format(name=package))
            continue


        upgradable_packages[package] = version

    local = upgradable_packages
    remote = upgrader.load_all_packages("0.17", "http://package.elm-lang.org/all-packages?elm-package-version=")


    upgrade_suggestions = upgrader.find_newer_versions(local, remote)

    for (dep, suggestions) in upgrade_suggestions.items():
        try:
            update_to = upgrader.newest_version(suggestions)
        except Exception as e:
            notes.append('package {} already updated'.format(dep))
            package_data['dependencies'][dep] = upgradable_packages[dep]
            continue

        notes.append('updating {} to {}'.format(dep, update_to))

        package_data['dependencies'][dep] = "{} <= v <= {}".format(update_to, update_to)


    print('=======================')
    print('Notes:')
    print('\n'.join(notes))

    print('=======================')
    print('Warnings: ')
    print('\n'.join(errors))

    print('========================\n\n')
    print(json.dumps(package_data, sort_keys=False, indent=4))

    if not dry:
        with open(root_folder + '/elm-package.json', 'w') as f:
            json.dump(package_data, f, sort_keys=False, indent=4)

    if errors:
        print('There were errors that need to be handled manually!')
        sys.exit(1)

def upgrade_elm_files_in_folder(folder, root_folder):
    if folder[0] != '.':
        folder = root_folder + '/' + folder

    for file in glob.glob('{}/**/*.elm'.format(folder), recursive=True):
        with open(file, 'r') as f:
            text = f.read()

        (name, exposing) = get_module_name_and_exposing(text)
        new_line = upgrade_module_syntax(name, exposing)

        new_text = replace_module_line(text, new_line)

        with open(file, 'w') as f:
            f.write(new_text)



def upgrade_elm_files(root_folder):
    with open(root_folder + '/elm-package.json') as f:
        package_data = json.load(f, object_pairs_hook=OrderedDict)

    dirs = package_data['source-directories']

    for dir in dirs:
        upgrade_elm_files_in_folder(dir, root_folder)

def run_elm_make(root_folder):
    from subprocess import call
    os.chdir(root_folder)

    call(["elm-package", "install", "--yes"])
    call(["elm-make"])

def main():

    parser = argparse.ArgumentParser(description='Automatically upgrade your package to 0.17')
    parser.add_argument('--dry', '-d', action='store_true', help='only print possible changes', default=False)

    parser.add_argument('package_dir')
    args = parser.parse_args()

    update_elm_package(args.package_dir, dry=args.dry)
    upgrade_elm_files(args.package_dir)
    run_elm_make(args.package_dir)


if __name__ == '__main__':
    main()

