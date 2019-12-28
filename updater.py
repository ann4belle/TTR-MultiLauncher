"""Updates TTR"""
import json
import sys
import hashlib
import pathlib
from multiprocessing.pool import ThreadPool
import requests

MANIFEST_URL = 'http://s3.amazonaws.com/cdn.toontownrewritten.com/content/patchmanifest.txt'
PATCH_URL = 'http://s3.amazonaws.com/download.toontownrewritten.com/patches/'

class TTRUpdater():
    """Updates TTR installation at the indicated folder."""
    def __init__(self, installdir):
        self.do_update(installdir)

    def build_update_list(self, installdir):
        """Builds the list of files requiring an update based on the current operating system."""
        files = []
        ttrdir = pathlib.Path(installdir)
        if not ttrdir.is_dir():
            print('Error - ' + repr(installdir) + ' is not a directory or does not exist.')
            return
        manifest = json.loads(requests.get(MANIFEST_URL).content)
        for file in manifest.keys():
            hasher = hashlib.sha1()
            if not (ttrdir / file).exists():
                if sys.platform in manifest[file]['only']:
                    files.append((installdir + '/' + file, PATCH_URL + manifest[file]['dl']))
                continue
            hasher.update((ttrdir / file).open('rb').read())
            if manifest[file]['hash'] != hasher.hexdigest():
                files.append((installdir + '/' + file, PATCH_URL + manifest[file]['dl']))
        return files

    def download(self, url):
        """Downloads and saves the file pointed at by url"""
        path, uri = url
        online_file = requests.get(uri, stream=True)
        if online_file.status_code == 200:
            with open(path, 'wb') as file:
                for chunk in online_file:
                    file.write(chunk)
        else:
            print('Error - ' + uri + ' did not return 200 OK.')
        return path

    def do_update(self, installdir):
        """Main function - automates downloading of required files using multithreading."""
        urls = self.build_update_list(installdir)
        if not len(urls) > 0:
            return
        ThreadPool(len(urls)).imap_unordered(self.download, urls)
