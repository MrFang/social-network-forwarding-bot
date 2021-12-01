import bottle

server = bottle.default_app()


# Currently not working. Probably delete later
@server.route('/')
def index():
    pass
