sbl2py - A Snowball-to-Python Compiler
#######################################
*sbl2py* translates code written in the Snowball_ string processing
language into Python_::

    import sbl2py
    import sbl2py.utils

    sbl_code = """
    externals ( stem )
    define stem as (
        backwards ( ['ly'] delete )
    )
    """
    py_code = sbl2py.translate_string(sbl_code)
    module = sbl2py.utils.module_from_code('demo_module', py_code)
    print module.stem('fabulously')

Output::

    fabulous

.. _Snowball: http://snowball.tartarus.org/compiler/snowman.html
.. _Python: https://www.python.org


Features
========
*sbl2py* should support all of the Snowball features that are commonly
used. In particular, all features used by the stemming algorithms from
the Snowball stemmer package are supported.


Installation
============
Installing *sbl2py* is easy using pip_::

    pip install sbl2py

.. _pip: http://pip.readthedocs.org/en/latest/index.html


Usage
=====
The easiest way to translate a Snowball file into a Python module is
using the ``sbl2py`` script which is automatically installed with
*sbl2py*::

    sbl2py SNOWBALL_FILE PYTHON_FILE

See ``sbl2py --help`` for the available options.

You can also use *sbl2py* from within Python. The ``sbl2py`` module
offers two functions that translate Snowball code from a string
(``translate_string``) or a file (``translate_file``) and return the
corresponding Python source as a string. If you want to execute the
code, simply use the ``module_from_code`` function of the
``sbl2py.utils`` module.

The generated Python modules export all routines from the original
Snowball code that are listed in the ``externals`` section. That is,
if you have ``externals ( stem )`` in your Snowball code and store
the generated Python module in a file called ``mystemmer.py`` then
you can call the ``stem`` routine as follows::

    import mystemmer
    print mystemmer.stem('foobar')
