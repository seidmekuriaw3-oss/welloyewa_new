# ============================
# WOLLOYEWA STORE BOT - MOBILE API MODULE
# ============================
"""Mobile API support for push notifications, offline sync, and mobile features."""

from infrastructure.mobile_api.push_notifications.firebase import (
    FirebasePushNotifier,
    PushNotification,
    PushMessage,
    send_push_notification,
    send_bulk_push,
    register_device,
    unregister_device,
    DevicePlatform,
)
from infrastructure.mobile_api.offline_sync import (
    OfflineSyncManager,
    SyncQueue,
    SyncOperation,
    SyncStatus,
    queue_offline_operation,
    process_sync_queue,
    get_pending_sync_count,
    SyncConflictResolver,
)
from infrastructure.mobile_api.biometric_auth import (
    BiometricAuthManager,
    BiometricSession,
    BiometricType,
    create_biometric_session,
    verify_biometric,
    revoke_biometric_session,
    BiometricVerificationResult,
)
from infrastructure.mobile_api.qr_scanner_integration import (
    QRScannerIntegration,
    QRCodeData,
    QRCodeType,
    generate_qr_code,
    scan_qr_code,
    decode_qr_data,
    QRPaymentData,
    QRProductData,
)
from infrastructure.mobile_api.deep_linking_router import (
    DeepLinkRouter,
    DeepLinkHandler,
    DeepLinkData,
    DeepLinkType,
    register_deep_link_handler,
    handle_deep_link,
    generate_deep_link,
    parse_deep_link,
)

__all__ = [
    # Push Notifications
    "FirebasePushNotifier",
    "PushNotification",
    "PushMessage",
    "send_push_notification",
    "send_bulk_push",
    "register_device",
    "unregister_device",
    "DevicePlatform",
    # Offline Sync
    "OfflineSyncManager",
    "SyncQueue",
    "SyncOperation",
    "SyncStatus",
    "queue_offline_operation",
    "process_sync_queue",
    "get_pending_sync_count",
    "SyncConflictResolver",
    # Biometric Auth
    "BiometricAuthManager",
    "BiometricSession",
    "BiometricType",
    "create_biometric_session",
    "verify_biometric",
    "revoke_biometric_session",
    "BiometricVerificationResult",
    # QR Scanner
    "QRScannerIntegration",
    "QRCodeData",
    "QRCodeType",
    "generate_qr_code",
    "scan_qr_code",
    "decode_qr_data",
    "QRPaymentData",
    "QRProductData",
    # Deep Linking
    "DeepLinkRouter",
    "DeepLinkHandler",
    "DeepLinkData",
    "DeepLinkType",
    "register_deep_link_handler",
    "handle_deep_link",
    "generate_deep_link",
    "parse_deep_link",
]