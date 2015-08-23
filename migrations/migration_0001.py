from . import MigrationBase


class Migration(MigrationBase):
    DB_VERSION = 1

    def forward(self):
        self.root._db_version = self.DB_VERSION
