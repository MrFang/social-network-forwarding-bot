from db import connection
import bottle
import psycopg2.extras

server = bottle.default_app()


@server.route('/vk_auth')
def finish_register():
    if len(bottle.request.query) == 0:
        # Vk sends params in url hash so we need to move it to query params
        return '''
        <!DOCTYPE html>
        <html>
            <head>
                <script>
                    fetch(`${window.location.origin}${window.location.pathname}?${window.location.hash.slice(1)}`)
                </script>
            </head>
            <body>
                Registration is complete
            </body>
        </html>
        '''
    else:
        state = bottle.request.query.state
        access_token = bottle.request.query.access_token
        [channel_id, user_id] = [int(i) for i in state.split('_')]
        with connection as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute('''
                SELECT id
                FROM channel_to_vk
                WHERE channel_id = %s AND issued_by = %s
                ORDER BY issued_at DESC
                LIMIT 1
            ''', (channel_id, user_id))
            record_id = cur.fetchone()['id']

            cur.execute('''
                UPDATE channel_to_vk
                SET vk_access_token = %s
                WHERE id = %s
            ''', (access_token, record_id))
