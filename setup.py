import glob
import os.path
import sys

from setuptools import setup, find_packages

_base_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_base_dir, 'src'))
import sbl2py
_version = sbl2py.__version__

setup(
    name='sbl2py',
    version=_version,
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
    ],
    keywords='snowball compiler',
    packages=find_packages(exclude='test'),
    install_requires=['pyparsing >= 2.0'],
    entry_points={'console_scripts':['sbl2py=sbl2py.__main__:main']},
)
