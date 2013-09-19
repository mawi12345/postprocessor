# postprocessor

transform ProE/CLFiles (Creo) to G-Codes

## usage

```
usage: postprocessor.py [-h] [-v] [-r] [-f] [-c] [--file-extension extension]
                        [--num-steps N] [--num-start N] [-o FILE]
                        file

transform Pro/CLfile files to G-Codes

positional arguments:
  file                  Pro/CLfile Version 2.0

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  -r, --recursive       recursive search for Pro/CLfiles
  -f, --force           overwrite genartated G-Code files
  -c, --no-comments     do not include comments
  --file-extension extension
                        set the file extension (default: din)
  --num-steps N         step size for line numbers (default: 1)
  --num-start N         start line number (default: 1)
  -o FILE, --output FILE
                        DIN G-Codes file

Samples:

  -> transform a single file:
  postprocessor -o programm.din programm.ncl.1
   
  -> tranform all files in directory "cncfiles"
  postprocessor cncfiles
  
  -> transform a single file to stout:
  postprocessor programm.ncl.1
```