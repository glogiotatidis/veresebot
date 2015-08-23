import BTrees.OOBTree

from . import MigrationBase


class Migration(MigrationBase):
    DB_VERSION = 2

    def forward(self):
        self.root.last_update = 0
        self.root.tabs = BTrees.OOBTree.BTree()
        self.root.users = BTrees.OOBTree.BTree()
        self.root.stats = {'number_of_messages': 0}
