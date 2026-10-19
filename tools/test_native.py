#!/usr/bin/env python3
"""Compile native plugin and exercise direct SIP without Android or external calls."""
import os
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
sdk=Path(os.environ['ANDROID_HOME'])
platforms=sorted(sdk.glob('platforms/*/android.jar'))
if not platforms: raise SystemExit('Install an Android SDK platform and set ANDROID_HOME')
java=Path(os.environ['JAVA_HOME'])/'bin'
exe='.exe' if os.name=='nt' else ''
sources=[*sorted((root/'sdk/src').rglob('*.java')),*sorted((root/'src').rglob('*.java')),root/'tests/NativePhoneTest.java']
with tempfile.TemporaryDirectory(prefix='native-phone-test-') as classes:
    subprocess.run([str(java/('javac'+exe)),'--release','8','-encoding','UTF-8','-cp',str(platforms[-1]),'-d',classes,*map(str,sources)],check=True)
    subprocess.run([str(java/('java'+exe)),'-ea','-cp',os.pathsep.join([classes,str(platforms[-1])]),'de.eibelucas.kiosksip.nativephone.NativePhoneTest'],check=True)
