from shtk import Shell, Job, PipeStreamFactory
import os
import sys
import time

class Parted:
    def __init__(self, img_path):
        self.img_path = img_path
        
        sh = Shell.get_shell()
        parted = sh.command('parted')

        psf_input = PipeStreamFactory(flags=os.O_NONBLOCK)
        psf_output = PipeStreamFactory(flags=os.O_NONBLOCK)

        self.job = sh(parted(self.img_path).stdin(psf_input).stdout(psf_output), wait=False)[0]
        time.sleep(1)

        reader = self.job.pipeline.stdout_stream.reader()
        
        time.sleep(0.1)

        self._write('unit s\n')
        print(self._read())

    def _write(self, msg):
        writer = self.job.pipeline.stdin_stream.writer()
        return os.write(writer.fileno(), msg.encode('utf-8'))

    def _read(self):
        reader = self.job.pipeline.stdout_stream.reader()

        result = ""
        while 1:
            result += os.read(reader.fileno(), 1024*1024).decode('utf-8')
            if result.endswith("(parted) "):
                break
            time.sleep(0.0001)

        return result

    def __del__(self):
        if hasattr(self, 'job') and self.job:
            writer = self.job.pipeline.stdin_stream.close()
            reader = self.job.pipeline.stdout_stream.close()

    def describe(self):
        self._write("p\n")
        time.sleep(0.1)
        return self._read()

    def create_image(self, byte_size):
        sh = Shell.get_shell()
        truncate = sh.command('truncate')
        sh(
            truncate('-s', f">{int(byte_size)}", self.img_path)
        )



with Shell() as sh:
    xxd = sh.command('xxd')
    head = sh.command('head')
    wc = sh.command('wc')
    
    parted = Parted(sys.argv[1])
    print(parted.describe())
