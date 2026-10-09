---
layout: plugin
    
id: PrusaXLFix
title: Prusa XL/XL+ Fix
description: A fix for an incompatibility introduced with Prusa firmware 6.10.x and later
authors:
- Greg Anuzelli
license: MIT License
    
date: 2026-10-06
    
homepage: your plugin's homepage URL
source: your plugin's source repository URL
archive: archive link to install your plugin via pip, e.g. from github: https://github.com/username/repository/archive/master.zip
    
    
tags:
- prusa
        
    
compatibility:    
  octoprint:
  - 1.11.0
    
   
  os:
  - linux
  - windows
  - macos
  - freebsd
    
  python: ">=3,<4" # Python 3 only
    
- ai-developed 
    
---
Prusa firmware v6.10.x for the XL and XL+ printers introduced an incompatibility with Octorprint. Specifically the the `M106/M107/M201/M203/M221` commands now want a valid tool to be specified. See [this GitHub issue] (https://github.com/prusa3d/Prusa-Firmware-Buddy/issues/5449#top) for more info. This is (probably) a temporary fix until the bug in the firmware is corrected, assuming it is in-fact a bug. 