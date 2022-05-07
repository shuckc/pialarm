from aiohttp import web
import aiohttp_jinja2
import json
import jinja2

@aiohttp_jinja2.template('index.jinja2')
async def handle_index(request):
    panel = request.app["panel"]
    return {'panel': panel.decode()}

async def handle_json(request):
    text = "Config\n\n"
    panel = request.app["panel"]
    text = text + json.dumps(panel.decode(), indent=4)
    return web.Response(text=text)

@aiohttp_jinja2.template('rich.jinja2')
async def handle_rich(request):
    text = "Config\n\n"
    panel = request.app["panel"]
    return {'panel': panel.decode()}

def get_web_app(mem, io, args, panel):
    app = web.Application()
    app.add_routes([
        web.get("/", handle_index),
        web.get("/json", handle_json),
        web.get("/rich", handle_rich)
    ])
    aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader('templates'))

    app["panel"] = panel
    app["args"] = args
    return app


async def start_server(mem, io, args, panel):
    app = get_web_app(mem, io, args, panel)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "", args.web_port)
    await site.start()
    print(f"Serving web interface on {args.web_port}")
    return runner


if __name__ == "__main__":
    web.run_app(get_web_app())
