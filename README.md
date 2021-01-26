# Python Shell Toolkit (SHTK)

Python SHTK is a python module that seeks to make replacing shell scripts with
Python scripts an easier process.  Python has a number of syntax advantages
over traditional shell scripting languages such as BASH, including:
* Classes
* Modules
* With statements
* Try/Except statements
* Async and await for coroutines

The module and package oriented structure of Python's toolchain enables broad
code re-use and redistribution. Python also benefits from a wide selection of
built-in modules, and expands itself via the wide assortment of packages
that can be quickly installed using its built-in package manager. 

Finally, built-in automated test harnesses and long-standing code-quality
integrations make it easy to review, document, test, and maintain its
libraries.  

The author's primary intended use cases for Python SHTK include replacing BASH
scripts that automate builds of disk images, docker containers, and system
configurations.


## Installation
Using pip you can install shtk as follows:
```
pip3 install shtk
```

Or you can install the module from source as follows:
```
pip3 install .
```

## Tests
To run the automated tests, run the following command from the project's root
directory:

```
pip3 install coverage
python3 run_tests.py
```

## Documentation
The documentation is publically available at https://shtk.readthedocs.org

To build the documentation from source, run the following which generates
documention in ./docs/html/index.html

```
cd docs
make html
cd ..
```

## Examples

More examples can be found in the source code's examples directory (these are
still under construction).

```
import shtk

sh = shtk.Shell.get_shell()

ls = sh.command('ls')
wc = sh.command('wc')
cat = sh.command('cat')
sleep = sh.command('sleep')
touch = sh.command('touch')

#touch tmp.txt
sh(touch('tmp.txt'))

#cat tmp.txt
sh(cat('tmp.txt'))

#cat tmp.txt | wc -l
sh(cat('tmp.txt') | wc('-l'))

#wc -l < tmp.txt
sh(wc('-l').stdin('tmp.txt'))

#ls | wc -l > /dev/null
sh(ls | wc('-l').stdout(None))

#ls | wc -l > tmp.txt
sh(ls | wc('-l').stdout('tmp.txt'))

#ls | wc -l >> tmp.txt
sh(ls | wc('-l').stdout('tmp.txt', mode='a'))

with open('test_file1.txt', 'w') as fout:
    msg = """
abc
xyz
The quick brown fox jumps over the lazy dog.
""".lstrip()
    print(msg, file=fout)

sh(
    ls('test_file2.txt').stderr('/dev/null'),
    ls('test_file1.txt'),
    exceptions=False
)

sh(
    ls('test_file1.txt')
)

#echo $(ls | wc -l)
print(sh.evaluate(ls | wc('-l')).strip())
```

