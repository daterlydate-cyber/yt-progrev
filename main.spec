# main.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gui/styles.qss', 'gui'),
        ('config.example.json', '.'),
    ],
    hiddenimports=[
        # selenium — динамически загружаемые подмодули
        'selenium.webdriver.common.action_chains',
        'selenium.webdriver.common.actions',
        'selenium.webdriver.common.actions.action_builder',
        'selenium.webdriver.common.actions.key_input',
        'selenium.webdriver.common.actions.mouse_button',
        'selenium.webdriver.common.actions.pointer_input',
        'selenium.webdriver.common.actions.wheel_input',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.common.options',
        'selenium.webdriver.common.proxy',
        'selenium.webdriver.common.timeouts',
        'selenium.webdriver.common.utils',
        'selenium.webdriver.common.desired_capabilities',
        'selenium.webdriver.common.service',
        'selenium.webdriver.support',
        'selenium.webdriver.support.expected_conditions',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.wait',
        'selenium.webdriver.support.select',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.chrome.webdriver',
        'selenium.common.exceptions',
        # undetected_chromedriver
        'undetected_chromedriver',
        'undetected_chromedriver.options',
        'undetected_chromedriver.patcher',
        'undetected_chromedriver.dprocess',
        # PyQt5
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.sip',
        # schedule
        'schedule',
        # fake_useragent
        'fake_useragent',
        # python-dotenv
        'dotenv',
        # стандартные модули
        'pathlib',
        'logging.handlers',
    ],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YT-Progrev',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
