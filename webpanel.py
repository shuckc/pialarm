from aiohttp import web
import json


async def handle(request):
    text = "Config\n\n"
    panel = request.app["panel"]
    text = text + json.dumps(panel.decode(), indent=4)
    return web.Response(text=text)


def get_web_app(mem, io, args, panel):
    app = web.Application()
    app.add_routes([web.get("/", handle), web.get("/{name}", handle)])

    app["panel"] = panel
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
