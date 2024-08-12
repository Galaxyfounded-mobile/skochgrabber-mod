import random
import string
import base64
import codecs
import argparse
import os
import sys
from textwrap import wrap
from lzma import compress
from marshal import dumps

def printerr(data):
    print(data, file=sys.stderr)

class SkochOBF:
    def __init__(self, code, outputpath):
        self.code = code.encode()
        self.outpath = outputpath
        self.varlen = 4
        self.vars = {}

        self.fake_code()
        self.marshal()
        self.fake_code()
        self.encrypt1()
        self.fake_code()
        self.encrypt2()
        self.fake_code()
        self.finalize()

    def generate(self, name):
        if name not in self.vars:
            self.vars[name] = "_" + "".join(random.choices(string.ascii_letters + string.digits, k=self.varlen))
            self.varlen += 1
        return self.vars[name]

    def encryptstring(self, string, config=None, func=False):
        if config is None:
            config = {}
        b64 = b"base64"
        b64decode = b"b64decode"
        __import__ = config.get("__import__", "__import__")
        getattr = config.get("getattr", "getattr")
        bytes = config.get("bytes", "bytes")
        eval = config.get("eval", "eval")

        if not func:
            return (f'{getattr}({__import__}({bytes}({list(b64)}).decode()), '
                    f'{bytes}({list(b64decode)}).decode())'
                    f'({bytes}({list(base64.b64encode(string.encode()))})).decode()')
        else:
            attrs = string.split(".")
            base = self.encryptstring(attrs[0], config)
            newattr = base
            for attr in attrs[1:]:
                newattr = f'{getattr}({eval}({newattr}), {self.encryptstring(attr, config)})'
            return newattr

    def encryptor(self, config):
        return lambda string, func=False: self.encryptstring(string, config, func)

    def compress(self):
        self.code = compress(self.code)

    def marshal(self):
        self.code = dumps(compile(self.code, "<string>", "exec"))

    def fake_code(self):
        fake_snippets = [
            'exec("".join(chr(i) for i in [112, 114, 105, 110, 116, 40, 34, 72, 97, 99, 107, 101, 100, 33, 34, 41]))',
            'for i in range(10):\n    pass',
            'try:\n    random.choice([1, 2, 3])\nexcept:\n    pass'
        ]
        self.code += random.choice(fake_snippets).encode()

    def encrypt1(self):
        code = base64.b64encode(self.code).decode()
        partlen = len(code) // 4
        code = wrap(code, partlen)
        var1, var2, var3, var4 = [self.generate(name) for name in ("a", "b", "c", "d")]

        init = [
            f'{var1}="{codecs.encode(code[0], "rot13")}"',
            f'{var2}="{code[1]}"',
            f'{var3}="{code[2][::-1]}"',
            f'{var4}="{code[3]}"'
        ]
        random.shuffle(init)
        init_code = ";".join(init)
        self.code = (f'{init_code};__import__({self.encryptstring("builtins")}).exec('
                     f'__import__({self.encryptstring("marshal")}).loads('
                     f'__import__({self.encryptstring("base64")}).b64decode('
                     f'__import__({self.encryptstring("codecs")}).decode({var1}, '
                     f'__import__({self.encryptstring("base64")}).b64decode("{base64.b64encode(b"rot13").decode()}").decode())+{var2}+{var3}[::-1]+{var4})))').encode()

    def encrypt2(self):
        self.compress()
        varnames = [self.generate(name) for name in "efghijklm"]

        conf = {
            "getattr": varnames[3],
            "eval": varnames[2],
            "__import__": varnames[7],
            "bytes": varnames[8]
        }
        encryptstring = self.encryptor(conf)

        self.code = (f'# https://dsc.gg/skochworld\n'
                     f'{varnames[2]} = eval({self.encryptstring("eval")});'
                     f'{varnames[3]} = {varnames[2]}({self.encryptstring("getattr")});'
                     f'{varnames[7]} = {varnames[2]}({self.encryptstring("__import__")});'
                     f'{varnames[8]} = {varnames[2]}({self.encryptstring("bytes")});'
                     f'{varnames[4]} = lambda {varnames[6]}: {varnames[2]}({encryptstring("compile")})({varnames[6]}, {encryptstring("<string>")}, {encryptstring("exec")});'
                     f'{varnames[0]} = {self.code.decode()}\n'
                     f'{varnames[1]} = {encryptstring("__import__(\'builtins\').list", func=True)}({varnames[0]})\n'
                     f'try:\n'
                     f'    {encryptstring("__import__(\'builtins\').exec", func=True)}({varnames[4]}({encryptstring("__import__(\'lzma\').decompress", func=True)}({varnames[8]}({varnames[1]}))))\n'
                     f'except {encryptstring("__import__(\'lzma\').LZMAError", func=True)}:...').encode()

    def finalize(self):
        os.makedirs(os.path.dirname(self.outpath), exist_ok=True)
        with open(self.outpath, "w") as e:
            e.write(self.code.decode())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog=sys.argv[0], description="Obfuscates a Python program to make it harder to read")
    parser.add_argument("FILE", help="Path to the file containing the Python code")
    parser.add_argument("-o", type=str, help='Output file path [Default: "Obfuscated_<FILE>.py"]', dest="path")
    args = parser.parse_args()

    if not os.path.isfile(sourcefile := args.FILE):
        printerr(f'No such file: "{args.FILE}"')
        os._exit(1)
    elif not sourcefile.endswith((".py", ".pyw")):
        printerr('The file does not have a valid Python script extension!')
        os._exit(1)

    if args.path is None:
        args.path = "Obfuscated_" + os.path.basename(sourcefile)

    with open(sourcefile) as sourcefile:
        code = sourcefile.read()

    SkochOBF(code, args.path)
