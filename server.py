#! /usr/bin/env python
# SPDT-1: Create secure default Python webhook server.

import os

from sapiopycommons.general.time_util import TimeUtil
from sapiopycommons.webhook.webhook_handlers import CommonsWebhookHandler
from sapiopylib.rest.WebhookService import WebhookConfiguration, WebhookServerFactory
from sapiopylib.rest.pojo.webhook.WebhookContext import SapioWebhookContext
from sapiopylib.rest.pojo.webhook.WebhookResult import SapioWebhookResult
from waitress import serve
from webhooks.SelectionList.BillableAccount import BillableAccount
from webhooks.SelectionList.BillableAccountCopy import BillableAccountCopy
from webhooks.SelectionList.RequestedForUser import RequestedForUser
from webhooks.TableToolbar.CreateRequest import CreateRequest
from webhooks.TableToolbar.CreateCloneAndVectorRequest import CreateCloneAndVectorRequest

# TimeUtil is a utility provided by sapiopycommons for handling timezone conversions.
# This call sets up a default timezone that all calls to TimeUtil will use unless otherwise
# specified by the input parameters. This would typically be the timezone that matches the
# customer's location.
TimeUtil.set_default_timezone("UTC")

# SPDT-1: verify_sapio_cert should be true by default.
# verify_sapio_cert should be true by default. This means that the webhook server will verify the certifications
# of the system that it is interacting with.
# debug should be false by default, as having a deployed server in debug mode can be unsafe.
# client_timeout_seconds is the default amount of time that the webhook server will wait for a response from the
# Sapio server when making requests. This can be changed here to affect all registered endpoints, or changed on a
# per-endpoint basis by changing the webhook handler's client_timeout_seconds class variable.
config: WebhookConfiguration = WebhookConfiguration(verify_sapio_cert=True, debug=False, client_timeout_seconds=600)

# SPDT-1: If the insecure environment variable is true, set verify_sapio_cert to false.
# IMPORTANT NOTICE: This should never be true for deployed code. It should only be necessary to set this to false when
# developing on a local Sapio system that does not have valid certs (but does not need them because it is not on the
# wider internet). We suggest using environment variables instead of changing the values in the server file directly to
# avoid unintentionally deploying unsafe changes.
if os.environ.get('SapioWebhooksInsecure') == "True":
    config.verify_sapio_cert = False


class Ping(CommonsWebhookHandler):
    """
    A simple webhook that returns the time as a toaster popup when invoked from the system.
    Intended to be placed on the main toolbar to verify that the webhook server is running and
    is able to be access by the system.
    """
    def execute(self, context: SapioWebhookContext) -> SapioWebhookResult:
        now: str = TimeUtil.now_in_format("%H:%M:%S")
        return SapioWebhookResult(True, f"The webhook server is active.\nServer time: {now}.")


# You can call this webhook from the system by calling [base-url]/ping, where [base-url]
# is the base URL macro you configured in your system for your webhook server. New classes
# can be added to folders within this project.
config.register('/billable_accounts', BillableAccount)
config.register('/billable_accounts_copy', BillableAccountCopy)
config.register('/requested_for_user', RequestedForUser)
config.register('/create_request', CreateRequest)
config.register('/create_clone_and_vector_request', CreateCloneAndVectorRequest)

# Register new endpoints here:
# config.register('/endpoint', ClassName)
app = WebhookServerFactory.configure_flask_app(app=None, config=config)


# Health check route. This is required for deployments to services which use
# a specific endpoint to check the health of the webhook server.
@app.route("/ping")
def health_check():
    return "Alive!"
# Return the README.md file as a html file for the homepage of the webhook
@app.route('/')
def http_root():
    import markdown
    with open('README.md') as readme_file:
        readme_html = markdown.markdown(readme_file.read())
    output = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
</head>
<body>
"""
    output += readme_html
    output += "</body></html>"
    return output


# Run this to run a local server. The app you are using will need a way to access this
# port on your local host in order to interact with the webhook server. This can be achieved
# by using a service such as ngrok, or using your device's IP on an internal network as the webhook URL.
# A Docker image built using the provided Dockerfile will instead use Gunicorn as the entry point,
# meaning that changes to the below code will not affect a deployed webhook server.
if __name__ == '__main__':
    host = "0.0.0.0"
    port = 8090
    # You can set this environment variable to true on your local machine
    # to change this behavior when you run the server locally.
    if os.environ.get('SapioWebhooksDebug') == "True":
        app.run(host=host, port=port, debug=True)
    else:
        serve(app, host=host, port=port)
