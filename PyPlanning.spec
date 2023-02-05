# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

import sys
sitepackages = os.path.join(sys.prefix, 'Lib', 'site-packages')
guidata_images = os.path.join(sitepackages, 'guidata', 'images')
guidata_locale = os.path.join(sitepackages, 'guidata', 'locale', 'fr', 'LC_MESSAGES')

a = Analysis(['planning\\app.py'],
             pathex=[],
             binaries=[],
             datas=[
                    (guidata_images, 'guidata\\images'),
                    (guidata_locale, 'guidata\\locale\\fr\\LC_MESSAGES'),
                    ('planning\\data', 'planning\\data'),
                    ('planning\\locale\\fr\\LC_MESSAGES\\planning.mo', 'planning\\locale\\fr\\LC_MESSAGES'),
                    ],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='PyPlanning',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='planning\\data\\planning.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='PyPlanning')
