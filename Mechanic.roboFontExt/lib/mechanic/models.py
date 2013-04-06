import os, shutil, errno, sys, re, plistlib, fnmatch
from glob import glob

import requests
from zipfile import ZipFile

from mojo.extensions import ExtensionBundle
from mechanic.helpers import Version

class Extension(object):
    """Facilitates loading the configuration from and updating extensions."""
    def __init__(self, name=None, path=None):
        self.config = {}
        self.configured = False
        self.name = name
        self.bundle = ExtensionBundle(name=self.name, path=path)
        self.path = self.bundle.bundlePath()
        self.configure()

    def configure(self):
        """Set config attribute from info.plist contents."""
        self.configPath = os.path.join(self.path, 'info.plist')
        if(os.path.exists(self.configPath)):
            self.config = plistlib.readPlist(self.configPath)
            if 'repository' in self.config:
                extension_path = self.config['extensionPath'] if hasattr(self.config, 'extensionPath') else None
                self.remote = GithubRepo(self.config['repository'], 
                                         name=self.name,
                                         extension_path=extension_path)
                self.configured = True
            
    def update(self, extension_path=None):
        """Download and install the latest version of the extension."""
        if extension_path is None:
            extension_path = self.remote.download()
        
        new_extension = Extension(path=extension_path)

        self.bundle.deinstall()
        new_extension.bundle.install()
        
    def is_current_version(self):
        """Return if extension is at curent version"""
        if not self.remote.version:
            self.remote.get()
        return Version(self.remote.version) <= Version(self.config['version'])

class GithubRepo(object):
    
    tags_url = "https://api.github.com/repos/%(repo)s/tags"
    zip_url = "https://github.com/%(repo)s/archive/master.zip"
    plist_url = "https://raw.github.com/%(repo)s/master/%(plist_path)s"

    def __init__(self, repo, name=None, extension_path=None):
        self.repo = repo
        self.extension_path = extension_path
        self.username, self.name = repo.split('/')
        if name is not None:
            self.name = name
        self.version = None
        
    def get(self):
        """Return the version and location of remote extension."""
        if self.extension_path:
            plist_path = os.path.join(self.extension_path, 'info.plist')
            plist_url = self.plist_url % {'repo': self.repo, 'plist_path': plist_path}
            response = requests.get(plist_url)
            plist = plistlib.readPlistFromString(response.content)
            self.zip = self.zip_url % {'repo': self.repo}
            self.version = plist['version']
        elif self._get_tags():
            self.tags.sort(key=lambda s: list(Version(s["name"])), reverse=True)
            self.zip = self.tags[0]['zipball_url']
            self.version = self.tags[0]['name']
        else:
            self.zip = self.zip_url % {'repo': self.repo}
    
    def setup_download(self):
        """Clear extension tmp dir, open download stream and local file."""
        if not hasattr(self,'data'):
            self.get()
        self.tmp_path = os.path.join("/", "tmp", "Mechanic", self.repo)
        self._flush_tmp_path()
        filepath = os.path.join(self.tmp_path, "%s.zip" % os.path.basename(self.zip))
        self.file = open(filepath, "wb")
        self.stream = requests.get(self.zip, stream=True)
        self.stream_content = self.stream.iter_content(chunk_size=8192)
        self.content_length = self.stream.headers['content-length']
    
    def extract_file(self):
        """Extract downloaded zip file and return extension path."""
        zip_file = ZipFile(self.file.name)
        zip_file.extractall(self.tmp_path)
        os.remove(self.file.name)
        
        folder = os.path.join(self.tmp_path, os.listdir(self.tmp_path)[0])
        
        if self.extension_path:
            return os.path.join(folder, self.extension_path)
        else: 
            matches = []
            for root, dirnames, filenames in os.walk(self.tmp_path):
                for dirname in fnmatch.filter(dirnames, '*.roboFontExt'):
                    matches.append(os.path.join(root, dirname))
        
            exact = fnmatch.filter(matches, '*%s.roboFontExt' % self.name)
            return (exact and exact[0]) or matches[0]
    
    def download(self):
        """Download remote version of extension."""
        self.setup_download()
        for content in self.stream_content:
            self.file.write(content)
        self.file.close()
        return self.extract_file()

    def _get_tags(self):
        response = requests.get(self.tags_url % {'repo': self.repo})
        response.raise_for_status()
        self.tags = response.json()
        return self.tags

    def _flush_tmp_path(self):
        if os.path.exists(self.tmp_path):
            shutil.rmtree(self.tmp_path)
        mkdir_p(self.tmp_path)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise
