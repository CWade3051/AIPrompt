# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None

a = Analysis(
    ['AIPrompt.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],  # Include assets directory
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.scrolledtext'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform.startswith('win'):
    # Windows - create single file executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='AIPrompt',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icons/icon.ico',
        onefile=True
    )
else:
    # macOS - create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='AIPrompt',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,  # Enable argv emulation for macOS
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icons/icon.ico',
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='AIPrompt'
    )
    
    # Create the .app bundle for macOS
    app = BUNDLE(
        coll,
        name='AIPrompt.app',
        icon='assets/icons/icon.icns',
        bundle_identifier='com.aiprompt.app',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '10.13.0',
            'NSAppleEventsUsageDescription': 'AIPrompt needs to access Apple Events to function properly.',
        },
    )
