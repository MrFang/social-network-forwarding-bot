def get_all_connections(cur, user_id):
    cur.execute("SELECT * FROM channel_to_vk WHERE issued_by = %s",
                (user_id, )
                )
    data = cur.fetchall()
    message = "Your active links are: \n"
    if len(data) == 0:
        return False
    for num, link in enumerate(data):
        message += f"{num+1}) " \
            "{link['channel_id']} - {link['vk_access_token']}\n"
    return message


def add_new_line(cur, channel_id, vk_access_token, user_id):
    cur.execute('''
        INSERT INTO channel_to_vk
        (channel_id, vk_access_token, issued_by) VALUES
        (%s, %s, %s)''', (channel_id, vk_access_token, user_id))
