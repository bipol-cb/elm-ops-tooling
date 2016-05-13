#! /usr/bin/env python
from __future__ import print_function

import sys
import json
import requests
import struct
import argparse

def load_all_packages(elm_version, url=None):
    if url is None:
        url = "http://package.elm-lang.org/all-packages?elm-package-version="

    payload = requests.get("{url}{elm_version}".format(
        url=url,
        elm_version=elm_version
        ))

    return { item['name'] : item for item in payload.json() }

def load_versions(package_name, url=None):
    if url is None:
        url = "http://package.elm-lang.org/versions?name="

    payload = requests.get("{url}{package_name}".format(
        url=url,
        package_name=package_name
        ))

    return payload.content


def load_local_packages(elm_package):
    with open(elm_package) as f:
        return json.load(f)['dependencies']

def top_range(field):
    only_end = field[field.index('v'):]

    if '=' in only_end:
        return only_end.split('=')[-1].strip()
    if '<' in only_end:

        number = only_end.split('<')[-1].strip()

        if patch(number) == 0:
            if minor(number) == 0:
                return '{maj}.{min}.{pat}'.format(
                    maj = major(number) - 1,
                    min = 9999999,
                    pat = 0 )
            return '{maj}.{min}.{pat}'.format(
                    maj = major(number) - 1,
                    min = minor(number) - 1,
                    pat = 0 )
        return '{maj}.{min}.{pat}'.format(
            maj = major(number) - 1,
            min = minor(number) - 1,
            pat = patch(number) - 1 )



def major(version):
    return int(version.split('.')[0])

def minor(version):
    return int(version.split('.')[1])

def patch(version):
    return int(version.split('.')[2])

def get_major_upgrades(top, versions):
    major_top = major(top)

    return [ version for version in versions if major(version) > major_top ]

def get_minor_upgrades(top, versions):
    major_top = major(top)
    minor_top = minor(top)

    return [ version for version in versions if minor(version) > minor_top and major(version) == major_top ]

def get_patch_upgrades(top, versions):
    major_top = major(top)
    minor_top = minor(top)
    patch_top = patch(top)

    return [ version for version in versions
        if major(version) == major_top and minor_top == minor(version) and patch_top > patch(version) ]

def find_newer_versions(local_deps, remote_deps):
    upgrade_suggestions = {}

    for (dep, version) in local_deps.items():
        current_version = top_range(version)
        patches = get_patch_upgrades(current_version, remote_deps[dep]['versions'])
        minors = get_minor_upgrades(current_version, remote_deps[dep]['versions'])
        majors = get_major_upgrades(current_version, remote_deps[dep]['versions'])

        upgrade_suggestions[dep] = {
            'patches': patches,
            'minors': minors,
            'majors': majors
        }

    return upgrade_suggestions

def newest_version(suggestions):
    if suggestions['majors']:
        return suggestions['majors'][-1]
    elif suggestions['minors']:
        return suggestions['majors'][-1]
    else:
        return suggestions['patches'][-1]

def print_newer_versions(local_deps, remote_deps):
    upgrade_suggestions = []

    for (dep, suggestions) in find_newer_versions(local_deps, remote_deps).items():
        patches = suggestions['patches']
        minors = suggestions['minors']
        majors = suggestions['majors']

        if len(patches) > 0:
            upgrade_suggestions.append(
                'Patches available for {dep}: [{patches}]'.format(dep=dep, patches=', '.join(patches))
                )
        if len(minors) > 0:
            upgrade_suggestions.append(
                'Minors available for {dep}: [{minors}]'.format(dep=dep, minors=', '.join(minors))
                )
        if len(majors) > 0:
            upgrade_suggestions.append(
                'Majors available for {dep}: [{majors}]'.format(dep=dep, majors=', '.join(majors))
                )

    if not upgrade_suggestions:
        print('No upgrades available')
    else:
        print('\n'.join(upgrade_suggestions))


def main():

    parser = argparse.ArgumentParser(description='Check deps file for possible upgrades')

    parser.add_argument('--elm-version', help='specify your current elm version', default='0.16')

    parser.add_argument('local')
    args = parser.parse_args()

    local = load_local_packages(args.local)
    remote = load_all_packages(args.elm_version)

    print_newer_versions(local, remote)



if __name__ == '__main__':
    main()

