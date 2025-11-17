#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test wkhtmltopdf directly to see if issue is conversion
"""
import subprocess
import os

# Read the HTML file
html_path = '/tmp/test_liquidacion.html'
pdf_path = '/tmp/test_liquidacion_direct.pdf'

print("=== Testing wkhtmltopdf Direct Conversion ===")
print(f"Input: {html_path}")
print(f"Output: {pdf_path}")

if os.path.exists(html_path):
    # Test basic wkhtmltopdf command
    cmd = [
        '/usr/local/bin/wkhtmltopdf',
        '--page-size', 'Letter',
        '--orientation', 'Portrait',
        html_path,
        pdf_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(f"\nReturn code: {result.returncode}")
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")

    if os.path.exists(pdf_path):
        size = os.path.getsize(pdf_path)
        print(f"\n✅ PDF created: {pdf_path}")
        print(f"   Size: {size} bytes")
    else:
        print(f"\n❌ PDF not created!")
else:
    print(f"❌ HTML file not found: {html_path}")
