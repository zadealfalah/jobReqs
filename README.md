To get chrome_headless.zip must open up windows terminal
wsl -d Ubuntu
cd ........ To get to jobReqs folder
./lambda_layer.sh


Currently creates a layer that works on py3.7 but 3.7 will be out of date soon.  Need to see how to make it work with more up-to-date python versions.

Also 3.7 can throw:
Error in Imports: urllib3 v2.0 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips 26 Jan 2017'

Seems like lambci/lambda has a build-python3.8 version so re-package chrome_headless, re-upload the layer, and re-make the function to test.

Doesn't work, Lambda issue, urllib3 v2.0 requires >=py3.10, which lambda can't do.  Need to figure out where urllib3v2.0 is being downloaded at and lower it, or use ec2 w/ a docker image for using the weird setup I need as-is.