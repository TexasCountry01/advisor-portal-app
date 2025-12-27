# Windows PDF Generation Setup

## Problem
WeasyPrint requires GTK libraries that aren't included with Windows by default.

## Solution: Install GTK Runtime for Windows

### Step 1: Download GTK Runtime
1. Go to: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
2. Download the latest release (e.g., `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe`)

### Step 2: Install
1. Run the installer
2. **IMPORTANT:** During installation, check the box: "Set up PATH environment variable to include GTK+"
3. Install to default location: `C:\Program Files\GTK3-Runtime Win64`
4. Complete installation

### Step 3: Restart
1. Close VS Code completely
2. Close all PowerShell/Command Prompt windows
3. Reopen VS Code
4. Open a new terminal

### Step 4: Test Installation
```powershell
cd C:\Users\ProFed\workspace\advisor-portal-app
python test_weasyprint.py
```

You should see:
```
✓ WeasyPrint imported successfully!
✓ PDF generated successfully!
✓ Check test_output.pdf in the current directory
```

### Step 5: Test in Application
1. Restart Django server (if running)
2. Login and submit a case
3. Click the PDF button - it should now generate and display!

## Alternative Options

### Option 2: Use Docker (More Complex)
If you can't install GTK globally, run PDF generation in a Docker container:
```bash
docker run -v ${PWD}:/app python:3.12 bash -c "pip install weasyprint && python /app/generate_pdf.py"
```

### Option 3: Use Alternative Library (Less Quality)
Replace WeasyPrint with `xhtml2pdf` (works natively on Windows but lower quality):
```bash
pip install xhtml2pdf
```

## Troubleshooting

### "DLL load failed" error
- GTK wasn't added to PATH correctly
- Restart computer (sometimes required)
- Manually add to PATH: `C:\Program Files\GTK3-Runtime Win64\bin`

### "cannot load library 'gobject-2.0-0'" error  
- GTK not installed or installation incomplete
- Re-run installer and ensure PATH option is checked

### PDF still not generating
- Check Django logs for specific errors
- Ensure server was restarted after GTK installation
- Try the test script first to isolate the issue

## Production Note
On Linux production servers, GTK is already available via system packages:
```bash
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0
```

No additional setup needed on production!
