import shtk

sh = shtk.Shell.get_shell()

ls = sh.command('ls')
wc = sh.command('wc')
cat = sh.command('cat')
sleep = sh.command('sleep')

"cat tmp.txt"
sh(cat('tmp.txt'))

"cat tmp.txt | wc -l"
sh(cat('tmp.txt') | wc('-l'))

"wc -l < tmp.txt"
sh(wc('-l').stdin('tmp.txt'))

"ls | wc -l > /dev/null"
sh(ls | wc('-l').stdout(None))

"ls | wc -l > tmp.txt"
sh(ls | wc('-l').stdout('tmp.txt'))

"ls | wc -l >> tmp.txt"
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
    shtk.or_(
        ls('test_file2.txt').stderr('/dev/null'),
        ls('test_file1.txt')
    )
)

sh(
    ls('test_file1.txt')
)

"echo $(ls | wc -l)"
print(sh.evaluate(ls | wc('-l')).strip())
