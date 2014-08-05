import codecs
import os.path
import re
import sys

from setuptools import setup, find_packages

# We want the value of ``sbl2py.__version__``. However, we cannot
# simply ``import sbl2py`` since sbl2py requires pyparsing which
# might not be installed. Hence we extract the version information
# "manually".
module_dir = os.path.dirname(__file__)
init_filename = os.path.join(module_dir, 'sbl2py', '__init__.py')
with codecs.open(init_filename, 'r' ,'utf8') as f:
    for line in f:
        m = re.match(r'\s*__version__\s*=\s*[\'"](.*)[\'"]\s*', line)
        if m:
            version = m.group(1)
            break
    else:
        raise Exception('Could not find version number.')

setup(
    name='sbl2py',
    version=version,
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
