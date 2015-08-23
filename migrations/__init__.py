import transaction


class MigrationBase(object):
    def __init__(self, root):
        self.root = root

    @classmethod
    def is_applicable(cls, root):
        return getattr(root, '_db_version', 0) < cls.DB_VERSION

    def set_version(self):
        self.root._db_version = self.DB_VERSION

    def apply(self):
        transaction.begin()
        self.forward()
        self.set_version()
        transaction.commit()
