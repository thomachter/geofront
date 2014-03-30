from __future__ import with_statement

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from geofront.version import VERSION


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='Geofront',
    version=VERSION,
    description='Simple SSH key management service',
    long_description=readme(),
    author='Hong Minhee',
    author_email='minhee' '@' 'dahlia.kr',
    maintainer='Spoqa',
    maintainer_email='dev' '@' 'spoqa.com',
    license='AGPLv3 or later',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'setuptools',
        'Werkzeug >= 0.9',
        'Flask >= 0.10'
    ],
    entry_points='''
        [console_scripts]
        geofront-server = geofront.server:main
    ''',
    extras_require={
        'docs': ['Sphinx >= 1.2', 'sphinxcontrib-autoprogram']
    },
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved '
        ':: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: System :: Systems Administration :: Authentication/Directory'
    ]
)