# Troubleshooting Guide

Common issues and solutions for OpenAudit Platform users.

---

## File Upload Issues

### Problem: File upload fails or shows validation errors

**Possible Causes:**
- Missing required columns
- Incorrect file format
- Corrupted file
- File size too large

**Solutions:**
1. Verify your file includes all required columns: Tracking Number, Carrier, Service Type, Date, Billed Amount, Weight, Zone
2. Ensure file is in Excel (.xlsx, .xls) or CSV (.csv) format
3. Check that dates are properly formatted (MM/DD/YYYY or YYYY-MM-DD)
4. Remove any merged cells or complex formatting
5. Try saving the file with a new name and re-uploading
6. Split large files into smaller batches (under 10,000 rows recommended)

### Problem: Data appears incorrect after upload

**Solutions:**
1. Check that column headers match exactly (case-sensitive)
2. Verify data types (numbers in numeric columns, dates in date columns)
3. Remove any empty rows at the top of your spreadsheet
4. Ensure tracking numbers don't have leading/trailing spaces
5. Preview the data before running audit to verify accuracy

---

## Audit Issues

### Problem: Audit takes too long to complete

**Solutions:**
1. Check your file size - very large files may take longer
2. Refresh the page and try again
3. Split large datasets into monthly batches
4. Close other browser tabs to free up memory

### Problem: Audit finds no errors

**Possible Reasons:**
- Your shipments may genuinely have no billing errors (rare but possible)
- Data may be incomplete or incorrectly formatted
- Missing key columns needed for error detection

**Solutions:**
1. Verify all required columns are present and populated
2. Check that service types and carriers are spelled correctly
3. Ensure dates are within the refund eligibility window (typically 60-90 days)
4. Review a few tracking numbers manually to confirm data accuracy

### Problem: Audit results seem inaccurate

**Solutions:**
1. Verify your uploaded data is complete and accurate
2. Check that service types match actual services used
3. Ensure zones and weights are correct
4. Review specific error types that seem questionable
5. Cross-reference with actual carrier invoices

---

## Claim Submission Issues

### Problem: Email draft doesn't open automatically

**Possible Causes:**
- Browser settings blocking popups
- No default email client configured
- Browser compatibility issues

**Solutions:**
1. Check browser popup settings and allow popups for this site
2. Set up a default email client (Outlook, Mail, etc.)
3. Try a different browser (Chrome, Firefox, Edge)
4. Manually copy the claim information from the screen
5. Use the downloaded Excel file to create your own email

### Problem: Excel file doesn't download

**Solutions:**
1. Check browser download settings
2. Disable popup blockers temporarily
3. Clear browser cache and cookies
4. Try downloading in a different browser
5. Check your Downloads folder - file may have downloaded without notification

### Problem: FedEx redirect doesn't work

**Solutions:**
1. Allow popups for this site in browser settings
2. Manually navigate to FedEx website after downloading the Excel file
3. Clear browser cache and try again
4. Check that you have JavaScript enabled
5. Try using a different browser

---

## Dashboard Issues

### Problem: Charts not displaying or showing errors

**Solutions:**
1. Ensure you've run an audit first - charts require data
2. Refresh the page
3. Clear browser cache
4. Try a different browser
5. Check that JavaScript is enabled
6. Ensure you have a stable internet connection

### Problem: Data appears incomplete on dashboard

**Solutions:**
1. Verify the audit completed successfully
2. Check that all shipments were processed
3. Refresh the page to reload data
4. Re-run the audit if necessary

---

## Q&A Issues

### Problem: Questions don't load or page shows errors

**Solutions:**
1. Check your internet connection
2. Be more specific with your questions
3. Provide context in your query (e.g., "For FedEx Ground shipments...")
4. Try rephrasing your question
5. Refresh the page and try again

### Problem: Page takes too long to load

**Solutions:**
1. Simplify your question
2. Ask one question at a time instead of multiple
3. Check internet connection speed
4. Refresh page if waiting more than 30 seconds

---

## Contract Review Issues

### Problem: Contract upload fails

**Solutions:**
1. Verify file format is supported (PDF, XLSX, DOCX)
2. Ensure file size is under 10MB
3. Check that the file isn't password-protected
4. Try converting to a different supported format
5. Remove any special formatting or macros from Excel files

### Problem: Analysis results seem incomplete

**Solutions:**
1. Ensure your contract document is clearly formatted
2. Upload a higher quality scan if using a PDF
3. Provide a structured contract file with clear sections
4. Try uploading individual pages or sections separately

---

## General Browser Issues

### Problem: Page not loading or freezing

**Solutions:**
1. Hard refresh: Press Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
2. Clear browser cache and cookies
3. Close unnecessary browser tabs
4. Restart your browser
5. Try a different browser
6. Check internet connection

### Problem: Features not working as expected

**Solutions:**
1. Update your browser to the latest version
2. Disable browser extensions temporarily
3. Enable JavaScript in browser settings
4. Clear browser cache
5. Try using an incognito/private window

### Recommended Browsers:
- Google Chrome (latest version)
- Mozilla Firefox (latest version)
- Microsoft Edge (latest version)
- Safari (latest version for Mac users)

---

## Data and Results Issues

### Problem: Results from previous audit disappeared

**Solutions:**
1. Re-upload your file and run the audit again
2. The system may have timed out - refresh and re-run
3. Check that you're logged into the same session
4. Export and save results immediately after each audit

### Problem: Can't find specific tracking number

**Solutions:**
1. Use the search function in the detailed findings table
2. Check for typos in the tracking number
3. Verify the tracking number was in your original upload
4. Filter by carrier or date to narrow results
5. Re-run the audit if necessary

---

## Performance Issues

### Problem: App running slowly

**Solutions:**
1. Close unnecessary browser tabs and applications
2. Clear browser cache
3. Use a wired internet connection instead of WiFi
4. Process smaller batches of data
5. Restart your browser
6. Check system memory usage

---

## Still Need Help?

If your issue isn't resolved by these solutions:

1. **Document the issue:**
   - What were you trying to do?
   - What happened instead?
   - What error messages did you see?
   - What browser and version are you using?

2. **Try basic troubleshooting:**
   - Restart browser
   - Clear cache
   - Try different browser
   - Check internet connection

3. **Contact Support:**
   - Provide detailed description of the issue
   - Include screenshots if possible
   - Share any error messages
   - Specify which section of the app you were using

---

## Prevention Tips

### To avoid issues:
1. Keep your browser updated
2. Use supported file formats only
3. Verify data quality before upload
4. Save/export results after each audit
5. Keep original invoice files as backup
6. Use stable internet connection
7. Close unnecessary applications when processing large files
8. Regularly clear browser cache

---

**Note:** If you continue to experience technical difficulties, please contact your system administrator or support team with specific details about the problem.
