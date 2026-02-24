# Fix: Phone Conversation "Email Delivery Issue" (Freescout v1.8.206)

**Reported:** 2026-02-24
**Affected file:** `app/Listeners/SendReplyToCustomer.php` line 76
**Severity:** Medium — affects all phone conversations where the customer has an email address
**Status:** Reported to Freescout helpdesk forum, pending upstream guidance

---

## Symptom

When creating or replying to a **phone conversation** (type=2) for a customer that has an email address on file, Freescout shows "email delivery issue". The conversation and thread are saved correctly in the database, but the reply email is never dispatched.

## Error

```
ErrorException: Undefined array key 0
  at app/Listeners/SendReplyToCustomer.php:76
```

**Laravel log:** `/var/www/freescout/storage/logs/laravel-YYYY-MM-DD.log`

## Root Cause

PR [#5199](https://github.com/freescout-help-desk/freescout/pull/5199) introduced code to handle replies sent to a different customer than the original. However, it does not check for an empty array before accessing index `[0]`.

Phone conversations store `to = NULL` in the `threads` table. When `getToArray()` is called on a NULL value, it returns an empty array `[]`. Accessing `[][0]` throws the error.

### Current code (line 76):

```php
if ($thread && ($customer_email = $thread->getToArray()[0]) && $customer_email != $main_customer_email) {
```

### Proposed fix:

```php
$to_array = $thread ? $thread->getToArray() : [];
if ($to_array && ($customer_email = $to_array[0]) && $customer_email != $main_customer_email) {
```

## Impact

- **2,374** total phone conversations in the database
- **211** (9%) have customers with email addresses — all affected by this bug
- **2,163** (91%) have customers without email — unaffected (early return at line 32)
- First occurrence in logs: **2026-02-18**
- ~15 errors between 2026-02-18 and 2026-02-24

## How to Apply (when approved)

1. Edit `/var/www/freescout/app/Listeners/SendReplyToCustomer.php`
2. Replace line 76 with the proposed fix above
3. Clear Laravel cache:
   ```bash
   cd /var/www/freescout
   php artisan cache:clear
   php artisan config:clear
   ```
4. No database migration needed
5. No Freescout restart needed (PHP-FPM picks up file changes)

## Verification

After applying the fix, create a phone conversation for a customer that has an email address. The "email delivery issue" warning should no longer appear, and the reply email should be dispatched normally.
