class ShopError(Exception):
    """Base class for all shop errors."""
    pass


class ProductNotFoundError(ShopError):
    pass


class InvalidProductError(ShopError):
    pass


class DuplicateProductError(ShopError):
    pass


class OutOfStockError(ShopError):
    pass


class InventoryError(ShopError):
    pass


class EmptyCartError(ShopError):
    pass


class InvalidPaymentError(ShopError):
    pass


class InsufficientBalanceError(ShopError):
    pass


class DatabaseConnectionError(ShopError):
    pass


class CorruptedDataError(ShopError):
    pass


class AuthenticationError(ShopError):
    pass


class UnauthorizedAccessError(ShopError):
    pass
