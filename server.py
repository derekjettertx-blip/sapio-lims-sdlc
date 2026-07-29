from sapiopylib.rest.WebhookService import WebhookConfiguration, WebhookServerFactory
from waitress import serve
import os

from webhooks.pre_save import sample_pre_save_validation_hook

# Create the Sapio webhook configuration that will handle the processing of
config: WebhookConfiguration = WebhookConfiguration(verify_sapio_cert=True, debug=True, client_timeout_seconds=1200)
config.register('/get_build_info', sample_pre_save_validation_hook)

# Create a flask application with the Sapio Webhook configuration
app = WebhookServerFactory.configure_flask_app(app=None, config=config)


# Return the README.md file as a html file for the homepage of the webhook
@app.route('/')
def http_root():
    import markdown
    readme_file = open(os.path.join(os.path.dirname(__file__), 'README.md'))
    output = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style type="text/css">
"""
    output += open(os.path.join(os.path.dirname(__file__), 'doc/avenir-white.css')).read()
    output += "</style></head><body>"
    output += markdown.markdown(readme_file.read())
    output += "</body></html>"
    return output


# This method is a health check for render.com to use to know when the python process is alive and is healthy
@app.route('/health_check')
def health_check():
    return 'Alive'


# UNENCRYPTED! This should not be used in production. You should give the "app" a ssl_context or set up a reverse-proxy.
serve(app, host="0.0.0.0", port=8080)