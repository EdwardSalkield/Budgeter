import os.path
import urwid

class FileBrowser():
    currentlocation = "/"

    def __init__(self, startdir):
        startdir = self.reformat(startdir)
        self.currentlocation = startdir

    def reformat(self, dirname):
        if dirname [-1] != '/':
            dirname += '/'
        return dirname

    def up(self):
        self.currentlocation = self.reformat(os.path.realpath(self.currentlocation + "../"))

    def cd(self, dirname):
        dirname = self.reformat(dirname)

        if os.path.exists(self.currentlocation + dirname):
            self.currentlocation += dirname

    def ls(self, ):
        for (dirpath, dirnames, filenames) in os.walk(self.currentlocation):
            return (dirnames, filenames)

    def pwd(self, ):
        return self.currentlocation
