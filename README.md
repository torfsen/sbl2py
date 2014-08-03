# sbl2py -- A Snowball-to-Python Compiler

*sbl2py* translates code written in the
[Snowball](http://snowball.tartarus.org/compiler/snowman.html) string
processing language into [Python](https://www.python.org/):

    import sbl2py
    import sbl2py.utils

    sbl_code = """
    externals ( stem )
    define stem as (
        backwards (['ly'] delete)
    )
    """
    py_code = sbl2py.translate_string(sbl_code)
    module = sbl2py.utils.module_from_code('demo_module', py_code)
    print module.stem('fabulously')


## Features

*sbl2py* should support all of the Snowball features that are commonly used.
In particular, all features used by the stemming algorithms from the Snowball
stemmer package are supported.
