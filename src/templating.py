from fastapi.templating import Jinja2Templates

from .env import APP_VERSION, RELEASE_URL

# Single shared instance so the version globals are set once and every template
# response (across routers) can render the footer.
templates = Jinja2Templates(directory="src/templates")
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["release_url"] = RELEASE_URL
