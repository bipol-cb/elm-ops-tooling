#! /usr/bin/env python

import collections
import argparse
import json
import os
import subprocess
import sys
import tarfile
import urllib2


def read_native_elm_package(package_file):
    """
    Reads elm-native-package.json.
    """

    with open(package_file) as f:
        return json.load(f)


def format_url(package):
    """
    Creates the url to fetch the tar from github.
    >>> format_url({'namespace': 'elm-lang', 'name': 'navigation', 'version': '2.0.0'})
    'https://github.com/elm-lang/navigation/archive/2.0.0.tar.gz'
    """
    return "https://github.com/{namespace}/{name}/archive/{version}.tar.gz".format(**package)


def parse_json(raw):
    """
    Parses the json and returns a list of {version, namespace, name}.
    >>> parse_json({'elm-lang/navigation': '2.0.0'})
    [{'version': '2.0.0', 'namespace': 'elm-lang', 'name': 'navigation'}]
    """
    result = []

    for name, version in raw.items():
        namespace, package_name = name.split('/')
        result.append({
          'namespace': namespace,
          'name': package_name,
          'version': version
        })

    return result


def format_vendor_dir(base, namespace):
    """
    Creates the path in the vendor folder.
    >>> format_vendor_dir('foo', 'bar')
    'foo/bar'
    """
    path = os.path.join(base, namespace)

    try:
        os.makedirs(path)
    except Exception as e:
        pass

    return path


def package_dir(vendor_dir, package):
    """
    Creates the path to the elm package.
    >>> package_dir('vendor/assets/elm', {'version': '2.0.0', 'namespace': 'elm-lang', 'name': 'navigation'})
    'vendor/assets/elm/elm-lang/navigation-2.0.0'
    """
    return "{vendor_dir}/{package_name}-{version}".format(
        vendor_dir=format_vendor_dir(vendor_dir, package['namespace']),
        package_name=package['name'],
        version=package['version']
    )


def fetch_packages(vendor_dir, packages):
    """
    Fetches all packages from github.
    """
    for package in packages:
        tar_filename = format_tar_file(vendor_dir, package)
        vendor = format_vendor_dir(vendor_dir, package['namespace'])
        url = format_url(package)

        print "Downloading {namespace}/{name} {version}".format(**package)
        tar_file = urllib2.urlopen(url)
        with open(tar_filename, 'w') as tar:
            tar.write(tar_file.read())

        with tarfile.open(tar_filename) as tar:
            tar.extractall(vendor, members=tar.getmembers())

    return packages


def format_tar_file(vendor_dir, package):
    """
    The name of the tar.
    >>> format_tar_file('vendor/assets/elm', {'namespace': 'elm-lang', 'name': 'navigation', 'version': '2.0.0'})
    'vendor/assets/elm/elm-lang/navigation-2.0.0-tar.gz'
    """
    vendor = format_vendor_dir(vendor_dir, package['namespace'])
    return package_dir(vendor_dir, package) + "-tar.gz"

def format_native_name(namespace, name):
    """
    Formates the package to the namespace used in elm native.
    >>> format_native_name('elm-lang', 'navigation')
    '_elm_lang$navigation'
    """

    underscored_namespace = namespace.replace("-", "_")
    underscored_name = name.replace("-", "_")
    return "_{owner}${repo}".format(owner=underscored_namespace, repo=underscored_name)


def namespace_from_repo(repository):
    """
    Namespace and name from repository.
    >>> namespace_from_repo('https://github.com/NoRedInk/noredink.git')
    ['NoRedInk', 'noredink']
    """

    repo_without_domain = repository.lstrip('https://github.com/').rstrip('.git')

    (namespace, name) = repo_without_domain.split('/')
    return [namespace, name]


def get_source_dirs(vendor_dir, package):
    """ get the source-directories out of an elm-package file """
    elm_package_filename = os.path.join(package_dir(vendor_dir, package), 'elm-package.json')
    with open(elm_package_filename) as f:
        data = json.load(f)

    return data['source-directories']


def munge_names(vendor_dir, repository, packages):
    """
    Replaces the namespaced function names in all native code by the namespace from the given elm-package.json.
    """
    namespace, name = namespace_from_repo(repository)
    for package in packages:
        subprocess.Popen((
          "find",
          package_dir(vendor_dir, package),
          "-type",
          "f",
          "-exec",
          "sed",
          "-i",
          "",
          "-e",
          "s/{0}/{1}/g".format(
              format_native_name(package['namespace'], package['name']),
              format_native_name(namespace, name)
          ),
          "{}",
          ";"
        ))


def update_elm_package(vendor_dir, configs, packages):
    """
    Gets the repo name and updates the source-directories in the given elm-package.json.
    """

    repository = ""

    for config in configs:
        with open(config) as f:
            data = json.load(f, object_pairs_hook=collections.OrderedDict)

        repository = data['repository']
        source_directories = data['source-directories']
        path = '../' * config.count('/')

        for package in packages:
            current_package_dirs = get_source_dirs(vendor_dir, package)

            for dir_name in current_package_dirs:
                relative_path = os.path.join(path, package_dir(vendor_dir, package), dir_name)

                if relative_path not in data['source-directories']:
                    data['source-directories'].append(relative_path)

        with open(config, 'w') as f:
            f.write(json.dumps(data, indent=4))

    return repository


def filter_packages(vendor_dir, packages):
  return [x for x in packages if not os.path.isdir(format_tar_file(vendor_dir, x))]


def main(native_elm_package, configs, vendor):
    raw_json = read_native_elm_package(native_elm_package)
    parsed = parse_json(raw_json)
    packages = filter_packages(vendor, parsed)
    fetch_packages(vendor, packages)
    repository = update_elm_package(vendor, configs, packages)
    munge_names(vendor, repository, packages)


def test():
    import doctest
    doctest.testmod()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch elm packages')
    parser.add_argument(
        'native_elm_package',
        help='The elm-native-package.json file you want to use',
        default='elm-native-package.json'
    )
    parser.add_argument('--elm-config', '-e', nargs='+')
    parser.add_argument('--vendor-dir', default='vendor/assets/elm')
    parser.add_argument('--test', '-t', action='store_true')

    args = parser.parse_args()
    if args.test:
        test()
        exit()

    main(args.native_elm_package, args.elm_config, args.vendor_dir)
