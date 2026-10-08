# Mobile API authentication

All account routes use the versioned API under `/api/v1/users`.

## Telegram Mini App

The client must send Telegram's raw `Telegram.WebApp.initData` string without
editing or reconstructing it. The server verifies its signature and freshness.
The `telegram_id` must match the user ID inside that signed data.

```json
{
  "telegram_id": 123456789,
  "init_data": "<raw Telegram.WebApp.initData>"
}
```

Do not send `initDataUnsafe` as the authentication proof. It may be used to
display a name in the client, but only the signed `init_data` is verified.
Direct login or registration with a Telegram ID alone returns `401`.

## Phone/password accounts

Use `POST /api/v1/users/login`:

```json
{
  "phone_number": "0912345678",
  "password": "<account password>"
}
```

Phone login without a password is rejected. On success, store the returned
`access_token` securely and send it as `Authorization: Bearer <token>`.

## Registration

`POST /api/v1/users/register` requires signed Telegram Mini App data in live
environments. The submitted `telegram_id` must match the signed user ID.
Phone/password customer registration is available through the web registration
flow at `/app/register`.

## Password recovery

1. Call `POST /api/v1/users/password-reset/request` with
   `{"phone_number":"0912345678"}`.
2. If an active account exists and SMS delivery is configured, a six-digit code
   is sent. The response is intentionally the same for registered and
   unregistered phone numbers.
3. Call `POST /api/v1/users/password-reset/confirm` with
   `phone_number`, `otp`, `new_password`, and `confirm_password`.

Codes expire after five minutes, can be used once, and allow at most five
verification attempts. Requests are limited to three per phone number per hour.
The SMS provider must be configured before customers can receive codes.
