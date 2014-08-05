import glob
import os.path
import sys

from setuptools import setup, find_packages

import sbl2py

setup(
    name='sbl2py',
    version=sbl2py.__version__,
    description='A Snowball-to-Python compiler',
    url='https://github.com/torfuspolymorphus/sbl2py',
    author='Florian Brucker',
    author_email='mail@florianbrucker.de',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Compilers',
        'Topic :: Text Processing :: Linguistic',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent ',
    ],
    keywords='snowball compiler',
    packages=find_packages(exclude='test'),
    install_requires=['pyparsing >= 2.0'],
    platforms=['any'],
    entry_points={'console_scripts':['sbl2py=sbl2py.__main__:main']},
)
