# ============================
# WOLLOYEWA STORE BOT - MOBILE API MODULE
# ============================
"""Mobile API support for push notifications, offline sync, and mobile features."""

from infrastructure.mobile_api.biometric_auth import (
    BiometricAuthManager,
    BiometricSession,
    BiometricType,
    BiometricVerificationResult,
    create_biometric_session,
    revoke_biometric_session,
    verify_biometric,
)
from infrastructure.mobile_api.deep_linking_router import (
    DeepLinkData,
    DeepLinkHandler,
    DeepLinkRouter,
    DeepLinkType,
    generate_deep_link,
    handle_deep_link,
    parse_deep_link,
    register_deep_link_handler,
)
from infrastructure.mobile_api.offline_sync import (
    OfflineSyncManager,
    SyncConflictResolver,
    SyncOperation,
    SyncQueue,
    SyncStatus,
    get_pending_sync_count,
    process_sync_queue,
    queue_offline_operation,
)
from infrastructure.mobile_api.push_notifications.firebase import (
    DevicePlatform,
    FirebasePushNotifier,
    PushMessage,
    PushNotification,
    register_device,
    send_bulk_push,
    send_push_notification,
    unregister_device,
)
from infrastructure.mobile_api.qr_scanner_integration import (
    QRCodeData,
    QRCodeType,
    QRPaymentData,
    QRProductData,
    QRScannerIntegration,
    decode_qr_data,
    generate_qr_code,
    scan_qr_code,
)

__all__ = [
    # Biometric Auth
    "BiometricAuthManager",
    "BiometricSession",
    "BiometricType",
    "BiometricVerificationResult",
    "DeepLinkData",
    "DeepLinkHandler",
    # Deep Linking
    "DeepLinkRouter",
    "DeepLinkType",
    "DevicePlatform",
    # Push Notifications
    "FirebasePushNotifier",
    # Offline Sync
    "OfflineSyncManager",
    "PushMessage",
    "PushNotification",
    "QRCodeData",
    "QRCodeType",
    "QRPaymentData",
    "QRProductData",
    # QR Scanner
    "QRScannerIntegration",
    "SyncConflictResolver",
    "SyncOperation",
    "SyncQueue",
    "SyncStatus",
    "create_biometric_session",
    "decode_qr_data",
    "generate_deep_link",
    "generate_qr_code",
    "get_pending_sync_count",
    "handle_deep_link",
    "parse_deep_link",
    "process_sync_queue",
    "queue_offline_operation",
    "register_deep_link_handler",
    "register_device",
    "revoke_biometric_session",
    "scan_qr_code",
    "send_bulk_push",
    "send_push_notification",
    "unregister_device",
    "verify_biometric",
]
