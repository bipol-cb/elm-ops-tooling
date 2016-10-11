#! /usr/bin/env python
from __future__ import print_function

import sys
import json
import shutil
import os
import errno
import argparse
from collections import OrderedDict

def copy_package(location, destination, ignorer=None):
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(location, destination, ignore=ignorer)

def package_name(url):
    """ get the package name from a github url """

    project = url.split('/')[-1].split('.')[0]
    user = url.split('/')[-2]

    return {
        "project": project,
        "user": user
    }

def make_elm_stuff_folder(path):
    actual_path = '/'.join(path.split('/')[:-1])

    try:
        os.makedirs(actual_path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(actual_path):
            pass
        else:
            raise

def gitignores(path):
    try:
        with open(path) as f:
            return [line.strip() for line in f]
    except:
        return []

def self_publish(package_location, destination=".", quiet=False):
    """ package_location should be the local package to install
    """

    elm_package_file = "{location}/elm-package.json".format(location=package_location)
    destination_elm_package_file = "{destination}/elm-package.json".format(destination=destination)

    exact_deps_file = "{destination}/elm-stuff/exact-dependencies.json".format(
        destination=destination,
        location=package_location
    )

    git_ignore_file = "{location}/.gitignore".format(location=package_location)


    with open(elm_package_file) as f:
        elm_package = json.load(f)


    package_details = package_name(elm_package['repository'])
    version = elm_package['version']


    place = package_details['user'] + '/' + package_details['project']


    copy_package(package_location, '{destination}/elm-stuff/packages/{place}/{version}'.format(
        place=place,
        version=version,
        destination=destination
    ), ignorer=shutil.ignore_patterns(*gitignores(git_ignore_file)))


    try:
        with open(exact_deps_file) as f:
            data = f.read()
            package_info = {}

            if data:
                package_info = json.loads(data)
    except IOError:
        package_info = {}

    make_elm_stuff_folder(exact_deps_file)

    with open(exact_deps_file, 'w') as f:
        package_info[place] = version
        json.dump(package_info, f, sort_keys=False, indent=4)

    with open(destination_elm_package_file) as f:
        destination_elm_package = json.load(f, object_pairs_hook=OrderedDict)

    with open(destination_elm_package_file, 'w') as f:
        destination_elm_package['dependencies'][place] = "{version} <= v <= {version}".format(version=version)
        json.dump(destination_elm_package, f, sort_keys=False, indent=4)


def main():

    parser = argparse.ArgumentParser(description='Publish a local package into your project')

    parser.add_argument('--quiet', '-q', action='store_true', help='don\'t print anything', default=False)

    parser.add_argument('package_location')
    parser.add_argument('destination')
    args = parser.parse_args()

    self_publish(args.package_location, args.destination, quiet=args.quiet)

if __name__ == '__main__':
    main()
