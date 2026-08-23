# Quick Reference: Editing Sales and Expenses

## How to Edit a Sale

1. Navigate to the **Sales** page from the dashboard
2. Find the sale you want to edit in the Daily Sales table
3. Click the **Edit** link in the Actions column
   - (Only visible if you have `edit_sales` permission or are an admin)
4. Modify the payment details:
   - Payment Method (Cash, Online, Split)
   - Discount Type (No Discount, Normal, Special)
   - Online Amount (for split payments)
5. Click **Save Sale** to update
6. You'll be redirected back to the Sales list with a success message

## How to Edit an Expense

1. Navigate to the **Expenses** page from the dashboard
2. Find the expense you want to edit in the Daily Expense History table
3. Click the **Edit** link in the Actions column
   - (Only visible if you have `edit_expense` permission or are an admin)
4. Modify the expense details:
   - Amount
   - Purpose
5. Click **Save Expense** to update
6. You'll be redirected back to the Expenses list with a success message

## Permission Management

To grant edit permissions to staff members:

1. Go to **Accounts** from the dashboard
2. Click **Edit** on the staff member's account
3. Under Permissions section, check:
   - **Edit Sales** - to allow editing sales
   - **Edit Expense** - to allow editing expenses
4. Click **Save Account**

## Important Notes

- Admin users can edit all sales and expenses by default
- Staff members need explicit permissions to edit
- Edits only affect the sale/expense details, not the items sold
- For item-level changes, you may need to delete and recreate the sale
- All changes are logged and can be tracked through the system

## Troubleshooting

**Edit button not visible?**
- Check if you have the required permission
- Ask an admin to grant you edit permissions via Accounts

**Cannot save changes?**
- Ensure all required fields are filled
- Check for validation errors (displayed in red)
- Verify you have permission to edit

**Changes not reflecting?**
- Refresh the page after saving
- Check if another user modified the record

---

For technical issues, refer to the main FIXES_SUMMARY.md file.