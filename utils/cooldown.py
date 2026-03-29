import time

cooldowns = {}


def check(user, seconds):

    now = time.time()

    if user in cooldowns:

        remain = seconds - (now - cooldowns[user])

        if remain > 0:
            return int(remain)

    return 0


def update(user):
    cooldowns[user] = time.time()
