# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='package_builder',
    version='0.0.2',
    author=u'Wagner Souza',
    author_email='wagnersza@gmail.com',
    py_modules=['package_builder'],
    url='http://bitbucket.org/bruno/django-geoportail',
    license='BSD licence, see LICENCE.txt',
    description='Packege Builder make local enviroment to build SO packages' + \
                ' ',
    long_description=open('README.md').read(),
    install_requires = [
        'argparse==1.2.1',
        'docker-py==0.5.0',
        'dockerpty==0.2.3',
    ],
    entry_points={
        'console_scripts': [
            'package-builder = package_builder:main',
        ],
    }
)