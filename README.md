### Stowers POC by EPAM
This project aims to check some critical requirements feasibility in Sapio application for Stowers institute. All rights reserved to EPAM systems. 

### Prerequisites
Install the following:
* [Python 3.14](https://www.python.org)
* The Python packages in requirements.txt
  * For sapiopylib and sapiopycommons, visit our PyPI pages (linked below) to ensure that you are grabbing the 
    latest compatible library versions for your Sapio system's version.

Sapio utilizes [PyCharm](https://www.jetbrains.com/pycharm/) as our Python IDE. Some comments will include tips that 
reference key shortcuts or behaviors in PyCharm. Behavior may be different if you are using another IDE.

### Testing Locally
Webhooks can be tested locally by spinning up a webhook server within your IDE. Run the server.py file to start a
webhook server on your localhost port defined by the "port" variable at the bottom of the file.
In order to have Sapio make requests to your defined webhook endpoints, you will need to make your localhost port
available to the Sapio server.

If your local machine is on a separate network, you will need to use a tunneling/port forwarding service to make your
webhooks available to the Sapio server. Epam developers currently utilize [cloudflared] for this
purpose. Once installed, you can run `cloudflared tunnel --url http://localhost:8090` from a terminal to start an cloudflared instance. The final value in
the command is the port that the cloudflared instance will make available, which should match the port in the server.py file.
Once the cloudflared tunnel is ready, copy the tunneled url and configure the same as webhook base endpoint in Sapio.

If your local machine is on the same network as the Sapio server, contact your IT team about making your local device's
IP available to the Sapio server.

### Deploying Webhooks
This project contains a Dockerfile that can be used to build this project into a Docker image. This Docker image can 
then be deployed to your service of choice to run a webhook server with a permanent URL that the Sapio system can 
access.

### Resources

* [sapiopylib](https://pypi.org/project/sapiopylib/): Our PyPI page for all sapiopylib releases.
* [sapiopycommons](https://pypi.org/project/sapiopycommons/): Our PyPI page for all sapiopycommons releases.
* [Sapio Py Tutorials](https://github.com/sapiosciences/sapio-py-tutorials): Our GitHub repository containing further 
information and examples for sapiopylib.