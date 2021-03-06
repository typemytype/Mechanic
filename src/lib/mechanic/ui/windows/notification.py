from AppKit import NSImage
from vanilla import ImageView, TextBox, Button

from mechanic import logger
from mechanic.threaded import ThreadedObject
from mechanic.ui import progress
from mechanic.ui.text import Text
from mechanic.storage import Storage
from mechanic.update import Update
from mechanic.ui.windows.base import BaseWindow
from mechanic.ui.windows.main import MechanicWindow


class UpdateNotificationWindow(BaseWindow):
    window_size = (520, 130)
    window_title = "Extension Updates"

    def __init__(self, updates):
        self.updates = updates

        if self.updates:
            self.create_image()

            self.w.title = TextBox((105, 20, -20, 20), self.title)

            self.w.explanation = TextBox((105, 45, -20, 50), self.explanation)

            self.w.updateButton = Button((-150, -40, 130, 20),
                                         "Install Updates",
                                         callback=self.do_update)
            self.w.cancelButton = Button((-255, -40, 90, 20),
                                         "Not Now",
                                         callback=self.cancel)
            self.w.showDetailsButton = Button((105, -40, 110, 20),
                                              "Show Details",
                                              callback=self.show_details)
            self.w.setDefaultButton(self.w.updateButton)

            self.w.open()

    def do_update(self, sender):
        self.update()
        self.w.close()

    @progress.each('updates')
    @progress.tick('repositoryWillDownload',
                   'Downloading {repository.repo}')
    @progress.tick('extensionWillInstall',
                   'Installing {extension.bundle.name}')
    def update(self):
        for extension in self.updates:
            extension.update()

    def show_details(self, sender):
        self.w.close()
        MechanicWindow().open('updates')

    def cancel(self, sender):
        self.w.close()

    def create_image(self):
        image = NSImage.imageNamed_("ExtensionIcon")
        self.w.image = ImageView((15, 15, 80, 80), scale='fit')
        self.w.image.setImage(imageObject=image)

    @property
    def title(self):
        text = "Updates are available for %d of your extensions."
        return Text.string(text=text % len(self.updates),
                           style="bold")

    @property
    def explanation(self):
        text = "If you don't want to update now, choose Extensions > Mechanic > Updates when you're ready to install."
        return Text.string(text=text, size=11)
