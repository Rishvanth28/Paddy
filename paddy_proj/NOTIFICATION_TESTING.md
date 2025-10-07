# Testing Notifications in admin_product_subscription.html

## How to Test Notifications

### Option 1: Uncomment Test Notifications in the Code
In `admin_product_subscription.html`, find this section near the end of the file:

```javascript
// Test Notifications (remove these in production)
// Uncomment the lines below to test notifications
/*
setTimeout(() => {
    showNotification('success', 'Subscription Activated!', 'Your Rice Orders subscription has been successfully activated. You can now create rice orders for your customers.');
}, 1000);

setTimeout(() => {
    showNotification('info', 'Payment Processing', 'Your payment of ₹300 is being processed. You will receive a confirmation email shortly.');
}, 2000);

setTimeout(() => {
    showNotification('warning', 'Subscription Expiring Soon', 'Your Paddy Orders subscription will expire in 3 days. Renew now to avoid service interruption.');
}, 3000);

setTimeout(() => {
    showNotification('error', 'Payment Failed', 'Unable to process your payment. Please check your payment method and try again.');
}, 4000);
*/
```

**To test:** Remove the `/*` and `*/` comment markers to enable the test notifications.

### Option 2: Use Browser Console
Open the page, press F12 to open Developer Tools, go to Console tab, and run:

```javascript
// Success notification
showNotification('success', 'Subscription Activated!', 'Your Rice Orders subscription has been successfully activated.');

// Info notification
showNotification('info', 'Payment Processing', 'Your payment is being processed. Please wait...');

// Warning notification
showNotification('warning', 'Subscription Expiring', 'Your subscription will expire in 3 days.');

// Error notification
showNotification('error', 'Payment Failed', 'Unable to process payment. Please try again.');
```

## Sample Notification Messages

### Success Messages
- **Title:** "Subscription Activated!"
  **Message:** "Your Rice Orders subscription has been successfully activated. You can now create rice orders for your customers."

- **Title:** "Payment Successful!"
  **Message:** "Your payment of ₹300 has been processed successfully. Subscription is now active."

- **Title:** "Products Updated!"
  **Message:** "Your product subscriptions have been updated successfully."

### Error Messages
- **Title:** "Payment Failed!"
  **Message:** "Unable to process your payment. Please check your payment method and try again."

- **Title:** "Subscription Error!"
  **Message:** "Unable to activate subscription. Please contact support if the issue persists."

- **Title:** "Selection Required!"
  **Message:** "Please select at least one product before proceeding to checkout."

### Warning Messages
- **Title:** "Subscription Expiring Soon!"
  **Message:** "Your Paddy Orders subscription will expire in 3 days. Renew now to avoid service interruption."

- **Title:** "Payment Pending!"
  **Message:** "Your previous payment is still pending. Please complete it before creating a new subscription."

- **Title:** "Limited Access!"
  **Message:** "You currently have limited access. Subscribe to unlock all features."

### Info Messages
- **Title:** "Payment Processing"
  **Message:** "Your payment of ₹300 is being processed. You will receive a confirmation email shortly."

- **Title:** "Subscription Active"
  **Message:** "You currently have 2 active product subscriptions. Select more to expand your access."

- **Title:** "Price Updated"
  **Message:** "The total subscription cost is ₹300 per month for the selected products."

## Notification Types and Colors

1. **Success** (Green - #22c55e)
   - Subscription activated
   - Payment successful
   - Products updated

2. **Error** (Red - #ef4444)
   - Payment failed
   - Subscription error
   - Server errors

3. **Warning** (Orange - #f59e0b)
   - Expiring subscriptions
   - Pending payments
   - Limited access alerts

4. **Info** (Blue - #3b82f6)
   - Processing status
   - General information
   - Price updates

## Features

✅ Auto-dismiss after 5 seconds
✅ Manual close button
✅ Smooth slide-in animation
✅ Multiple notifications stack
✅ Responsive design
✅ Matches admin theme
✅ Inter font family
✅ Icon-based visual indicators
