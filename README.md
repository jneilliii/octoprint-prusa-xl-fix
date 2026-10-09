# Prusa XL/XL+  Fix 1.0

Adds a tool parameter (default T0) to the `M106, M107, M201, M203 and M221` command when no explicit tool parameter exists, to work around the change that was introduced with Prusa XL/XL+ Buddy 6.10.x firmware. 

The queuing hook runs before OctoPrint adds serial line numbers and checksums. Original uploaded files are unchanged. Direct printing from printer storage is not covered. Unusual pre-framed, multiline, quoted or malformed commands are passed through unchanged.

Run automated tests from the source folder with `python -B -m unittest discover -s tests -v`. Tests use host doubles; live printer validation is still required.
