import sys
import pathlib
import inspect

import_path = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(import_path))
import shtk
assert import_path in pathlib.Path(shtk.__file__).parents

def print_header(header, underline):
    print(header)
    print(underline * len(header))
    print("")


print_header("shtk package", "=")

for content_name in dir(shtk):
    if not content_name.startswith("_"):
        content = getattr(shtk, content_name)
        print_header(f"shtk.{content_name}", underline='-')

        if inspect.ismodule(content):
            print(f".. automodule:: shtk.{content_name}")
        elif inspect.isclass(content):
            print(f".. autoclass:: shtk.{content_name}")
        else:
            raise RuntimeError(f"Invalid type for content '{content_name}': {type(content)}")

        print("\t:members:")
        print("\t:undoc-members:")
        print("\t:show-inheritance:")
        print("\t:inherited-members:")
        print("")

