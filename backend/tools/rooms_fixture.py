"""Только локальные тесты: настоящий источник с новой временной SQLite."""
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path


class RoomsFixture:
    def __init__(self, actor):
        self.actor = str(actor)
        self.process = None

    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='basework-rooms-synthetic-')
        try:
            return self.start()
        except Exception:
            self.__exit__()
            raise

    def start(self):
        self.directory = Path(self.temp.name)
        source = Path(os.environ['BASEWORK_ROOMS_TEST_SOURCE']).resolve(strict=True)
        python = source/'.venv/Scripts/python.exe'
        if not python.is_file():
            python = source/'.venv/bin/python'
        if not python.is_file() or not (source/'basework_bridge.py').is_file():
            raise RuntimeError('Нет установленного окружения источника для теста')
        self.key_file = self.directory/'bridge.key'
        self.key_file.write_bytes(os.urandom(32))
        self.bindings_file = self.directory/'bindings.json'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            self.port = sock.getsockname()[1]
        self.env = dict(os.environ, DATA_DIR=str(self.directory), HOST='127.0.0.1',PORT=str(self.port),DEV_MODE='1',
                        BASEWORK_BRIDGE_KEY_FILE=str(self.key_file), BASEWORK_BRIDGE_BINDINGS_FILE=str(self.bindings_file),
                        PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
        bootstrap = "import storage,json; storage.initialize(); u=storage.add_user('fixture','Вымышленный сотрудник','Synthetic-rooms-only-2026!',must_change=False); print(json.dumps({'id':u['id']}))"
        result = subprocess.run([str(python),'-B','-c',bootstrap],cwd=source,env=self.env,capture_output=True,timeout=30,check=True)
        self.native_id = json.loads(result.stdout)['id']
        self.bindings_file.write_text(json.dumps({'bindings':{self.actor:self.native_id}}))
        self.process = subprocess.Popen([str(python),'-B','server.py'],cwd=source,env=self.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError('Тестовый источник не запустился')
            try:
                with socket.create_connection(('127.0.0.1',self.port),timeout=.2):
                    self.url = f'http://127.0.0.1:{self.port}/api/basework'
                    return self
            except OSError:
                time.sleep(.05)
        raise RuntimeError('Тестовый источник не ответил')

    def __exit__(self,*args):
        if self.process is not None:
            self.process.terminate()
            self.process.wait(timeout=10)
        self.temp.cleanup()
