class StorageError(RuntimeError):
    pass


class StorageConfigurationError(StorageError):
    pass


class StorageObjectNotFoundError(StorageError):
    pass


class StorageOperationError(StorageError):
    pass
