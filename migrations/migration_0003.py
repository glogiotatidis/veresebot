from . import MigrationBase


class Migration(MigrationBase):
    DB_VERSION = 3

    def forward(self):
        self.root.stats['number_of_users'] = len(self.root.users)
        self.root.stats['number_of_tabs'] = len(self.root.tabs)
