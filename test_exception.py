import shtk

sh = shtk.Shell()

ls = sh.command('ls')
wc = sh.command('wc')
cat = sh.command('cat')
sleep = sh.command('sleep')

sh(cat('/nonexistent.txt'))
